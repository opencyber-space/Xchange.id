const mongoose = require('mongoose');

const JobCoreDataSchema = new mongoose.Schema({
    job_id: { type: String, required: true, unique: true },
    job_goal: { type: mongoose.Schema.Types.Mixed, required: true }, // Made Mixed
    job_objectives: { type: mongoose.Schema.Types.Mixed, required: true }, // Made Mixed
    job_priority_value: { type: Number, required: true },
    job_completion_mode: {
        type: String,
        enum: ["single_window", "multi_window"],
        required: true
    },
    job_steerability_data: { type: mongoose.Schema.Types.Mixed },
    job_knowledge_base_reference_ptr: { type: mongoose.Schema.Types.Mixed },
    job_init_data: { type: mongoose.Schema.Types.Mixed },
    submitted_by: { type: String, required: true },
    job_sla_terms_json: { type: mongoose.Schema.Types.Mixed }, // Flexible for JSON
    job_completion_multiwindow_timeline_map: { type: mongoose.Schema.Types.Mixed },
    job_output_template_id: { type: String, required: true },
    job_output_convertor_dsl_id: { type: String },
    job_verification_subject_ids: { type: [String] },
    job_verification_subject_parameters: { type: mongoose.Schema.Types.Mixed },
    job_output_verification_stages_map: { type: mongoose.Schema.Types.Mixed }
}, { timestamps: true });

module.exports = mongoose.model('JobCoreData', JobCoreDataSchema);
