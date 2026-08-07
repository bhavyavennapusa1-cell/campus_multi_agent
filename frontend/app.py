"""
Person D owns this file.
Run with: streamlit run frontend/app.py  (from the project root)

Chat on the left/main area, live trace panel on the right showing each
plan step as it executes - this is the single most important thing to get
polished, since it's what proves "autonomous decision-making" to judges.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from orchestrator.orchestrator import run

st.set_page_config(page_title="Smart Campus Assistant", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "trace" not in st.session_state:
    st.session_state.trace = []

col_chat, col_trace = st.columns([2, 1])

with col_chat:
    st.title("Smart campus assistant")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask me anything about courses, placements, hostel, events...")

with col_trace:
    st.subheader("Agent trace")
    trace_placeholder = st.empty()


def render_trace():
    icon = {"pending": "\u25cb", "running": "\u25d0", "done": "\u2713", "failed": "\u2717"}
    lines = []
    for step in st.session_state.trace:
        lines.append(f"{icon.get(step.status, '?')} **{step.agent}.{step.action}** - {step.status}")
        if step.result:
            lines.append(f"　{step.result.message}")
    trace_placeholder.markdown("\n\n".join(lines) if lines else "No steps yet.")


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with col_chat:
        with st.chat_message("user"):
            st.write(user_input)

    st.session_state.trace = []

    def on_step_update(step):
        # update the step in our trace list, then re-render
        existing = next((s for s in st.session_state.trace if s.id == step.id), None)
        if existing:
            st.session_state.trace[st.session_state.trace.index(existing)] = step
        else:
            st.session_state.trace.append(step)
        render_trace()

    final_steps = run(user_input, on_step_update=on_step_update)

    # TODO Person D: replace this with a real LLM call that summarizes
    # final_steps into a natural-language reply, instead of just concatenating.
    summary = " ".join(s.result.message for s in final_steps if s.result)

    st.session_state.messages.append({"role": "assistant", "content": summary})
    with col_chat:
        with st.chat_message("assistant"):
            st.write(summary)

render_trace()
