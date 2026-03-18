const API_BASE = 'http://localhost/api/v1';

// DOM Elements
const views = {
    login: document.getElementById('login-view'),
    dashboard: document.getElementById('dashboard-view'),
    exam: document.getElementById('exam-view'),
    breakdown: document.getElementById('breakdown-view')
};

const state = {
    token: localStorage.getItem('access_token') || null,
    exams: [],
    currentExamData: null,
    currentSubmissionId: null,
    activeSectionIndex: 0
};

// Initialization
function init() {
    if (state.token) {
        const savedUsername = localStorage.getItem('username');
        if (savedUsername) {
            document.getElementById('user-display').textContent = savedUsername;
            document.getElementById('user-display').classList.remove('hidden');
        }
        showView('dashboard');
        fetchExams();
    } else {
        showView('login');
    }
}

function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');
    
    if(viewName !== 'login') {
        document.getElementById('logout-btn').classList.remove('hidden');
    } else {
        document.getElementById('logout-btn').classList.add('hidden');
    }
}

// Ensure JWT is attached to requests
async function apiFetch(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    // For FormData (audio uploads)
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: { ...headers, ...options.headers }
    });

    if (response.status === 401) {
        // Token expired
        logout();
        throw new Error('Unauthorized');
    }
    return response;
}

// ----------------- AUTHENTICATION -----------------

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const res = await fetch(`${API_BASE}/auth/token/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });

        if (res.ok) {
            const data = await res.json();
            state.token = data.access;
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('username', username);
            document.getElementById('login-error').classList.add('hidden');
            document.getElementById('user-display').textContent = username;
            document.getElementById('user-display').classList.remove('hidden');
            
            showView('dashboard');
            fetchExams();
        } else {
            document.getElementById('login-error').classList.remove('hidden');
        }
    } catch (err) {
        console.error("Login failed", err);
    }
});

function logout() {
    state.token = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    document.getElementById('user-display').classList.add('hidden');
    showView('login');
}

document.getElementById('logout-btn').addEventListener('click', logout);


// ----------------- DASHBOARD -----------------

async function fetchExams() {
    try {
        // 1. Fetch exams
        const res = await apiFetch('/exams/');
        if (!res.ok) return;
        let data = await res.json();
        
        // Handle DRF Pagination
        if (data.results) {
            data = data.results;
        }

        // 2. Fetch user's submissions to know what's completed
        const subRes = await apiFetch('/submissions/');
        let userSubmissions = [];
        if (subRes.ok) {
            const subData = await subRes.json();
            userSubmissions = subData.results ? subData.results : subData;
        }
        
        const container = document.getElementById('exams-container');
        container.innerHTML = '';
        
        if (!data || data.length === 0) {
            container.innerHTML = '<p class="text-muted">No exams available currently.</p>';
            return;
        }

        data.forEach(exam => {
            // Check if user has a completed submission for this exam
            const submission = userSubmissions.find(s => s.exam === exam.id);
            const isCompleted = submission && (submission.status === 'COMPLETED' || submission.status === 'GRADING');
            
            const card = document.createElement('div');
            card.className = `exam-card ${isCompleted ? 'completed-card' : ''}`;
            
            let actionHtml = `<button class="btn btn-outline w-100" onclick="startExam('${exam.id}')">Start Exam</button>`;
            
            if (isCompleted) {
                if (submission.status === 'COMPLETED') {
                    actionHtml = `
                        <div class="w-100 mt-auto pt-3">
                            <button class="btn btn-primary w-100" style="background-color: #10b981;" onclick="showScoreBreakdown('${submission.id}')">
                                View Final Score
                            </button>
                        </div>
                    `;
                } else {
                    actionHtml = `<div class="completion-status text-muted text-center w-100 mt-auto pt-4 fw-bold">Grading in progress...</div>`;
                }
            }

            card.innerHTML = `
                <div class="exam-title">${exam.title}</div>
                <div class="exam-meta">
                    <span>⏱ ${exam.duration_minutes} mins</span>
                    <span>🏅 ${exam.total_marks} marks</span>
                </div>
                ${actionHtml}
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("fetchExams failed:", e);
    }
}


// ----------------- EXAM LOGIC -----------------

