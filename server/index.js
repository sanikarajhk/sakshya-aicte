require('dotenv').config();
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Body parsing middleware (allow larger JSON payloads for long lecture notes/documents)
app.use(express.json({ limit: '15mb' }));
app.use(express.urlencoded({ extended: true, limit: '15mb' }));

// Serve frontend static assets
app.use(express.static(path.join(__dirname, '../public')));

// Routes
const healthRoutes = require('./routes/health');
const summarizeRoutes = require('./routes/summarize');
const uploadRoutes = require('./routes/upload');
const quizRoutes = require('./routes/quiz');
const doubtRoutes = require('./routes/doubt');

app.use('/api/health', healthRoutes);
app.use('/api/summarize', summarizeRoutes);
app.use('/api/upload', uploadRoutes);
app.use('/api/quiz', quizRoutes);
app.use('/api/doubt', doubtRoutes);

// Generic 404 handler for API routes
app.use('/api/*', (req, res) => {
  res.status(404).json({
    success: false,
    error: `Endpoint not found: ${req.method} ${req.originalUrl}`
  });
});

// Fallback to index.html for single page navigation
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Central error handling middleware
app.use((err, req, res, next) => {
  console.error('Unhandled server error:', err);
  res.status(err.status || 500).json({
    success: false,
    error: err.message || 'Internal Server Error'
  });
});

const { isApiKeyConfigured } = require('./lib/gemini');

const server = app.listen(PORT, () => {
  const isConfigured = isApiKeyConfigured(process.env.GEMINI_API_KEY);
  console.log(`\n==========================================`);
  console.log(`🚀 Notes Summarizer Server running at:`);
  console.log(`   http://localhost:${PORT}`);
  console.log(`   Health Check: http://localhost:${PORT}/api/health`);
  console.log(`   Gemini Model: ${process.env.GEMINI_MODEL || 'gemini-1.5-flash'}`);
  console.log(`   API Key Configured: ${isConfigured ? 'Yes ✅' : 'No ⚠️ (Set GEMINI_API_KEY in .env)'}`);
  console.log(`==========================================\n`);
});

module.exports = { app, server };
