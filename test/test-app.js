const { EventEmitter } = require('events');
const { Readable } = require('stream');
const { summarizeNotes } = require('../server/lib/gemini');

async function runTests() {
  console.log('--- Starting Notes Summarizer Integration Tests ---');
  
  const express = require('express');
  const path = require('path');

  const app = express();
  app.use(express.json({ limit: '15mb' }));
  app.use(express.urlencoded({ extended: true, limit: '15mb' }));
  app.use(express.static(path.join(__dirname, '../public')));

  const healthRoutes = require('../server/routes/health');
  const summarizeRoutes = require('../server/routes/summarize');
  const uploadRoutes = require('../server/routes/upload');
  const quizRoutes = require('../server/routes/quiz');
  const doubtRoutes = require('../server/routes/doubt');

  app.use('/api/health', healthRoutes);
  app.use('/api/summarize', summarizeRoutes);
  app.use('/api/upload', uploadRoutes);
  app.use('/api/quiz', quizRoutes);
  app.use('/api/doubt', doubtRoutes);

  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    try {
      await fn();
      console.log(`✅ PASS: ${name}`);
      passed++;
    } catch (err) {
      console.error(`❌ FAIL: ${name}`, err.message);
      failed++;
    }
  }

  function simulateRequest(url, method = 'GET', headers = {}, body = null) {
    return new Promise((resolve) => {
      const req = new Readable();
      req._read = () => {};
      req.url = url;
      req.method = method;
      req.headers = Object.assign({
        'host': 'localhost',
        'user-agent': 'test-agent'
      }, headers);

      if (body) {
        if (typeof body === 'string') {
          req.push(Buffer.from(body));
        } else if (Buffer.isBuffer(body)) {
          req.push(body);
        }
      }
      req.push(null);

      const res = new EventEmitter();
      let responseBody = '';
      res.statusCode = 200;
      res.headers = {};

      res.setHeader = (k, v) => { res.headers[k.toLowerCase()] = v; };
      res.getHeader = (k) => res.headers[k.toLowerCase()];
      res.status = (code) => { res.statusCode = code; return res; };
      res.json = (data) => {
        res.setHeader('content-type', 'application/json');
        responseBody = JSON.stringify(data);
        resolve({ statusCode: res.statusCode, headers: res.headers, body: responseBody, json: data });
      };
      res.send = (data) => {
        responseBody = typeof data === 'object' ? JSON.stringify(data) : String(data);
        resolve({ statusCode: res.statusCode, headers: res.headers, body: responseBody });
      };
      res.end = (chunk) => {
        if (chunk) responseBody += chunk;
        resolve({ statusCode: res.statusCode, headers: res.headers, body: responseBody });
      };

      app(req, res);
    });
  }

  // Test 1: Health check
  await test('GET /api/health returns 200 and health info', async () => {
    const res = await simulateRequest('/api/health');
    if (res.statusCode !== 200) throw new Error(`Status ${res.statusCode}`);
    if (res.json.status !== 'ok') throw new Error(`Status not ok: ${res.json.status}`);
    if (!Array.isArray(res.json.supportedUploads)) throw new Error('Missing supportedUploads');
  });

  // Test 2: Validation on /api/summarize - empty text
  await test('POST /api/summarize with empty text returns 400', async () => {
    const body = JSON.stringify({ text: '' });
    const res = await simulateRequest('/api/summarize', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);

    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('Please provide notes')) throw new Error(`Unexpected message: ${res.json.error}`);
  });

  // Test 3: Validation on /api/summarize - text too short
  await test('POST /api/summarize with text < 5 words returns 400', async () => {
    const body = JSON.stringify({ text: 'Quick note' });
    const res = await simulateRequest('/api/summarize', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);

    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('too short')) throw new Error(`Unexpected message: ${res.json.error}`);
  });

  // Test 4: File upload extraction (.txt)
  await test('POST /api/upload extracts text from uploaded file', async () => {
    const boundary = '---------------------------974767299852498929531610575';
    const textContent = 'Cellular respiration is a set of metabolic reactions that take place in organisms to convert chemical energy from nutrients into adenosine triphosphate.';
    let body = `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="file"; filename="biology_notes.txt"\r\n`;
    body += `Content-Type: text/plain\r\n\r\n`;
    body += `${textContent}\r\n`;
    body += `--${boundary}--\r\n`;

    const res = await simulateRequest('/api/upload', 'POST', {
      'content-type': `multipart/form-data; boundary=${boundary}`,
      'content-length': Buffer.byteLength(body)
    }, body);

    if (res.statusCode !== 200) throw new Error(`Expected 200, got ${res.statusCode}: ${res.body}`);
    if (res.json.success !== true) throw new Error('Expected success true');
    if (res.json.filename !== 'biology_notes.txt') throw new Error(`Unexpected filename: ${res.json.filename}`);
    if (res.json.text !== textContent) throw new Error('Text content mismatch');
  });

  // Test 5: File upload extraction (.md)
  await test('POST /api/upload extracts text from markdown file (.md)', async () => {
    const boundary = '---------------------------974767299852498929531610575';
    const mdContent = '# Lecture 4\n\n- Point A\n- Point B\n\nConcluded with analysis.';
    let body = `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="file"; filename="lecture4.md"\r\n`;
    body += `Content-Type: text/markdown\r\n\r\n`;
    body += `${mdContent}\r\n`;
    body += `--${boundary}--\r\n`;

    const res = await simulateRequest('/api/upload', 'POST', {
      'content-type': `multipart/form-data; boundary=${boundary}`,
      'content-length': Buffer.byteLength(body)
    }, body);

    if (res.statusCode !== 200) throw new Error(`Expected 200, got ${res.statusCode}: ${res.body}`);
    if (res.json.success !== true) throw new Error('Expected success true');
    if (res.json.filename !== 'lecture4.md') throw new Error(`Unexpected filename: ${res.json.filename}`);
    if (res.json.text !== mdContent) throw new Error('Markdown text mismatch');
  });

  // Test 6: File upload rejection for disallowed file type
  await test('POST /api/upload rejects executable/disallowed extensions', async () => {
    const boundary = '---------------------------974767299852498929531610575';
    let body = `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="file"; filename="script.sh"\r\n`;
    body += `Content-Type: application/x-sh\r\n\r\n`;
    body += `echo hello\r\n`;
    body += `--${boundary}--\r\n`;

    const res = await simulateRequest('/api/upload', 'POST', {
      'content-type': `multipart/form-data; boundary=${boundary}`,
      'content-length': Buffer.byteLength(body)
    }, body);

    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('Unsupported file type')) throw new Error(`Unexpected error message: ${res.json.error}`);
  });

  // Test 7: Gemini missing API key handling
  await test('summarizeNotes throws friendly error when GEMINI_API_KEY is placeholder', async () => {
    const origKey = process.env.GEMINI_API_KEY;
    try {
      process.env.GEMINI_API_KEY = 'your_api_key_here';
      let threw = false;
      try {
        await summarizeNotes('Valid long note content for testing error state.');
      } catch (err) {
        threw = true;
        if (!err.message.includes('GEMINI_API_KEY is not configured')) {
          throw new Error(`Unexpected error message: ${err.message}`);
        }
      }
      if (!threw) throw new Error('Should have thrown for placeholder API key');
    } finally {
      process.env.GEMINI_API_KEY = origKey;
    }
  });

  // Test 8: Quiz endpoint validation - empty notes
  await test('POST /api/quiz with empty notes returns 400', async () => {
    const body = JSON.stringify({ notes: '', numQuestions: 5, difficulty: 'Easy' });
    const res = await simulateRequest('/api/quiz', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);
    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('Please provide notes')) throw new Error('Expected provide notes message');
  });

  // Test 9: Quiz endpoint validation - short notes
  await test('POST /api/quiz with short notes returns 400', async () => {
    const body = JSON.stringify({ notes: 'Two words', numQuestions: 5, difficulty: 'Easy' });
    const res = await simulateRequest('/api/quiz', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);
    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('too short')) throw new Error('Expected too short message');
  });

  // Test 10: Doubt endpoint validation - empty notes
  await test('POST /api/doubt with empty notes returns 400', async () => {
    const body = JSON.stringify({ notes: '', question: 'What is X?' });
    const res = await simulateRequest('/api/doubt', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);
    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('Please provide notes')) throw new Error('Expected provide notes message');
  });

  // Test 11: Doubt endpoint validation - empty question
  await test('POST /api/doubt with empty question returns 400', async () => {
    const body = JSON.stringify({ notes: 'This is a long enough set of notes for testing doubt questions.', question: '' });
    const res = await simulateRequest('/api/doubt', 'POST', {
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body)
    }, body);
    if (res.statusCode !== 400) throw new Error(`Expected 400, got ${res.statusCode}`);
    if (!res.json.error.includes('Please enter a question')) throw new Error('Expected enter question message');
  });

  console.log(`\n--- In-Process Test Summary: ${passed} passed, ${failed} failed ---`);
  process.exit(failed > 0 ? 1 : 0);
}

runTests();
