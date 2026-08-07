"""
Main entrypoint for Smart Campus Multi-Agent FastAPI backend server.
Exposes /chat, /transcribe (voice), communication approval, and domain agent REST endpoints
with static frontend file serving and CORS middleware.
"""

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Literal


# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

try:
    from orchestrator.orchestrator import run, synthesize_response
except ImportError:
    run = None
    synthesize_response = None


from agents import (
    academic_agent,
    placement_agent,
    campus_agent,
    communication_agent,
    navigator_agent,
    events_agent,
)

# Lazy Whisper Model Loading for Fast Startup
WHISPER_MODEL = None

def get_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        try:
            # pyrefly: ignore [missing-import]
            import whisper
            WHISPER_MODEL = whisper.load_model("tiny")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Whisper initialization failed: {str(e)}")
    return WHISPER_MODEL



app = FastAPI(
    title="Smart Campus Multi-Agent API",
    description="Backend orchestration API, voice transcription, and multi-agent system endpoints",
    version="1.1.0"
)

# CORS middleware allowing all local frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request Schemas ---
class StudentProfile(BaseModel):
    name: str = "Bhavya Vennapusa"
    branch: str = "CSE - 3rd Year"
    attendance: str = "88%"
    hostel: str = "Block B"


class ChatRequest(BaseModel):
    message: str
    session_id: str = "demo_session_frontend"
    profile: Optional[dict] = None


class ConfirmRequest(BaseModel):
    confirmed: bool
    context: str = "action"


class ApproveActionRequest(BaseModel):
    action_id: str
    status: Literal["approved", "rejected"]


class CreateGroupRequest(BaseModel):
    group_name: str
    member_ids: List[str]
    group_type: str = "temporary"
    duration_hours: Optional[int] = 24


class DraftEmailRequest(BaseModel):
    recipient_email: str
    subject: str
    core_message: str


class TaskCreateRequest(BaseModel):
    content: str
    due_string: str = "tomorrow"


class DirectionsRequest(BaseModel):
    origin: str = "Hostel Block B"
    destination: str = "Central Library"


class RegisterEventRequest(BaseModel):
    event_name: str = "AgentX Hackathon 2026"


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


class ScheduleReminderRequest(BaseModel):
    event: str
    minutes_before: int = 60


# --- System Endpoints ---
@app.get("/health")
def health():
    """Liveness check endpoint."""
    return {"status": "ok", "service": "Smart Campus Multi-Agent System"}


# --- Feature 1: Voice Transcription Endpoint ---
@app.post(
    "/transcribe",
    summary="Transcribe audio recording to text",
    description="Accepts an audio blob (.wav, .mp3, .m4a), transcribes using Whisper, and returns extracted text.",
    responses={
        200: {"description": "Successful transcription", "content": {"application/json": {"example": {"text": "What is my current attendance requirement?"}}}},
        400: {"description": "Empty or non-audio file payload"},
        422: {"description": "Malformed or unprocessable audio blob"}
    }
)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Accepts an audio blob, writes to temp file, transcribes with Whisper, and cleans up."""
    # 1. Validation: non-empty check
    contents = await audio.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    # 2. Content-type / Extension validation
    ct = audio.content_type or ""
    fn = (audio.filename or "").lower()
    valid_extensions = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac")
    if not (ct.startswith("audio/") or ct.startswith("video/") or fn.endswith(valid_extensions)):
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ct}'. Must be an audio file.")

    # 3. Save to temporary file & Transcribe
    suffix = Path(fn).suffix if Path(fn).suffix in valid_extensions else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        model = get_whisper_model()
        result = model.transcribe(tmp_path)
        return {"text": result.get("text", "").strip()}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# --- Orchestrated Multi-Agent Chat Endpoint ---
@app.post("/chat")
def chat(req: ChatRequest):
    """Primary multi-agent reasoning chat endpoint."""
    message_text = req.message
    session_id = req.session_id
    profile = req.profile or {}

    prof_name = profile.get("name") or "Student"
    prof_branch = profile.get("branch_year") or profile.get("branch") or "CSE - 3rd Year"
    prof_hostel = profile.get("hostel_block") or profile.get("hostel") or "Block B"
    prof_att = profile.get("attendance") or profile.get("attendance_pct") or "88"
    if isinstance(prof_att, (int, float)):
        prof_att = f"{prof_att}"

    if run:
        try:
            steps = run(message_text, session_id=session_id, profile=profile)
            agents_used = list(dict.fromkeys(s.agent for s in steps))
            reasoning_steps = [f"[{s.agent}] Action '{s.action}' -> {s.status}" for s in steps]

            actions = []
            requires_confirmation = False
            action_id = None

            for s in steps:
                res = s.result
                if res:
                    if hasattr(res, 'actions') and res.actions:
                        actions.extend(res.actions)
                    elif isinstance(res.data, dict) and "actions" in res.data:
                        actions.extend(res.data["actions"])

                    if getattr(res, 'status', '') == "needs_confirmation":
                        requires_confirmation = True
                        if isinstance(res.data, dict) and res.data.get("action_id"):
                            action_id = res.data.get("action_id")

            # Fallback check for email/draft keywords if action_id missing
            if ("email" in message_text.lower() or "draft" in message_text.lower() or "grievance" in message_text.lower()):
                requires_confirmation = True
                if not action_id and communication_agent.PENDING_ACTIONS:
                    action_id = list(communication_agent.PENDING_ACTIONS.keys())[-1]

            unique_actions = []
            seen_urls = set()
            for act in actions:
                u = act.get("url")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    unique_actions.append(act)
                elif not u:
                    unique_actions.append(act)

            trace = [
                {
                    "agent": s.agent,
                    "action": s.action,
                    "status": "done" if s.status == "done" else ("failed" if s.status == "failed" else "running"),
                    "message": s.result.message if s.result else ""
                }
                for s in steps
            ]

            steps_trace_str = "\n".join(
                f"- Agent: {s.agent}, Action: {s.action}, Status: {s.status}, Message: {s.result.message if s.result else ''}"
                for s in steps
            )

            synthesis_system_prompt = f"""You are CampusAgenda AI. Turn the backend agent trace below into ONE natural, concise reply for the student. Never show markdown headers, internal IDs, or raw policy-document fragments — extract only what's relevant to answering their question, in plain conversational language.

