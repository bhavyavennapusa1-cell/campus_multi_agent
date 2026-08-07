"""
Person B owns this file too.
This one has real logic already (eligibility checking) - use it as the
template for filling in campus_agent.py and communication_agent.py.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import AgentResponse

BASE = Path(__file__).resolve().parent.parent / "data"

with open(BASE / "students.json") as f:
    STUDENTS = {s["id"]: s for s in json.load(f)["students"]}

with open(BASE / "internships.json") as f:
    INTERNSHIPS = {i["company"].lower(): i for i in json.load(f)["internships"]}


def check_eligibility(params: dict) -> AgentResponse:
    student_id = params.get("student_id", "S001")
    company = params.get("company", "").lower()

    student = STUDENTS.get(student_id)
    posting = INTERNSHIPS.get(company)

    if not student:
        return AgentResponse(status="error", message=f"No student found with id {student_id}")
    if not posting:
        return AgentResponse(status="error", message=f"No internship posting found for {company}")

    eligible = (
        student["cgpa"] >= posting["min_cgpa"]
        and student["attendance_percent"] >= posting["min_attendance"]
        and student["branch"] in posting["eligible_branches"]
        and student["year"] in posting["eligible_years"]
    )

    return AgentResponse(
        status="success",
        data={"eligible": eligible, "company": company, "reasons": posting},
        message=f"{'Eligible' if eligible else 'Not eligible'} for {company}",
    )


def get_internships(params: dict) -> AgentResponse:
    return AgentResponse(
        status="success",
        data={"internships": list(INTERNSHIPS.values())},
        message=f"Found {len(INTERNSHIPS)} open internships",
    )


ACTIONS = {
    "check_eligibility": check_eligibility,
    "get_internships": get_internships,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown placement action: {action}")
    return ACTIONS[action](params)
