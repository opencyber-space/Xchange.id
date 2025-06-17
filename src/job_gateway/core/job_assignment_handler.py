import os
import logging

from .task_registry_client import TasksRegistryClient
from .task_registry_listing_client import TasksDBRegistryClient
from .filter_converter import query_translator
from .org_interface import OrgJobPusher

logger = logging.getLogger("MainLogger")


def new_task_registry_client(api_url):
    return TasksRegistryClient(api_url)


def new_task_db_registry_client():
    task_db_url = os.getenv("TASK_DB_REGISTRY_SERVER_URL")
    if not task_db_url:
        raise ValueError(
            "Environment variable TASK_DB_REGISTRY_SERVER_URL is not set.")
    return TasksDBRegistryClient(task_db_url)


class AssignmentHelper:

    def __init__(self, job_data: dict, assignment_data: dict) -> None:
        self.job_data = job_data
        self.assignment_data = assignment_data

    def _send_task_to_registry(self, task_registry_data, job_data: dict):
        try:
            task_db_url = task_registry_data['task_listing_db_api_url']

            # Make API request:
            task_db_api = new_task_registry_client(task_db_url)
            task_db_api.create_job(job_data)

            logger.info(f"Sent task to registry: {task_db_url}")

            return task_registry_data['task_listing_db_id']

        except Exception as e:
            logger.error(
                f"Failed to send task to registry: {e}", exc_info=True)
            raise RuntimeError("Error sending task to registry") from e

    def determine_path(self):
        try:
            assignment_type = self.assignment_data.get('assignmentType')
            if assignment_type == "open":
                filter_query = self.assignment_data.get('filterQuery')
                tasks_registry_id = self.assignment_data.get('tasksRegistryId')

                if filter_query:
                    translated_query = query_translator(filter_query)

                    tasks_db_client = new_task_db_registry_client()
                    result = tasks_db_client.query_tasks(translated_query)

                    if not result:
                        raise ValueError(
                            "No tasks found matching the filter query.")
                    if len(result) > 1:
                        raise ValueError(
                            "Filter query returned multiple matching tasks registries.")

                    task_data = result[0]
                    return self._send_task_to_registry(task_data, self.job_data)

                elif tasks_registry_id:
                    tasks_db_client = new_task_db_registry_client()
                    task_data = tasks_db_client.get_task_by_id(
                        tasks_registry_id)
                    return self._send_task_to_registry(task_data, self.job_data)
                else:
                    raise ValueError(
                        "Either 'filterQuery' or 'tasksRegistryId' must be provided for 'open' assignment.")
            else:
                org_id = self.assignment_data.get('org_id')
                pusher = OrgJobPusher(nats_url=os.getenv("ORG_SUBSCRIBERS_NATS_URL"), topic=org_id)
                pusher.push(message_dict=self.job_data)

                return org_id

        except Exception as e:
            logger.error(f"Error determining path: {e}", exc_info=True)
            raise RuntimeError(
                "Failed to determine task assignment path") from e
