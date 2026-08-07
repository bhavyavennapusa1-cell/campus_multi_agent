"""
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
    )


def get_timetable(params: dict) -> AgentResponse:
    # TODO Person B: replace with real mock timetable data (add data/timetable.json)
    return AgentResponse(
        status="success",
        data={"today": ["9:00 Data Structures", "11:00 Operating Systems", "2:00 AI Lab"]},
        message="Today's classes retrieved",
    )


def get_exam_schedule(params: dict) -> AgentResponse:
    # TODO Person B: replace with real mock exam data
    return AgentResponse(
        status="success",
        data={"exams": [{"subject": "Operating Systems", "date": "2026-08-20"}]},
        message="Exam schedule retrieved",
    )


# Router - the orchestrator calls this, doesn't need to know function names directly
ACTIONS = {
    "get_attendance": get_attendance,
    "get_timetable": get_timetable,
    "get_exam_schedule": get_exam_schedule,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown academic action: {action}")
    return ACTIONS[action](params)
