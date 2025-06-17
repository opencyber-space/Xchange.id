const mongoose = require('mongoose');
const OrgSchema = require('./schema_org');


class OrgAssociationsCRUD {
    constructor() {
        this.dbUrl = process.env.DB_HOST_URL;
        this.Organization = OrgSchema;
        await this.connect()
    }

    // Connect to the database
    async connect() {
        try {
            await mongoose.connect(this.dbUrl, { useNewUrlParser: true, useUnifiedTopology: true });
            console.log('Connected to MongoDB');
        } catch (error) {
            console.error('Database connection error:', error);
            throw new Error('Database connection failed');
        }
    }

    // Create an organization
    async create(orgData) {
        try {
            const org = new this.Organization(orgData);
            await org.save();
            console.log('Organization created:', org);
            return org;
        } catch (error) {
            console.error('Error creating organization:', error);
            throw new Error('Failed to create organization');
        }
    }

    // Read an organization by org_id
    async read(orgId) {
        try {
            const org = await this.Organization.findOne({ org_id: orgId });
            if (!org) {
                throw new Error('Organization not found');
            }
            return org;
        } catch (error) {
            console.error('Error reading organization:', error);
            throw new Error('Failed to read organization');
        }
    }

    // Update an organization
    async update(orgId, updatedData) {
        try {
            const org = await this.Organization.findOneAndUpdate(
                { org_id: orgId },
                updatedData,
                { new: true, runValidators: true }
            );
            if (!org) {
                throw new Error('Organization not found');
            }
            console.log('Organization updated:', org);
            return org;
        } catch (error) {
            console.error('Error updating organization:', error);
            throw new Error('Failed to update organization');
        }
    }

    // Delete an organization
    async delete(orgId) {
        try {
            const result = await this.Organization.deleteOne({ org_id: orgId });
            if (result.deletedCount === 0) {
                throw new Error('Organization not found');
            }
            console.log('Organization deleted');
            return result;
        } catch (error) {
            console.error('Error deleting organization:', error);
            throw new Error('Failed to delete organization');
        }
    }

    // Execute an arbitrary query
    async query(queryObj) {
        try {
            const result = await this.Organization.find(queryObj);
            return result;
        } catch (error) {
            console.error('Error executing query:', error);
            throw new Error('Failed to execute query');
        }
    }
}

module.exports = OrgAssociationsCRUD;
