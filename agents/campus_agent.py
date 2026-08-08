"""
Campus Agent for Synapse Multi-Agent System.
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


def resolve_profile(params: dict) -> dict:
    prof = params.get("profile")
    session_id = params.get("session_id", "default")
    if not prof:
        prof = get_profile(session_id) or create_session(session_id)
    else:
        prof = dict(prof)
        if "name" not in prof:
            prof["name"] = "Student"
        if "hostel_block" not in prof:
            prof["hostel_block"] = prof.get("hostel", "Block B")
    return prof


def get_hostel_info(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

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
            "info_text": info_text,
            "source": "mock"
        },
        message=f"Hostel Regulation ({sec_title}): {info_text[:120]}...",
        citation=citation
    )


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
                {"title": "AgentX National Hackathon 2026", "date": "April 10-11, 2026"},
                {"title": "Annual Cultural Fest Mantra 2026", "date": "April 22-23, 2026"}
            ],
            "details": top_rag["text"] if top_rag else "",
            "source": "mock"
        },
        message=f"Retrieved upcoming campus hackathons and fests for {profile['name']}.",
        citation=citation
    )


def file_grievance(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

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
            "sop_summary": top_rag["text"] if top_rag else "",
            "source": "mock"
        },
        message=f"Grievance drafted for {profile['name']}. Awaiting confirmation to submit under SLA guidelines.",
        citation=citation
    )


def general_synthesis(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    query = params.get("query", "campus rules hostel grievances events general guidance")


    rag_results = retrieve(query, k=2, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    synthesis_msg = (
        f"Campus Life & Regulations Summary for {profile['name']} ({profile['hostel_block']}):\n"
        f"1. Hostel Rules: Curfew entry gate closes at 10:30 PM (weekdays) / 11:30 PM (weekends).\n"
        f"2. Active Fests: AgentX Hackathon & Mantra Fest 2026.\n"
        f"3. Policy Detail: {top_rag['text'][:150] if top_rag else 'Submit grievances via campus portal.'}"
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
    "get_hostel_info": get_hostel_info,
    "get_events": get_events,
    "file_grievance": file_grievance,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown campus action: {action}")
    return ACTIONS[action](params)
