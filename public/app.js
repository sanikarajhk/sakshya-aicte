/**
 * AI Study Assistant Frontend Client Application
 * Features:
 * 1. Notes Summarizer (Short, Detailed, Key Points, Terms, Review Questions)
 * 2. Interactive Quiz Session (5/10/15 questions, Easy/Medium/Hard, MCQ & True/False, scoring, review)
 * 3. Doubt Clarification / AI Tutor (Context-aware tutoring, student-friendly explanations, examples, step-by-step)
 */

// ==========================================================================
// Application State
// ==========================================================================
let currentMode = 'summarize';

// Summarize State
let currentSummaryData = null;
let isSummarizing = false;
let isUploading = false;

// Quiz State
let currentQuiz = null;
let currentQuestionIndex = 0;
let userQuizAnswers = {}; // { [questionId]: selectedOptionString }
let quizNumQuestions = 5;
let quizDifficulty = 'Medium';
let isGeneratingQuiz = false;
let quizReviewFilter = 'all';

// Doubt Clarification State
let doubtConversationHistory = []; // [ { role: 'user'|'assistant', content: string } ]
let isAskingDoubt = false;

// ==========================================================================
// DOM Elements
// ==========================================================================
// Mode Tabs
const modeTabs = document.querySelectorAll('.mode-tab');
const modeViews = {
  summarize: document.getElementById('view-summarize'),
  quiz: document.getElementById('view-quiz'),
  doubt: document.getElementById('view-doubt')
};

// Notes Input & Controls (Summarize Mode)
const notesInput = document.getElementById('notes-input');
const wordCountEl = document.getElementById('word-count');
const charCountEl = document.getElementById('char-count');
const summarizeBtn = document.getElementById('summarize-btn');
const summarizeBtnText = document.getElementById('summarize-btn-text');
const summarizeSpinner = document.getElementById('summarize-spinner');
const summarizeIcon = document.getElementById('summarize-icon');
const clearBtn = document.getElementById('clear-btn');
const sampleBtn = document.getElementById('sample-btn');

// File Upload Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const uploadSpinner = document.getElementById('upload-spinner');
const dropzoneContent = dropzone ? dropzone.querySelector('.dropzone-content') : null;
const fileInfoBadge = document.getElementById('file-info-badge');
const fileBadgeName = document.getElementById('file-badge-name');
const fileBadgeSize = document.getElementById('file-badge-size');
const removeFileBtn = document.getElementById('remove-file-btn');

// Loading & Notification Elements
const loadingCard = document.getElementById('loading-card');
const loadingSubtext = document.getElementById('loading-subtext');
const errorBanner = document.getElementById('error-banner');
const errorMessageEl = document.getElementById('error-message');
const closeErrorBtn = document.getElementById('close-error-btn');
const apiStatusBadge = document.getElementById('api-status-badge');
const apiStatusText = document.getElementById('api-status-text');
const toastContainer = document.getElementById('toast-container');

// Summarize Results Elements
const resultsCard = document.getElementById('results-card');
const shortSummaryContent = document.getElementById('short-summary-content');
const detailedSummaryContent = document.getElementById('detailed-summary-content');
const keyPointsList = document.getElementById('key-points-list');
const termsGrid = document.getElementById('terms-grid');
const questionsList = document.getElementById('questions-list');
const copyBtn = document.getElementById('copy-btn');
const copyBtnBottom = document.getElementById('copy-btn-bottom');
const downloadBtn = document.getElementById('download-btn');
const downloadBtnBottom = document.getElementById('download-btn-bottom');
const clearResultsBtn = document.getElementById('clear-results-btn');

// Quiz Elements
const quizNotesContextBar = document.getElementById('quiz-notes-context-bar');
const quizNotesWordCount = document.getElementById('quiz-notes-wordcount');
const quizEmptyState = document.getElementById('quiz-empty-state');
const quizSetupCard = document.getElementById('quiz-setup-card');
const quizCountGroup = document.getElementById('quiz-count-group');
const quizDiffGroup = document.getElementById('quiz-diff-group');
const startQuizBtn = document.getElementById('start-quiz-btn');
const quizLoadingCard = document.getElementById('quiz-loading-card');
const quizLoadingSubtext = document.getElementById('quiz-loading-subtext');
const quizActiveCard = document.getElementById('quiz-active-card');
const quizTopicBadge = document.getElementById('quiz-topic-badge');
const quizDifficultyBadge = document.getElementById('quiz-difficulty-badge');
const quizTypeBadge = document.getElementById('quiz-type-badge');
const quizCurrentNum = document.getElementById('quiz-current-num');
const quizTotalNum = document.getElementById('quiz-total-num');
const quizProgressBar = document.getElementById('quiz-progress-bar');
const quizQuestionText = document.getElementById('quiz-question-text');
const quizOptionsContainer = document.getElementById('quiz-options-container');
const quitQuizBtn = document.getElementById('quit-quiz-btn');
const nextQuestionBtn = document.getElementById('next-question-btn');
const quizResultsCard = document.getElementById('quiz-results-card');
const scorePercentageCircle = document.getElementById('score-percentage-circle');
const scorePercentageText = document.getElementById('score-percentage-text');
const scoreTitle = document.getElementById('score-title');
const scoreFraction = document.getElementById('score-fraction');
const statCorrect = document.getElementById('stat-correct');
const statIncorrect = document.getElementById('stat-incorrect');
const reviewFilterGroup = document.getElementById('review-filter-group');
const quizReviewList = document.getElementById('quiz-review-list');
const retryQuizBtn = document.getElementById('retry-quiz-btn');
const newQuizBtn = document.getElementById('new-quiz-btn');

