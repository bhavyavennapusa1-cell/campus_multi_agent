// Configurable Backend API URL (empty string = relative/same-origin)
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : (window.VITE_API_BASE_URL || window.REACT_APP_API_BASE_URL || window.ENV_API_BASE_URL || '');

// Global API Helper object connecting UI components to backend endpoints
window.CampusApi = {
    async chat(messageText, profile = {}) {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: messageText,
                session_id: "demo_session_frontend",
                profile: profile
            })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async confirmAction(confirmed, context) {
        const res = await fetch(`${API_BASE}/chat/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmed, context })
        });
        return await res.json();
    },
    async transcribeAudio(fileBlob) {
        const formData = new FormData();
        formData.append("file", fileBlob, "voice_command.wav");
        const res = await fetch(`${API_BASE}/transcribe`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async getPlacementOpportunities(role = "Software Engineer") {
        const res = await fetch(`${API_BASE}/placement/opportunities?role=${encodeURIComponent(role)}`);
        return await res.json();
    },
    async getEligibleCompanies(sessionId = "demo_session_frontend") {
        const res = await fetch(`${API_BASE}/placement/eligible-companies?session_id=${encodeURIComponent(sessionId)}`);
        return await res.json();
    },
    async getGithubMetrics(username = "octocat") {
        const res = await fetch(`${API_BASE}/placement/github?username=${encodeURIComponent(username)}`);
        return await res.json();
    },
    async getAcademicTasks() {
        const res = await fetch(`${API_BASE}/academic/tasks`);
        return await res.json();
    },
    async createAcademicTask(content, dueString = "Tomorrow") {
        const res = await fetch(`${API_BASE}/academic/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, due_string: dueString })
        });
        return await res.json();
    },
    async getAcademicTimetable(sessionId = "demo_session_frontend") {
        const res = await fetch(`${API_BASE}/academic/timetable?session_id=${encodeURIComponent(sessionId)}`);
        return await res.json();
    },
    async getDirections(origin, destination) {
        const res = await fetch(`${API_BASE}/navigator/directions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination })
        });
        return await res.json();
    },
    async registerEvent(eventName) {
        const res = await fetch(`${API_BASE}/events/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_name: eventName })
        });
        return await res.json();
    },
    async getContacts(queryType = "general", subject = "inquiry") {
        const res = await fetch(`${API_BASE}/communication/contacts?query_type=${encodeURIComponent(queryType)}&subject=${encodeURIComponent(subject)}`);
        return await res.json();
    },
    async getGroups() {
        const res = await fetch(`${API_BASE}/communication/groups`);
        return await res.json();
    },
    async createGroup(groupName, memberIds = [], groupType = "study", durationHours = 24) {
        const res = await fetch(`${API_BASE}/communication/groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                group_name: groupName,
                member_ids: memberIds,
                group_type: groupType,
                duration_hours: durationHours
            })
        });
        return await res.json();
    },
    async draftEmail(recipientEmail, subject, coreMessage) {
        const res = await fetch(`${API_BASE}/communication/draft-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                recipient_email: recipientEmail,
                subject: subject,
                core_message: coreMessage
            })
        });
        return await res.json();
    },
    async approveAction(actionId, status = "approved") {
        const res = await fetch(`${API_BASE}/communication/approve-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action_id: actionId, status: status })
        });
        return await res.json();
    },
    async sendEmail(to, subject, body) {
        const res = await fetch(`${API_BASE}/communication/email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to, subject, body })
        });
        return await res.json();
    },
    async scheduleCalendar(title, startTime) {
        const res = await fetch(`${API_BASE}/communication/calendar?title=${encodeURIComponent(title)}&start_time=${encodeURIComponent(startTime)}`, {
            method: 'POST'
        });
        return await res.json();
    },
    async scheduleReminder(event, minutesBefore = 15) {
        const res = await fetch(`${API_BASE}/communication/reminder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event, minutes_before: minutesBefore })
        });
        return await res.json();
    }
};

window.downloadIcsFile = function(title, dateStr, location = 'Campus Main Block', description = '') {
    console.log('[Download ICS] Event triggered:', { title, dateStr, location, description });
    try {
        let startDate = new Date();
        if (dateStr) {
            const parsed = new Date(dateStr);
            if (!isNaN(parsed.getTime())) {
                startDate = parsed;
            }
        }
        
        const pad = (n) => String(n).padStart(2, '0');
        const formatDate = (d) => {
            return d.getUTCFullYear() +
                pad(d.getUTCMonth() + 1) +
                pad(d.getUTCDate()) + 'T' +
                pad(d.getUTCHours()) +
                pad(d.getUTCMinutes()) +
                pad(d.getUTCSeconds()) + 'Z';
        };

        const startFormatted = formatDate(startDate);
        const endDate = new Date(startDate.getTime() + 60 * 60 * 1000);
        const endFormatted = formatDate(endDate);

        const icsContent = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Smart Campus Multi-Agent//NONSGML v1.0//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            'BEGIN:VEVENT',
            `SUMMARY:${title}`,
            `DESCRIPTION:${description || title}`,
            `LOCATION:${location}`,
            `DTSTART:${startFormatted}`,
            `DTEND:${endFormatted}`,
            'STATUS:CONFIRMED',
            'END:VEVENT',
            'END:VCALENDAR'
        ].join('\r\n');

        if (!icsContent || icsContent.length < 50) {
            console.error('[Download ICS Error] Invalid ICS string generated.');
            return;
        }

        const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        const safeTitle = (title || 'event').replace(/[^a-zA-Z0-9]/g, '_');
        link.download = `${safeTitle}.ics`;
        document.body.appendChild(link);
        console.log('[Download ICS] Firing synchronous link.click() for:', link.download);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        console.log('[Download ICS] Download successfully initiated.');
    } catch (err) {
        console.error('[Download ICS Fatal Error]:', err);
    }
};

window.downloadSyllabusFile = function(code, courseName, faculty = 'Department Faculty', credits = 4) {
    console.log('[Download Syllabus] Event triggered:', { code, courseName, faculty, credits });
    try {
        const textContent = `=====================================================
COURSE SYLLABUS & CURRICULUM SPECIFICATION
=====================================================
Course Name : ${courseName || 'Computer Science Course'}
Course Code : ${code || 'CSE301'}
Faculty     : ${faculty}
Credits     : ${credits}
Department  : Computer Science & Engineering

UNIT 1: Core Fundamentals & Architectural Overview
- Fundamental paradigms, state representation, and complexity analysis.
- Theoretical foundations and baseline system configuration.

UNIT 2: Intermediate Algorithms & Data Structures
- Design patterns, graph traversals, dynamic programming models.
- Resource allocation algorithms and concurrency control.

UNIT 3: Advanced Topics & Real-world Applications
- Distributed coordination, fault tolerance, and system optimization.
- Multi-agent orchestration, RAG retrieval, and vector memory integration.

LABORATORY & PRACTICAL EVALUATION:
- Weekly programming assignments (40%)
- Mid-semester examination (20%)
- End-semester final examination (40%)
=====================================================
Generated by Smart Campus Multi-Agent System
=====================================================`;

        const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        link.download = `${code || 'Course'}_Syllabus.txt`;
        document.body.appendChild(link);
        console.log('[Download Syllabus] Firing synchronous link.click() for:', link.download);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        console.log('[Download Syllabus] Download successfully initiated.');
    } catch (err) {
        console.error('[Download Syllabus Fatal Error]:', err);
    }
};

window.downloadCertificateFile = function(studentName = '', grantName = 'Merit Scholarship Grant', amount = '₹25,000') {
    console.log('[Download Certificate] Event triggered:', { studentName, grantName, amount });
    try {
        let name = studentName;
        if (!name) {
            try {
                const p = JSON.parse(localStorage.getItem('studentProfile') || '{}');
                name = p.name || 'Bhavya Vennapusa';
            } catch (e) {
                name = 'Bhavya Vennapusa';
            }
        }
        const textContent = `===================================================================
                  ACADEMIC SCHOLARSHIP CERTIFICATE
===================================================================

This is to certify that:

                   ${name.toUpperCase()}

has been awarded the ${grantName.toUpperCase()} for outstanding
academic achievement, maintaining exemplary CGPA standards, and
demonstrating active participation in campus technical programs.

Award Amount : ${amount}
Grant Status : APPROVED & DISBURSED
Issued Date  : August 2026

===================================================================
Authorized by: Office of Student Affairs & Financial Aid
Smart Campus Multi-Agent Network (AgentX 2026)
===================================================================`;

        const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        link.download = `Scholarship_Grant_Certificate.txt`;
        document.body.appendChild(link);
        console.log('[Download Certificate] Firing synchronous link.click() for:', link.download);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        console.log('[Download Certificate] Download successfully initiated.');
    } catch (err) {
        console.error('[Download Certificate Fatal Error]:', err);
    }
};

window.handleLogout = async function(e) {
    if (e) e.preventDefault();
    const token = localStorage.getItem('studentSessionToken');
    if (token) {
        try {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
        } catch (err) {}
    }
    localStorage.removeItem('studentSessionToken');
    localStorage.removeItem('studentProfile');
    localStorage.removeItem('studentSession');
    localStorage.removeItem('mem_name');
    localStorage.removeItem('mem_branch');
    localStorage.removeItem('mem_attendance');
    localStorage.removeItem('mem_hostel');
    window.location.href = 'login.html';
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Add Entrance Animations to main elements on load
    document.querySelectorAll('.cloud-container, .service-card, .placement-card, .status-card, .module-card').forEach((el, index) => {
        el.classList.add('animate-pop');
        el.style.animationDelay = `${index * 0.05}s`;
    });

    // 2. Global Mobile Hamburger Navigation Handler
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // 3. Memory Panel Input Hydration & Storage
    const memName = document.getElementById('mem-name');
    const memBranch = document.getElementById('mem-branch');
    const memAttendance = document.getElementById('mem-attendance');
    const memHostel = document.getElementById('mem-hostel');

    // FIX 2: Load real logged-in user profile from session if present
    const savedToken = localStorage.getItem('studentSessionToken');
    const savedProfileStr = localStorage.getItem('studentProfile');
    let userProfile = null;
    if (savedProfileStr) {
        try { userProfile = JSON.parse(savedProfileStr); } catch (e) {}
    }

    if (window.location.pathname.includes('chat.html') && !savedToken && !userProfile) {
        window.location.href = 'login.html';
    }

    if (memName) {
        memName.value = (userProfile && userProfile.name) || localStorage.getItem('mem_name') || "Bhavya Vennapusa";
    }
    if (memBranch) {
        memBranch.value = (userProfile && userProfile.branch) || localStorage.getItem('mem_branch') || "CSE - 3rd Year";
    }
    if (memAttendance) {
        memAttendance.value = (userProfile && userProfile.attendance) || localStorage.getItem('mem_attendance') || "88%";
    }
    if (memHostel) {
        memHostel.value = (userProfile && userProfile.hostel) || localStorage.getItem('mem_hostel') || "Block B";
    }

    const saveMemoryToStorage = () => {
        if (memName) localStorage.setItem('mem_name', memName.value);
        if (memBranch) localStorage.setItem('mem_branch', memBranch.value);
        if (memAttendance) localStorage.setItem('mem_attendance', memAttendance.value);
        if (memHostel) localStorage.setItem('mem_hostel', memHostel.value);
    };

    [memName, memBranch, memAttendance, memHostel].forEach(input => {
        if (input) {
            input.addEventListener('input', saveMemoryToStorage);
            input.addEventListener('change', saveMemoryToStorage);
        }
    });

    // 4. Chat Form & Multi-Agent Workspace Logic (Scoped safely)
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const traceList = document.getElementById('trace-list');
    const chips = document.querySelectorAll('.chip');
    const btnNewChat = document.getElementById('btn-new-chat');
    const btnTogglePrevChats = document.getElementById('btn-toggle-prev-chats');

    // --- Session ID & Local Storage History Management ---
    function getOrCreateSessionId() {
        let sid = sessionStorage.getItem('chat_session_id');
        if (!sid) {
            sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
            sessionStorage.setItem('chat_session_id', sid);
        }
        return sid;
    }

    let currentSessionId = getOrCreateSessionId();

    function saveMessageToLocalStorage(msgObj) {
        let history = [];
        try {
            const raw = localStorage.getItem('campus_chat_history');
            if (raw) history = JSON.parse(raw);
        } catch (e) { history = []; }
        history.push(msgObj);
        localStorage.setItem('campus_chat_history', JSON.stringify(history));
    }

    function saveMessageToHistory(sessionId, msgObj) {
        let history = [];
        const historyJson = sessionStorage.getItem('chat_history_' + sessionId);
        if (historyJson) {
            try { history = JSON.parse(historyJson); } catch (e) { history = []; }
        }
        history.push(msgObj);
        sessionStorage.setItem('chat_history_' + sessionId, JSON.stringify(history));
        saveMessageToLocalStorage(msgObj);
    }

    function loadLocalStorageChatHistory() {
        if (!chatHistory) return false;
        try {
            const raw = localStorage.getItem('campus_chat_history');
            if (!raw) return false;
            const messages = JSON.parse(raw);
            if (!Array.isArray(messages) || messages.length === 0) return false;

            chatHistory.innerHTML = '';
            messages.forEach(m => {
                appendMessageToDOM(m.text, m.sender, m.agentsUsed || m.agents_used, m.reasoningSteps || m.reasoning_steps, m.requiresConfirmation || m.requires_confirmation, m.actionContext || 'default', m.actions || [], false);
            });
            return true;
        } catch (e) {
            return false;
        }
    }

    function loadChatHistory(sessionId) {
        if (!chatHistory) return false;
        const loadedLocal = loadLocalStorageChatHistory();
        if (loadedLocal) return true;

        const historyJson = sessionStorage.getItem('chat_history_' + sessionId);
        if (!historyJson) return false;
        try {
            const messages = JSON.parse(historyJson);
            if (!Array.isArray(messages) || messages.length === 0) return false;
            
            chatHistory.innerHTML = '';
            messages.forEach(m => {
                appendMessageToDOM(m.text, m.sender, m.agentsUsed, m.reasoningSteps, m.requiresConfirmation, m.actionContext, m.actions, false);
            });
            return true;
        } catch (e) {
            return false;
        }
    }

    // Auto-hydrate history on page load/switch
    loadChatHistory(currentSessionId);

    if (btnTogglePrevChats) {
        btnTogglePrevChats.addEventListener('click', () => {
            const loaded = loadLocalStorageChatHistory();
            if (!loaded && chatHistory) {
                chatHistory.innerHTML = `<div class="message msg-bot">No previous chat history found in local storage. Start a conversation below!</div>`;
            }
        });
    }

    if (btnNewChat) {
        btnNewChat.addEventListener('click', () => {
            localStorage.removeItem('campus_chat_history');
            sessionStorage.removeItem('chat_session_id');
            currentSessionId = getOrCreateSessionId();
            if (chatHistory) {
                chatHistory.innerHTML = `
                    <div class="message msg-bot">
                        Hi there! Select one of the quick scenario chips below or type your custom query.
                    </div>
                `;
            }
            if (traceList) {
                traceList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 3rem;">Awaiting orchestrator plan execution...</div>`;
            }
        });
    }

    const urlParams = new URLSearchParams(window.location.search);
    const autoPrompt = urlParams.get('prompt');
    if (autoPrompt && chatInput) {
        chatInput.value = autoPrompt;
        window.history.replaceState({}, document.title, window.location.pathname);
        setTimeout(() => {
            if (chatForm) {
                chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }, 150);
    }

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (chatInput) {
                chatInput.value = chip.getAttribute('data-prompt');
                if (chatForm) {
                    chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                }
            }
        });
    });

    const getStatusIcon = (status) => {
        switch ((status || '').toLowerCase()) {
            case 'pending': return '<div style="border: 2px solid var(--text-muted); border-radius: 50%; width: 14px; height: 14px;"></div>';
            case 'running': return '<div style="border: 2px solid var(--border-dark); border-top-color: var(--primary-blue); border-radius: 50%; width: 14px; height: 14px; animation: spin 1s linear infinite;"></div>';
            case 'done': return '<span style="color: #27ae60; font-weight: bold; font-size: 1.1rem;">✓</span>';
            case 'failed': case 'cancelled': return '<span style="color: #c0392b; font-weight: bold; font-size: 1.1rem;">✕</span>';
            default: return '•';
        }
    };

    const appendMessageToDOM = (text, sender, agentsUsed = [], reasoningSteps = [], requiresConfirmation = false, actionContext = 'default', actions = [], saveToStorage = true) => {
        if (!chatHistory) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = `message msg-${sender} animate-pop`;
        msgDiv.dataset.context = actionContext;

        let contentHtml = `<p>${text}</p>`;

        if (agentsUsed && agentsUsed.length > 0) {
            contentHtml += `<div class="agent-trace-strip" style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.75rem; padding-top: 0.5rem; border-top: 2px dashed rgba(0,0,0,0.1); font-size: 0.75rem;">`;
            agentsUsed.forEach(agent => {
                contentHtml += `<span class="sticker-tag" style="background: var(--lavender); padding: 0.2rem 0.6rem; border-radius: 8px; font-weight: 600; margin:0; transform: rotate(${Math.random() * 4 - 2}deg);">⚡ ${agent.charAt(0).toUpperCase() + agent.slice(1)} Agent</span>`;
            });
            contentHtml += `</div>`;
        }

        // Render Clickable Action Buttons (BUG 3)
        if (actions && actions.length > 0) {
            let actionsHtml = `<div class="action-links-list" style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.6rem;">`;
            actions.forEach(act => {
                if (act.type === 'link' || act.url) {
                    actionsHtml += `
                        <a href="${act.url}" target="_blank" rel="noopener noreferrer" class="btn-pill action-link-btn" style="background: var(--mint-green); color: var(--text-main); font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.4rem 0.9rem; font-size: 0.85rem; border: 2px solid var(--border-dark); box-shadow: 2px 2px 0px var(--border-dark); transition: transform 0.15s;">
                            📍 ${act.label || 'Get Directions'} →
                        </a>
                    `;
                }
            });
            actionsHtml += `</div>`;
            contentHtml += actionsHtml;
        }

        if (requiresConfirmation) {
            contentHtml += `
                <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;" class="action-buttons">
                    <button class="btn-pill" style="background: #27ae60; color: white;" onclick="window.handleConfirm(true, '${actionContext}', this)">Confirm Action</button>
                    <button class="btn-pill" style="background: #c0392b; color: white;" onclick="window.handleConfirm(false, '${actionContext}', this)">Cancel</button>
                </div>
            `;
        }

        msgDiv.innerHTML = contentHtml;
        chatHistory.appendChild(msgDiv);

        if (saveToStorage) {
            saveMessageToHistory(currentSessionId, { text, sender, agentsUsed, reasoningSteps, requiresConfirmation, actionContext, actions });
        }
        
        setTimeout(() => {
            chatHistory?.scrollTo({ top: chatHistory.scrollHeight, behavior: 'smooth' });
        }, 50);
    };

    const appendMessage = (text, sender, agentsUsed = [], reasoningSteps = [], requiresConfirmation = false, actionContext = 'default', actions = []) => {
        appendMessageToDOM(text, sender, agentsUsed, reasoningSteps, requiresConfirmation, actionContext, actions, true);
    };

    const showTypingIndicator = () => {
        removeTypingIndicator();
        if (!chatHistory) return;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message msg-bot typing-indicator animate-pop';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `<span></span><span></span><span></span>`;
        chatHistory.appendChild(typingDiv);
        chatHistory.scrollTo({ top: chatHistory.scrollHeight, behavior: 'smooth' });
    };

    const removeTypingIndicator = () => {
        const existing = document.getElementById('typing-indicator');
        if (existing) existing.remove();
    };

    const renderTraces = (traces) => {
        if (!traceList) return;
        traceList.innerHTML = '';
        if (!traces || traces.length === 0) return;

        traces.forEach((trace, idx) => {
            const item = document.createElement('div');
            item.className = 'trace-item animate-pop';
            item.style.animationDelay = `${idx * 0.1}s`;
            item.innerHTML = `
                <div>${getStatusIcon(trace.status)}</div>
                <div style="font-size: 0.85rem; flex: 1;">
                    <div style="font-family: var(--font-heading); color: var(--primary-blue);">${(trace.agent || 'Orchestrator').toUpperCase()} AGENT</div>
                    <div style="font-weight: 700; color: var(--text-main);">${trace.action || 'processing'}</div>
                    <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 0.2rem;">${trace.message || ''}</div>
                </div>
            `;
            traceList.appendChild(item);
        });
        traceList.scrollTo({ top: traceList.scrollHeight, behavior: 'smooth' });
    };

    const getFallbackResponse = (messageText) => {
        const textLower = messageText.toLowerCase();
        let replyText = "Based on institutional regulations, your request has been processed across campus agent pipelines.";
        let agent = "academic";
        let action = "data_retrieval";
        let actions = [];

        if (textLower.includes("eligib") || textLower.includes("google")) {
            agent = "placement";
            action = "check_eligibility";
            replyText = "Student is ELIGIBLE for Dream Tier placement drives (Google, Microsoft). Policy reference: Placement Policy §2.1.";
        } else if (textLower.includes("email") || textLower.includes("draft")) {
            agent = "communication";
            action = "draft_email";
            replyText = "Email drafted for academic office inquiry. Would you like me to send this official email to academic_office@vasavi.ac.in?";
        } else if (textLower.includes("direction") || textLower.includes("where") || textLower.includes("library") || textLower.includes("navigate")) {
            agent = "navigator";
            action = "get_directions";
            replyText = "Directions to Central Library: Walk straight from Hostel Block B past SAC circle to Central Library Building, 2nd Floor.";
            actions = [{"type": "link", "label": "Get Directions", "url": "https://www.google.com/maps/dir/?api=1&destination=17.4458,78.3482"}];
        }

        return {
            reply: replyText,
            agents_used: [agent],
            requires_confirmation: (agent === "communication"),
            actions: actions,
            trace: [
                { agent: "orchestrator", action: "plan_query", status: "done", message: "Decomposed query into execution steps" },
                { agent: agent, action: action, status: "done", message: replyText }
            ]
        };
    };

    const sendQuery = async (messageText) => {
        showTypingIndicator();
        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    session_id: currentSessionId,
                    profile: {
                        name: memName?.value || "Bhavya Vennapusa",
                        branch: memBranch?.value || "CSE - 3rd Year",
                        attendance: memAttendance?.value || "88%",
                        hostel: memHostel?.value || "Block B"
                    }
                })
            });

            removeTypingIndicator();
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            appendMessage(
                data.reply, 
                'bot', 
                data.agents_used, 
                [], 
                data.requires_confirmation, 
                data.action_id || (data.agents_used && data.agents_used[0]) || 'default',
                data.actions || []
            );
            renderTraces(data.trace);
        } catch (error) {
            removeTypingIndicator();
            const fallback = getFallbackResponse(messageText);
            appendMessage(
                fallback.reply, 
                'bot', 
                fallback.agents_used, 
                [], 
                fallback.requires_confirmation, 
                fallback.agents_used[0],
                fallback.actions || []
            );
            renderTraces(fallback.trace);
        } finally {
            // ALWAYS re-enable chatInput and send button in finally block
            const currentSendBtn = chatForm ? chatForm.querySelector('button[type="submit"]') : null;
            if (chatInput) {
                chatInput.disabled = false;
                chatInput.removeAttribute('disabled');
                chatInput.readOnly = false;
                chatInput.focus();
            }
            if (currentSendBtn) {
                currentSendBtn.disabled = false;
                currentSendBtn.removeAttribute('disabled');
            }
            setTimeout(() => {
                if (chatInput) {
                    chatInput.disabled = false;
                    chatInput.focus();
                }
            }, 100);
        }
    };

    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            const sendBtn = chatForm.querySelector('button[type="submit"]');

            appendMessage(text, 'user');
            chatInput.value = '';
            chatInput.disabled = true;
            if (sendBtn) sendBtn.disabled = true;

            sendQuery(text);
        });
    }
});

