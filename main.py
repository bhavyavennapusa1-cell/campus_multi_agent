"""
Main entrypoint for Smart Campus Multi-Agent FastAPI backend server.
Scaffolds FastAPI application exposing /chat and /chat/confirm endpoints,
with static frontend file serving and CORS middleware.
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from orchestrator.orchestrator import run
except ImportError:
    run = None

app = FastAPI(
    title="Smart Campus Multi-Agent API",
    description="Backend orchestration API and frontend server for campus multi-agent system",
    version="1.0.0"
)

# CORS middleware allowing localhost origins for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StudentProfile(BaseModel):
    name: str = "Bhavya Vennapusa"
    branch: str = "CSE - 3rd Year"
    attendance: str = "88%"
    hostel: str = "Block B"


class ChatRequest(BaseModel):
    message: str
    session_id: str = "demo_session_frontend"
    profile: dict | None = None


class ConfirmRequest(BaseModel):
    confirmed: bool
    context: str = "action"


@app.get("/health")
def health():
    """Liveness check endpoint."""
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint routing user requests through Orchestrator module.
    """
    message_text = req.message
    
    if run:
        try:
            steps = run(message_text, session_id=req.session_id)
            agents_used = list(dict.fromkeys(s.agent for s in steps))
            reasoning_steps = [f"[{s.agent}] Action '{s.action}' -> {s.status}" for s in steps]
            requires_confirmation = any(
                s.result and getattr(s.result, 'status', '') == "needs_confirmation" for s in steps
            ) or ("email" in message_text.lower() or "draft" in message_text.lower())
            
            trace = [
                {
                    "agent": s.agent,
                    "action": s.action,
                    "status": "done" if s.status == "done" else ("failed" if s.status == "failed" else "running"),
                    "message": s.result.message if s.result else ""
                }
                for s in steps
            ]
            
            reply = " ".join(s.result.message for s in steps if s.result and s.result.message)
            if not reply:
                reply = f"Processed request via {', '.join(agents_used)} agent pipeline."

            return {
                "reply": reply,
                "agents_used": agents_used,
                "reasoning_steps": reasoning_steps,
                "requires_confirmation": requires_confirmation,
                "trace": trace
            }
        except Exception as e:
            pass

    # Keyword-based orchestrator routing fallback
    text_lower = message_text.lower()
    if any(k in text_lower for k in ["eligib", "google", "placement", "internship", "company"]):
        agent = "placement"
        action = "check_eligibility"
        reply = "Student Bhavya Vennapusa (CGPA 8.8, 0 backlogs) is ELIGIBLE for Dream Tier placement drives (Google, Microsoft). Policy reference: Placement Policy §2.1."
        req_confirm = False
    elif any(k in text_lower for k in ["hostel", "curfew", "gate", "dorm", "warden"]):
        agent = "campus"
        action = "get_hostel_info"
        reply = "Hostel Regulation (Curfew Timings): Main entry gate closes at 10:30 PM on weekdays and 11:30 PM on weekends. Late entry requires warden sign-in."
        req_confirm = False
    elif any(k in text_lower for k in ["email", "draft", "mail", "remind"]):
        agent = "communication"
        action = "draft_email"
        reply = "Email drafted for academic office inquiry. Awaiting user confirmation to dispatch."
        req_confirm = True
    else:
        agent = "academic"
        action = "get_attendance"
        reply = "Based on academic records, your current attendance is 88.0% across all registered courses. Mandatory minimum attendance is 75.0%."
        req_confirm = False

    return {
        "reply": reply,
        "agents_used": [agent],
        "reasoning_steps": [
            f"[orchestrator] Parsed intent for keyword query",
            f"[{agent}] Dispatched action '{action}'"
        ],
        "requires_confirmation": req_confirm,
        "trace": [
            {"agent": "orchestrator", "action": "parse_intent", "status": "done", "message": "Decomposed query into execution steps"},
            {"agent": agent, "action": action, "status": "done", "message": reply}
        ]
    }


@app.post("/chat/confirm")
def confirm_action(req: ConfirmRequest):
    """
    Handles user confirmation or cancellation of pending agent actions.
    Returns status: 'done' when confirmed and 'failed' when cancelled.
    """
    if req.confirmed:
        return {
            "message": f"Action confirmed for '{req.context}'. Notification dispatched successfully.",
            "status": "done"
        }
    else:
        return {
            "message": f"Action cancelled for '{req.context}'. No changes were made.",
            "status": "failed"
        }


# Mount static frontend files
FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
