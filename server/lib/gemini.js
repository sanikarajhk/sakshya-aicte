const { GoogleGenerativeAI, SchemaType } = require('@google/generative-ai');

function isApiKeyConfigured(apiKey) {
  if (!apiKey || typeof apiKey !== 'string') return false;
  const trimmed = apiKey.trim();
  return trimmed !== '' && !trimmed.startsWith('your_') && trimmed !== 'your_api_key_here';
}

/**
 * Validates and retrieves the Gemini API client.
 * Reads GEMINI_API_KEY strictly from the environment variable.
 */
function getGenAIClient() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!isApiKeyConfigured(apiKey)) {
    const error = new Error('GEMINI_API_KEY is not configured. Please set a valid API key in your .env file or environment variables.');
    error.status = 400;
    error.code = 'MISSING_API_KEY';
    throw error;
  }
  return new GoogleGenerativeAI(apiKey.trim());
}

/**
 * Summarizes the provided notes into structured sections:
 * - shortSummary
 * - detailedSummary
 * - keyPoints
 * - importantTerms
 * - 5 review questions
 * 
 * @param {string} text - The input notes to summarize
 * @returns {Promise<Object>} Structured summary
 */
async function summarizeNotes(text) {
  if (!text || typeof text !== 'string' || text.trim().length === 0) {
    const error = new Error('No notes provided for summarization.');
    error.status = 400;
    throw error;
  }

  const genAI = getGenAIClient();
  const preferredModel = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
  const candidateModels = Array.from(new Set([
    preferredModel,
    'gemini-3.5-flash-lite',
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.5-flash'
  ]));

  const schema = {
    type: SchemaType.OBJECT,
    properties: {
      shortSummary: {
        type: SchemaType.STRING,
        description: 'A concise 2-3 sentence overview highlighting the central message and purpose of the notes.'
      },
      detailedSummary: {
        type: SchemaType.STRING,
        description: 'A comprehensive, well-structured, multi-paragraph detailed summary explaining core arguments, context, and conclusions.'
      },
      keyPoints: {
        type: SchemaType.ARRAY,
        items: {
          type: SchemaType.STRING
        },
        description: 'A list of distinct, bulleted key takeaways and essential takeaways from the notes.'
      },
      importantTerms: {
        type: SchemaType.ARRAY,
        items: {
          type: SchemaType.OBJECT,
          properties: {
            term: {
              type: SchemaType.STRING,
              description: 'The keyword, technical term, or concept.'
            },
            definition: {
              type: SchemaType.STRING,
              description: 'A clear and concise definition or explanation of the term based on the notes.'
            }
          },
          required: ['term', 'definition']
        },
        description: 'Crucial terms, concepts, vocabulary, or formulas mentioned in the notes with explanations.'
      },
      questions: {
        type: SchemaType.ARRAY,
        items: {
          type: SchemaType.OBJECT,
          properties: {
            question: {
              type: SchemaType.STRING,
              description: 'A thoughtful comprehension or self-study question covering a major concept in the notes.'
            },
            answer: {
              type: SchemaType.STRING,
              description: 'The correct answer and brief explanation based on the notes.'
            }
          },
          required: ['question', 'answer']
        },
        description: 'Exactly 5 self-study or comprehension review questions derived directly from the notes to test understanding.'
      }
    },
    required: ['shortSummary', 'detailedSummary', 'keyPoints', 'importantTerms', 'questions']
  };

  const prompt = `You are an expert academic and professional notes summarizer.
Analyze the following notes thoroughly and produce a structured, high-quality summary in JSON format according to the requested schema.

Guidelines:
1. "shortSummary": Provide a crisp, clear 2-3 sentence overview.
2. "detailedSummary": Provide an in-depth, coherent explanation covering all major aspects of the notes.
3. "keyPoints": Provide 4 to 8 critical takeaways as clear statements.
4. "importantTerms": Identify 3 to 8 key terms, acronyms, or concepts and provide clear, contextual definitions.
5. "questions": Generate EXACTLY 5 high-quality review/comprehension questions with accurate answers based strictly on the content of the notes.

Input Notes:
---
${text}
---`;

  let lastError = null;

  for (const modelCandidate of candidateModels) {
    try {
      const model = genAI.getGenerativeModel({
        model: modelCandidate,
        generationConfig: {
          responseMimeType: 'application/json',
          responseSchema: schema,
          temperature: 0.2
        }
      });

      const result = await model.generateContent(prompt);
      const response = await result.response;
      const rawText = response.text();

      // Clean JSON text if wrapped in markdown code fences
      let cleanedText = rawText.trim();
      if (cleanedText.startsWith('```json')) {
        cleanedText = cleanedText.slice(7);
      } else if (cleanedText.startsWith('```')) {
        cleanedText = cleanedText.slice(3);
      }
      if (cleanedText.endsWith('```')) {
        cleanedText = cleanedText.slice(0, -3);
      }
      cleanedText = cleanedText.trim();

      const parsed = JSON.parse(cleanedText);
      return sanitizeSummary(parsed);
    } catch (err) {
      console.warn(`Model '${modelCandidate}' failed: ${err.message}`);
      lastError = err;

      // If invalid API key, fail immediately without trying other models
      if (err.message && err.message.includes('API_KEY_INVALID')) {
        const error = new Error('The configured GEMINI_API_KEY is invalid. Please check your API key in .env');
        error.status = 401;
        throw error;
      }

      // Continue to next model candidate if 404, 503, or service unavailable
      if (err.status === 404 || err.status === 503 || (err.message && (err.message.includes('503') || err.message.includes('404')))) {
        continue;
      }

      // For other critical errors, rethrow
      throw err;
    }
  }

  // If all candidate models failed, throw enhanced error
  if (lastError) {
    if (lastError.message && (lastError.message.includes('quota') || lastError.status === 429)) {
      const error = new Error('Gemini API rate limit or quota exceeded. Please wait a moment and try again.');
      error.status = 429;
      throw error;
    }
    throw lastError;
  }
}

