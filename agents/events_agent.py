"""
Events Agent for Synapse Multi-Agent System.
Handles event registration, waitlisting, and Google Calendar event sync using adapter pattern.
"""

import os
import requests
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session


def resolve_profile(params: dict) -> dict:
    prof = params.get("profile")
    session_id = params.get("session_id", "default")
    if not prof:
        prof = get_profile(session_id) or create_session(session_id)
    else:
        prof = dict(prof)
        if "name" not in prof:
            prof["name"] = "Student"
    return prof


def get_events(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

    query = params.get("query", "upcoming technical hackathons fests cultural Axiom Euphoria Mantra")
    rag_results = retrieve(query, k=1, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "events": [
                {"event_id": "evt_001", "title": "AgentX National Hackathon 2026", "date": "2026-08-15", "venue": "Main Auditorium"},
                {"event_id": "evt_002", "title": "AI & Robotics Workshop", "date": "2026-08-18", "venue": "Tech Block Seminar Hall"}
            ],
            "details": top_rag["text"] if top_rag else "",
            "source": "mock"
        },
        message=f"Retrieved upcoming campus hackathons and workshops for {profile['name']}.",
        citation=citation
    )


def register_event(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    event_name = params.get("event_name") or params.get("event_id") or "AgentX Hackathon 2026"


    # Auto sync to Google Calendar upon registration
    cal_res = add_event_to_calendar({
        "event_id": "evt_001",
        "event_name": event_name,
        "date_str": "2026-08-15"
    })

    return AgentResponse(
        status="success",
        data={
            "student_name": profile["name"],
            "event_name": event_name,
            "registration_id": f"REG_{profile['name'][:3].upper()}_9921",
            "calendar_sync": cal_res.data,
            "source": "mock"
        },
        message=f"Successfully registered {profile['name']} for '{event_name}'. Synced to Google Calendar.",
        citation=None
    )


def add_event_to_calendar(params: dict) -> AgentResponse:
    """Feature 2: Google Calendar API -> add_event_to_calendar()"""
    event_name = params.get("event_name", "Campus Event")
    date_str = params.get("date_str", "2026-08-15")
    api_key = os.environ.get("GOOGLE_CALENDAR_API_KEY")

    if api_key:
        try:
            resp = requests.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "summary": event_name,
                    "start": {"date": date_str},
                    "end": {"date": date_str}
                },
                timeout=3.0
            )
            if resp.status_code in (200, 201):
                return AgentResponse(
                    status="success",
                    data={"gcal_id": resp.json().get("id"), "source": "live"},
                    message=f"Added '{event_name}' on {date_str} to live Google Calendar.",
                    citation=None
                )
        except Exception:
            pass

    return AgentResponse(
        status="success",
        data={"gcal_id": "mock_gcal_evt_10928", "event_name": event_name, "date": date_str, "source": "mock"},
        message=f"Added '{event_name}' on {date_str} to Google Calendar [mock mode].",
        citation=None
    )


def general_synthesis(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    query = params.get("query", "upcoming events workshops registration")


    rag_results = retrieve(query, k=2, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    synthesis_msg = (
        f"Campus Events Summary for {profile['name']}:\n"
        f"1. Top Upcoming Event: AgentX National Hackathon 2026 (Aug 15).\n"
        f"2. Registration Status: Open for all CSE 3rd Year students.\n"
        f"3. Event Policy: {top_rag['text'][:150] if top_rag else 'Certificate provided for participation.'}"
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "rag_chunks": rag_results,
            "synthesis_text": synthesis_msg,
            "source": "mock"
        },
        message=synthesis_msg,
        citation=citation
    )


ACTIONS = {
    "get_events": get_events,
    "register_event": register_event,
    "add_event_to_calendar": add_event_to_calendar,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown events action: {action}")
    return ACTIONS[action](params)
