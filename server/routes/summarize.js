const express = require('express');
const router = express.Router();
const { summarizeNotes } = require('../lib/gemini');

/**
 * POST /api/summarize
 * Request body: { text: string }
 * Response: { success: true, summary: { shortSummary, detailedSummary, keyPoints, importantTerms, questions } }
 */
router.post('/', async (req, res) => {
  try {
    const { text } = req.body;

    if (!text || typeof text !== 'string' || text.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Please provide notes to summarize. You can paste text or upload a document.'
      });
    }

    const trimmed = text.trim();
    const wordCount = trimmed.split(/\s+/).filter(Boolean).length;
    if (wordCount < 5) {
      return res.status(400).json({
        success: false,
        error: 'Notes are too short. Please provide at least a few sentences (minimum 5 words) for an effective summary.'
      });
    }

    const summary = await summarizeNotes(trimmed);

    res.json({
      success: true,
      summary,
      stats: {
        inputWordCount: wordCount,
        inputCharCount: trimmed.length
      }
    });
  } catch (error) {
    console.error('Error in /api/summarize route:', error);
    const statusCode = error.status || 500;
    res.status(statusCode).json({
      success: false,
      error: error.message || 'An unexpected error occurred while generating the summary.'
    });
  }
});

module.exports = router;