// Doubt Clarification Elements
const doubtNotesContextBar = document.getElementById('doubt-notes-context-bar');
const doubtNotesWordCount = document.getElementById('doubt-notes-wordcount');
const doubtEmptyState = document.getElementById('doubt-empty-state');
const doubtChatCard = document.getElementById('doubt-chat-card');
const doubtMessagesContainer = document.getElementById('doubt-messages-container');
const doubtForm = document.getElementById('doubt-form');
const doubtInput = document.getElementById('doubt-input');
const sendDoubtBtn = document.getElementById('send-doubt-btn');
const doubtSendSpinner = document.getElementById('doubt-send-spinner');
const doubtSendIcon = document.getElementById('doubt-send-icon');
const clearChatBtn = document.getElementById('clear-chat-btn');

// Sample Study Notes
const SAMPLE_NOTES = `Distributed Systems: Consistency and Consensus

In distributed systems, managing state across multiple autonomous nodes introduces fundamental challenges known as the CAP theorem. Stated by Eric Brewer, the CAP theorem asserts that a distributed data store can simultaneously provide at most two out of three guarantees: Consistency (every read receives the most recent write or an error), Availability (every non-failing node returns a non-error response), and Partition Tolerance (the system continues to operate despite arbitrary message loss or network partitions).

Because network partitions are inevitable in real-world networks due to physical link failures and router timeouts, distributed architectures must realistically choose between CP (Consistency and Partition Tolerance) and AP (Availability and Partition Tolerance). Systems like Apache Cassandra and Amazon DynamoDB favor high availability with eventual consistency, whereas traditional relational databases and distributed consensus protocols prioritize strong consistency.

To achieve strong consistency across replicas in the presence of failures, consensus algorithms such as Paxos and Raft are widely adopted. Raft breaks down consensus into three distinct sub-problems: Leader Election, Log Replication, and Safety. Nodes in a Raft cluster exist in one of three states: Follower, Candidate, or Leader. When a leader fails or heartbeats timeout, a follower transitions to candidate, increments its term number, and requests votes. Once elected, only the leader accepts client write requests and replicates log entries to follower nodes. A log entry is committed once a quorum (majority) of nodes successfully appends it.

Another essential technique is the Two-Phase Commit (2PC) protocol used in distributed transactions. In 2PC, a coordinator node orchestrates the prepare phase, asking all participants whether they can commit the transaction. If every participant votes "yes", the coordinator enters the commit phase; otherwise, an abort command is sent. However, 2PC is a blocking protocol—if the coordinator crashes after participants have agreed to commit, participants remain locked in doubt. Modern systems often combine Paxos or Raft with atomic commit to avoid coordinator single-points of failure.`;

/* ==========================================================================
   Initialization & Event Listeners
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
  checkApiHealth();
  setupModeTabs();
  setupTextareaEvents();
  setupUploadEvents();
  setupSummarizeActions();
  setupQuizActions();
  setupDoubtActions();
  setupGlobalShortcuts();
  initDoubtChatWelcome();
});

// Helper: Get notes text from textarea
function getNotesText() {
  return notesInput ? notesInput.value.trim() : '';
}

function getNotesWordCount() {
  const text = getNotesText();
  return text ? text.split(/\s+/).filter(Boolean).length : 0;
}

/* ==========================================================================
   Mode Navigation Tabs
   ========================================================================== */
function setupModeTabs() {
  modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const mode = tab.getAttribute('data-mode');
      switchMode(mode);
    });
  });

  // "Go to Notes" buttons found across empty states and context bars
  document.querySelectorAll('.goto-notes-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      switchMode('summarize');
      if (notesInput) {
        notesInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        notesInput.focus();
      }
    });
  });

  // "Load Sample Notes" buttons in Quiz and Doubt empty states
  document.querySelectorAll('.load-sample-quiz-btn, .load-sample-doubt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      handleLoadSample();
      syncNotesState();
    });
  });
}

function switchMode(mode) {
  currentMode = mode;

  modeTabs.forEach(t => {
    const isTarget = t.getAttribute('data-mode') === mode;
    t.classList.toggle('active', isTarget);
    t.setAttribute('aria-selected', isTarget ? 'true' : 'false');
  });

  Object.keys(modeViews).forEach(m => {
    if (modeViews[m]) {
      if (m === mode) {
        modeViews[m].classList.remove('hidden');
        modeViews[m].classList.add('active-view');
      } else {
        modeViews[m].classList.add('hidden');
        modeViews[m].classList.remove('active-view');
      }
    }
  });

  hideError();
  syncNotesState();
}

