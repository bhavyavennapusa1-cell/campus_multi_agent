"""
<<<<<<< HEAD
Campus Agent for Smart Campus Multi-Agent System.
Handles hostel regulations, campus events/hackathons, and grievance SOPs using RAG & Memory.
"""

from pathlib import Path
import sys

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session


def get_hostel_info(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "hostel curfew gate closing timings late entry outpass rules")
    rag_results = retrieve(query, k=1, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    info_text = top_rag["text"] if top_rag else "Hostel regulations unavailable."
    sec_title = top_rag["section_title"] if top_rag else "Hostel Rules"

    return AgentResponse(
        status="success",
        data={
            "student_name": profile["name"],
            "hostel_block": profile["hostel_block"],
            "info_text": info_text
        },
        message=f"Hostel Regulation ({sec_title}): {info_text[:120]}...",
        citation=citation
    )


def get_events(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "upcoming technical hackathons fests cultural Axiom Euphoria Mantra")
    rag_results = retrieve(query, k=1, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "events": [
                {"title": "AgentX National Hackathon 2026", "date": "April 10-11, 2026"},
                {"title": "Annual Cultural Fest Mantra 2026", "date": "April 22-23, 2026"}
            ],
            "details": top_rag["text"] if top_rag else ""
        },
        message=f"Retrieved upcoming campus hackathons and fests for {profile['name']}.",
        citation=citation
=======
Person B owns this file. Fill in the TODOs following the same pattern as
placement_agent.py.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import AgentResponse

BASE = Path(__file__).resolve().parent.parent / "data"

with open(BASE / "events.json") as f:
    EVENTS = json.load(f)["events"]


def get_events(params: dict) -> AgentResponse:
    return AgentResponse(
        status="success",
        data={"events": EVENTS},
        message=f"Found {len(EVENTS)} upcoming events",
    )


def get_hostel_info(params: dict) -> AgentResponse:
    # TODO Person B: pull from knowledge/docs/hostel_rules.md via the RAG agent instead,
    # or add data/hostel.json with room/mess/warden contact info
    return AgentResponse(
        status="success",
        data={"gate_closing": "9:30 PM weekdays, 11:00 PM weekends"},
        message="Hostel info retrieved",
>>>>>>> frontend
    )


def file_grievance(params: dict) -> AgentResponse:
<<<<<<< HEAD
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    grievance_text = params.get("text", "General grievance submission")
    query = params.get("query", "grievance redressal SOP categories SLA submission")
    rag_results = retrieve(query, k=1, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    return AgentResponse(
        status="needs_confirmation",
        data={
            "student": profile["name"],
            "grievance": grievance_text,
            "sop_summary": top_rag["text"] if top_rag else ""
        },
        message=f"Grievance drafted for {profile['name']}. Awaiting confirmation to submit under SLA guidelines.",
        citation=citation
=======
    grievance_text = params.get("text", "")
    # TODO Person B: actually append to a grievances.json or SQLite table
    return AgentResponse(
        status="needs_confirmation",
        data={"grievance": grievance_text},
        message="Grievance drafted, awaiting confirmation to submit",
>>>>>>> frontend
    )


ACTIONS = {
<<<<<<< HEAD
    "get_hostel_info": get_hostel_info,
    "get_events": get_events,
=======
    "get_events": get_events,
    "get_hostel_info": get_hostel_info,
>>>>>>> frontend
    "file_grievance": file_grievance,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown campus action: {action}")
    return ACTIONS[action](params)