async function startExam(examId) {
    // 1. Fetch full exam nested structure
    const examRes = await apiFetch(`/exams/${examId}/`);
    const examData = await examRes.json();
    state.currentExamData = examData;

    // 2. Create an ExamSubmission on backend
    const subRes = await apiFetch('/submissions/', {
        method: 'POST',
        body: JSON.stringify({ exam: examId })
    });
    const subData = await subRes.json();
    state.currentSubmissionId = subData.id;
    state.activeSectionIndex = 0;

    document.getElementById('exam-title-display').textContent = examData.title;
    showView('exam');
    renderSectionNav();
    loadActiveSection();
}

function renderSectionNav() {
    const nav = document.getElementById('section-nav');
    nav.innerHTML = '';
    
    state.currentExamData.sections.forEach((sec, idx) => {
        const btn = document.createElement('button');
        btn.className = `nav-item ${idx === state.activeSectionIndex ? 'active' : ''}`;
        btn.textContent = `${idx + 1}. ${sec.section_type}`;
        btn.disabled = true; // Lock navigation, enforce linear progression for VSTEP
        nav.appendChild(btn);
    });
}

let sectionTimerId = null;

async function loadActiveSection() {
    if (state.activeSectionIndex >= state.currentExamData.sections.length) {
        finishExam();
        return;
    }

    const section = state.currentExamData.sections[state.activeSectionIndex];
    document.getElementById('section-title').textContent = section.section_type;
    
    // Start section submission on backend
    const res = await apiFetch(`/submissions/${state.currentSubmissionId}/start_section/`, {
        method: 'POST',
        body: JSON.stringify({ section_id: section.id })
    });
    const sectionSubData = await res.json();
    section.submission_id = sectionSubData.id;

    renderSectionContent(section);
    
    // Timer Logic
    clearInterval(sectionTimerId);
    let timeLeft = section.time_limit_minutes * 60;
    
    sectionTimerId = setInterval(() => {
        timeLeft--;
        if(timeLeft <= 0) {
            clearInterval(sectionTimerId);
            submitCurrentSection(); // Auto-submit when time up
        }
        
        const h = Math.floor(timeLeft / 3600).toString().padStart(2, '0');
        const m = Math.floor((timeLeft % 3600) / 60).toString().padStart(2, '0');
        const s = (timeLeft % 60).toString().padStart(2, '0');
        document.getElementById('countdown-display').textContent = `${h}:${m}:${s}`;
    }, 1000);
}

function renderSectionContent(section) {
    const container = document.getElementById('question-container');
    container.innerHTML = '';

    section.parts.forEach(part => {
        const partDiv = document.createElement('div');
        partDiv.className = 'part-block';
        
        // Part header
        let html = `
            <h3 class="part-title">${part.title}</h3>
            <div class="part-directions">${part.directions}</div>
        `;
        
        if (part.passage_text) {
            html += `<div class="passage-box">${part.passage_text}</div>`;
        }
        if (part.audio_file) {
            html += `
                <div class="audio-player-box">
                    <audio controls src="${part.audio_file}" class="w-100"></audio>
                </div>`;
        }

        partDiv.innerHTML = html;

        // Render questions
        part.questions.forEach((q, qIndex) => {
            const qDiv = document.createElement('div');
            qDiv.className = 'question-item';
            qDiv.innerHTML = `<div class="question-prompt">Q${q.order}: ${q.prompt}</div>`;

            if (q.question_type === 'MCQ' || q.question_type === 'TFNG' || q.question_type === 'MATCHING') {
                const choicesDiv = document.createElement('div');
                choicesDiv.className = 'choices-list';
                q.choices.forEach(c => {
                    const label = document.createElement('label');
                    label.className = 'choice-label';
                    label.innerHTML = `
                        <input type="radio" name="q_${q.id}" value="${c.id}" onchange="saveAnswer('${q.id}', '${c.id}', null)">
                        <span>${c.text}</span>
                    `;
                    choicesDiv.appendChild(label);
                });
                qDiv.appendChild(choicesDiv);
            } 
            else if (q.question_type === 'TEXT_LONG') {
                const textarea = document.createElement('textarea');
                textarea.className = 'text-long-input';
                textarea.placeholder = 'Type your essay/letter here...';
                // Autosave on blur
                textarea.addEventListener('blur', (e) => saveAnswer(q.id, null, e.target.value));
                qDiv.appendChild(textarea);
            }
            else if (q.question_type === 'AUDIO_REC') {
                qDiv.innerHTML += `
                    <div class="text-muted" style="font-size:0.875rem; margin-bottom: 0.5rem">
                        Prep time: ${q.prep_time_seconds}s | Response time: ${q.response_time_seconds}s
                    </div>
                    <button class="btn btn-outline" onclick="alert('Recording feature mocked for demo.')">🎤 Start Recording</button>
                `;
            }

            partDiv.appendChild(qDiv);
        });

        container.appendChild(partDiv);
    });
}

