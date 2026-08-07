import asyncio
import json
import uuid
import pytest

from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.academic_agent.agent import AcademicAgent
from agents.placement_agent.agent import PlacementAgent
from agents.campus_agent.agent import CampusAgent
from agents.communication_agent.agent import CommunicationAgent


def setup_agent_system() -> AgentRegistry:
    """Helper to instantiate and register all 4 backend agents."""
    registry = AgentRegistry()

    acad_agent = AcademicAgent(registry=registry)
    place_agent = PlacementAgent(registry=registry)
    campus_agent = CampusAgent(registry=registry)
    comms_agent = CommunicationAgent(registry=registry)

    registry.register("academic_agent", acad_agent)
    registry.register("academic", acad_agent)

    registry.register("placement_agent", place_agent)
    registry.register("placement", place_agent)

    registry.register("campus_agent", campus_agent)
    registry.register("campus", campus_agent)

    registry.register("communication_agent", comms_agent)
    registry.register("comms", comms_agent)

    return registry


@pytest.mark.asyncio
async def test_workflow_1_placement_eligibility_and_event_registration():
    """
    DEMO WORKFLOW 1:
    Student checks Google internship eligibility -> Placement calls Academic (attendance)
    -> registers for placement workshop via Campus Events -> Events checks timetable clash via Academic
    -> Communication schedules calendar entry + 60-min reminder -> single consolidated envelope.
    """
    registry = setup_agent_system()
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    student_id = "STU001"  # John Doe: CGPA 8.8, Attendance 82.5%

    print("\n" + "="*80)
    print(f"RUNNING DEMO WORKFLOW 1: Placement Eligibility & Workshop Registration [Trace: {trace_id}]")
    print("="*80)

    # Step 1: Check Google internship eligibility via Placement Agent
    placement_client = registry.get("placement_agent", caller_name="orchestrator")
    elig_req = TaskRequest(
        trace_id=trace_id,
        task="check_eligibility",
        params={"company_id": "COMP001", "cgpa": 8.8, "branch": "Computer Science", "backlogs": 0},
        student_id=student_id
    )
    elig_resp = await placement_client.handle(elig_req)

    assert elig_resp.status == "success"
    assert elig_resp.data["eligible"] is True
    assert len(elig_resp.a2a_calls) >= 1
    assert elig_resp.a2a_calls[0]["target"] == "academic_agent"
    print(f"Step 1 Verdict: {elig_resp.message}")

    # Step 2: Register for Google Workshop via Campus Agent (Events sub-module)
    campus_client = registry.get("campus_agent", caller_name="orchestrator")
    event_req = TaskRequest(
        trace_id=trace_id,
        task="register_for_event",
        params={"event_id": "EVT001"},
        student_id=student_id
    )
    event_resp = await campus_client.handle(event_req)

    assert event_resp.status == "success"
    assert event_resp.data["registration"]["status"] == "confirmed"
    # A2A calls include Academic get_timetable and Communication schedule_appointment + schedule_reminder
    assert len(event_resp.a2a_calls) >= 3

    print(f"Step 2 Verdict: {event_resp.message}")
    print(f"Trace of A2A Calls in Response Envelope:")
    print(json.dumps(event_resp.a2a_calls, indent=2))
    print("="*80)


@pytest.mark.asyncio
async def test_workflow_2_low_attendance_email_draft():
    """
    DEMO WORKFLOW 2:
    Student STU002 (Attendance 68% < 75%) checks attendance eligibility -> Academic detects shortfall
    -> Academic calls Communication to draft makeup exam permission email
    -> Returns both eligibility status and draft for review.
    """
    registry = setup_agent_system()
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    student_id = "STU002"  # Jane Smith: Attendance 68.0%

    print("\n" + "="*80)
    print(f"RUNNING DEMO WORKFLOW 2: Low Attendance Shortfall & Email Draft [Trace: {trace_id}]")
    print("="*80)

    academic_client = registry.get("academic_agent", caller_name="orchestrator")
    acad_req = TaskRequest(
        trace_id=trace_id,
        task="check_attendance_eligibility",
        params={"student_id": student_id},
        student_id=student_id
    )
    resp = await academic_client.handle(acad_req)

    assert resp.status == "partial"
    assert resp.data["eligible"] is False
    assert resp.data["attendance_pct"] == 68.0
    assert "email_draft" in resp.data
    assert len(resp.a2a_calls) == 1
    assert resp.a2a_calls[0]["target"] == "communication_agent"
    assert resp.a2a_calls[0]["tool"] == "draft_email"

    print(f"Verdict: {resp.message}")
    print(f"Generated Email Draft:")
    print(json.dumps(resp.data["email_draft"], indent=2))
    print("="*80)


