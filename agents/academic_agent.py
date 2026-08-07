"""
<<<<<<< HEAD
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
=======
Person B owns this file.
Each function takes params (a dict) and returns an AgentResponse.
Load data/students.json once at the top so you're not re-reading the file
on every call.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import AgentResponse

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "students.json"

with open(DATA_PATH) as f:
    STUDENTS = {s["id"]: s for s in json.load(f)["students"]}


def get_attendance(params: dict) -> AgentResponse:
    student_id = params.get("student_id", "S001")  # default demo student
    student = STUDENTS.get(student_id)

    if not student:
        return AgentResponse(status="error", message=f"No student found with id {student_id}")

    return AgentResponse(
        status="success",
        data={"attendance_percent": student["attendance_percent"]},
        message=f"Attendance is {student['attendance_percent']}%",
>>>>>>> frontend
    )


def get_timetable(params: dict) -> AgentResponse:
<<<<<<< HEAD
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
=======
    # TODO Person B: replace with real mock timetable data (add data/timetable.json)
    return AgentResponse(
        status="success",
        data={"today": ["9:00 Data Structures", "11:00 Operating Systems", "2:00 AI Lab"]},
        message="Today's classes retrieved",
>>>>>>> frontend
    )


def get_exam_schedule(params: dict) -> AgentResponse:
<<<<<<< HEAD
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


=======
    # TODO Person B: replace with real mock exam data
    return AgentResponse(
        status="success",
        data={"exams": [{"subject": "Operating Systems", "date": "2026-08-20"}]},
        message="Exam schedule retrieved",
    )


# Router - the orchestrator calls this, doesn't need to know function names directly
>>>>>>> frontend
ACTIONS = {
    "get_attendance": get_attendance,
    "get_timetable": get_timetable,
    "get_exam_schedule": get_exam_schedule,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown academic action: {action}")
    return ACTIONS[action](params)
