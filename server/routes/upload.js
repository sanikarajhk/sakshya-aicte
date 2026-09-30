const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const pdfParse = require('pdf-parse');
const mammoth = require('mammoth');

// Configure multer memory storage (files stored in memory buffer, max 10MB)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB
  },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const allowedExtensions = ['.txt', '.text', '.md', '.markdown', '.pdf', '.docx', '.json', '.csv'];
    if (allowedExtensions.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error(`Unsupported file type '${ext}'. Please upload a .txt, .md, .pdf, .docx, .json, or .csv file.`));
    }
  }
});

/**
 * POST /api/upload
 * Accepts a multipart/form-data upload with field name "file"
 * Extracts plain text from the document and returns it.
 */
router.post('/', (req, res) => {
  upload.single('file')(req, res, async (err) => {
    if (err) {
      if (err instanceof multer.MulterError && err.code === 'LIMIT_FILE_SIZE') {
        return res.status(400).json({
          success: false,
          error: 'File size exceeds 10MB limit. Please upload a smaller document.'
        });
      }
      return res.status(400).json({
        success: false,
        error: err.message || 'File upload failed.'
      });
    }

    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: 'No file uploaded. Please select a document to upload.'
      });
    }

    try {
      const { originalname, buffer, mimetype } = req.file;
      const ext = path.extname(originalname).toLowerCase();
      let extractedText = '';

      if (ext === '.pdf' || mimetype === 'application/pdf') {
        const data = await pdfParse(buffer);
        extractedText = data.text || '';
      } else if (ext === '.docx' || mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
        const result = await mammoth.extractRawText({ buffer });
        extractedText = result.value || '';
      } else if (['.txt', '.text', '.md', '.markdown', '.json', '.csv'].includes(ext)) {
        extractedText = buffer.toString('utf-8');
      } else {
        return res.status(400).json({
          success: false,
          error: `Unsupported file format '${ext}'.`
        });
      }

      const trimmedText = extractedText.trim();
      if (!trimmedText) {
        return res.status(400).json({
          success: false,
          error: 'The uploaded file appears to be empty or contains no readable text.'
        });
      }

      const wordCount = trimmedText.split(/\s+/).filter(Boolean).length;

      res.json({
        success: true,
        filename: originalname,
        fileSize: req.file.size,
        text: trimmedText,
        wordCount,
        charCount: trimmedText.length
      });
    } catch (parseError) {
      console.error('Error parsing uploaded file:', parseError);
      res.status(500).json({
        success: false,
        error: `Failed to extract text from '${req.file.originalname}': ${parseError.message}`
      });
    }
  });
});

module.exports = router;
