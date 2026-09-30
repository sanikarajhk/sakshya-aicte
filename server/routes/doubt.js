const express = require('express');
const router = express.Router();
const { clarifyDoubt } = require('../lib/gemini');

/**
 * POST /api/doubt
 * Clarifies student doubts based primarily on the provided notes.
 * Body: { notes: string, question: string, history?: Array }
 */
router.post('/', async (req, res) => {
  try {
    const { notes, question, history = [] } = req.body;

    if (!notes || typeof notes !== 'string' || notes.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Please provide notes to serve as study context.'
      });
    }

    if (!question || typeof question !== 'string' || question.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Please enter a question or doubt to clarify.'
      });
    }

    const result = await clarifyDoubt({
      notes: notes.trim(),
      question: question.trim(),
      history: Array.isArray(history) ? history : []
    });

    res.json({
      success: true,
      answer: result.answer,
      inNotes: result.inNotes
    });
  } catch (error) {
    console.error('Error in /api/doubt route:', error);
    const statusCode = error.status || 500;
    res.status(statusCode).json({
      success: false,
      error: error.message || 'Failed to clarify doubt. Please try again.'
    });
  }
});

module.exports = router;