function syncNotesState() {
  const wordCount = getNotesWordCount();
  const hasNotes = wordCount >= 5;

  // Update Quiz Mode
  if (quizNotesContextBar) {
    if (hasNotes) {
      quizNotesContextBar.classList.remove('hidden');
      quizNotesWordCount.textContent = `${wordCount.toLocaleString()} words`;
      quizEmptyState.classList.add('hidden');

      if (!currentQuiz && !isGeneratingQuiz) {
        quizSetupCard.classList.remove('hidden');
      }
    } else {
      quizNotesContextBar.classList.add('hidden');
      if (!currentQuiz && !isGeneratingQuiz) {
        quizEmptyState.classList.remove('hidden');
        quizSetupCard.classList.add('hidden');
        quizActiveCard.classList.add('hidden');
        quizResultsCard.classList.add('hidden');
      }
    }
  }

  // Update Doubt Mode
  if (doubtNotesContextBar) {
    if (hasNotes) {
      doubtNotesContextBar.classList.remove('hidden');
      doubtNotesWordCount.textContent = `${wordCount.toLocaleString()} words`;
      doubtEmptyState.classList.add('hidden');
      doubtChatCard.classList.remove('hidden');
    } else {
      doubtNotesContextBar.classList.add('hidden');
      doubtEmptyState.classList.remove('hidden');
      doubtChatCard.classList.add('hidden');
    }
  }
}

/* ==========================================================================
   API Health & Status
   ========================================================================== */
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();

    if (data.geminiConfigured) {
      apiStatusBadge.className = 'status-badge ready';
      apiStatusText.textContent = `Gemini Ready (${data.model})`;
      apiStatusBadge.title = 'Gemini API is connected and ready';
    } else {
      apiStatusBadge.className = 'status-badge warning';
      apiStatusText.textContent = 'API Key Needed';
      apiStatusBadge.title = 'Please configure GEMINI_API_KEY in your .env file';
    }
  } catch (err) {
    apiStatusBadge.className = 'status-badge warning';
    apiStatusText.textContent = 'Server Offline';
    apiStatusBadge.title = 'Cannot reach backend server';
  }
}

/* ==========================================================================
   Textarea & File Upload Handlers (Summarize Mode)
   ========================================================================== */
function setupTextareaEvents() {
  notesInput.addEventListener('input', () => {
    updateTextCounts();
    syncNotesState();
  });
}

function updateTextCounts() {
  const text = getNotesText();
  const wordCount = text ? text.split(/\s+/).filter(Boolean).length : 0;
  const charCount = notesInput.value.length;

  wordCountEl.textContent = `${wordCount.toLocaleString()} ${wordCount === 1 ? 'word' : 'words'}`;
  charCountEl.textContent = `${charCount.toLocaleString()} ${charCount === 1 ? 'character' : 'characters'}`;
}

function handleLoadSample() {
  notesInput.value = SAMPLE_NOTES;
  updateTextCounts();
  syncNotesState();
  hideError();
  showToast('Sample study notes loaded!', 'success');
}

function setupUploadEvents() {
  if (!dropzone) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleSelectedFile(files[0]);
    }
  });

  if (removeFileBtn) {
    removeFileBtn.addEventListener('click', handleRemoveFile);
  }
}

async function handleSelectedFile(file) {
  hideError();

  if (file.size > 10 * 1024 * 1024) {
    showError('File exceeds 10MB limit. Please upload a smaller file.');
    return;
  }

  const extension = '.' + file.name.split('.').pop().toLowerCase();
  const textExtensions = ['.txt', '.text', '.md', '.markdown', '.json', '.csv'];
  const binaryExtensions = ['.pdf', '.docx'];

  if (!textExtensions.includes(extension) && !binaryExtensions.includes(extension)) {
    showError(`Unsupported file format '${extension}'. Please upload .txt, .md, .pdf, .docx, .json, or .csv.`);
    return;
  }

  displayFileBadge(file.name, file.size);

  if (textExtensions.includes(extension)) {
    const reader = new FileReader();
    reader.onload = (e) => {
      notesInput.value = e.target.result;
      updateTextCounts();
      syncNotesState();
      showToast(`Loaded ${file.name}`, 'success');
    };
    reader.onerror = () => {
      showError('Failed to read the selected file in browser.');
    };
    reader.readAsText(file);
    return;
  }

  await uploadAndExtractBinaryFile(file);
}

async function uploadAndExtractBinaryFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    setUploadingState(true);
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to extract text from document.');
    }

    notesInput.value = data.text;
    updateTextCounts();
    syncNotesState();
    showToast(`Extracted ${data.wordCount.toLocaleString()} words from ${file.name}`, 'success');
  } catch (err) {
    console.error('File extraction error:', err);
    showError(err.message || 'Error uploading document.');
    handleRemoveFile();
  } finally {
    setUploadingState(false);
  }
}

