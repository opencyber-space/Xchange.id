import logging
import threading
import time
from typing import Any, Dict, List

from .bidding_client import BiddingClient
from .crud import ExchangeSubjectsCRUD, ExchangeTasksCRUD
from .functions import FunctionCaller
from .schema import ExchangeTasks
from .subject_task import SubjectTask

logger = logging.getLogger(__name__)

DIRECT = "direct"
FUNCTION = "function"
OPEN = "open"
BIDDING = "bidding"

BID_JOB_MODE_CLOSED = "closed"
BID_JOB_MODE_OPEN = "open"
# Fixed roster like "closed", but Orcade also auto-tags each named subject
# (subject::<id>) so it's discoverable by tag. Needs no special handling here
# since only "open" skips subject-pool resolution below.
BID_JOB_MODE_MIXED = "mixed"


class TaskAssignmentService:
    def __init__(
        self,
        *,
        tasks_crud: ExchangeTasksCRUD,
        subjects_crud: ExchangeSubjectsCRUD,
        subject_task: SubjectTask,
        function_caller: FunctionCaller,
        bidding_client: BiddingClient,
        bid_poll_interval: float = 5.0,
    ):
        self._tasks_crud = tasks_crud
        self._subjects_crud = subjects_crud
        self._subject_task = subject_task
        self._function_caller = function_caller
        self._bidding_client = bidding_client
        self._bid_poll_interval = bid_poll_interval

    def assign(self, task: ExchangeTasks) -> None:
        if task.task_assignment_type == DIRECT:
            self._handle_direct(task)
        elif task.task_assignment_type == FUNCTION:
            self._handle_function(task)
        elif task.task_assignment_type == OPEN:
            self._handle_open(task)
        elif task.task_assignment_type == BIDDING:
            self._handle_bidding(task)
        else:
            raise ValueError(f"Unsupported task_assignment_type: {task.task_assignment_type}")

    def _handle_direct(self, task: ExchangeTasks) -> None:
        assignment = task.task_metadata.get("task_assignment", {})
        subject_id = assignment["subject_id"]

        threading.Thread(
            target=self._submit_and_save,
            args=(task, subject_id),
            daemon=True,
        ).start()

    def _handle_function(self, task: ExchangeTasks) -> None:
        assignment = task.task_metadata.get("task_assignment", {})
        function_id = assignment["function_id"]
        parameters = assignment.get("parameters", {})

        subjects = self._subjects_crud.list()
        result = self._function_caller.call(
            function_id=function_id,
            input_data={
                "task_data": task.task_data,
                "subjects": [s.to_dict() for s in subjects],
            },
            parameters=parameters,
        )

        selected_subject_id = result.get("selected_subject_id")
        if not selected_subject_id:
            raise ValueError(f"Function '{function_id}' did not return a 'selected_subject_id'.")

        self._tasks_crud.update(task.task_id, {"task_assignment_status": "assigned"})

        threading.Thread(
            target=self._submit_and_save,
            args=(task, selected_subject_id),
            daemon=True,
        ).start()

    def _handle_open(self, task: ExchangeTasks) -> None:
        threading.Thread(
            target=self._run_open_assignment,
            args=(task,),
            daemon=True,
        ).start()

    def _run_open_assignment(self, task: ExchangeTasks) -> None:
        subjects = self._subjects_crud.list()

        for subject in subjects:
            if not subject.task_evaluation_function:
                continue

            try:
                result = self._function_caller.call(
                    function_id=subject.task_evaluation_function,
                    input_data={
                        "task_data": task.task_data,
                        "subject": subject.to_dict(),
                    },
                )
            except Exception as e:
                logger.error(
                    f"Task evaluation function '{subject.task_evaluation_function}' failed "
                    f"for subject '{subject.subject_id}' on task '{task.task_id}': {e}"
                )
                continue

            if result.get("status") == "accepted":
                self._tasks_crud.update(task.task_id, {"task_assignment_status": "assigned"})
                self._submit_and_save(task, subject.subject_id)
                return

        logger.info(f"No subject accepted task '{task.task_id}'.")
        self._tasks_crud.update(
            task.task_id,
            {
                "task_assignment_status": "rejected",
                "task_output": {"error": "no subject accepted the task"},
            },
        )

    def _handle_bidding(self, task: ExchangeTasks) -> None:
        assignment = task.task_metadata.get("task_assignment", {})
        if assignment.get("bid_job_mode", BID_JOB_MODE_CLOSED) == BID_JOB_MODE_OPEN and (
            assignment.get("bid_job_subject_ids") or assignment.get("topics")
        ):
            raise ValueError(
                "Open-mode bidding must not specify bid_job_subject_ids or topics; "
                "subjects apply to the job themselves."
            )

        threading.Thread(
            target=self._run_bidding,
            args=(task,),
            daemon=True,
        ).start()

    def _run_bidding(self, task: ExchangeTasks) -> None:
        assignment = task.task_metadata.get("task_assignment", {})
        is_open = assignment.get("bid_job_mode", BID_JOB_MODE_CLOSED) == BID_JOB_MODE_OPEN

        subject_ids: List[str] = []
        if not is_open:
            explicit_subject_ids = assignment.get("bid_job_subject_ids") or []
            topics = assignment.get("topics")
            topic_subject_ids = (
                [s.subject_id for s in self._subjects_crud.list({"topics": {"$in": topics}})]
                if topics
                else []
            )

            if explicit_subject_ids or topic_subject_ids:
                subject_ids = list(dict.fromkeys(explicit_subject_ids + topic_subject_ids))
            else:
                subject_ids = [s.subject_id for s in self._subjects_crud.list()]

        try:
            bid_job = self._bidding_client.create_bid_job(
                bid_job_metadata=assignment.get("bid_job_metadata", {}),
                bid_job_description=assignment.get("bid_job_description", {}),
                bid_job_name=assignment.get("bid_job_name", {}),
                bid_job_evaluator_id=assignment["bid_job_evaluator_id"],
                bid_job_pqt_id=assignment.get("bid_job_pqt_id", ""),
                bid_job_tie_id=assignment.get("bid_job_tie_id", ""),
                bid_job_creator_id=assignment.get("bid_job_creator_id", ""),
                bid_job_subject_ids=subject_ids,
                bid_job_mode=assignment.get("bid_job_mode", BID_JOB_MODE_CLOSED),
                bid_job_max_subjects=assignment.get("bid_job_max_subjects"),
                bid_job_max_time=assignment.get("bid_job_max_time"),
                bid_job_tags=assignment.get("bid_job_tags", []),
            )
        except Exception as e:
            logger.error(f"Failed to create bid job for task '{task.task_id}': {e}")
            self._tasks_crud.update(
                task.task_id,
                {"task_assignment_status": "failed", "task_output": {"error": str(e)}},
            )
            return

        bid_job_id = bid_job["bid_job_id"]
        self._tasks_crud.update(
            task.task_id,
            {"task_metadata.bid_job_id": bid_job_id, "task_assignment_status": "bidding"},
        )

        while True:
            try:
                task_results = self._bidding_client.get_task_results(bid_job_id)
                winner_result = next(
                    (r for r in task_results if r.get("task_type") == "bid_winner"), None
                )
                no_applicants = (
                    winner_result is None
                    and is_open
                    and self._open_job_closed_without_applicants(bid_job_id)
                )
            except Exception as e:
                logger.error(
                    f"Failed to poll bid job '{bid_job_id}' for task '{task.task_id}': {e}"
                )
                time.sleep(self._bid_poll_interval)
                continue

            if winner_result is not None:
                self._tasks_crud.update(
                    task.task_id,
                    {
                        "task_output": winner_result["task_result"],
                        "task_assignment_status": "completed",
                    },
                )
                return

            if no_applicants:
                self._tasks_crud.update(
                    task.task_id,
                    {
                        "task_assignment_status": "rejected",
                        "task_output": {"error": "no subject applied to the bid job"},
                    },
                )
                return

            time.sleep(self._bid_poll_interval)

    def _open_job_closed_without_applicants(self, bid_job_id: str) -> bool:
        job = self._bidding_client.get_bid_job(bid_job_id)
        if job.get("bid_job_status") != "closed":
            return False
        return not self._bidding_client.get_bids(bid_job_id)

    def _submit_and_save(self, task: ExchangeTasks, subject_id: str) -> None:
        try:
            result: Dict[str, Any] = self._subject_task.submit_and_wait(
                subject_id=subject_id,
                session_id=task.task_id,
                task_id=task.task_id,
                task_data=task.task_data,
            )
            self._tasks_crud.update(
                task.task_id,
                {"task_output": result, "task_assignment_status": "completed"},
            )
        except Exception as e:
            logger.error(
                f"Failed to submit task '{task.task_id}' to subject '{subject_id}': {e}"
            )
            self._tasks_crud.update(
                task.task_id,
                {"task_assignment_status": "failed", "task_output": {"error": str(e)}},
            )
