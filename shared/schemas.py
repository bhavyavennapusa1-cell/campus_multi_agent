"""
SHARED CONTRACT - everyone reads this file before writing any code.
Do not change these shapes without telling the whole team.
"""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class AgentResponse:
    """
    Every single agent function (in agents/*.py) must return exactly this shape.
    This is what makes it possible for 4 people to build separately and have
    it all plug together at the end without surprises.
    """
    status: Literal["success", "error", "needs_confirmation"]
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""          # one-line human-readable summary, shown in the trace panel
    citation: str | None = None  # source doc filename, only set when RAG was used

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "data": self.data,
            "message": self.message,
            "citation": self.citation,
        }


@dataclass
class PlanStep:
    """
    One step inside the orchestrator's plan. The orchestrator (Person A) generates
    a list of these from the user's request. Person B's agents get called with
    step.action and step.params.
    """
    id: int
    agent: str          # must match a key in AGENT_REGISTRY, e.g. "academic", "placement"
    action: str         # must match a function name inside that agent's file
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)
    status: Literal["pending", "running", "done", "failed"] = "pending"
    result: AgentResponse | None = None


# Every agent must expose functions matching these action names.
# Person B: implement all of these (start with the easy ones, mock the rest).
AGENT_ACTIONS = {
    "academic": ["get_timetable", "get_attendance", "get_exam_schedule"],
    "placement": ["check_eligibility", "get_internships"],
    "campus": ["get_hostel_info", "get_events", "file_grievance"],
    "communication": ["draft_email", "schedule_reminder"],
}
