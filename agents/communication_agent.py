"""
<<<<<<< HEAD
Communication Agent for Smart Campus Multi-Agent System.
Simulates sending emails, drafting communications, and scheduling reminders.
=======
Person B owns this file.
These actions simulate sending email/reminders rather than actually sending
them - that's fine and expected per the problem statement (Simulated campus
services).
>>>>>>> frontend
"""

from pathlib import Path
import sys

<<<<<<< HEAD
# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.memory import get_profile, create_session


def draft_email(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    to = params.get("to", "academic_office@vasavi.ac.in")
    subject = params.get("subject", f"Academic Inquiry from {profile['name']}")
    body = params.get("body", f"Dear Sir/Madam,\n\nI am writing regarding my academic details.\n\nRegards,\n{profile['name']} ({profile['branch']})")

=======
sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import AgentResponse


def draft_email(params: dict) -> AgentResponse:
    to = params.get("to", "professor@college.edu")
    subject = params.get("subject", "Request")
    body = params.get("body", "")

    # TODO Person B: this is where you'd call the LLM to actually draft the body
    # if it wasn't provided by the orchestrator already.
>>>>>>> frontend
    drafted = f"To: {to}\nSubject: {subject}\n\n{body}"

    return AgentResponse(
        status="needs_confirmation",
<<<<<<< HEAD
        data={
            "student_name": profile["name"],
            "to": to,
            "subject": subject,
            "draft": drafted
        },
        message=f"Email drafted for {profile['name']}. Awaiting user confirmation to dispatch.",
        citation=None
=======
        data={"draft": drafted},
        message="Email drafted, awaiting confirmation to send",
>>>>>>> frontend
    )


def schedule_reminder(params: dict) -> AgentResponse:
<<<<<<< HEAD
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    event = params.get("event", "Campus Event")
    minutes_before = params.get("minutes_before", 60)

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "event": event,
            "minutes_before": minutes_before
        },
        message=f"Reminder scheduled for {profile['name']}: {minutes_before} minutes prior to {event}.",
        citation=None
=======
    event = params.get("event", "an event")
    minutes_before = params.get("minutes_before", 60)

    # TODO Person B: actually store this in a reminders table keyed by session_id
    return AgentResponse(
        status="success",
        data={"event": event, "minutes_before": minutes_before},
        message=f"Reminder set for {minutes_before} minutes before {event}",
>>>>>>> frontend
    )


ACTIONS = {
    "draft_email": draft_email,
    "schedule_reminder": schedule_reminder,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown communication action: {action}")
    return ACTIONS[action](params)