// Autosave mechanism
async function saveAnswer(question_id, selected_choice_id, text_answer) {
    const section = state.currentExamData.sections[state.activeSectionIndex];
    if(!section.submission_id) return;

    const body = {
        section_submission: section.submission_id,
        question: question_id
    };
    if (selected_choice_id) body.selected_choice = selected_choice_id;
    if (text_answer != null) body.text_answer = text_answer;

    try {
        await apiFetch('/responses/', {
            method: 'POST',
            body: JSON.stringify(body)
        });
        console.log(`Saved answer for q ${question_id}`);
    } catch(e) {
        console.error('Failed to autosave', e);
    }
}

document.getElementById('submit-section-btn').addEventListener('click', submitCurrentSection);

async function submitCurrentSection() {
    clearInterval(sectionTimerId);
    
    const section = state.currentExamData.sections[state.activeSectionIndex];
    
    // Finalize section on backend
    try {
        await apiFetch(`/section-submissions/${section.submission_id}/complete/`, {
            method: 'POST',
            body: JSON.stringify({ time_spent_seconds: section.time_limit_minutes * 60 }) // Mocking time spent
        });
    } catch (e) {
        console.error("Failed to submit section", e);
    }

    state.activeSectionIndex++;
    renderSectionNav();
    loadActiveSection();
}

async function finishExam() {
    try {
        await apiFetch(`/submissions/${state.currentSubmissionId}/finish_exam/`, {
            method: 'POST'
        });
        
        showModal(
            'Exam Completed',
            'Your exam has been finished successfully! Your objective scores are processed and subjective answers are currently queued for AI grading.',
            false,
            () => {
                showView('dashboard');
                fetchExams();
            }
        );
    } catch (e) {
        console.error('Finish exam error', e);
        showModal('Error', 'Failed to finalize your exam. Please try again or contact support.', false);
    }
}

// Final quit button
document.getElementById('submit-exam-btn').addEventListener('click', () => {
    showModal(
        'Submit Early?',
        'Are you sure you want to quit the exam early? You will not be able to return to this attempt.',
        true,
        () => {
            clearInterval(sectionTimerId);
            finishExam();
        }
    );
});

// Custom Modal Logic
function showModal(title, message, isConfirm = false, onConfirm = null) {
    const overlay = document.getElementById('custom-modal');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').innerHTML = message;
    
    const cancelBtn = document.getElementById('modal-cancel-btn');
    const confirmBtn = document.getElementById('modal-confirm-btn');
    
    // Reset listeners
    const newCancel = cancelBtn.cloneNode(true);
    const newConfirm = confirmBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);
    confirmBtn.parentNode.replaceChild(newConfirm, confirmBtn);
    
    if (!isConfirm) {
        newCancel.classList.add('hidden');
        newConfirm.textContent = 'OK';
    } else {
        newCancel.classList.remove('hidden');
        newConfirm.textContent = 'Confirm';
    }
    
    const closeModal = () => overlay.classList.add('hidden');
    
    newCancel.addEventListener('click', closeModal);
    newConfirm.addEventListener('click', () => {
        closeModal();
        if(onConfirm) onConfirm();
    });
    
    overlay.classList.remove('hidden');
}

// Score Breakdown Logic
async function showScoreBreakdown(submissionId) {
    try {
        const res = await apiFetch(`/submissions/${submissionId}/`);
        if (!res.ok) throw new Error('Failed to fetch details');
        const submission = await res.json();
        
        document.getElementById('breakdown-total-score').textContent = `${(parseFloat(submission.consolidated_score) || 0).toFixed(2)} / 10`;
        
        const grid = document.getElementById('breakdown-grid-container');
        grid.innerHTML = '';
        
        if (submission.section_submissions) {
            submission.section_submissions.forEach(ss => {
                grid.innerHTML += `
                    <div class="score-cell">
                        <div class="score-cell-title">${ss.section_type || 'Section'}</div>
                        <div class="score-cell-value">${ss.score !== null ? parseFloat(ss.score).toFixed(2) : '0.00'}</div>
                    </div>
                `;
            });
        }
        
        showView('breakdown');
    } catch (e) {
        console.error("Failed to load breakdown", e);
        showModal('Error', 'Could not load score breakdown details.');
    }
}

// Initialize app when DOM is fully loaded
document.addEventListener('DOMContentLoaded', init);
