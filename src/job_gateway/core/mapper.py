import uuid
from .job_assignment_handler import AssignmentHelper


def validate_job_data(mapped_job_data):
    if not isinstance(mapped_job_data, dict):
        raise ValueError("Job data must be a dictionary.")

    # Validation for each field's data type
    if not isinstance(mapped_job_data.get("job_goal"), (dict, list)):
        raise ValueError("job_goal must be a dictionary or a list.")
    if not isinstance(mapped_job_data.get("job_objectives"), (list, type(None))):
        raise ValueError("job_objectives must be a list or None.")
    if not isinstance(mapped_job_data.get("job_priority_value"), (int, float)):
        raise ValueError("job_priority_value must be a number.")
    if mapped_job_data.get("job_completion_mode") not in ["single_window", "multi_window"]:
        raise ValueError(
            "job_completion_mode must be either 'single_window' or 'multi_window'.")
    if mapped_job_data.get("job_steerability_data") is not None and not isinstance(mapped_job_data.get("job_steerability_data"), (dict, list)):
        raise ValueError(
            "job_steerability_data must be a dictionary or a list.")
    if mapped_job_data.get("job_knowledge_base_reference_ptr") is not None and not isinstance(mapped_job_data.get("job_knowledge_base_reference_ptr"), (dict, list)):
        raise ValueError(
            "job_knowledge_base_reference_ptr must be a dictionary or a list.")
    if mapped_job_data.get("job_init_data") is not None and not isinstance(mapped_job_data.get("job_init_data"), (dict, list)):
        raise ValueError("job_init_data must be a dictionary or a list.")
    if not isinstance(mapped_job_data.get("submitted_by"), str):
        raise ValueError("submitted_by must be a string.")
    if mapped_job_data.get("job_sla_terms_json") is not None and not isinstance(mapped_job_data.get("job_sla_terms_json"), (dict, list)):
        raise ValueError("job_sla_terms_json must be a dictionary or a list.")
    if mapped_job_data.get("job_completion_multiwindow_timeline_map") is not None and not isinstance(mapped_job_data.get("job_completion_multiwindow_timeline_map"), (dict, list)):
        raise ValueError(
            "job_completion_multiwindow_timeline_map must be a dictionary or a list.")
    if not isinstance(mapped_job_data.get("job_output_template_id"), str):
        raise ValueError("job_output_template_id must be a string.")
    if mapped_job_data.get("job_output_convertor_dsl_id") is not None and not isinstance(mapped_job_data.get("job_output_convertor_dsl_id"), str):
        raise ValueError("job_output_convertor_dsl_id must be a string.")
    if not isinstance(mapped_job_data.get("job_verification_subject_ids"), list):
        raise ValueError("job_verification_subject_ids must be a list.")
    if mapped_job_data.get("job_verification_subject_parameters") is not None and not isinstance(mapped_job_data.get("job_verification_subject_parameters"), (dict, list)):
        raise ValueError(
            "job_verification_subject_parameters must be a dictionary or a list.")
    if mapped_job_data.get("job_output_verification_stages_map") is not None and not isinstance(mapped_job_data.get("job_output_verification_stages_map"), (dict, list)):
        raise ValueError(
            "job_output_verification_stages_map must be a dictionary or a list.")

    return True


def map_to_db_data(input_data):
    input_data_mapped = {
        "job_id": input_data.get("jobId", ""),
        "job_goal": input_data.get("jobGoal"),
        "job_objectives": input_data.get("jobObjectives"),
        "job_priority_value": input_data.get("jobPriorityValue"),
        "job_completion_mode": input_data.get("jobCompletionMode"),
        "job_steerability_data": input_data.get("jobSteerabilityData"),
        "job_knowledge_base_reference_ptr": input_data.get("jobKnowledgeBaseReferencePtr"),
        "job_init_data": input_data.get("jobInitData"),
        "submitted_by": input_data.get("submittedBy"),
        "job_sla_terms_json": input_data.get("jobSlaTermsJson"),
        "job_completion_multiwindow_timeline_map": input_data.get("jobCompletionMultiwindowTimelineMap"),
        "job_output_template_id": input_data.get("jobOutputTemplateId"),
        "job_output_convertor_dsl_id": input_data.get("jobOutputConvertorDslId"),
        "job_verification_subject_ids": input_data.get("jobVerificationSubjectIds"),
        "job_verification_subject_parameters": input_data.get("jobVerificationSubjectParameters"),
        "job_output_verification_stages_map": input_data.get("jobOutputVerificationStagesMap")
    }

    return input_data_mapped


def validate_inputs(input_data):
    try:
        mapped = map_to_db_data(input_data)
        validate_job_data(mapped)
        return mapped
    except Exception as e:
        raise e


def map_to_db(input_data):
    try:
        return map_to_db_data(input_data)
    except Exception as e:
        raise e


def job_handler(inputs):
    try:
        job_data = inputs['jobData']
        assignment_data = inputs['assignmentInfo']

        job_data['id'] = str(uuid.uuid4())

        mapped_job_data = map_to_db_data(job_data)

        is_valid = validate_job_data(mapped_job_data)

        if not is_valid:
            raise Exception("validation failed")

        assignment_helper = AssignmentHelper(job_data, assignment_data)
        task_db_listing_uri = assignment_helper.determine_path()

        return {"job_id": job_data['id'], "task_db_id": task_db_listing_uri}

    except Exception as e:
        raise e
