"""
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
    )


def file_grievance(params: dict) -> AgentResponse:
    grievance_text = params.get("text", "")
    # TODO Person B: actually append to a grievances.json or SQLite table
    return AgentResponse(
        status="needs_confirmation",
        data={"grievance": grievance_text},
        message="Grievance drafted, awaiting confirmation to submit",
    )


ACTIONS = {
    "get_events": get_events,
    "get_hostel_info": get_hostel_info,
    "file_grievance": file_grievance,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown campus action: {action}")
    return ACTIONS[action](params)
