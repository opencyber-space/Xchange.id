import os
import logging
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from flask import Flask, request, jsonify

from .bidding_client import BiddingClient
from .crud import ExchangeSubjectsCRUD, ExchangeTasksCRUD
from .functions import FunctionCaller
from .schema import ExchangeSubjects, ExchangeTasks
from .subject_task import SubjectTask
from .task_assignment import TaskAssignmentService

logger = logging.getLogger(__name__)

tasks_crud = ExchangeTasksCRUD()
subjects_crud = ExchangeSubjectsCRUD()
subject_task = SubjectTask()

function_caller = FunctionCaller(
    executor_id=os.getenv("EXECUTOR_ID", "xchange-executor"),
    unique_parameter=os.getenv("UNIQUE_PARAMETER", "xchange"),
    num_workers=int(os.getenv("NUM_WORKERS", "8")),
)
bidding_client = BiddingClient()

task_assignment_service = TaskAssignmentService(
    tasks_crud=tasks_crud,
    subjects_crud=subjects_crud,
    subject_task=subject_task,
    function_caller=function_caller,
    bidding_client=bidding_client,
    bid_poll_interval=float(os.getenv("BID_POLL_INTERVAL", "5")),
)

app = Flask(__name__)


def _json_response(ok: bool, data: Any = None, error: str = None, status: int = 200):
    payload: Dict[str, Any] = {"ok": ok}
    if ok:
        if data is not None:
            payload["data"] = data
    else:
        payload["error"] = error or "unknown_error"
    return jsonify(payload), status


# ------------------ TASKS ------------------

@app.post("/tasks")
def submit_task():
    body = request.get_json(silent=True) or {}
    try:
        task_assignment_type = body["task_assignment_type"]
        task_data = body["task_data"]
    except KeyError as e:
        return _json_response(False, error=f"Missing required field: {e}", status=400)

    task = ExchangeTasks(
        task_id=body.get("task_id") or str(uuid4()),
        task_assignment_type=task_assignment_type,
        task_data=task_data,
        task_assignment_status=body.get("task_assignment_status", "pending"),
        task_metadata=body.get("task_metadata", {}),
        taski_creation_time=datetime.utcnow(),
        task_output={},
    )

    try:
        tasks_crud.create(task)
    except Exception as e:
        logger.exception("submit_task failed to persist task")
        return _json_response(False, error=str(e), status=500)

    try:
        task_assignment_service.assign(task)
    except Exception as e:
        logger.exception("submit_task failed to assign task")
        tasks_crud.update(
            task.task_id,
            {"task_assignment_status": "failed", "task_output": {"error": str(e)}},
        )
        return _json_response(False, error=str(e), status=400)

    return _json_response(True, task.to_dict(), status=201)


@app.get("/tasks/<task_id>")
def get_task(task_id: str):
    task = tasks_crud.get(task_id)
    if task is None:
        return _json_response(False, error="task not found", status=404)
    return _json_response(True, task.to_dict())


@app.get("/tasks/<task_id>/output")
def get_task_output(task_id: str):
    task = tasks_crud.get(task_id)
    if task is None:
        return _json_response(False, error="task not found", status=404)
    return _json_response(
        True,
        {
            "task_assignment_status": task.task_assignment_status,
            "task_output": task.task_output,
        },
    )


@app.post("/tasks/query")
def query_tasks():
    query = request.get_json(silent=True) or {}
    try:
        tasks = tasks_crud.list(query)
        return _json_response(True, [t.to_dict() for t in tasks])
    except Exception as e:
        logger.exception("query_tasks failed")
        return _json_response(False, error=str(e), status=400)


# ------------------ SUBJECTS ------------------

@app.post("/subjects")
def create_subject():
    body = request.get_json(silent=True) or {}
    subject = ExchangeSubjects(
        subject_id=body.get("subject_id") or str(uuid4()),
        subject_metadata=body.get("subject_metadata", {}),
        task_evaluation_function=body.get("task_evaluation_function", ""),
        subject_capabilities=body.get("subject_capabilities", {}),
        topics=body.get("topics", []),
    )
    try:
        subjects_crud.create(subject)
        return _json_response(True, subject.to_dict(), status=201)
    except Exception as e:
        logger.exception("create_subject failed")
        return _json_response(False, error=str(e), status=500)


@app.get("/subjects/<subject_id>")
def get_subject(subject_id: str):
    subject = subjects_crud.get(subject_id)
    if subject is None:
        return _json_response(False, error="subject not found", status=404)
    return _json_response(True, subject.to_dict())


@app.put("/subjects/<subject_id>")
@app.patch("/subjects/<subject_id>")
def update_subject(subject_id: str):
    body = request.get_json(silent=True) or {}
    if subjects_crud.get(subject_id) is None:
        return _json_response(False, error="subject not found", status=404)
    try:
        subjects_crud.update(subject_id, body)
        return _json_response(True, subjects_crud.get(subject_id).to_dict())
    except Exception as e:
        logger.exception("update_subject failed")
        return _json_response(False, error=str(e), status=500)


@app.delete("/subjects/<subject_id>")
def delete_subject(subject_id: str):
    try:
        deleted = subjects_crud.delete(subject_id)
        if not deleted:
            return _json_response(False, error="subject not found", status=404)
        return _json_response(True, {"deleted": True})
    except Exception as e:
        logger.exception("delete_subject failed")
        return _json_response(False, error=str(e), status=500)


@app.post("/subjects/query")
def query_subjects():
    query = request.get_json(silent=True) or {}
    try:
        subjects = subjects_crud.list(query)
        return _json_response(True, [s.to_dict() for s in subjects])
    except Exception as e:
        logger.exception("query_subjects failed")
        return _json_response(False, error=str(e), status=400)


def run_server():
    app.run(host="0.0.0.0", port=5000)