@pytest.mark.asyncio
async def test_workflow_3_event_registration_timetable_clash():
    """
    DEMO WORKFLOW 3:
    Student STU003 tries to register for Hackathon EVT002 (2026-08-10 10:00-16:00).
    Campus Events calls Academic get_timetable -> detects clash with STU003's Midterm Exam.
    Returns status: 'needs_clarification' with conflict details, NOT silent success!
    """
    registry = setup_agent_system()
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    student_id = "STU003"  # Alex Johnson: Has Midterm Exam on 2026-08-10 at 10:00

    print("\n" + "="*80)
    print(f"RUNNING DEMO WORKFLOW 3: Event Registration Timetable Clash [Trace: {trace_id}]")
    print("="*80)

    campus_client = registry.get("campus_agent", caller_name="orchestrator")
    clash_req = TaskRequest(
        trace_id=trace_id,
        task="register_for_event",
        params={"event_id": "EVT002"},  # AI/ML Hackathon on 2026-08-10
        student_id=student_id
    )
    resp = await campus_client.handle(clash_req)

    assert resp.status == "needs_clarification"
    assert resp.data["clash_detected"] is True
    assert len(resp.data["conflict_details"]) > 0
    assert resp.data["conflict_details"][0]["conflict_type"] == "EXAM_CLASH"
    assert len(resp.a2a_calls) >= 1
    assert resp.a2a_calls[0]["target"] == "academic_agent"

    print(f"Verdict Status: {resp.status}")
    print(f"Conflict Message: {resp.message}")
    print(f"Conflict Details Data:")
    print(json.dumps(resp.data["conflict_details"], indent=2))
    print("="*80)


@pytest.mark.asyncio
async def test_invalid_student_id_validation():
    """Validates student_id existence check returning clean error envelope."""
    registry = setup_agent_system()
    acad_client = registry.get("academic_agent", caller_name="orchestrator")
    req = TaskRequest(
        trace_id="test-invalid-student",
        task="check_attendance_eligibility",
        params={},
        student_id="STU999_NONEXISTENT"
    )
    resp = await acad_client.handle(req)
    assert resp.status == "error"
    assert "not found" in resp.data["error"].lower()


@pytest.mark.asyncio
async def test_a2a_depth_capping_limit():
    """Validates that A2A calls depth capped at 3 return a clean depth error envelope."""
    registry = setup_agent_system()
    place_client = registry.get("placement_agent", caller_name="orchestrator")
    
    # Simulate an incoming call that is already at depth 3
    req = TaskRequest(
        trace_id="test-depth-limit",
        task="check_eligibility",
        params={"company_id": "COMP001"},
        student_id="STU001",
        context={"call_depth": 3}
    )
    resp = await place_client.handle(req)
    assert resp.status in ["error", "partial"]
    assert resp.data.get("depth_exceeded") is True


if __name__ == "__main__":
    asyncio.run(test_workflow_1_placement_eligibility_and_event_registration())
    asyncio.run(test_workflow_2_low_attendance_email_draft())
    asyncio.run(test_workflow_3_event_registration_timetable_clash())
    asyncio.run(test_invalid_student_id_validation())
    asyncio.run(test_a2a_depth_capping_limit())
    print("\nAll 3 demo workflows and verification tests executed successfully!")
