import requests


class TasksDBRegistryClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def _handle_response(self, response):
        try:
            response_data = response.json()
            if not response_data.get('success'):
                raise Exception(response_data.get(
                    'message', 'An error occurred'))
            return response_data.get('data')
        except Exception as e:
            raise Exception(f"Failed to process response: {str(e)}")

    def create_task(self, task_data):
        try:
            url = f"{self.base_url}/api/task-listings/create"
            response = requests.post(url, json=task_data)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to create task: {str(e)}")

    def read_tasks(self, query_params=None):
        try:
            url = f"{self.base_url}/api/task-listings/read"
            response = requests.get(url, params=query_params)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to read tasks: {str(e)}")

    def update_task(self, filter_data, update_data):
        try:
            url = f"{self.base_url}/api/task-listings/update"
            payload = {"filter": filter_data, "updateData": update_data}
            response = requests.put(url, json=payload)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to update task: {str(e)}")

    def delete_task(self, filter_data):
        try:
            url = f"{self.base_url}/api/task-listings/delete"
            payload = {"filter": filter_data}
            response = requests.delete(url, json=payload)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to delete task: {str(e)}")

    def get_task_by_id(self, task_id):
        try:
            url = f"{self.base_url}/api/task-listings/getById/{task_id}"
            response = requests.get(url)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to get task by ID: {str(e)}")

    def query_tasks(self, query_data):
        try:
            url = f"{self.base_url}/api/task-listings/query"
            response = requests.post(url, json=query_data)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to query tasks: {str(e)}")
