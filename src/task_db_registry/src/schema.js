const mongoose = require('mongoose');

const TaskListingSchema = new mongoose.Schema({
    task_listing_db_id: { type: String, required: true },
    association_ids: { type: [String], required: true },
    task_listing_db_api_url: { type: String, required: true },
    search_metadata: { type: mongoose.Schema.Types.Mixed, required: true },
    task_db_characteristics_data: { type: mongoose.Schema.Types.Mixed, required: true },
    task_db_aggregate_performance_stats: { type: mongoose.Schema.Types.Mixed, required: true },
    collection_ids: { type: [String], required: true },
    accessibility_data: { type: mongoose.Schema.Types.Mixed, required: true }
});

module.exports = mongoose.model('TaskListing', TaskListingSchema);
