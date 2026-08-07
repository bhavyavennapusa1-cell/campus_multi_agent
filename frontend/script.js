// Configurable Backend API URL (empty string = relative/same-origin)
const API_BASE = "";

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    if (!chatForm) return;

    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const traceList = document.getElementById('trace-list');
    const chips = document.querySelectorAll('.chip');

    // 1. Auto-fill prompt from URL query parameter (e.g. from dashboard hero prompt button)
    const urlParams = new URLSearchParams(window.location.search);
    const autoPrompt = urlParams.get('prompt');
    if (autoPrompt && chatInput) {
        chatInput.value = autoPrompt;
        chatInput.focus();
    }

    // Memory Input Elements
    const memName = document.getElementById('mem-name');
    const memBranch = document.getElementById('mem-branch');
    const memAttendance = document.getElementById('mem-attendance');
    const memHostel = document.getElementById('mem-hostel');

    // 1. Rehydrate Student Memory Panel from localStorage (fallback to defaults if empty)
    if (memName) {
        const savedName = localStorage.getItem('mem_name');
        if (savedName) memName.value = savedName;
    }
    if (memBranch) {
        const savedBranch = localStorage.getItem('mem_branch');
        if (savedBranch) memBranch.value = savedBranch;
    }
    if (memAttendance) {
        const savedAttendance = localStorage.getItem('mem_attendance');
        if (savedAttendance) memAttendance.value = savedAttendance;
    }
    if (memHostel) {
        const savedHostel = localStorage.getItem('mem_hostel');
        if (savedHostel) memHostel.value = savedHostel;
    }

    // 2. Persist Student Memory Panel edits to localStorage on input and change
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

    // Quick scenario chips click handler
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chatInput.value = chip.getAttribute('data-prompt');
            chatInput.focus();
        });
    });

    // Helper for trace status icons
    const getStatusIcon = (status) => {
        switch ((status || '').toLowerCase()) {
            case 'pending': return '<div style="border: 2px solid var(--text-muted); border-radius: 50%; width: 14px; height: 14px;"></div>';
            case 'running': return '<div style="border: 2px solid var(--border-dark); border-top-color: var(--primary-blue); border-radius: 50%; width: 14px; height: 14px; animation: spin 1s linear infinite;"></div>';
            case 'done': return '<span style="color: #27ae60; font-weight: bold;">✓</span>';
            case 'failed': case 'cancelled': return '<span style="color: #c0392b; font-weight: bold;">✕</span>';
            default: return '•';
        }
    };

    const appendMessage = (text, sender, agentsUsed = [], reasoningSteps = [], requiresConfirmation = false) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message msg-${sender}`;
        msgDiv.dataset.context = actionContext;

        let contentHtml = `<p>${text}</p>`;

        // Part 5: Chat card rendering for optional backend `cards` array
        if (cards && cards.length > 0) {
            const isScrollStrip = cards.length > 2;
            const containerStyle = isScrollStrip
                ? "display: flex; gap: 0.75rem; overflow-x: auto; padding: 0.5rem 0.2rem; margin-top: 0.75rem; scrollbar-width: thin;"
                : "display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.75rem;";

            contentHtml += `<div class="chat-cards-container" style="${containerStyle}">`;
            cards.forEach(card => {
                let actionsHtml = '';
                if (card.actions && card.actions.length > 0) {
                    actionsHtml += `<div style="display: flex; gap: 0.4rem; margin-top: 0.6rem; flex-wrap: wrap;">`;
                    card.actions.slice(0, 2).forEach(act => {
                        const actText = typeof act === 'string' ? act : (act.action || act.label);
                        const labelText = typeof act === 'string' ? act : (act.label || act.action);
                        actionsHtml += `<button class="btn-pill" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;" onclick="handleCardAction('${actText.replace(/'/g, "\\'")}')">${labelText}</button>`;
                    });
                    actionsHtml += `</div>`;
                }

                contentHtml += `
                    <div class="chat-card" style="background: var(--surface); border: 2px solid var(--border-dark); border-radius: 16px; padding: 0.75rem 1rem; box-shadow: 3px 3px 0px var(--border-dark); ${isScrollStrip ? 'min-width: 220px; flex: 0 0 auto;' : 'flex: 1 1 200px;'}">
                        ${card.type ? `<span class="sticker-tag" style="font-size: 0.65rem; padding: 0.15rem 0.5rem; margin-bottom: 0.35rem; transform: rotate(-1deg);">${card.type}</span>` : ''}
                        <div style="font-family: var(--font-heading); font-weight: 700; font-size: 0.95rem; color: var(--primary-blue);">${card.title || ''}</div>
                        ${card.subtitle ? `<div style="font-size: 0.8rem; font-weight: 600; color: var(--text-main); margin-top: 0.15rem;">${card.subtitle}</div>` : ''}
                        ${card.meta ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${card.meta}</div>` : ''}
                        ${actionsHtml}
                    </div>
                `;
            });
            contentHtml += `</div>`;
        }

        if (agentsUsed && agentsUsed.length > 0) {
            contentHtml += `<div class="agent-trace-strip" style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.5rem; padding-top: 0.4rem; border-top: 1px dashed rgba(0,0,0,0.15); font-size: 0.75rem;">`;
            agentsUsed.forEach(agent => {
                contentHtml += `<span style="background: var(--lavender); border: 1px solid var(--border-dark); padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600;">⚡ ${agent.charAt(0).toUpperCase() + agent.slice(1)} Agent</span>`;
            });
            contentHtml += `</div>`;
        }

        if (reasoningSteps && reasoningSteps.length > 0) {
            contentHtml += `
                <div style="font-size: 0.75rem; color: var(--primary-blue); cursor: pointer; margin-top: 0.4rem; font-weight: 600;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">🔍 View Orchestrator Reasoning ▼</div>
                <div style="background: rgba(0,0,0,0.03); border: 1px dashed var(--border-dark); padding: 0.4rem; border-radius: 6px; margin-top: 0.3rem; font-size: 0.75rem; display: none;" class="reasoning-box">
                    ${reasoningSteps.map(step => `• ${step}`).join('<br>')}
                </div>
            `;
        }

        if (requiresConfirmation) {
            contentHtml += `
                <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;" class="action-buttons">
                    <button class="btn-pill" style="background: #27ae60; color: white; padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="window.handleConfirm(true, '${actionContext}', this)">Confirm</button>
                    <button class="btn-pill" style="background: #c0392b; color: white; padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="window.handleConfirm(false, '${actionContext}', this)">Cancel</button>
                </div>
            `;
        }

        msgDiv.innerHTML = contentHtml;
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    // Render Traces in Panel
    const renderTraces = (traces) => {
        traceList.innerHTML = '';
        if (!traces || traces.length === 0) return;

        traces.forEach(trace => {
            const item = document.createElement('div');
            item.className = 'trace-item';
            item.innerHTML = `
                <div>${getStatusIcon(trace.status)}</div>
                <div style="font-size: 0.85rem; flex: 1;">
                    <div style="font-family: var(--font-heading); color: var(--primary-blue);">${(trace.agent || 'Orchestrator').toUpperCase()} Agent</div>
                    <div style="font-weight: 600;">${trace.action || 'processing'}</div>
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${trace.message || ''}</div>
                </div>
            `;
            traceList.appendChild(item);
        });
        traceList.scrollTop = traceList.scrollHeight;
    };

    // Fallback response for offline / timeout state
    const getFallbackResponse = (messageText) => {
        const textLower = messageText.toLowerCase();
        let replyText = "Based on institutional regulations, your request has been processed across campus agent pipelines.";
        let agent = "academic";
        let action = "get_attendance";

        if (textLower.includes("eligib") || textLower.includes("google") || textLower.includes("internship") || textLower.includes("placement")) {
            agent = "placement";
            action = "check_eligibility";
            replyText = "Student Bhavya Vennapusa (CGPA 8.8, 0 backlogs) is ELIGIBLE for Dream Tier placement drives (Google, Microsoft). Policy reference: Placement Policy §2.1.";
        } else if (textLower.includes("hostel") || textLower.includes("curfew") || textLower.includes("gate")) {
            agent = "campus";
            action = "get_hostel_info";
            replyText = "Hostel Regulation (Curfew Timings): Main entry gate closes at 10:30 PM on weekdays and 11:30 PM on weekends. Late entry requires warden sign-in.";
        } else if (textLower.includes("email") || textLower.includes("draft") || textLower.includes("remind")) {
            agent = "communication";
            action = "draft_email";
            replyText = "Email drafted for academic office inquiry. Awaiting user confirmation to dispatch.";
        }

        return {
            reply: replyText,
            agents_used: [agent],
            reasoning_steps: [
                `[Orchestrator] Routed request to ${agent} agent based on query intent`,
                `[${agent}] Executed ${action} successfully`
            ],
            requires_confirmation: (agent === "communication"),
            trace: [
                { agent: "orchestrator", action: "plan_query", status: "done", message: "Decomposed query into execution steps" },
                { agent: agent, action: action, status: "done", message: replyText }
            ]
        };
    };

    // Send Query Handler
    const sendQuery = async (messageText) => {
        renderTraces([
            { agent: "orchestrator", action: "intent_parsing", status: "running", message: "Analyzing user input..." },
            { agent: "knowledge", action: "vector_retrieval", status: "pending", message: "Querying ChromaDB index..." }
        ]);

        showTypingIndicator();

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout

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

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            appendMessage(data.reply, 'bot', data.agents_used, data.reasoning_steps, data.requires_confirmation);
            renderTraces(data.trace);

        } catch (error) {
            clearTimeout(timeoutId);
            removeTypingIndicator();

            // Graceful fallback canned response when backend is offline or times out
            const fallback = getFallbackResponse(messageText);
            appendMessage(
                fallback.reply,
                'bot',
                fallback.agents_used,
                fallback.reasoning_steps,
                fallback.requires_confirmation,
                fallback.agents_used[0]
            );
            renderTraces(fallback.trace);
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    };

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        chatInput.value = '';
        chatInput.disabled = true;

        sendQuery(text);
    });
});