/**
 * Sanitizes and guarantees the structure of the summary output.
 */
function sanitizeSummary(data) {
  const shortSummary = typeof data.shortSummary === 'string' ? data.shortSummary.trim() : 'Summary not available.';
  const detailedSummary = typeof data.detailedSummary === 'string' ? data.detailedSummary.trim() : shortSummary;

  let keyPoints = [];
  if (Array.isArray(data.keyPoints)) {
    keyPoints = data.keyPoints.map(p => (typeof p === 'string' ? p.trim() : JSON.stringify(p))).filter(Boolean);
  }

  let importantTerms = [];
  if (Array.isArray(data.importantTerms)) {
    importantTerms = data.importantTerms
      .map(item => ({
        term: item.term ? String(item.term).trim() : 'Concept',
        definition: item.definition ? String(item.definition).trim() : ''
      }))
      .filter(item => item.term && item.definition);
  }

  let questions = [];
  if (Array.isArray(data.questions)) {
    questions = data.questions
      .map((q, idx) => ({
        question: q.question ? String(q.question).trim() : `Review Question ${idx + 1}`,
        answer: q.answer ? String(q.answer).trim() : 'Refer to the notes.'
      }))
      .filter(q => q.question);
  }

  // Ensure exactly 5 questions if possible, or trim to 5
  if (questions.length > 5) {
    questions = questions.slice(0, 5);
  }

  return {
    shortSummary,
    detailedSummary,
    keyPoints,
    importantTerms,
    questions
  };
}

/**
 * Cleans markdown code fences around JSON outputs.
 */
function cleanJsonText(rawText) {
  let cleaned = rawText.trim();
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.slice(7);
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.slice(3);
  }
  if (cleaned.endsWith('```')) {
    cleaned = cleaned.slice(0, -3);
  }
  return cleaned.trim();
}

