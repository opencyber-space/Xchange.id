from flask import Flask, request, jsonify
import logging
import os
from .task_registry_listing_client import TasksDBRegistryClient
from .task_registry_client import TasksRegistryClient
from .mapper import job_handler, validate_inputs, map_to_db
from .filter_converter import query_translator

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def new_task_db_registry_client():
    task_db_url = os.getenv("TASK_DB_REGISTRY_SERVER_URL")
    if not task_db_url:
        raise ValueError(
            "Environment variable TASK_DB_REGISTRY_SERVER_URL is not set.")
    return TasksDBRegistryClient(task_db_url)


registry: TasksDBRegistryClient = new_task_db_registry_client()


def success_response(data):
    return jsonify({"success": True, "data": data})


def error_response(message):
    return jsonify({"success": False, "message": message}), 400


def log_request_response(endpoint, req_data, response):
    res_data = response.get_json() if response.is_json else response.get_data(as_text=True)
    logging.info(f"Endpoint: {endpoint}")
    logging.info(f"Request: {req_data}")
    logging.info(f"Response: {res_data}")
    logging.info(f"Endpoint: {endpoint}")
    logging.info(f"Request: {req_data}")
    logging.info(f"Response: {res_data}")


@app.route("/jobs/<string:task_registry_id>", methods=["POST"])
def create_job(task_registry_id):
    try:
        job_data = request.get_json()
        data = registry.get_task_by_id(task_registry_id)
        tasks_client = TasksRegistryClient(data['task_listing_db_api_url'])
        result = tasks_client.create_job(job_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/jobs/<string:task_registry_id>/<string:job_id>", methods=["GET"])
def get_job(task_registry_id, job_id):
    try:
        data = registry.get_task_by_id(task_registry_id)
        tasks_client = TasksRegistryClient(data['task_listing_db_api_url'])
        result = tasks_client.get_job(job_id)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


@app.route("/jobs/<string:task_registry_id>/<string:job_id>", methods=["PUT"])
def update_job(task_registry_id, job_id):
    try:
        update_data = request.get_json()
        data = registry.get_task_by_id(task_registry_id)
        tasks_client = TasksRegistryClient(data['task_listing_db_api_url'])
        result = tasks_client.update_job(job_id, update_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


@app.route("/jobs/<string:task_registry_id>/<string:job_id>", methods=["DELETE"])
def delete_job(task_registry_id, job_id):
    try:
        data = registry.get_task_by_id(task_registry_id)
        tasks_client = TasksRegistryClient(data['task_listing_db_api_url'])
        result = tasks_client.delete_job(job_id)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


@app.route("/jobs/<string:task_registry_id>/query", methods=["POST"])
def query_jobs(task_registry_id):
    try:
        query_data = request.get_json()
        data = registry.get_task_by_id(task_registry_id)
        tasks_client = TasksRegistryClient(data['task_listing_db_api_url'])
        result = tasks_client.query_jobs(query_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


@app.route("/registry/tasks", methods=["POST"])
def create_task():
    try:
        task_data = request.get_json()
        result = registry.create_task(task_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/registry/tasks", methods=["GET"])
def read_tasks():
    try:
        query_params = request.args.to_dict()
        result = registry.read_tasks(query_params)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/registry/tasks", methods=["PUT"])
def update_task():
    try:
        req_data = request.get_json()
        filter_data = req_data.get("filter")
        update_data = req_data.get("updateData")
        result = registry.update_task(filter_data, update_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/registry/tasks", methods=["DELETE"])
def delete_task():
    try:
        filter_data = request.get_json().get("filter")
        result = registry.delete_task(filter_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/registry/tasks/<string:task_id>", methods=["GET"])
def get_task_by_id(task_id):
    try:
        result = registry.get_task_by_id(task_id)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/registry/tasks/query", methods=["POST"])
def query_tasks():
    try:
        query_data = request.get_json()
        result = registry.query_tasks(query_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/job-submission/validate", methods=["POST"])
def validate_job_submission():
    try:
        input_data = request.get_json()
        result = validate_inputs(input_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/job-submission/map", methods=["POST"])
def map_job_submission():
    try:
        input_data = request.get_json()
        result = map_to_db(input_data)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/job-submission/submit", methods=["POST"])
def submit_job():
    try:
        inputs = request.get_json()
        result = job_handler(inputs)
        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))
    return response


@app.route("/search/task_registries", methods=["POST"])
def search_task_registries():
    try:
        query_data = request.get_json()
        data = registry.get_task_by_id(query_data.get("task_registry_id"))
        tasks_db_client = TasksDBRegistryClient(
            data["task_listing_db_api_url"])

        translated_query = query_translator(query_data["query"])
        result = tasks_db_client.query_tasks(translated_query)

        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


@app.route("/search/task_registry", methods=["POST"])
def search_task_registry():
    try:
        query_data = request.get_json()
        data = registry.get_task_by_id(query_data.get("task_registry_id"))
        tasks_client = TasksRegistryClient(data["task_listing_db_api_url"])

        translated_query = query_translator(query_data["query"])
        result = tasks_client.query_jobs(translated_query)

        response = success_response(result)
    except Exception as e:
        response = error_response(str(e))

    return response


def run_server():
    try:
        app.run(host='0.0.0.0', port=8000)
    except Exception as e:
        raise e
