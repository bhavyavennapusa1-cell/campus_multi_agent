"""
API Server for Smart Campus Multi-Agent System.
Exposes FastAPI REST endpoints for frontend integration and multi-agent query orchestration.
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.orchestrator import run
from knowledge.memory import get_profile, create_session, get_history

app = FastAPI(
    title="Smart Campus Multi-Agent API",
    description="Backend orchestration API and frontend server for campus multi-agent system",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    profile: dict = None


@app.get("/")
def root():
    """Root endpoint returning service status and available endpoints."""
    return {
        "service": "Smart Campus Multi-Agent API",
        "status": "online",
        "endpoints": {
            "GET /": "Service overview and endpoint directory",
            "GET /health": "Liveness and health check",
            "POST /chat": "Multi-agent orchestrator chat query pipeline (Body: {message, session_id})",
            "GET /session/{session_id}": "Returns student profile and conversation history"
        }
    }


@app.get("/health")
def health():
    """Liveness check endpoint."""
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint routing user requests through Orchestrator -> Agents -> Memory & RAG chain.
    """
    # Ensure profile exists for session
    profile = get_profile(req.session_id)
    if not profile:
        profile = create_session(req.session_id, profile_overrides=req.profile)

    steps = run(req.message, session_id=req.session_id)

    agents_used = list(dict.fromkeys(s.agent for s in steps))
    reasoning_steps = [f"[{s.agent}] Action '{s.action}' -> {s.status}" for s in steps]
    requires_confirmation = any(s.result and s.result.status == "needs_confirmation" for s in steps)

    trace = [
        {
            "id": s.id,
            "agent": s.agent,
            "action": s.action,
            "status": s.status,
            "message": s.result.message if s.result else "",
            "citation": s.result.citation if s.result else None,
            "data": s.result.data if s.result else None,
        }
        for s in steps
    ]

    reply = " ".join(s.result.message for s in steps if s.result)

    return {
        "status": "success",
        "reply": reply,
        "trace": trace,
        "agents_used": agents_used,
        "reasoning_steps": reasoning_steps,
        "requires_confirmation": requires_confirmation
    }


@app.get("/session/{session_id}")
def get_session_info(session_id: str):
    """
    Returns the student profile and conversation history for a session.
    If session doesn't exist, returns 404 cleanly.
    """
    profile = get_profile(session_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    
    history = get_history(session_id, last_n=20)
    return {
        "status": "success",
        "session_id": session_id,
        "profile": profile,
        "history": history
    }


# Mount static frontend directory if present
FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