/**
 * Generates an interactive quiz based strictly on the provided notes.
 * 
 * @param {Object} params
 * @param {string} params.notes - Source notes text
 * @param {number} [params.numQuestions=5] - 5, 10, or 15 questions
 * @param {string} [params.difficulty='Medium'] - 'Easy', 'Medium', or 'Hard'
 * @returns {Promise<Object>} Quiz object with topic, difficulty, and questions
 */
async function generateQuiz({ notes, numQuestions = 5, difficulty = 'Medium' }) {
  if (!notes || typeof notes !== 'string' || notes.trim().length === 0) {
    const error = new Error('No notes provided for quiz generation.');
    error.status = 400;
    throw error;
  }

  const validCounts = [5, 10, 15];
  const count = validCounts.includes(Number(numQuestions)) ? Number(numQuestions) : 5;

  const validDifficulties = ['Easy', 'Medium', 'Hard'];
  const diff = validDifficulties.includes(difficulty) ? difficulty : 'Medium';

  const genAI = getGenAIClient();
  const preferredModel = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
  const candidateModels = Array.from(new Set([
    preferredModel,
    'gemini-3.5-flash-lite',
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.5-flash'
  ]));

  const quizSchema = {
    type: SchemaType.OBJECT,
    properties: {
      topic: {
        type: SchemaType.STRING,
        description: 'A brief 2-5 word topic or title for the quiz derived from the notes'
      },
      difficulty: {
        type: SchemaType.STRING,
        description: 'The difficulty level of the quiz (Easy, Medium, Hard)'
      },
      questions: {
        type: SchemaType.ARRAY,
        items: {
          type: SchemaType.OBJECT,
          properties: {
            id: {
              type: SchemaType.INTEGER,
              description: 'Question number index starting at 1'
            },
            type: {
              type: SchemaType.STRING,
              description: 'Must be either "multiple_choice" or "true_false"'
            },
            question: {
              type: SchemaType.STRING,
              description: 'The question text, derived ONLY from facts and concepts in the notes'
            },
            options: {
              type: SchemaType.ARRAY,
              items: {
                type: SchemaType.STRING
              },
              description: 'For "multiple_choice", exactly 4 distinct choices. For "true_false", exactly ["True", "False"].'
            },
            correctAnswer: {
              type: SchemaType.STRING,
              description: 'The exact string matching one of the choices in the options array.'
            },
            explanation: {
              type: SchemaType.STRING,
              description: 'A clear, educational explanation based on the notes explaining why this answer is correct and others are incorrect.'
            }
          },
          required: ['id', 'type', 'question', 'options', 'correctAnswer', 'explanation']
        },
        description: `Array of exactly ${count} quiz questions.`
      }
    },
    required: ['topic', 'difficulty', 'questions']
  };

  const prompt = `You are an expert educational quiz creator.
Generate an interactive quiz based STRICTLY and ONLY on the provided study notes.

PARAMETERS:
- Number of Questions: Exactly ${count}
- Difficulty Level: ${diff}
- Source Material: Read the notes below carefully.

RULES & CONSTRAINTS:
1. STRICT SOURCE FIDELITY: Every question, answer, and explanation must be directly verifiable in the provided notes. Do NOT invent concepts, outside trivia, or details not present in the notes.
2. MIXTURE OF QUESTION TYPES: Provide a balanced mix of:
   - Multiple-Choice Questions (type: "multiple_choice") with 4 distinct options.
   - True/False Questions (type: "true_false") with options ["True", "False"].
3. DIFFICULTY CALIBRATION:
   - Easy: Direct recall of clear definitions, terms, or prominent facts stated in the notes.
   - Medium: Conceptual understanding, cause-and-effect, and comparisons between ideas in the notes.
   - Hard: In-depth synthesis, distinguishing nuanced differences, or analyzing implications stated in the notes.
4. EXPLANATION: Write a helpful explanation for each question citing the concept from the notes.

Input Notes:
---
${notes}
---`;

  let lastError = null;

  for (const modelCandidate of candidateModels) {
    try {
      const model = genAI.getGenerativeModel({
        model: modelCandidate,
        generationConfig: {
          responseMimeType: 'application/json',
          responseSchema: quizSchema,
          temperature: 0.3
        }
      });

      const result = await model.generateContent(prompt);
      const response = await result.response;
      const rawText = response.text();

      const cleanedText = cleanJsonText(rawText);
      const parsed = JSON.parse(cleanedText);
      return sanitizeQuiz(parsed, count, diff);
    } catch (err) {
      console.warn(`Model '${modelCandidate}' failed for quiz: ${err.message}`);
      lastError = err;

      if (err.message && err.message.includes('API_KEY_INVALID')) {
        const error = new Error('The configured GEMINI_API_KEY is invalid. Please check your API key in .env');
        error.status = 401;
        throw error;
      }

      if (err.status === 404 || err.status === 503 || (err.message && (err.message.includes('503') || err.message.includes('404')))) {
        continue;
      }

      throw err;
    }
  }

  if (lastError) {
    if (lastError.message && (lastError.message.includes('quota') || lastError.status === 429)) {
      const error = new Error('Gemini API rate limit or quota exceeded. Please wait a moment and try again.');
      error.status = 429;
      throw error;
    }
    throw lastError;
  }
}

