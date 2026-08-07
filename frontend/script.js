document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    if (!chatForm) return;

    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const traceList = document.getElementById('trace-list');
    const chips = document.querySelectorAll('.chip');

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chatInput.value = chip.getAttribute('data-prompt');
            chatInput.focus();
        });
    });

    const getStatusIcon = (status) => {
        switch(status.toLowerCase()) {
            case 'pending': return '<div style="border: 2px solid var(--text-muted); border-radius: 50%; width: 14px; height: 14px;"></div>';
            case 'running': return '<div style="border: 2px solid var(--border-dark); border-top-color: var(--primary-blue); border-radius: 50%; width: 14px; height: 14px; animation: spin 1s linear infinite;"></div>';
            case 'done': return '<span style="color: #27ae60; font-weight: bold;">✓</span>';
            case 'failed': return '<span style="color: #c0392b; font-weight: bold;">✕</span>';
            default: return '•';
        }
    };

    const appendMessage = (text, sender, agentsUsed = [], reasoningSteps = [], requiresConfirmation = false) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message msg-${sender}`;
        
        let contentHtml = `<p>${text}</p>`;

        if (agentsUsed && agentsUsed.length > 0) {
            contentHtml += `<div class="agent-trace-strip" style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.5rem; padding-top: 0.4rem; border-top: 1px dashed rgba(0,0,0,0.1); font-size: 0.75rem;">`;
            agentsUsed.forEach(agent => {
                contentHtml += `<span style="background: var(--lavender); border: 1px solid var(--border-dark); padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600;">⚡ ${agent} Agent</span>`;
            });
            contentHtml += `</div>`;
        }

        if (reasoningSteps && reasoningSteps.length > 0) {
            contentHtml += `
                <div style="font-size: 0.75rem; color: var(--primary-blue); cursor: pointer; margin-top: 0.4rem; font-weight: 600;" onclick="this.nextElementSibling.classList.toggle('show')">🔍 View Orchestrator Reasoning ▼</div>
                <div style="background: rgba(0,0,0,0.02); border: 1px dashed var(--border-dark); padding: 0.4rem; border-radius: 6px; margin-top: 0.3rem; font-size: 0.75rem; display: none;" class="reasoning-box">
                    ${reasoningSteps.map(step => `• ${step}`).join('<br>')}
                </div>
            `;
        }

        if (requiresConfirmation) {
            contentHtml += `
                <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                    <button class="btn-pill" style="background: #27ae60; color: white; padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="handleConfirm(true)">Confirm</button>
                    <button class="btn-pill" style="background: #c0392b; color: white; padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="handleConfirm(false)">Cancel</button>
                </div>
            `;
        }

        msgDiv.innerHTML = contentHtml;
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    const renderTraces = (traces) => {
        traceList.innerHTML = '';
        if (!traces || traces.length === 0) return;

        traces.forEach(trace => {
            const item = document.createElement('div');
            item.className = 'trace-item';
            item.innerHTML = `
                <div>${getStatusIcon(trace.status)}</div>
                <div style="font-size: 0.85rem;">
                    <div style="font-family: var(--font-heading); color: var(--primary-blue);">${trace.agent} Agent</div>
                    <div style="font-weight: 600;">${trace.action}</div>
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${trace.message}</div>
                </div>
            `;
            traceList.appendChild(item);
        });
        traceList.scrollTop = traceList.scrollHeight;
    };

    const sendQuery = async (messageText) => {
        renderTraces([
            { agent: "Orchestrator", action: "Intent Parsing", status: "running", message: "Analyzing user input..." },
            { agent: "Knowledge", action: "Vector Retrieval", status: "pending", message: "Querying ChromaDB..." }
        ]);

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: messageText,
                    profile: {
                        name: document.getElementById('mem-name')?.value,
                        branch: document.getElementById('mem-branch')?.value,
                        attendance: document.getElementById('mem-attendance')?.value,
                        hostel: document.getElementById('mem-hostel')?.value
                    }
                })
            });

            if (!response.ok) throw new Error('Backend offline');

            const data = await response.json();
            appendMessage(data.reply, 'bot', data.agents_used, data.reasoning_steps, data.requires_confirmation);
            renderTraces(data.trace);

        } catch (error) {
            appendMessage('⚠️ Could not connect to backend server at localhost:8000. Please ensure Person A’s FastAPI backend is running.', 'bot', ['System'], ['Error handling triggered: fallback response active.']);
            renderTraces([{ agent: "System", action: "API Request", status: "failed", message: "Connection refused." }]);
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

window.handleConfirm = (isConfirmed) => {
    const chatHistory = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = 'message msg-user';
    msg.textContent = isConfirmed ? "Confirmed action." : "Cancelled action.";
    chatHistory.appendChild(msg);
};