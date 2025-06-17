const mongoose = require('mongoose');

const OrgSchema = new mongoose.Schema({
    org_id: { type: String, required: true, unique: true },
    org_pub_sub_topic_name: { type: String, required: true },
    org_metadata: { type: mongoose.Schema.Types.Mixed, default: {} },
    org_type: { type: String, required: true }
}, {
    timestamps: true
});

const Organization = mongoose.model('Organization', OrgSchema);

module.exports = Organization;
