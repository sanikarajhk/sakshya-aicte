const express = require('express');
const router = express.Router();
const { generateQuiz } = require('../lib/gemini');

/**
 * POST /api/quiz
 * Generates an interactive quiz based on the provided notes.
 * Body: { notes: string, numQuestions: number, difficulty: string }
 */
router.post('/', async (req, res) => {
  try {
    const { notes, numQuestions = 5, difficulty = 'Medium' } = req.body;

    if (!notes || typeof notes !== 'string' || notes.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Please provide notes to generate a quiz from.'
      });
    }

    const trimmedNotes = notes.trim();
    const wordCount = trimmedNotes.split(/\s+/).filter(Boolean).length;
    if (wordCount < 5) {
      return res.status(400).json({
        success: false,
        error: 'Notes are too short (less than 5 words). Please provide more content to generate meaningful quiz questions.'
      });
    }

    const quiz = await generateQuiz({
      notes: trimmedNotes,
      numQuestions: Number(numQuestions) || 5,
      difficulty: difficulty || 'Medium'
    });

    res.json({
      success: true,
      quiz
    });
  } catch (error) {
    console.error('Error in /api/quiz route:', error);
    const statusCode = error.status || 500;
    res.status(statusCode).json({
      success: false,
      error: error.message || 'Failed to generate quiz. Please try again.'
    });
  }
});

module.exports = router;
