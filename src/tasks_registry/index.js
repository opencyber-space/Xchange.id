const express = require('express');
const bodyParser = require('body-parser');
const JobCoreDataCRUD = require('./src/controllers_job');

const app = express();
const port = process.env.PORT || 3000;
const jobCoreDataCRUD = new JobCoreDataCRUD();

app.use(bodyParser.json());

app.post('/jobs', async (req, res) => {
    try {
        const jobData = req.body;
        const result = await jobCoreDataCRUD.create(jobData);
        res.status(201).json({ success: true, data: result, message: 'Job created successfully' });
    } catch (error) {
        res.status(500).json({ success: false, data: null, message: error.message });
    }
});

app.get('/jobs/:jobId', async (req, res) => {
    try {
        const jobId = req.params.jobId;
        const result = await jobCoreDataCRUD.read(jobId);
        if (result) {
            res.status(200).json({ success: true, data: result, message: 'Job retrieved successfully' });
        } else {
            res.status(404).json({ success: false, data: null, message: 'Job not found' });
        }
    } catch (error) {
        res.status(500).json({ success: false, data: null, message: error.message });
    }
});

app.put('/jobs/:jobId', async (req, res) => {
    try {
        const jobId = req.params.jobId;
        const updateData = req.body;
        const result = await jobCoreDataCRUD.update(jobId, updateData);
        if (result) {
            res.status(200).json({ success: true, data: result, message: 'Job updated successfully' });
        } else {
            res.status(404).json({ success: false, data: null, message: 'Job not found' });
        }
    } catch (error) {
        res.status(500).json({ success: false, data: null, message: error.message });
    }
});

app.delete('/jobs/:jobId', async (req, res) => {
    try {
        const jobId = req.params.jobId;
        const result = await jobCoreDataCRUD.delete(jobId);
        if (result) {
            res.status(200).json({ success: true, data: null, message: 'Job deleted successfully' });
        } else {
            res.status(404).json({ success: false, data: null, message: 'Job not found' });
        }
    } catch (error) {
        res.status(500).json({ success: false, data: null, message: error.message });
    }
});

app.post('/jobs/query', async (req, res) => {
    try {
        const query = req.body;
        const result = await jobCoreDataCRUD.query(query);
        res.status(200).json({ success: true, data: result, message: 'Query executed successfully' });
    } catch (error) {
        res.status(500).json({ success: false, data: null, message: error.message });
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://0.0.0.0:${port}`);
});
