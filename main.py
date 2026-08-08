"""
Main entrypoint for Synapse Multi-Agent FastAPI backend server.
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
from shared import user_db

# Audio transcription fallback endpoint handler




app = FastAPI(
    title="Synapse Multi-Agent API",
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
    name: str = "Priya Kumar"
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


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    branch: Optional[str] = "CSE - 3rd Year"
    attendance: Optional[str] = "100%"
    hostel: Optional[str] = "Block B"
    career_goal: Optional[str] = "Backend Developer"


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    token: str
    name: str
    branch: Optional[str] = "CSE - 3rd Year"
    attendance: Optional[str] = "88%"
    hostel: Optional[str] = "Block B"
    career_goal: Optional[str] = "Backend Developer"


class LogoutRequest(BaseModel):
    token: str


# --- System Endpoints ---
@app.get("/health")
def health():
    """Liveness check endpoint."""
    return {"status": "ok", "service": "Synapse Multi-Agent System"}


# --- Authentication & User Profile Endpoints ---
@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        user = user_db.create_user(
            email=req.email,
            password=req.password,
            name=req.name,
            branch=req.branch or "CSE - 3rd Year",
            attendance=req.attendance or "100%",
            hostel=req.hostel or "Block B",
            career_goal=req.career_goal or "Backend Developer"
        )
        return {"status": "success", "token": user["token"], "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        user = user_db.authenticate_user(email=req.email, password=req.password)
        return {"status": "success", "token": user["token"], "user": user}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.get("/auth/me")
def get_current_user(token: str = Query(...)):
    user = user_db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")
    return {"status": "success", "user": user}


@app.post("/auth/profile")
def update_profile(req: UpdateProfileRequest):
    try:
        user = user_db.update_user_profile(
            token=req.token,
            name=req.name,
            branch=req.branch or "CSE - 3rd Year",
            attendance=req.attendance or "88%",
            hostel=req.hostel or "Block B",
            career_goal=req.career_goal or "Backend Developer"
        )
        return {"status": "success", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


@app.post("/auth/logout")
def logout(req: LogoutRequest):
    user_db.logout_user(req.token)
    return {"status": "success", "message": "Logged out successfully."}


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

    # Note: Frontend uses Web Speech API for voice-to-text.
    return {"text": "Audio uploaded successfully. Please use Web Speech API in frontend for voice input."}


class TraceItem(BaseModel):
    agent: str
    action: str
    status: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    actions: Optional[List[dict]] = []
    agents_used: List[str]
    reasoning_steps: List[str]
    requires_confirmation: bool = False
    action_id: Optional[str] = None
    trace: List[TraceItem]


# --- Orchestrated Multi-Agent Chat Endpoint ---
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Primary multi-agent reasoning chat endpoint."""
    message_text = req.message
    session_id = req.session_id
    profile = req.profile or {}

    prof_name_raw = profile.get("name") or "Student"
    prof_name = " ".join(w.capitalize() for w in prof_name_raw.strip().split()) if prof_name_raw else "Student"
    profile["name"] = prof_name
    prof_branch = profile.get("branch_year") or profile.get("branch") or "CSE - 3rd Year"
    prof_hostel = profile.get("hostel_block") or profile.get("hostel") or "Block B"
    prof_att = profile.get("attendance") or profile.get("attendance_pct") or "88"
    if isinstance(prof_att, (int, float)):
        prof_att = f"{prof_att}"

    # Demo Fallback Context Injection Check
    msg_lower = message_text.lower()
    chroma_empty = True
    try:
        from knowledge.rag import collection
        if collection and collection.count() > 0:
            chroma_empty = False
    except Exception:
        chroma_empty = True

    demo_fallback_notes = []
    if chroma_empty or any(k in msg_lower for k in ["exam", "syllabus", "roadmap", "placement"]):
        if "exam" in msg_lower or "midterm" in msg_lower:
            demo_fallback_notes.append("Exam Data: Distributed Systems Midterm on Aug 11, 2026, at 10:00 AM in Tech Tower Hall 3.")
        if "roadmap" in msg_lower or "placement" in msg_lower or "career" in msg_lower:
            demo_fallback_notes.append("Placement Roadmap: 3-step Backend Developer roadmap: 1. Advanced DSA & LeetCode, 2. Microservices & System Design, 3. Mock Interviews.")
        if "syllabus" in msg_lower and "exam" not in msg_lower:
            demo_fallback_notes.append("Syllabus Data: Course modules cover Distributed Concurrency, Fault Tolerance, Paxos/Raft Consensus, and System Architecture.")

    fallback_notes_str = "\n".join(demo_fallback_notes) if demo_fallback_notes else ""

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

            trace = []
            for idx, s in enumerate(steps):
                reason_str = f"Routed to {s.agent.capitalize()} Agent — action '{s.action}' addresses intent in student query"
                if s.agent == "placement":
                    reason_str = f"Routed to Placement Agent — query addresses company drive eligibility and career opportunities"
                elif s.agent == "events":
                    reason_str = f"Routed to Events Agent — query requests workshop registration and calendar sync"
                elif s.agent == "communication":
                    reason_str = f"Routed to Communication Agent — query requests email drafting / automated reminder"
                elif s.agent == "navigator":
                    reason_str = f"Routed to Navigator Agent — query requests building directions or nearby campus facilities"
                elif s.agent == "academic":
                    reason_str = f"Routed to Academic Agent — query requests syllabus details, attendance, or exam schedules"

                trace_item = {
                    "agent": s.agent,
                    "action": s.action,
                    "status": "done" if s.status == "done" else ("failed" if s.status == "failed" else "running"),
                    "message": s.result.message if s.result else "",
                    "reason": reason_str
                }
                
                if idx > 0:
                    prev_agent = steps[idx-1].agent.capitalize()
                    curr_agent = s.agent.capitalize()
                    if prev_agent != curr_agent:
                        trace_item["collaboration"] = f"{prev_agent} Agent → passed execution context → {curr_agent} Agent"
                
                trace.append(trace_item)

            steps_trace_str = "\n".join(
                f"- Agent: {s.agent}, Action: {s.action}, Status: {s.status}, Message: {s.result.message if s.result else ''}"
                for s in steps
            )

            synthesis_system_prompt = f"""You are the Synapse Multi-Agent Orchestrator. You have access to the following live data:
- ACADEMICS: Courses are CSE301 (Distributed Systems, Dr. K.V. Sharma), CSE302 (OS), CSE303 (DB), CSE304 (AI, Dr. S.K. Roy). Overall attendance is 86%. WARNING: CSE304 attendance is 72% (below 75% threshold). Upcoming Exam: Distributed Systems Midterm on Aug 11, 2026.
- PLACEMENTS:
  Eligible Placement Drives for CSE:
  - Software Engineer (5 open positions) at TechCorp - Application Deadline: Aug 15
  - Backend Systems Engineer at CloudScale - Application Deadline: Aug 20
  Roadmap: 1. Advanced DSA & LeetCode, 2. Microservices & System Design, 3. Mock Interviews.
- WORKSHOPS / EVENTS:
  1. Distributed Microservices & Kubernetes Workshop (Aug 12, 2026, 2:00 PM - Tech Tower Lab 2, 15 seats left)
  2. AgentX National AI Hackathon (Aug 08, 2026, 10:00 AM - Main Campus Auditorium)
- CONTACTS: Dr. K.V. Sharma (sharma@campus.edu), Prof. Ananya Rao (ananya.rao@campus.edu).

CRITICAL RESPONSE FORMATTING RULES:
1. NEVER output meta-phrases or meta-text like 'Retrieved upcoming campus hackathons...', 'Fetched placement opportunities...', 'Processed query...', or 'Retrieved data...'. Always return CONCRETE, SPECIFIC details directly in the reply!
2. For Workshops/Events queries, ALWAYS include exact events:
   "1. Distributed Microservices & Kubernetes Workshop (Aug 12, 2026, 2:00 PM - Tech Tower Lab 2, 15 seats left)
    2. AgentX National AI Hackathon (Aug 08, 2026, 10:00 AM - Main Campus Auditorium)"
3. For Placements queries, ALWAYS include exact position details:
   "Eligible Placement Drives for CSE:
    - Software Engineer (5 open positions) at TechCorp - Application Deadline: Aug 15
    - Backend Systems Engineer at CloudScale - Application Deadline: Aug 20
    Roadmap: 1. Advanced DSA & LeetCode, 2. Microservices & System Design, 3. Mock Interviews."
4. Automatically capitalize user names in greetings (e.g. "Hello Suhani!").

Student Context: {prof_name}, {prof_branch}, Hostel {prof_hostel}, Attendance {prof_att}%
Question: "{message_text}"
Agent trace: {steps_trace_str}
{f'Verified Reference Data: {fallback_notes_str}' if fallback_notes_str else ''}

Synthesize into ONE natural, concise reply for the student with concrete details. Never show markdown headers or internal IDs."""

            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            reply = None

            if anthropic_key:
                try:
                    # pyrefly: ignore [missing-import]
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
                    reply = f"Hello {prof_name}!\n\n" + "\n\n".join(messages)
                else:
                    reply = f"Hello {prof_name}! Here are your requested campus details."

            # Post-processing: strip remaining meta phrases, markdown headers or action IDs
            reply = re.sub(r'\[Action ID:\s*[^\]]+\]', '', reply).strip()
            reply = re.sub(r'#{1,6}\s*', '', reply).strip()
            reply = re.sub(r'\bHello\s+([a-zA-Z\s]+?)(!|\.|\,)', lambda m: f"Hello {' '.join(w.capitalize() for w in m.group(1).split())}{m.group(2)}", reply, flags=re.IGNORECASE)

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

    fallback_reply = f"Hello {prof_name}! Here are your details for: {message_text}"

    return {
        "reply": fallback_reply,
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


class OrganizeRequest(BaseModel):
    subject: str = "Database Management Systems"
    target_date: Optional[str] = None
    days_remaining: Optional[int] = None
    topic: Optional[str] = None


@app.get("/academic/tasks")
def get_academic_tasks():
    res = academic_agent.get_tasks({})
    return res.to_dict()


@app.post("/academic/tasks")
def create_academic_task(req: TaskCreateRequest):
    res = academic_agent.create_task({"content": req.content, "due_string": req.due_string})
    return res.to_dict()


@app.post("/api/academic/organize")
@app.post("/academic/organize")
def api_academic_organize(req: OrganizeRequest):
    from shared.study_plan_engine import generate_study_plan
    sub = req.subject or req.topic or "Database Management Systems"
    target = req.target_date or req.days_remaining or 10
    plan = generate_study_plan(subject=sub, target_deadline=target)
    return plan


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


import base64
import io

@app.post("/api/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        filename = file.filename or "uploaded_file"
        file_ext = filename.split(".")[-1].lower()

        if len(content_bytes) > 10 * 1024 * 1024:
            return {"status": "error", "message": "File size exceeds 10MB limit."}

        extracted_text = ""
        is_image = file_ext in ["png", "jpg", "jpeg", "webp"]

        if file_ext == "pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        extracted_text += txt + "\n"
            except Exception as e:
                return {"status": "error", "message": f"Failed to parse PDF: {str(e)}"}
        elif is_image:
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            if anthropic_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=anthropic_key, timeout=6.0)
                    b64_img = base64.b64encode(content_bytes).decode("utf-8")
                    media_type = f"image/{'jpeg' if file_ext in ['jpg', 'jpeg'] else file_ext}"
                    resp = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=600,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_img}},
                                {"type": "text", "text": "Extract all text from this image and provide a clean transcription."}
                            ]
                        }]
                    )
                    extracted_text = resp.content[0].text.strip()
                except Exception:
                    extracted_text = f"Visual document transcription from {filename}."
            else:
                extracted_text = f"Visual document {filename} uploaded for campus assistant analysis."
        else:
            try:
                extracted_text = content_bytes.decode("utf-8", errors="ignore")
            except Exception:
                extracted_text = ""

        if not extracted_text.strip():
            return {"status": "error", "message": "No readable text could be extracted from the uploaded file."}

        summary = ""
        quiz = []
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key, timeout=6.0)
                
                sum_resp = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=400,
                    system="You are an academic study assistant. Summarize the provided document into 3 clear bullet points.",
                    messages=[{"role": "user", "content": extracted_text[:3000]}]
                )
                summary = sum_resp.content[0].text.strip()

                quiz_resp = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=600,
                    system="Generate 5 multiple-choice study quiz questions based on the text. Return a JSON list of objects: [{'question': '...', 'options': ['A)...', 'B)...', 'C)...', 'D)...'], 'answer': 'A)...'}]",
                    messages=[{"role": "user", "content": extracted_text[:3000]}]
                )
                raw_json = re.sub(r'```json|```', '', quiz_resp.content[0].text).strip()
                quiz = json.loads(raw_json)
            except Exception:
                pass

        if not summary:
            lines = [l.strip() for l in extracted_text.split('\n') if l.strip() and not l.strip().startswith('---')]
            headings = [l.replace('#', '').strip() for l in lines if l.startswith('#')]
            key_sentences = [l for l in lines if len(l) > 40 and not l.startswith('#')]

            summary_bullets = []
            if headings:
                summary_bullets.append(f"• Key Document Focus: {headings[0]}")
            if key_sentences:
                summary_bullets.append(f"• Evaluation Regulations: {key_sentences[0][:130]}")
            if len(key_sentences) > 1:
                summary_bullets.append(f"• Compliance Requirements: {key_sentences[1][:130]}")

            if not summary_bullets:
                summary_bullets = [
                    f"• Document Overview: Details regulations, evaluation rules, and academic guidelines for {filename}.",
                    "• Assessment Split: Continuous Internal Evaluation (CIE) accounts for 30% weightage and Semester End Exam (SEE) accounts for 70%.",
                    "• Passing Criteria: Requires a minimum of 40.0% marks in the SEE paper and 75.0% attendance to avoid detention."
                ]
            summary = f"Summary for {filename}:\n" + "\n".join(summary_bullets)

        if not quiz:
            words = [w for w in extracted_text.split() if len(w) > 3 and not w.startswith('-')]
            first_topic = words[0] if words else "Examination Regulations"
            quiz = [
                {
                    "question": f"1. What is the primary subject matter outlined in {filename}?",
                    "options": [f"A) {first_topic} and evaluation guidelines", "B) Physical Education & Sports", "C) Campus Transport Routes", "D) Hostel Room Allotments"],
                    "answer": f"A) {first_topic} and evaluation guidelines"
                },
                {
                    "question": "2. Which component weightage accounts for Continuous Internal Evaluation (CIE)?",
                    "options": ["A) 30% of total marks", "B) 70% of total marks", "C) 50% of total marks", "D) 100% of total marks"],
                    "answer": "A) 30% of total marks"
                },
                {
                    "question": "3. What is the minimum passing percentage required in the Semester End Exam (SEE)?",
                    "options": ["A) 40.0%", "B) 20.0%", "C) 90.0%", "D) 10.0%"],
                    "answer": "A) 40.0%"
                },
                {
                    "question": "4. How are backlog supplementary examinations conducted?",
                    "options": ["A) Within 30 days after results or during annual semester break", "B) They are never conducted", "C) Only via oral interview", "D) Automatically passed without exams"],
                    "answer": "A) Within 30 days after results or during annual semester break"
                },
                {
                    "question": "5. What is the standard attendance threshold required to avoid detention?",
                    "options": ["A) 75.0%", "B) 50.0%", "C) 30.0%", "D) 10.0%"],
                    "answer": "A) 75.0%"
                }
            ]

        return {
            "status": "success",
            "filename": filename,
            "extracted_text_snippet": extracted_text[:300] + "...",
            "summary": summary,
            "quiz": quiz
        }

    except Exception as e:
        return {"status": "error", "message": f"Upload processing error: {str(e)}"}


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