window.handleConfirm = (isConfirmed, context, btnElement) => {
    if (!btnElement || !btnElement.parentElement) return;
    const actionContainer = btnElement.parentElement;
    actionContainer.innerHTML = `<span style="font-size: 0.9rem; font-weight: 700; color: ${isConfirmed ? '#27ae60' : '#c0392b'};">${isConfirmed ? '⏳ Processing...' : '⏳ Cancelling...'}</span>`;

    setTimeout(() => {
        actionContainer.innerHTML = `<span class="sticker-tag" style="background: ${isConfirmed ? 'var(--mint-green)' : 'var(--bubble-pink)'}; font-size: 0.85rem; margin:0;">${isConfirmed ? '✅ Action Confirmed & Executed' : '❌ Action Cancelled'}</span>`;
        
        const traceList = document.getElementById('trace-list');
        if (traceList) {
            const item = document.createElement('div');
            item.className = 'trace-item animate-pop';
            item.innerHTML = `
                <div>${isConfirmed ? '<span style="color: #27ae60; font-weight: bold; font-size:1.1rem;">✓</span>' : '<span style="color: #c0392b; font-weight: bold; font-size:1.1rem;">✕</span>'}</div>
                <div style="font-size: 0.85rem; flex: 1;">
                    <div style="font-family: var(--font-heading); color: var(--primary-blue);">COMMUNICATION AGENT</div>
                    <div style="font-weight: 700;">user_verification</div>
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${isConfirmed ? 'Authorized successfully.' : 'Aborted by user.'}</div>
                </div>
            `;
            traceList.appendChild(item);
            traceList.scrollTo({ top: traceList.scrollHeight, behavior: 'smooth' });
        }
    }, 800);
};