/**
 * Sanitizes and validates the generated quiz structure.
 */
function sanitizeQuiz(data, requestedCount, requestedDifficulty) {
  const topic = data.topic ? String(data.topic).trim() : 'Study Notes Quiz';
  const difficulty = requestedDifficulty;

  let rawQuestions = Array.isArray(data.questions) ? data.questions : [];
  let sanitizedQuestions = [];

  rawQuestions.forEach((q, idx) => {
    if (!q || !q.question) return;

    const type = (q.type && q.type.toLowerCase().includes('true')) ? 'true_false' : 'multiple_choice';
    let options = [];

    if (type === 'true_false') {
      options = ['True', 'False'];
    } else {
      if (Array.isArray(q.options) && q.options.length >= 2) {
        options = q.options.map(opt => String(opt).trim()).filter(Boolean);
      }
      if (options.length < 4) {
        // Ensure 4 options for MCQ
        while (options.length < 4) {
          options.push(`Option ${String.fromCharCode(65 + options.length)}`);
        }
      }
      if (options.length > 4) {
        options = options.slice(0, 4);
      }
    }

    // Match correct answer accurately
    let correctAnswer = String(q.correctAnswer || '').trim();
    const matchingOption = options.find(opt => opt.toLowerCase() === correctAnswer.toLowerCase());
    if (matchingOption) {
      correctAnswer = matchingOption;
    } else {
      correctAnswer = options[0];
    }

    const explanation = q.explanation ? String(q.explanation).trim() : `Based on the provided notes, "${correctAnswer}" is the correct answer.`;

    sanitizedQuestions.push({
      id: idx + 1,
      type,
      question: String(q.question).trim(),
      options,
      correctAnswer,
      explanation
    });
  });

  // Re-index and slice to requested count if more returned
  if (sanitizedQuestions.length > requestedCount) {
    sanitizedQuestions = sanitizedQuestions.slice(0, requestedCount);
  }

  sanitizedQuestions.forEach((q, i) => {
    q.id = i + 1;
  });

  if (sanitizedQuestions.length === 0) {
    throw new Error('Could not generate valid quiz questions from the provided notes.');
  }

  return {
    topic,
    difficulty,
    totalQuestions: sanitizedQuestions.length,
    questions: sanitizedQuestions
  };
}

/**
 * Answers student questions and clarifies doubts based primarily on the notes.
 * 
 * @param {Object} params
 * @param {string} params.notes - Source notes text
 * @param {string} params.question - Student question or doubt
 * @param {Array} [params.history=[]] - Previous conversation history
 * @returns {Promise<Object>} Tutor answer response
 */
