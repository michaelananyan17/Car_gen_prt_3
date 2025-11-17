const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware with security restrictions
app.use(cors({
    origin: ['http://localhost:3000', 'http://127.0.0.1:3000', 'file://'],
    credentials: false
}));
app.use(express.json({ limit: '10mb' }));

// Rate limiting middleware
const requestCounts = new Map();
const RATE_LIMIT = 10; // 10 requests per hour per API key
const HOUR_MS = 60 * 60 * 1000;

const rateLimitMiddleware = (req, res, next) => {
    const { apiKey } = req.body;
    if (!apiKey) return next();
    
    const now = Date.now();
    const keyData = requestCounts.get(apiKey) || { count: 0, resetTime: now + HOUR_MS };
    
    // Reset counter if hour has passed
    if (now > keyData.resetTime) {
        keyData.count = 0;
        keyData.resetTime = now + HOUR_MS;
    }
    
    // Check rate limit
    if (keyData.count >= RATE_LIMIT) {
        return res.status(429).json({ 
            error: 'Rate limit exceeded. Maximum 10 requests per hour per API key.' 
        });
    }
    
    keyData.count++;
    requestCounts.set(apiKey, keyData);
    next();
};

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'OK', message: 'Car Photo Generator Server is running' });
});

// Image generation endpoint
app.post('/generate-image', rateLimitMiddleware, async (req, res) => {
    try {
        const { prompt, apiKey } = req.body;

        // Validate input
        if (!prompt || prompt.trim().length === 0) {
            return res.status(400).json({ error: 'Prompt is required' });
        }

        if (!apiKey) {
            return res.status(400).json({ error: 'API key is required' });
        }

        if (!apiKey.startsWith('sk-') || apiKey.length < 20) {
            return res.status(400).json({ error: 'Invalid OpenAI API key format' });
        }

        // Validate prompt length for DALL-E 3
        if (prompt.length > 1000) {
            return res.status(400).json({ error: 'Prompt too long. Maximum 1000 characters.' });
        }

        console.log('Generating image with prompt:', prompt.substring(0, 100) + '...');

        // Call OpenAI DALL-E API
        const openaiResponse = await fetch('https://api.openai.com/v1/images/generations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "dall-e-3",
                prompt: prompt.trim(),
                n: 1,
                size: "1024x1024",
                quality: "standard"
            })
        });

        if (!openaiResponse.ok) {
            const errorData = await openaiResponse.json();
            console.error('OpenAI API error:', errorData);
            return res.status(openaiResponse.status).json({ 
                error: `OpenAI API error: ${errorData.error?.message || 'Unknown error'}` 
            });
        }

        const data = await openaiResponse.json();
        const imageUrl = data.data[0].url;

        console.log('Image generated successfully');

        res.json({
            success: true,
            imageUrl: imageUrl,
            prompt: prompt
        });

    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ 
            error: `Internal server error: ${error.message}` 
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Car Photo Generator Server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
});

module.exports = app;