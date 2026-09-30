# 🎓 AI Study Assistant (Powered by Google Gemini AI)

An AI-powered Study Assistant web application that transforms study notes, lecture transcripts, and documents into an interactive study environment with three dedicated modes: **Summarize**, **Quiz Session**, and **Doubt Clarification**.

---

## 🌟 Study Modes

### 1. 📝 Summarize
- **⚡ Short Summary**: A crisp 2–3 sentence overview.
- **📖 Detailed Summary**: In-depth, multi-paragraph conceptual breakdown.
- **🎯 Key Takeaways**: Bulleted highlights with custom markers.
- **💡 Important Terms & Concepts**: Glossary cards with keywords and definitions.
- **❓ 5 Review Questions**: Active recall self-study cards with interactive "Show Answer" toggles.
- **📋 Copy & 📥 Download**: Instant Markdown export and clipboard copy.

### 2. 🎯 Quiz Session
- **Customizable Configuration**:
  - **Question Count**: Choose 5, 10, or 15 questions.
  - **Difficulty**: Choose Easy (recall & terms), Medium (conceptual understanding), or Hard (deep synthesis).
- **Strict Source Fidelity**: Questions are generated strictly from the provided notes without fabricating outside information.
- **Diverse Question Types**: Balanced mix of Multiple-Choice Questions (MCQ) and True/False questions.
- **Step-by-Step Runner**: Displays one question at a time with a progress bar.
- **Comprehensive Score & Review**:
  - Total score, percentage, and performance assessment badge.
  - Filter by All, Incorrect Only, or Correct Only.
  - Detailed explanation for every question based on the notes.
- **🔄 Retry Quiz**: Re-attempts the same quiz with a clean slate to test retention.
- **✨ Generate New Quiz**: Creates fresh questions from the same source notes.

### 3. 💬 Doubt Clarification (AI Tutor)
- **Context-Aware Dialogue**: Uses the user's uploaded or entered notes as primary context.
- **Student-Friendly Language**: Explains complex topics in intuitive, accessible terms.
- **Real-World Examples & Step-by-Step Logic**: Vivid analogies and numbered walkthroughs.
- **Out-of-Notes Transparency**: If a question asks about a concept not present in the notes, the tutor clearly specifies: *"This concept is not mentioned in your provided notes. However, here is a general explanation: ..."*
- **Follow-up Continuity**: Maintains conversational context across multiple turns.
- **Quick Prompt Chips**: One-click prompt suggestions to jumpstart doubt resolution.

---

## 📁 Multi-Format Document Upload
Upload notes directly via drag-and-drop or file browser:
- PDF documents (`.pdf`)
- Word documents (`.docx`)
- Markdown files (`.md`, `.markdown`)
- Plain text & data files (`.txt`, `.json`, `.csv`)

---

## 🏗️ Project Structure

```
├── server/
│   ├── index.js              # Express server & static asset serving
│   ├── lib/
│   │   └── gemini.js         # Gemini API client, model fallback, & schemas
│   └── routes/
│       ├── health.js         # GET /api/health
│       ├── summarize.js      # POST /api/summarize
│       ├── upload.js         # POST /api/upload (extracts text from pdf, docx, txt, etc.)
│       ├── quiz.js           # POST /api/quiz (generates MCQs & True/False quizzes)
│       └── doubt.js          # POST /api/doubt (handles doubt clarification & tutoring)
├── public/
│   ├── index.html            # Responsive UI layout for all 3 study modes
│   ├── styles.css            # Clean, modern CSS with responsive variables & themes
│   └── app.js                # Frontend client managing tabs, quiz runner, & chat
├── test/
│   └── test-app.js           # Automated integration test suite (11 test cases)
├── .env                      # Active environment configuration
├── .env.example              # Environment variables template
├── .gitignore                # Excludes .env and node_modules
├── package.json              # Dependencies and npm scripts
└── README.md                 # Complete documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js** (v18.0.0 or higher)
- **npm**

### 2. Configure Environment Variables
1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Configure `.env`:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   GEMINI_MODEL=gemini-3.5-flash
   PORT=3000
   ```

### 3. Install Dependencies
```bash
npm install
```

### 4. Run the Application
Start the server:
```bash
npm start
```
Or for development:
```bash
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

### 5. Run Automated Tests
```bash
npm test
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | Health check & Gemini configuration status |
| `/api/upload` | `POST` | Multipart document upload & text extraction (`.pdf`, `.docx`, `.txt`, `.md`, `.json`, `.csv`) |
| `/api/summarize` | `POST` | Generates 5-part structured summary |
| `/api/quiz` | `POST` | Generates custom quiz based strictly on notes (5/10/15 questions, Easy/Medium/Hard) |
| `/api/doubt` | `POST` | Clarifies student doubts using notes as primary context, with conversation history |

---

## 🛡️ Security

- `GEMINI_API_KEY` is strictly managed server-side and never exposed to the client or browser.
- File uploads are processed in memory buffers and never written unencrypted to disk.

---

## 📝 License

MIT