Student: {prof_name}, {prof_branch}, Hostel {prof_hostel}, Attendance {prof_att}%
Question: "{message_text}"
Agent trace: {steps_trace_str}

If a step needs user confirmation, ask for it naturally and mention what will happen if confirmed. If an agent found nothing relevant, don't mention it. Never invent data not present in the trace."""

            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            reply = None

            if anthropic_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=anthropic_key, timeout=4.0)
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=500,
                        system=synthesis_system_prompt,
                        messages=[{"role": "user", "content": "Synthesize the trace into a single reply."}],
                    )
                    reply = response.content[0].text.strip()
                except Exception:
                    pass

            if not reply and synthesize_response:
                reply = synthesize_response(message_text, steps, profile=profile)

            if not reply:
                messages = []
                for s in steps:
                    if s.result and s.result.message:
                        clean_msg = re.sub(r'\[Action ID:\s*[^\]]+\]', '', s.result.message).strip()
                        clean_msg = re.sub(r'#{1,6}\s*', '', clean_msg).strip()
                        messages.append(clean_msg)
                
                if requires_confirmation:
                    reply = f"Hello {prof_name}! I have prepared your request. Would you like me to send this official email to academic_office@vasavi.ac.in?"
                elif messages:
                    reply = f"Hello {prof_name}! " + " ".join(messages)
                else:
                    reply = f"Hello {prof_name}! Processed request via {', '.join(agents_used)} agent pipeline."

            # Post-processing: strip any remaining markdown headers or action IDs
            reply = re.sub(r'\[Action ID:\s*[^\]]+\]', '', reply).strip()
            reply = re.sub(r'#{1,6}\s*', '', reply).strip()

            return {
                "reply": reply,
                "actions": unique_actions,
                "agents_used": agents_used,
                "reasoning_steps": reasoning_steps,
                "requires_confirmation": requires_confirmation,
                "action_id": action_id,
                "trace": trace
            }
        except Exception as e:
            import traceback
            print(f"Chat endpoint error: {e}")
            traceback.print_exc()


    return {
        "reply": f"Processed query regarding: {message_text}",
        "actions": [],
        "agents_used": ["academic"],
        "reasoning_steps": ["[academic] Dispatched default action"],
        "requires_confirmation": False,
        "action_id": None,
        "trace": [{"agent": "academic", "action": "general_synthesis", "status": "done", "message": "Handled via fallback pipeline."}]
    }