function displayFileBadge(filename, sizeBytes) {
  if (!fileBadgeName || !fileInfoBadge) return;
  fileBadgeName.textContent = filename;
  const sizeFormatted = sizeBytes > 1024 * 1024
    ? `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.round(sizeBytes / 1024)} KB`;
  fileBadgeSize.textContent = sizeFormatted;
  fileInfoBadge.classList.remove('hidden');
}

function handleRemoveFile(e) {
  if (e) e.stopPropagation();
  if (fileInput) fileInput.value = '';
  if (fileInfoBadge) fileInfoBadge.classList.add('hidden');
}

function setUploadingState(uploading) {
  isUploading = uploading;
  if (uploading) {
    uploadSpinner.classList.remove('hidden');
    dropzoneContent.classList.add('hidden');
    summarizeBtn.disabled = true;
  } else {
    uploadSpinner.classList.add('hidden');
    dropzoneContent.classList.remove('hidden');
    summarizeBtn.disabled = false;
  }
}

/* ==========================================================================
   Summarize Mode Logic
   ========================================================================== */
function setupSummarizeActions() {
  summarizeBtn.addEventListener('click', handleSummarize);
  clearBtn.addEventListener('click', handleClearAll);
  sampleBtn.addEventListener('click', handleLoadSample);
  closeErrorBtn.addEventListener('click', hideError);

  copyBtn.addEventListener('click', () => copySummaryToClipboard(copyBtn));
  if (copyBtnBottom) copyBtnBottom.addEventListener('click', () => copySummaryToClipboard(copyBtnBottom));
  downloadBtn.addEventListener('click', downloadSummaryFile);
  if (downloadBtnBottom) downloadBtnBottom.addEventListener('click', downloadSummaryFile);
  clearResultsBtn.addEventListener('click', () => {
    resultsCard.classList.add('hidden');
    currentSummaryData = null;
  });
}

async function handleSummarize() {
  const text = getNotesText();
  hideError();

  if (!text) {
    showError('Please enter notes or upload a document to summarize.');
    notesInput.focus();
    return;
  }

  const wordCount = text.split(/\s+/).filter(Boolean).length;
  if (wordCount < 5) {
    showError('Notes are too short (less than 5 words). Please provide more context for a meaningful summary.');
    return;
  }

  try {
    setSummarizingState(true);

    const response = await fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to generate summary.');
    }

    currentSummaryData = data.summary;
    renderSummaryResults(data.summary);
    showToast('Summary generated successfully!', 'success');

    resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    console.error('Summarize error:', err);
    showError(err.message || 'An error occurred during summarization.');
  } finally {
    setSummarizingState(false);
  }
}

function setSummarizingState(loading) {
  isSummarizing = loading;
  if (loading) {
    summarizeBtn.disabled = true;
    clearBtn.disabled = true;
    summarizeSpinner.classList.remove('hidden');
    summarizeIcon.classList.add('hidden');
    summarizeBtnText.textContent = 'Summarizing...';

    loadingCard.classList.remove('hidden');
    resultsCard.classList.add('hidden');
    startLoadingSubtextCycle();
  } else {
    summarizeBtn.disabled = false;
    clearBtn.disabled = false;
    summarizeSpinner.classList.add('hidden');
    summarizeIcon.classList.remove('hidden');
    summarizeBtnText.textContent = 'Summarize Notes';

    loadingCard.classList.add('hidden');
    stopLoadingSubtextCycle();
  }
}

let subtextInterval = null;
function startLoadingSubtextCycle() {
  const messages = [
    'Analyzing notes structure and key themes...',
    'Synthesizing key points and takeaways...',
    'Extracting technical terms and concepts...',
    'Formulating 5 comprehension review questions...'
  ];
  let index = 0;
  loadingSubtext.textContent = messages[0];
  subtextInterval = setInterval(() => {
    index = (index + 1) % messages.length;
    loadingSubtext.textContent = messages[index];
  }, 2200);
}

function stopLoadingSubtextCycle() {
  if (subtextInterval) {
    clearInterval(subtextInterval);
    subtextInterval = null;
  }
}

