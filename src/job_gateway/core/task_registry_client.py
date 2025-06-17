import requests


class TasksRegistryClient:
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

    def create_job(self, job_data):
        try:
            url = f"{self.base_url}/jobs"
            response = requests.post(url, json=job_data)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to create job: {str(e)}")

    def get_job(self, job_id):
        try:
            url = f"{self.base_url}/jobs/{job_id}"
            response = requests.get(url)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to get job: {str(e)}")

    def update_job(self, job_id, update_data):
        try:
            url = f"{self.base_url}/jobs/{job_id}"
            response = requests.put(url, json=update_data)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to update job: {str(e)}")

    def delete_job(self, job_id):
        try:
            url = f"{self.base_url}/jobs/{job_id}"
            response = requests.delete(url)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to delete job: {str(e)}")

    def query_jobs(self, query_data):
        try:
            url = f"{self.base_url}/jobs/query"
            response = requests.post(url, json=query_data)
            return self._handle_response(response)
        except Exception as e:
            raise Exception(f"Failed to query jobs: {str(e)}")
