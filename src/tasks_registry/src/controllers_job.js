const mongoose = require('mongoose');
const JobCoreData = require('./schema_job');

const redis = require('redis');


class JobCoreDataCRUD {
    constructor() {
        const dbHostUrl = process.env.DB_HOST_URL;
        if (!dbHostUrl) {
            throw new Error("Environment variable 'DB_HOST_URL' is not set");
        }

        mongoose.connect(dbHostUrl, { useNewUrlParser: true, useUnifiedTopology: true })
            .then(() => console.log('Connected to the database successfully'))
            .catch(err => {
                console.error('Database connection error:', err);
                process.exit(1);
            });

        this.redisClient = redis.createClient({
            url: process.env.REDIS_URL || 'redis://localhost:6379'
        });

        this.initializeRedis();
    }

    async initializeRedis() {
        try {
            await this.redisClient.connect();
            console.log('Connected to Redis successfully');
        } catch (err) {
            console.error('Failed to connect to Redis:', err);
            process.exit(1);
        }
    }

    async create(jobData) {
        try {
            const job = new JobCoreData(jobData);
            const savedJob = await job.save();

            setTimeout(async () => {
                try {
                    const orgs = await Org.find({});
                    const payload = {
                        job: savedJob,
                        organizations: orgs
                    };

                    await this.redisClient.publish('job_notification', JSON.stringify(
                        {
                            type: "message",
                            data: {
                                "job_data": payload,
                                "job_entry_id": payload.job_id
                            }
                        }
                    ));
                    console.log('Published job_insertion event:', payload);
                } catch (error) {
                    console.error('Error during job_insertion processing:', error);
                }
            }, 5000);

            return savedJob;
        } catch (error) {
            console.error('Error creating job:', error);
            throw new Error('Failed to create job');
        }
    }

    async read(jobId) {
        try {
            return await JobCoreData.findOne({ job_id: jobId });
        } catch (error) {
            console.error('Error reading job:', error);
            throw new Error('Failed to read job');
        }
    }

    async update(jobId, updateData) {
        try {
            return await JobCoreData.findOneAndUpdate({ job_id: jobId }, updateData, { new: true });
        } catch (error) {
            console.error('Error updating job:', error);
            throw new Error('Failed to update job');
        }
    }

    async delete(jobId) {
        try {
            return await JobCoreData.findOneAndDelete({ job_id: jobId });
        } catch (error) {
            console.error('Error deleting job:', error);
            throw new Error('Failed to delete job');
        }
    }

    async query(jsonQuery) {
        try {
            return await JobCoreData.find(jsonQuery);
        } catch (error) {
            console.error('Error executing query:', error);
            throw new Error('Failed to execute query');
        }
    }
}

module.exports = JobCoreDataCRUD;