function renderSummaryResults(summary) {
  shortSummaryContent.textContent = summary.shortSummary;

  detailedSummaryContent.innerHTML = '';
  const paragraphs = summary.detailedSummary.split(/\n\s*\n|\n/);
  paragraphs.forEach(p => {
    const trimmed = p.trim();
    if (trimmed) {
      const pEl = document.createElement('p');
      pEl.textContent = trimmed;
      detailedSummaryContent.appendChild(pEl);
    }
  });

  keyPointsList.innerHTML = '';
  summary.keyPoints.forEach(point => {
    const li = document.createElement('li');
    li.className = 'key-point-item';
    li.innerHTML = `
      <span class="key-point-marker">✓</span>
      <span>${escapeHtml(point)}</span>
    `;
    keyPointsList.appendChild(li);
  });

  termsGrid.innerHTML = '';
  if (summary.importantTerms && summary.importantTerms.length > 0) {
    summary.importantTerms.forEach(item => {
      const card = document.createElement('div');
      card.className = 'term-card';
      card.innerHTML = `
        <div class="term-title">${escapeHtml(item.term)}</div>
        <div class="term-definition">${escapeHtml(item.definition)}</div>
      `;
      termsGrid.appendChild(card);
    });
  } else {
    termsGrid.innerHTML = '<p class="text-muted">No explicit terms extracted.</p>';
  }

  questionsList.innerHTML = '';
  summary.questions.forEach((q, idx) => {
    const qCard = document.createElement('div');
    qCard.className = 'question-card';
    qCard.innerHTML = `
      <div class="question-header" tabindex="0" role="button" aria-expanded="false">
        <div class="question-title-wrap">
          <span class="question-badge">Q${idx + 1}</span>
          <span class="question-text">${escapeHtml(q.question)}</span>
        </div>
        <button type="button" class="question-toggle-btn">Show Answer</button>
      </div>
      <div class="question-answer hidden">
        <strong>Answer:</strong> ${escapeHtml(q.answer)}
      </div>
    `;

    const header = qCard.querySelector('.question-header');
    const toggleBtn = qCard.querySelector('.question-toggle-btn');
    const answerEl = qCard.querySelector('.question-answer');

    const toggleAnswer = () => {
      const isHidden = answerEl.classList.contains('hidden');
      if (isHidden) {
        answerEl.classList.remove('hidden');
        toggleBtn.textContent = 'Hide Answer';
        header.setAttribute('aria-expanded', 'true');
      } else {
        answerEl.classList.add('hidden');
        toggleBtn.textContent = 'Show Answer';
        header.setAttribute('aria-expanded', 'false');
      }
    };

    header.addEventListener('click', toggleAnswer);
    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleAnswer();
      }
    });

    questionsList.appendChild(qCard);
  });

  resultsCard.classList.remove('hidden');
}

function formatSummaryAsMarkdown(summary) {
  let md = `# Notes Summary\n\n`;
  md += `## ⚡ Quick Summary\n${summary.shortSummary}\n\n`;
  md += `## 📖 Detailed Summary\n${summary.detailedSummary}\n\n`;
  md += `## 🎯 Key Takeaways\n`;
  summary.keyPoints.forEach(p => { md += `- ${p}\n`; });
  md += `\n## 💡 Important Terms & Concepts\n`;
  summary.importantTerms.forEach(item => { md += `- **${item.term}**: ${item.definition}\n`; });
  md += `\n## ❓ Review Questions\n`;
  summary.questions.forEach((q, idx) => {
    md += `### Question ${idx + 1}: ${q.question}\n**Answer:** ${q.answer}\n\n`;
  });
  md += `---\n*Generated by AI Study Assistant with Google Gemini AI*\n`;
  return md;
}

async function copySummaryToClipboard(buttonEl) {
  if (!currentSummaryData) {
    showError('No summary available to copy.');
    return;
  }

  const textToCopy = formatSummaryAsMarkdown(currentSummaryData);
  try {
    await navigator.clipboard.writeText(textToCopy);
    showToast('Summary copied to clipboard!', 'success');

    const originalHtml = buttonEl.innerHTML;
    buttonEl.innerHTML = `<span>✓</span><span>Copied!</span>`;
    buttonEl.classList.add('btn-primary');
    setTimeout(() => {
      buttonEl.innerHTML = originalHtml;
      buttonEl.classList.remove('btn-primary');
    }, 2000);
  } catch (err) {
    fallbackCopyText(textToCopy);
  }
}

function fallbackCopyText(text) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand('copy');
    showToast('Summary copied to clipboard!', 'success');
  } catch (err) {
    showError('Could not copy to clipboard automatically.');
  }
  document.body.removeChild(textArea);
}

