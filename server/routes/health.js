const express = require('express');
const router = express.Router();
const { isApiKeyConfigured } = require('../lib/gemini');

/**
 * GET /api/health
 * Returns server and Gemini API configuration status
 */
router.get('/', (req, res) => {
  const hasValidApiKey = isApiKeyConfigured(process.env.GEMINI_API_KEY);

  res.json({
    status: 'ok',
    message: 'Notes Summarizer API is running',
    environmentLoaded: hasValidApiKey,
    geminiConfigured: hasValidApiKey,
    model: process.env.GEMINI_MODEL || 'gemini-1.5-flash',
    supportedUploads: ['.txt', '.md', '.pdf', '.docx', '.json', '.csv']
  });
});

module.exports = router;
