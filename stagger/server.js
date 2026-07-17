const express = require('express');
const app = express();
const PORT = process.env.STAGGER_PORT || 3000;

app.use(express.json());

app.post('/stagger', (req, res) => {
    const { delay = 5000 } = req.body;
    const actualDelay = Math.min(Math.max(delay, 2000), 12000);
    setTimeout(() => {
        res.json({ status: 'delayed', delay: actualDelay, original: delay });
    }, actualDelay);
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.listen(PORT, () => {
    console.log(`Stagger service running on port ${PORT}`);
});

module.exports = app;