async function clarifyDoubt({ notes, question, history = [] }) {
  if (!notes || typeof notes !== 'string' || notes.trim().length === 0) {
    const error = new Error('No notes provided for context.');
    error.status = 400;
    throw error;
  }

  if (!question || typeof question !== 'string' || question.trim().length === 0) {
    const error = new Error('Please enter a question or doubt.');
    error.status = 400;
    throw error;
  }

  const genAI = getGenAIClient();
  const preferredModel = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
  const candidateModels = Array.from(new Set([
    preferredModel,
    'gemini-3.5-flash-lite',
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.5-flash'
  ]));

  // Format previous history if provided
  let formattedHistory = '';
  if (Array.isArray(history) && history.length > 0) {
    formattedHistory = history
      .slice(-8) // Keep last 8 turns for relevant context window
      .map(h => `${h.role === 'user' ? 'Student' : 'AI Tutor'}: ${h.content}`)
      .join('\n\n');
  }

  const prompt = `You are a patient, supportive, and expert AI Study Tutor.
A student is asking for clarification or asking a question about their study notes.

STUDENT'S SOURCE NOTES:
==========================================
${notes}
==========================================
${formattedHistory ? `\nPREVIOUS CONVERSATION CONTEXT:\n${formattedHistory}\n` : ''}
STUDENT'S QUESTION:
"${question.trim()}"

YOUR INSTRUCTIONS:
1. PRIMARY CONTEXT: Use the provided source notes as your primary source of truth.
2. SIMPLE STUDENT-FRIENDLY TONE: Explain the concept in clear, intuitive, and engaging language. Avoid unnecessary jargon; if technical terms are necessary, define them simply.
3. CONCRETE EXAMPLES: Provide a practical, real-world example or analogy to make the concept memorable whenever useful.
4. STEP-BY-STEP BREAKDOWNS: If the concept involves a workflow, process, calculation, or multi-part mechanism, explain it clearly in numbered steps.
5. OUT-OF-NOTES CONCEPTS: If the student asks about something that is NOT mentioned or covered in their provided notes, you MUST start your answer with this exact sentence:
   "This concept is not mentioned in your provided notes. However, here is a general explanation: "
   and then provide a clear, accurate, and student-friendly general explanation.
6. FOLLOW-UP READINESS: If this is a follow-up question referencing earlier points, maintain conversational continuity smoothly.`;

  let lastError = null;

  for (const modelCandidate of candidateModels) {
    try {
      const model = genAI.getGenerativeModel({
        model: modelCandidate,
        generationConfig: {
          temperature: 0.3
        }
      });

      const result = await model.generateContent(prompt);
      const response = await result.response;
      const answerText = response.text().trim();

      const notInNotes = answerText.toLowerCase().includes('this concept is not mentioned in your provided notes');

      return {
        answer: answerText,
        inNotes: !notInNotes
      };
    } catch (err) {
      console.warn(`Model '${modelCandidate}' failed for doubt: ${err.message}`);
      lastError = err;

      if (err.message && err.message.includes('API_KEY_INVALID')) {
        const error = new Error('The configured GEMINI_API_KEY is invalid. Please check your API key in .env');
        error.status = 401;
        throw error;
      }

      if (err.status === 404 || err.status === 503 || (err.message && (err.message.includes('503') || err.message.includes('404')))) {
        continue;
      }

      throw err;
    }
  }

  if (lastError) {
    if (lastError.message && (lastError.message.includes('quota') || lastError.status === 429)) {
      const error = new Error('Gemini API rate limit or quota exceeded. Please wait a moment and try again.');
      error.status = 429;
      throw error;
    }
    throw lastError;
  }
}

module.exports = {
  summarizeNotes,
  generateQuiz,
  clarifyDoubt,
  getGenAIClient,
  isApiKeyConfigured
};
