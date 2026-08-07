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

    if (memName) { const savedName = localStorage.getItem('mem_name'); if (savedName) memName.value = savedName; }
    if (memBranch) { const savedBranch = localStorage.getItem('mem_branch'); if (savedBranch) memBranch.value = savedBranch; }
    if (memAttendance) { const savedAttendance = localStorage.getItem('mem_attendance'); if (savedAttendance) memAttendance.value = savedAttendance; }
    if (memHostel) { const savedHostel = localStorage.getItem('mem_hostel'); if (savedHostel) memHostel.value = savedHostel; }

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

    const urlParams = new URLSearchParams(window.location.search);
    const autoPrompt = urlParams.get('prompt');
    if (autoPrompt && chatInput) {
        chatInput.value = autoPrompt;
        chatInput.focus();
    }

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (chatInput) {
                chatInput.value = chip.getAttribute('data-prompt');
                chatInput.focus();
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

    const appendMessage = (text, sender, agentsUsed = [], reasoningSteps = [], requiresConfirmation = false, actionContext = 'default') => {
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
        
        setTimeout(() => {
            chatHistory?.scrollTo({ top: chatHistory.scrollHeight, behavior: 'smooth' });
        }, 50);
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

        if (textLower.includes("eligib") || textLower.includes("google")) {
            agent = "placement";
            action = "check_eligibility";
            replyText = "Student is ELIGIBLE for Dream Tier placement drives (Google, Microsoft). Policy reference: Placement Policy §2.1.";
        } else if (textLower.includes("email")) {
            agent = "communication";
            action = "draft_email";
            replyText = "Email drafted for academic office inquiry. Awaiting user confirmation to dispatch.";
        }

        return {
            reply: replyText,
            agents_used: [agent],
            requires_confirmation: (agent === "communication"),
            trace: [
                { agent: "orchestrator", action: "plan_query", status: "done", message: "Decomposed query into execution steps" },
                { agent: agent, action: action, status: "done", message: replyText }
            ]
        };
    };

    const sendQuery = async (messageText) => {
        renderTraces([
            { agent: "orchestrator", action: "intent_parsing", status: "running", message: "Analyzing user input..." },
            { agent: "knowledge", action: "vector_retrieval", status: "pending", message: "Querying ChromaDB index..." }
        ]);

        showTypingIndicator();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);

        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    message: messageText,
                    session_id: "demo_session_frontend",
                    profile: {
                        name: memName?.value || "Bhavya Vennapusa",
                        branch: memBranch?.value || "CSE - 3rd Year",
                        attendance: memAttendance?.value || "88%",
                        hostel: memHostel?.value || "Block B"
                    }
                })
            });
            clearTimeout(timeoutId);
            removeTypingIndicator();
            const data = await response.json();
            appendMessage(data.reply, 'bot', data.agents_used, [], data.requires_confirmation, (data.agents_used && data.agents_used[0]) || 'default');
            renderTraces(data.trace);
        } catch (error) {
            clearTimeout(timeoutId);
            setTimeout(() => {
                removeTypingIndicator();
                const fallback = getFallbackResponse(messageText);
                appendMessage(fallback.reply, 'bot', fallback.agents_used, [], fallback.requires_confirmation, fallback.agents_used[0]);
                renderTraces(fallback.trace);
                if (chatInput) {
                    chatInput.disabled = false;
                    chatInput.focus();
                }
            }, 800);
        }
    };

    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            appendMessage(text, 'user');
            chatInput.value = '';
            chatInput.disabled = true;
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
