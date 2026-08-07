import sys
from pathlib import Path

# Ensure specialized_agents folder is in sys.path
SPEC_AGENTS_ROOT = Path(__file__).resolve().parent
if str(SPEC_AGENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SPEC_AGENTS_ROOT))

import uuid
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from pydantic import BaseModel, Field

from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.academic_agent.agent import AcademicAgent
from agents.placement_agent.agent import PlacementAgent
from agents.campus_agent.agent import CampusAgent
from agents.communication_agent.agent import CommunicationAgent, PENDING_APPROVAL_ACTIONS
from agents.services.transcription import transcribe_audio_file
from agents.adapters.gmail_adapter import GmailAdapter

logger = logging.getLogger("SmartCampusServer")

app = FastAPI(
    title="Smart Campus Multi-Agent System API",
    description="REST Contract endpoints for Smart Campus frontend integration (Suhani). Exposes Voice Transcription, Agent Tools, External API Adapters, and Human-in-the-Loop Approval.",
    version="2.0.0"
)

# Global Agent Registry Initialization
registry = AgentRegistry()
acad_agent = AcademicAgent(registry=registry)
place_agent = PlacementAgent(registry=registry)
campus_agent = CampusAgent(registry=registry)
comms_agent = CommunicationAgent(registry=registry)

registry.register("academic_agent", acad_agent)
registry.register("placement_agent", place_agent)
registry.register("campus_agent", campus_agent)
registry.register("communication_agent", comms_agent)

gmail_adapter = GmailAdapter()