function downloadSummaryFile() {
  if (!currentSummaryData) {
    showError('No summary available to download.');
    return;
  }

  const mdContent = formatSummaryAsMarkdown(currentSummaryData);
  const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `notes-summary-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();

  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 100);

  showToast('Downloaded notes-summary.md', 'success');
}

function handleClearAll() {
  notesInput.value = '';
  updateTextCounts();
  handleRemoveFile();
  hideError();
  resultsCard.classList.add('hidden');
  currentSummaryData = null;

  // Clear quiz and doubts
  currentQuiz = null;
  userQuizAnswers = {};
  doubtConversationHistory = [];
  initDoubtChatWelcome();

  syncNotesState();
  showToast('Notes and study data cleared.', 'success');
  notesInput.focus();
}

/* ==========================================================================
   Quiz Session Logic
   ========================================================================== */
function setupQuizActions() {
  // Question Count Pills
  if (quizCountGroup) {
    quizCountGroup.querySelectorAll('.pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        quizCountGroup.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        quizNumQuestions = Number(btn.getAttribute('data-count')) || 5;
      });
    });
  }

  // Difficulty Pills
  if (quizDiffGroup) {
    quizDiffGroup.querySelectorAll('.pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        quizDiffGroup.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        quizDifficulty = btn.getAttribute('data-diff') || 'Medium';
      });
    });
  }

  // Start Quiz Button
  if (startQuizBtn) {
    startQuizBtn.addEventListener('click', handleGenerateQuiz);
  }

  // Next Question Button
  if (nextQuestionBtn) {
    nextQuestionBtn.addEventListener('click', handleNextQuizQuestion);
  }

  // Quit Quiz Button
  if (quitQuizBtn) {
    quitQuizBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to quit the current quiz session?')) {
        currentQuiz = null;
        userQuizAnswers = {};
        quizActiveCard.classList.add('hidden');
        quizResultsCard.classList.add('hidden');
        quizSetupCard.classList.remove('hidden');
      }
    });
  }

  // Results Actions: Retry Quiz & Generate New Quiz
  if (retryQuizBtn) {
    retryQuizBtn.addEventListener('click', handleRetryQuiz);
  }
  if (newQuizBtn) {
    newQuizBtn.addEventListener('click', () => {
      currentQuiz = null;
      userQuizAnswers = {};
      quizResultsCard.classList.add('hidden');
      quizSetupCard.classList.remove('hidden');
    });
  }

  // Review Filter Pills
  if (reviewFilterGroup) {
    reviewFilterGroup.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        reviewFilterGroup.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        quizReviewFilter = btn.getAttribute('data-filter') || 'all';
        renderQuizReviewCards();
      });
    });
  }
}

async function handleGenerateQuiz() {
  const notes = getNotesText();
  hideError();

  if (!notes || getNotesWordCount() < 5) {
    showError('Please provide notes first before generating a quiz.');
    switchMode('summarize');
    return;
  }

  try {
    setQuizLoadingState(true);

    const response = await fetch('/api/quiz', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notes,
        numQuestions: quizNumQuestions,
        difficulty: quizDifficulty
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to generate quiz questions.');
    }

    currentQuiz = data.quiz;
    currentQuestionIndex = 0;
    userQuizAnswers = {};

    quizSetupCard.classList.add('hidden');
    quizResultsCard.classList.add('hidden');
    quizActiveCard.classList.remove('hidden');

    renderActiveQuestion();
    showToast(`Quiz generated! ${currentQuiz.questions.length} questions ready.`, 'success');
  } catch (err) {
    console.error('Quiz generation error:', err);
    showError(err.message || 'Could not generate quiz from notes.');
  } finally {
    setQuizLoadingState(false);
  }
}

function setQuizLoadingState(loading) {
  isGeneratingQuiz = loading;
  if (loading) {
    quizSetupCard.classList.add('hidden');
    quizActiveCard.classList.add('hidden');
    quizResultsCard.classList.add('hidden');
    quizLoadingCard.classList.remove('hidden');
  } else {
    quizLoadingCard.classList.add('hidden');
  }
}

function renderActiveQuestion() {
  if (!currentQuiz || !currentQuiz.questions || !currentQuiz.questions[currentQuestionIndex]) return;

  const total = currentQuiz.questions.length;
  const q = currentQuiz.questions[currentQuestionIndex];
  const qNum = currentQuestionIndex + 1;

  quizTopicBadge.textContent = currentQuiz.topic || 'Study Notes Quiz';
  quizDifficultyBadge.textContent = currentQuiz.difficulty || 'Medium';
  quizTypeBadge.textContent = q.type === 'true_false' ? 'True / False' : 'Multiple Choice';

  quizCurrentNum.textContent = qNum;
  quizTotalNum.textContent = total;

  const progressPct = Math.round((qNum / total) * 100);
  quizProgressBar.style.width = `${progressPct}%`;

  quizQuestionText.textContent = q.question;

  quizOptionsContainer.innerHTML = '';
  const selectedAnswer = userQuizAnswers[q.id];

  q.options.forEach((opt, idx) => {
    const isSelected = selectedAnswer === opt;
    const badgeLetter = q.type === 'true_false'
      ? (opt.toLowerCase() === 'true' ? 'T' : 'F')
      : String.fromCharCode(65 + idx);

    const card = document.createElement('div');
    card.className = `quiz-option-card ${isSelected ? 'selected' : ''}`;
    card.tabIndex = 0;
    card.setAttribute('role', 'radio');
    card.setAttribute('aria-checked', isSelected ? 'true' : 'false');
    card.innerHTML = `
      <span class="option-badge">${badgeLetter}</span>
      <span class="option-text">${escapeHtml(opt)}</span>
    `;

    const selectOption = () => {
      userQuizAnswers[q.id] = opt;
      quizOptionsContainer.querySelectorAll('.quiz-option-card').forEach(c => {
        c.classList.remove('selected');
        c.setAttribute('aria-checked', 'false');
      });
      card.classList.add('selected');
      card.setAttribute('aria-checked', 'true');
      nextQuestionBtn.disabled = false;
    };

    card.addEventListener('click', selectOption);
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectOption();
      }
    });

    quizOptionsContainer.appendChild(card);
  });

  // Next button text & disabled state
  const isLast = qNum === total;
  nextQuestionBtn.innerHTML = isLast
    ? `<span>Submit &amp; View Results</span><span>✓</span>`
    : `<span>Next Question</span><span>→</span>`;
  nextQuestionBtn.disabled = !selectedAnswer;
}

function handleNextQuizQuestion() {
  if (!currentQuiz) return;

  const total = currentQuiz.questions.length;
  if (currentQuestionIndex < total - 1) {
    currentQuestionIndex++;
    renderActiveQuestion();
  } else {
    // End of quiz -> render results
    renderQuizResults();
  }
}

function renderQuizResults() {
  quizActiveCard.classList.add('hidden');
  quizResultsCard.classList.remove('hidden');

  const questions = currentQuiz.questions;
  let correctCount = 0;

  questions.forEach(q => {
    const userAnswer = userQuizAnswers[q.id];
    if (userAnswer && userAnswer.trim().toLowerCase() === q.correctAnswer.trim().toLowerCase()) {
      correctCount++;
    }
  });

  const total = questions.length;
  const incorrectCount = total - correctCount;
  const percentage = Math.round((correctCount / total) * 100);

  scorePercentageText.textContent = `${percentage}%`;
  scoreFraction.textContent = `You scored ${correctCount} out of ${total} questions correctly.`;
  statCorrect.textContent = correctCount;
  statIncorrect.textContent = incorrectCount;

  scorePercentageCircle.className = 'score-circle';
  if (percentage >= 70) {
    scorePercentageCircle.classList.add('pass');
    scoreTitle.textContent = 'Outstanding Performance! 🌟';
  } else if (percentage >= 50) {
    scoreTitle.textContent = 'Solid Effort! 👍';
  } else {
    scorePercentageCircle.classList.add('fail');
    scoreTitle.textContent = 'Keep Studying! 📚';
  }

  // Render review questions list
  renderQuizReviewCards();
  quizResultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderQuizReviewCards() {
  if (!currentQuiz) return;
  quizReviewList.innerHTML = '';

  const questions = currentQuiz.questions;

  questions.forEach((q, idx) => {
    const userAnswer = userQuizAnswers[q.id];
    const isCorrect = userAnswer && userAnswer.trim().toLowerCase() === q.correctAnswer.trim().toLowerCase();

    if (quizReviewFilter === 'correct' && !isCorrect) return;
    if (quizReviewFilter === 'incorrect' && isCorrect) return;

    const card = document.createElement('div');
    card.className = `review-card ${isCorrect ? 'correct' : 'incorrect'}`;

    card.innerHTML = `
      <div class="review-card-top">
        <span class="badge-subtle">Question ${idx + 1} • ${q.type === 'true_false' ? 'True/False' : 'Multiple Choice'}</span>
        <span class="review-status-tag ${isCorrect ? 'correct' : 'incorrect'}">
          ${isCorrect ? '✓ Correct' : '✕ Incorrect'}
        </span>
      </div>
      <div class="review-question">${escapeHtml(q.question)}</div>
      <div class="review-answer-row">
        <div class="user-answer ${isCorrect ? 'correct' : 'wrong'}">
          <strong>Your Answer:</strong> ${escapeHtml(userAnswer || 'No answer selected')}
        </div>
        ${!isCorrect ? `
          <div class="correct-answer-ref">
            <strong>Correct Answer:</strong> ${escapeHtml(q.correctAnswer)}
          </div>
        ` : ''}
      </div>
      <div class="review-explanation">
        <strong>Explanation:</strong> ${escapeHtml(q.explanation)}
      </div>
    `;

    quizReviewList.appendChild(card);
  });
}

function handleRetryQuiz() {
  if (!currentQuiz) return;
  userQuizAnswers = {};
  currentQuestionIndex = 0;
  quizResultsCard.classList.add('hidden');
  quizActiveCard.classList.remove('hidden');
  renderActiveQuestion();
  showToast('Quiz reset! Give it another shot.', 'info');
}

/* ==========================================================================
   Doubt Clarification Logic (AI Study Tutor)
   ========================================================================== */
function setupDoubtActions() {
  if (doubtForm) {
    doubtForm.addEventListener('submit', handleDoubtSubmit);
  }

  if (doubtInput) {
    doubtInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleDoubtSubmit(e);
      }
    });
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      doubtConversationHistory = [];
      initDoubtChatWelcome();
      showToast('Conversation cleared.', 'info');
    });
  }

  // Suggestion chips
  document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const promptText = chip.textContent.replace(/^[^a-zA-Z]+/, '').trim();
      if (doubtInput) {
        doubtInput.value = promptText;
        doubtInput.focus();
      }
    });
  });
}

function initDoubtChatWelcome() {
  if (!doubtMessagesContainer) return;
  doubtMessagesContainer.innerHTML = `
    <div class="doubt-message tutor">
      <div class="message-avatar">🎓</div>
      <div class="message-body">
        <p><strong>Hello! I'm your AI Study Tutor.</strong></p>
        <p>Ask me any question or doubt about your loaded study notes (for example: <em>"I don't understand what this means"</em>, <em>"Can you give me a real-world example?"</em>, or <em>"Explain this step-by-step"</em>).</p>
        <p>I will guide you with clear, student-friendly explanations and maintain context as you ask follow-up questions!</p>
      </div>
    </div>
  `;
}

async function handleDoubtSubmit(e) {
  if (e) e.preventDefault();
  if (isAskingDoubt) return;

  const notes = getNotesText();
  const question = doubtInput ? doubtInput.value.trim() : '';

  if (!notes || getNotesWordCount() < 5) {
    showError('Please enter notes in the Summarize tab before asking doubts.');
    switchMode('summarize');
    return;
  }

  if (!question) {
    doubtInput.focus();
    return;
  }

  // Append user message
  appendDoubtMessage('user', question);
  doubtInput.value = '';

  // Append typing indicator
  const typingIndicator = appendTypingIndicator();

  try {
    setDoubtSendingState(true);

    const response = await fetch('/api/doubt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notes,
        question,
        history: doubtConversationHistory
      })
    });

    const data = await response.json();
    removeTypingIndicator(typingIndicator);

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to clarify doubt.');
    }

    // Record in history for follow-up turns
    doubtConversationHistory.push({ role: 'user', content: question });
    doubtConversationHistory.push({ role: 'assistant', content: data.answer });

    // Append tutor response
    appendDoubtMessage('tutor', data.answer, data.inNotes);
  } catch (err) {
    removeTypingIndicator(typingIndicator);
    console.error('Doubt error:', err);
    appendDoubtMessage('tutor', `⚠️ Error: ${err.message || 'Unable to get response. Please try again.'}`);
  } finally {
    setDoubtSendingState(false);
  }
}

function appendDoubtMessage(role, content, inNotes = true) {
  if (!doubtMessagesContainer) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = `doubt-message ${role}`;

  const avatar = role === 'user' ? '👤' : '🎓';

  let formattedContent = formatChatMessage(content);

  // If tutor and concept was not in the notes
  const notInNotesNotice = (role === 'tutor' && inNotes === false)
    ? `<div class="out-of-notes-pill">ℹ️ Extended explanation (not in notes)</div>`
    : '';

  msgDiv.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      ${notInNotesNotice}
      ${formattedContent}
    </div>
  `;

  doubtMessagesContainer.appendChild(msgDiv);
  doubtMessagesContainer.scrollTop = doubtMessagesContainer.scrollHeight;
}

