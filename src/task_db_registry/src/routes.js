const express = require('express');
const TaskListingSchemaCRUD = require('./controllers.js');

const router = express.Router();
const crud = new TaskListingSchemaCRUD();

router.post('/create', async (req, res) => {
    try {
        const result = await crud.create(req.body);
        res.status(201).json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

router.get('/read', async (req, res) => {
    try {
        const result = await crud.read(req.query);
        res.status(200).json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

router.put('/update', async (req, res) => {
    try {
        const { filter, updateData } = req.body;
        const result = await crud.update(filter, updateData);
        res.status(200).json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

router.delete('/delete', async (req, res) => {
    try {
        const result = await crud.delete(req.body.filter);
        res.status(200).json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

router.get('/getById/:task_listing_db_id', async (req, res) => {
    try {
        const result = await crud.getById(req.params.task_listing_db_id);
        if (!result) {
            res.status(404).json({ success: false, message: 'Document not found' });
        } else {
            res.status(200).json({ success: true, data: result });
        }
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

router.post('/query', async (req, res) => {
    try {
        const result = await crud.query(req.body);
        res.status(201).json({ success: true, data: result });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
})

module.exports = router;
