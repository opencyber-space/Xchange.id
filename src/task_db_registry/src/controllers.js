const axios = require('axios');
const mongoose = require('mongoose');
const TaskListing = require('./schema.js');


class TaskListingSchemaCRUD {
    constructor() {
        const dbHost = process.env.DB_HOST_URL;
        if (!dbHost) throw new Error('DB_HOST_URL is not defined');
        mongoose.connect(dbHost, { useNewUrlParser: true, useUnifiedTopology: true });
        this.model = TaskListing;
    }

    async check_registry_connection(apiUrl) {
        try {
            const response = await axios.get(`${apiUrl}/health`);
            if (response.status === 200) {
                console.log(`Connection to ${apiUrl} is healthy.`);
                return true;
            } else {
                throw new Error(`Health check failed with status code ${response.status}`);
            }
        } catch (error) {
            throw new Error(`Error connecting to ${apiUrl}: ${error.message}`);
        }
    }

    async create(data) {
        try {

            const { task_listing_db_api_url } = data;
            if (!task_listing_db_api_url) {
                throw new Error('task_listing_db_api_url is required');
            }

            await this.check_registry_connection(task_listing_db_api_url);

            const result = await this.model.create(data);
            console.log('Document created:', result);
            return result;
        } catch (error) {
            console.error('Error creating document:', error);
            throw error;
        }
    }

    async read(filter = {}) {
        try {
            const result = await this.model.find(filter);
            console.log('Documents retrieved:', result);
            return result;
        } catch (error) {
            console.error('Error reading documents:', error);
            throw error;
        }
    }

    async update(filter, updateData) {
        try {
            const result = await this.model.updateMany(filter, updateData);
            console.log('Documents updated:', result);
            return result;
        } catch (error) {
            console.error('Error updating documents:', error);
            throw error;
        }
    }

    async delete(filter) {
        try {
            const result = await this.model.deleteMany(filter);
            console.log('Documents deleted:', result);
            return result;
        } catch (error) {
            console.error('Error deleting documents:', error);
            throw error;
        }
    }

    async getById(taskListingDbId) {
        try {
            const result = await this.model.findOne({ task_listing_db_id: taskListingDbId });
            console.log('Document retrieved by ID:', result);
            return result;
        } catch (error) {
            console.error('Error retrieving document by ID:', error);
            throw error;
        }
    }

    async query(query) {
        try {
            const result = await this.model.find(query);
            return result;
        } catch (error) {
            console.error('Error reading documents:', error);
            throw error;
        }
    }
}

module.exports = TaskListingSchemaCRUD;
