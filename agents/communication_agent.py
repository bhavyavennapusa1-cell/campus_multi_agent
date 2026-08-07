"""
Person B owns this file.
These actions simulate sending email/reminders rather than actually sending
them - that's fine and expected per the problem statement (Simulated campus
services).
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import AgentResponse


def draft_email(params: dict) -> AgentResponse:
    to = params.get("to", "professor@college.edu")
    subject = params.get("subject", "Request")
    body = params.get("body", "")

    # TODO Person B: this is where you'd call the LLM to actually draft the body
    # if it wasn't provided by the orchestrator already.
    drafted = f"To: {to}\nSubject: {subject}\n\n{body}"

    return AgentResponse(
        status="needs_confirmation",
        data={"draft": drafted},
        message="Email drafted, awaiting confirmation to send",
    )


def schedule_reminder(params: dict) -> AgentResponse:
    event = params.get("event", "an event")
    minutes_before = params.get("minutes_before", 60)

    # TODO Person B: actually store this in a reminders table keyed by session_id
    return AgentResponse(
        status="success",
        data={"event": event, "minutes_before": minutes_before},
        message=f"Reminder set for {minutes_before} minutes before {event}",
    )


ACTIONS = {
    "draft_email": draft_email,
    "schedule_reminder": schedule_reminder,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown communication action: {action}")
    return ACTIONS[action](params)