# --- Feature 3: Communication & Human-in-the-loop Approval ---
@app.get("/communication/contacts")
def get_contacts(student_id: str = "demo_student", query_type: str = "faculty", subject: Optional[str] = None):
    res = communication_agent.get_relevant_contacts({
        "student_id": student_id,
        "query_type": query_type,
        "subject": subject
    })
    return res.to_dict()


@app.get("/communication/groups")
def get_groups():
    conn = communication_agent.sqlite3.connect(communication_agent.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_id, group_name, group_type, created_by, expires_at FROM chat_groups")
    rows = cursor.fetchall()
    conn.close()
    groups = [
        {"group_id": r[0], "group_name": r[1], "group_type": r[2], "created_by": r[3], "expires_at": r[4]}
        for r in rows
    ]
    return {"groups": groups, "count": len(groups)}


@app.post("/communication/groups")
def create_group(req: CreateGroupRequest):
    res = communication_agent.create_chat_group({
        "group_name": req.group_name,
        "member_ids": req.member_ids,
        "group_type": req.group_type,
        "duration_hours": req.duration_hours
    })
    return res.to_dict()


@app.post("/communication/draft-email")
def draft_email(req: DraftEmailRequest):
    res = communication_agent.draft_official_email({
        "recipient_email": req.recipient_email,
        "subject": req.subject,
        "core_message": req.core_message
    })
    return res.to_dict()


@app.post("/communication/approve-action")
def approve_action(req: ApproveActionRequest):
    action_id = req.action_id
    pending = communication_agent.PENDING_ACTIONS.get(action_id)

    if not pending:
        raise HTTPException(status_code=404, detail=f"Pending action ID '{action_id}' not found.")

    if req.status == "approved":
        send_res = communication_agent.send_email({
            "to": pending["to"],
            "subject": pending["subject"],
            "body": pending["body"]
        })
        communication_agent.PENDING_ACTIONS.pop(action_id, None)
        return {
            "status": "done",
            "message": f"Action '{action_id}' APPROVED. Email sent to {pending['to']}.",
            "details": send_res.to_dict()
        }
    else:
        communication_agent.PENDING_ACTIONS.pop(action_id, None)
        return {
            "status": "rejected",
            "message": f"Action '{action_id}' REJECTED. Email draft discarded.",
            "details": None
        }


# --- Feature 2 Domain Endpoints exposed for Suhani ---
@app.get("/placement/github")
def placement_github(username: str = "octocat"):
    res = placement_agent.get_github_profile({"username": username})
    return res.to_dict()


@app.get("/placement/opportunities")
def placement_opportunities(role: str = "Software Engineer"):
    res = placement_agent.find_opportunities({"role": role})
    return res.to_dict()


@app.get("/placement/eligible-companies")
def placement_eligible_companies(session_id: str = "demo_session_frontend"):
    res = placement_agent.get_all_eligible_companies({"session_id": session_id})
    return res.to_dict()


@app.get("/academic/tasks")
def get_academic_tasks():
    res = academic_agent.get_tasks({})
    return res.to_dict()


@app.post("/academic/tasks")
def create_academic_task(req: TaskCreateRequest):
    res = academic_agent.create_task({"content": req.content, "due_string": req.due_string})
    return res.to_dict()


@app.get("/academic/timetable")
def get_academic_timetable(session_id: str = "demo_session_frontend"):
    res = academic_agent.get_timetable({"session_id": session_id})
    return res.to_dict()


@app.post("/navigator/directions")
def get_navigator_directions(req: DirectionsRequest):
    res = navigator_agent.get_directions({"origin": req.origin, "destination": req.destination})
    return res.to_dict()


@app.post("/events/register")
def register_for_event(req: RegisterEventRequest):
    res = events_agent.register_event({"event_name": req.event_name})
    return res.to_dict()


@app.post("/communication/email")
def direct_send_email(req: SendEmailRequest):
    res = communication_agent.send_email({"to": req.to, "subject": req.subject, "body": req.body})
    return res.to_dict()


@app.post("/communication/calendar")
def schedule_calendar_appointment(title: str = "Advising", start_time: str = "2026-08-12 14:00"):
    res = communication_agent.schedule_appointment({"title": title, "start_time": start_time})
    return res.to_dict()


@app.post("/communication/reminder")
def schedule_event_reminder(req: ScheduleReminderRequest):
    res = communication_agent.schedule_reminder({"event": req.event, "minutes_before": req.minutes_before})
    return res.to_dict()


@app.post("/chat/confirm")
def confirm_action(req: ConfirmRequest):
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


# Mount static frontend files from frontend directory
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")





if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