# -----------------------------------------------------------------------------
# FEATURE 1 — Voice Transcription Endpoint
# -----------------------------------------------------------------------------
@app.post("/transcribe", summary="Transcribe Audio File to Text", response_model=Dict[str, str])
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Accepts an audio file upload (.wav, .mp3, .m4a, .ogg), transcribes speech to text using Whisper,
    and returns a clean JSON response {"text": "..."}.
    Includes strict validation and clean 400/422 error handling.
    """
    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file uploaded.")

    # Validate content-type or filename extension
    filename = audio.filename.lower()
    content_type = (audio.content_type or "").lower()
    valid_exts = (".wav", ".mp3", ".m4a", ".ogg", ".webm")

    if not content_type.startswith("audio/") and not filename.endswith(valid_exts):
        raise HTTPException(status_code=400, detail=f"Invalid file format '{audio.filename}'. Expected an audio file (.wav, .mp3, .m4a, .ogg).")

    file_bytes = await audio.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty (0 bytes).")

    try:
        text = await transcribe_audio_file(file_bytes, audio.filename)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {str(e)}")


# -----------------------------------------------------------------------------
# FEATURE 3 — Communication Agent Endpoints & Human-in-the-loop Approval
# -----------------------------------------------------------------------------
class ActionApprovalRequest(BaseModel):
    action_id: str
    status: str = Field(..., description="'approved' or 'rejected'")


@app.get("/communication/contacts", summary="Get Categorized Contacts")
async def get_contacts(student_id: str = "STU001", query_type: str = "faculty", subject: Optional[str] = None):
    req = TaskRequest(
        trace_id=f"api-{uuid.uuid4().hex[:6]}",
        task="get_relevant_contacts",
        params={"query_type": query_type, "subject": subject},
        student_id=student_id
    )
    resp = await comms_agent.handle(req)
    return resp


@app.get("/communication/groups", summary="Get Active Permanent and Temporary Groups")
async def get_groups():
    req = TaskRequest(
        trace_id=f"api-{uuid.uuid4().hex[:6]}",
        task="get_active_groups",
        params={}
    )
    resp = await comms_agent.handle(req)
    return resp


@app.post("/communication/draft-email", summary="Draft Official Email with Human-in-the-Loop Approval")
async def draft_email(
    student_id: str = Body(..., embed=True),
    recipient_email: str = Body(..., embed=True),
    subject: str = Body(..., embed=True),
    core_message: str = Body(..., embed=True)
):
    req = TaskRequest(
        trace_id=f"api-{uuid.uuid4().hex[:6]}",
        task="draft_official_email",
        params={"recipient_email": recipient_email, "subject": subject, "core_message": core_message},
        student_id=student_id
    )
    resp = await comms_agent.handle(req)
    return resp


@app.post("/communication/approve-action", summary="Approve or Reject Pending Action")
async def approve_action(payload: ActionApprovalRequest):
    action_id = payload.action_id
    status = payload.status.lower()

    if action_id not in PENDING_APPROVAL_ACTIONS:
        raise HTTPException(status_code=404, detail=f"Pending action '{action_id}' not found or already processed.")

    action = PENDING_APPROVAL_ACTIONS.pop(action_id)

    if status == "approved":
        send_res = await gmail_adapter.send_email(
            recipient_email=action.get("recipient_email"),
            subject=action.get("subject"),
            body=action.get("body")
        )
        return {
            "action_id": action_id,
            "status": "approved",
            "execution": send_res,
            "message": f"Action '{action_id}' approved and email sent to {action.get('recipient_email')}."
        }
    else:
        return {
            "action_id": action_id,
            "status": "rejected",
            "message": f"Action '{action_id}' was rejected and draft discarded."
        }


# -----------------------------------------------------------------------------
# FEATURE 2 — Agent REST Endpoints (Response includes "source": "live" | "mock")
# -----------------------------------------------------------------------------
@app.get("/placement/github", summary="Get GitHub Profile")
async def get_github(username: str = "octocat"):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="get_github_profile", params={"username": username})
    return await place_agent.handle(req)


@app.get("/placement/opportunities", summary="Get Placement Opportunities")
async def get_placement_opportunities(query: str = "Software Engineering"):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="list_opportunities", params={"query": query})
    return await place_agent.handle(req)


@app.get("/placement/eligible-companies", summary="Get All Eligible Companies")
async def get_eligible_companies(student_id: str = "STU001", cgpa: float = 8.8, branch: str = "Computer Science"):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="check_all_company_eligibility", params={"cgpa": cgpa, "branch": branch}, student_id=student_id)
    return await place_agent.handle(req)


@app.get("/academic/tasks", summary="Get Academic Tasks")
async def get_academic_tasks():
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="get_tasks", params={})
    return await acad_agent.handle(req)


@app.post("/academic/tasks", summary="Create Academic Task")
async def create_academic_task(content: str = Body(..., embed=True), due_string: str = Body("today", embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="create_task", params={"content": content, "due_string": due_string})
    return await acad_agent.handle(req)


@app.get("/academic/timetable", summary="Get Student Timetable")
async def get_academic_timetable(student_id: str = "STU001"):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="get_timetable", params={}, student_id=student_id)
    return await acad_agent.handle(req)


@app.post("/navigator/directions", summary="Get Campus / Off-Campus Directions")
async def get_directions(origin: str = Body("Main Gate", embed=True), destination: str = Body("Auditorium A", embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="get_directions", params={"origin": origin, "destination": destination})
    return await campus_agent.handle(req)


@app.post("/events/register", summary="Register for Event")
async def register_event(event_id: str = Body("EVT001", embed=True), student_id: str = Body("STU001", embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="register_for_event", params={"event_id": event_id}, student_id=student_id)
    return await campus_agent.handle(req)


@app.post("/communication/email", summary="Send or Draft Email")
async def send_or_draft_email(recipient: str = Body(..., embed=True), subject: str = Body(..., embed=True), body: str = Body(..., embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="draft_email", params={"recipient": recipient, "subject": subject, "body": body})
    return await comms_agent.handle(req)


@app.post("/communication/calendar", summary="Schedule Appointment")
async def schedule_calendar(title: str = Body(..., embed=True), date: str = Body("2026-08-10", embed=True), time_slot: str = Body("14:00-15:00", embed=True), location: str = Body("Main Library", embed=True), student_id: str = Body("STU001", embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="schedule_appointment", params={"title": title, "date": date, "time": time_slot, "location": location}, student_id=student_id)
    return await comms_agent.handle(req)


@app.post("/communication/reminder", summary="Schedule Reminder")
async def schedule_event_reminder(title: str = Body(..., embed=True), event_time: str = Body("2026-08-10 14:00:00", embed=True), lead_time_minutes: int = Body(60, embed=True), target_user: str = Body("STU001", embed=True)):
    req = TaskRequest(trace_id=f"api-{uuid.uuid4().hex[:6]}", task="schedule_reminder", params={"title": title, "event_time": event_time, "lead_time_minutes": lead_time_minutes, "target_user": target_user}, student_id=target_user)
    return await comms_agent.handle(req)
