"""
Person D owns this file.
This is the bridge between your HTML/JS frontend and the Python orchestrator
your teammates are building. Run it separately from your HTML files:

    uvicorn api_server:app --reload --port 8000

Then your HTML/JS calls http://localhost:8000/chat with fetch().
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent))
from orchestrator.orchestrator import run

app = FastAPI()

# allow your HTML file (opened as file:// or served on another port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    steps = run(req.message)

    trace = [
        {
            "id": s.id,
            "agent": s.agent,
            "action": s.action,
            "status": s.status,
            "message": s.result.message if s.result else "",
        }
        for s in steps
    ]

    # TODO Person D / whoever's on orchestrator: replace this with a real LLM
    # call that turns the trace into a natural sentence, same as the Streamlit
    # version's summary line did.
    reply = " ".join(s.result.message for s in steps if s.result)

    return {"reply": reply, "trace": trace}


@app.get("/health")
def health():
    return {"status": "ok"}