function appendTypingIndicator() {
  if (!doubtMessagesContainer) return null;
  const indicator = document.createElement('div');
  indicator.className = 'doubt-message tutor typing-indicator-wrap';
  indicator.innerHTML = `
    <div class="message-avatar">🎓</div>
    <div class="message-body">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  `;
  doubtMessagesContainer.appendChild(indicator);
  doubtMessagesContainer.scrollTop = doubtMessagesContainer.scrollHeight;
  return indicator;
}

function removeTypingIndicator(el) {
  if (el && el.parentNode) {
    el.parentNode.removeChild(el);
  }
}

function setDoubtSendingState(sending) {
  isAskingDoubt = sending;
  if (sendDoubtBtn) sendDoubtBtn.disabled = sending;
  if (doubtSendSpinner) doubtSendSpinner.classList.toggle('hidden', !sending);
  if (doubtSendIcon) doubtSendIcon.classList.toggle('hidden', sending);
}

function formatChatMessage(text) {
  if (!text) return '';

  const paragraphs = text.split(/\n\s*\n/);
  return paragraphs.map(p => {
    let formatted = escapeHtml(p.trim());

    // Bold formatting **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Bullet points
    if (formatted.includes('\n- ') || formatted.startsWith('- ')) {
      const items = formatted.split(/\n- |- /).filter(Boolean);
      return `<ul>${items.map(it => `<li>${it.trim()}</li>`).join('')}</ul>`;
    }

    // Numbered lists
    if (/^\d+\.\s/m.test(formatted)) {
      const items = formatted.split(/\n\d+\.\s|^\d+\.\s/).filter(Boolean);
      return `<ol>${items.map(it => `<li>${it.trim()}</li>`).join('')}</ol>`;
    }

    return `<p>${formatted.replace(/\n/g, '<br>')}</p>`;
  }).join('');
}

/* ==========================================================================
   Global Shortcuts & Utilities
   ========================================================================== */
function setupGlobalShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to trigger summarize when focused in textarea
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && document.activeElement === notesInput) {
      e.preventDefault();
      handleSummarize();
    }
  });
}

function showError(message) {
  if (!errorMessageEl || !errorBanner) return;
  errorMessageEl.textContent = message;
  errorBanner.classList.remove('hidden');
  errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  if (errorBanner) errorBanner.classList.add('hidden');
}

function showToast(message, type = 'info') {
  if (!toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <span>${escapeHtml(message)}</span>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 250);
  }, 3000);
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