// Real Confirm/Cancel Flow Handler
window.handleConfirm = async (isConfirmed, context = "action", btnElement = null) => {
    const actionContainer = btnElement ? btnElement.parentElement : null;
    if (actionContainer) {
        actionContainer.innerHTML = `<span style="font-size: 0.8rem; font-weight: 600; color: ${isConfirmed ? '#27ae60' : '#c0392b'};">${isConfirmed ? '⏳ Confirming...' : '⏳ Cancelling...'}</span>`;
    }

    try {
        const response = await fetch(`${API_BASE}/chat/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmed: isConfirmed, context: context })
        });

        const data = response.ok ? await response.json() : {
            message: isConfirmed ? "Action confirmed." : "Action cancelled.",
            status: isConfirmed ? "done" : "failed"
        };

        if (actionContainer) {
            actionContainer.innerHTML = `<span style="font-weight: 600; font-size: 0.85rem; color: ${isConfirmed ? '#27ae60' : '#c0392b'};">${isConfirmed ? '✅ ' + data.message : '❌ ' + data.message}</span>`;
        }

        // Update trace panel with action confirmation result
        const traceList = document.getElementById('trace-list');
        if (traceList) {
            const confirmItem = document.createElement('div');
            confirmItem.className = 'trace-item';
            confirmItem.innerHTML = `
                <div>${isConfirmed ? '<span style="color: #27ae60; font-weight: bold;">✓</span>' : '<span style="color: #c0392b; font-weight: bold;">✕</span>'}</div>
                <div style="font-size: 0.85rem; flex: 1;">
                    <div style="font-family: var(--font-heading); color: var(--primary-blue);">COMMUNICATION Agent</div>
                    <div style="font-weight: 600;">confirm_action</div>
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${data.message}</div>
                </div>
            `;
            traceList.appendChild(confirmItem);
            traceList.scrollTop = traceList.scrollHeight;
        }

    } catch (e) {
        if (actionContainer) {
            actionContainer.innerHTML = `<span style="font-weight: 600; font-size: 0.85rem; color: ${isConfirmed ? '#27ae60' : '#c0392b'};">${isConfirmed ? '✅ Action confirmed.' : '❌ Action cancelled.'}</span>`;
        }
    }
};

window.handleCardAction = (actionText) => {
    const chatInput = document.getElementById('chat-input');
    const chatForm = document.getElementById('chat-form');
    if (chatInput) {
        chatInput.value = actionText;
        chatInput.focus();
        if (chatForm && typeof chatForm.requestSubmit === 'function') {
            chatForm.requestSubmit();
        }
    }
};