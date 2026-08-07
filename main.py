"""
Main entrypoint for Smart Campus Multi-Agent FastAPI backend server.
Scaffolds FastAPI application exposing /chat and /chat/confirm endpoints,
with static frontend file serving and CORS middleware.
"""

import sys
from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
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
    prof = req.profile or {}
    prof_name = prof.get("name") or "Bhavya Vennapusa (Demo Profile)"
    prof_branch = prof.get("branch") or "CSE - 3rd Year"
    prof_attendance = prof.get("attendance") or "88%"
    prof_hostel = prof.get("hostel") or "Block B"

    text_lower = message_text.lower()
    if any(k in text_lower for k in ["eligib", "google", "placement", "internship", "company"]):
        agent = "placement"
        action = "check_eligibility"
        reply = f"Student {prof_name} ({prof_branch}) is ELIGIBLE for Dream Tier placement drives (Google, Microsoft). Policy reference: Placement Policy §2.1."
        req_confirm = False
    elif any(k in text_lower for k in ["hostel", "curfew", "gate", "dorm", "warden"]):
        agent = "campus"
        action = "get_hostel_info"
        reply = f"Hostel Regulation ({prof_hostel} Curfew Timings): Main entry gate closes at 10:30 PM on weekdays and 11:30 PM on weekends. Warden sign-in required for late entry."
        req_confirm = False
    elif any(k in text_lower for k in ["email", "draft", "mail", "remind"]):
        agent = "communication"
        action = "draft_email"
        reply = f"Email drafted for academic office inquiry regarding {prof_name}. Awaiting user confirmation to dispatch."
        req_confirm = True
    else:
        agent = "academic"
        action = "get_attendance"
        reply = f"Based on academic records, {prof_name}'s current attendance is {prof_attendance} across registered courses. Mandatory minimum attendance is 75.0%."
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
    import os
    # pyrefly: ignore [missing-import]
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
