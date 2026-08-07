"""
Academic Agent for Smart Campus Multi-Agent System.
Handles student attendance checks, exam schedules, and academic policy queries using RAG & Memory.
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


def get_attendance(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "minimum attendance percentage required condonation detention threshold")
    rag_results = retrieve(query, k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    att = profile["attendance_pct"]
    name = profile["name"]

    if att >= 75.0:
        status_str = f"Student {name} has {att}% attendance (>= 75.0%), meeting the standard requirement."
        is_detained = False
    elif att >= 65.0:
        status_str = f"Student {name} has {att}% attendance (65.0-74.9%), eligible for condonation on medical grounds."
        is_detained = False
    else:
        status_str = f"Student {name} has {att}% attendance (< 65.0%), resulting in strict detention."
        is_detained = True

    policy_text = top_rag["text"] if top_rag else "Policy not available."

    return AgentResponse(
        status="success",
        data={
            "student_name": name,
            "attendance_pct": att,
            "is_detained": is_detained,
            "policy_text": policy_text,
            "profile": profile
        },
        message=f"{status_str} Policy detail: {policy_text[:120]}...",
        citation=citation
    )


def get_timetable(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "branch": profile["branch"],
            "today": ["09:00 AM Data Structures", "11:00 AM Operating Systems", "02:00 PM AI Lab"]
        },
        message=f"Timetable for {profile['name']} ({profile['branch']} Year {profile['year']}) retrieved.",
        citation=None
    )


def get_exam_schedule(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "examination regulations passing marks grading scale CIE SEE")
    rag_results = retrieve(query, k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "exams": [
                {"subject": "Operating Systems", "date": "2026-08-20", "time": "10:00 AM"},
                {"subject": "Data Structures", "date": "2026-08-22", "time": "10:00 AM"}
            ],
            "rules": top_rag["text"] if top_rag else ""
        },
        message=f"Exam schedule for {profile['name']}. Passing rule: Minimum 40% in SEE & 40% overall aggregate.",
        citation=citation
    )


def general_synthesis(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id)
    if not profile:
        profile = create_session(session_id)

    query = params.get("query", "academic regulations attendance passing requirements roadmap guidance")
    rag_results = retrieve(query, k=2, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    context_str = "\n".join([r.get("text", "") for r in rag_results])
    summary = (
        f"Academic Overview for {profile['name']} ({profile['branch']} Year {profile['year']}): "
        f"Current attendance is {profile['attendance_pct']}%. "
        f"Key academic guidance: {context_str[:250]}..."
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "rag_documents": rag_results,
            "synthesis": summary
        },
        message=summary,
        citation=citation
    )


ACTIONS = {
    "get_attendance": get_attendance,
    "get_timetable": get_timetable,
    "get_exam_schedule": get_exam_schedule,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown academic action: {action}")
    return ACTIONS[action](params)
