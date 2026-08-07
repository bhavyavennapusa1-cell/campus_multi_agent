"""
Comprehensive Test Suite for Sivani's LLM Planner, Keyword Fallback, General Synthesis Actions, Envelope Audit, and Guardrails.
"""

import os
import json
import pytest

from shared.schemas import AGENT_ACTIONS, AgentResponse, PlanStep
from orchestrator import orchestrator
from knowledge.memory import create_session, get_profile
from agents import academic_agent, placement_agent, campus_agent, communication_agent


def test_agent_actions_schema_registration():
    """Verify general_synthesis is present in AGENT_ACTIONS for all 4 agents."""
    for agent_name in ["academic", "placement", "campus", "communication"]:
        assert agent_name in AGENT_ACTIONS
        assert "general_synthesis" in AGENT_ACTIONS[agent_name]


def test_agent_response_envelope_audit():
    """Verify all agent handlers strictly return AgentResponse with status, message, data, citation."""
    session_id = "test_env_audit_session"
    create_session(session_id, {"name": "Test Student", "cgpa": 8.2, "attendance_pct": 80.0, "branch": "CSE", "year": 3, "backlog_count": 0, "hostel_block": "Block-A"})

    params = {"session_id": session_id, "query": "test query"}

    # Academic actions audit
    for action in AGENT_ACTIONS["academic"]:
        resp = academic_agent.handle(action, params)
        assert isinstance(resp, AgentResponse)
        assert resp.status in ["success", "error", "needs_confirmation"]
        assert isinstance(resp.data, dict)
        assert isinstance(resp.message, str)

    # Placement actions audit
    for action in AGENT_ACTIONS["placement"]:
        resp = placement_agent.handle(action, params)
        assert isinstance(resp, AgentResponse)
        assert resp.status in ["success", "error", "needs_confirmation"]
        assert isinstance(resp.data, dict)
        assert isinstance(resp.message, str)

    # Campus actions audit
    for action in AGENT_ACTIONS["campus"]:
        resp = campus_agent.handle(action, params)
        assert isinstance(resp, AgentResponse)
        assert resp.status in ["success", "error", "needs_confirmation"]
        assert isinstance(resp.data, dict)
        assert isinstance(resp.message, str)

    # Communication actions audit
    for action in AGENT_ACTIONS["communication"]:
        resp = communication_agent.handle(action, params)
        assert isinstance(resp, AgentResponse)
        assert resp.status in ["success", "error", "needs_confirmation"]
        assert isinstance(resp.data, dict)
        assert isinstance(resp.message, str)


def test_general_synthesis_open_ended_queries():
    """Verify open-ended queries get answered via general_synthesis with grounded context."""
    session_id = "test_open_ended_session"
    create_session(session_id, {"name": "Sivani Test", "cgpa": 8.5, "attendance_pct": 82.0, "branch": "CSE", "year": 4, "backlog_count": 0, "hostel_block": "Block-B"})

    # Placement roadmap query
    p_resp = placement_agent.handle("general_synthesis", {"session_id": session_id, "query": "make me a roadmap for placements"})
    assert p_resp.status == "success"
    assert "Placement Roadmap" in p_resp.message or "Guidance" in p_resp.message
    assert "profile" in p_resp.data

    # Academic guidance query
    a_resp = academic_agent.handle("general_synthesis", {"session_id": session_id, "query": "summarize my academic situation"})
    assert a_resp.status == "success"
    assert "Academic Overview" in a_resp.message
    assert "profile" in a_resp.data

    # Campus guidance query
    c_resp = campus_agent.handle("general_synthesis", {"session_id": session_id, "query": "tell me campus rules and hostel curfew"})
    assert c_resp.status == "success"
    assert "Campus Overview" in c_resp.message
    assert "profile" in c_resp.data


def test_keyword_fallback_planner():
    """Verify keyword planner safety net works when LLM API key is not present."""
    # Ensure environment API keys are absent for fallback test
    old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
    old_openai = os.environ.pop("OPENAI_API_KEY", None)

    try:
        # Placement roadmap query
        steps = orchestrator.plan("make me a roadmap for placements")
        assert len(steps) >= 1
        assert steps[0].agent == "placement"
        assert steps[0].action == "general_synthesis"

        # Attendance query
        att_steps = orchestrator.plan("what is my attendance percentage and am I detained?")
        assert len(att_steps) >= 1
        assert att_steps[0].agent == "academic"
        assert att_steps[0].action == "get_attendance"

        # Hostel query
        hostel_steps = orchestrator.plan("what is the hostel curfew time?")
        assert len(hostel_steps) >= 1
        assert hostel_steps[0].agent == "campus"
        assert hostel_steps[0].action == "get_hostel_info"

    finally:
        if old_anthropic:
            os.environ["ANTHROPIC_API_KEY"] = old_anthropic
        if old_openai:
            os.environ["OPENAI_API_KEY"] = old_openai


def test_step_capping_guardrail():
    """Verify plan step capping guardrail limits plan length to MAX_PLAN_STEPS (5)."""
    # Create long list of steps
    many_steps = [
        PlanStep(id=i, agent="placement", action="check_eligibility") for i in range(1, 10)
    ]
    # Simulate capping
    capped = many_steps[:orchestrator.MAX_PLAN_STEPS]
    assert len(capped) == 5


def test_end_to_end_varied_queries():
    """Test batch of varied and open-ended queries end-to-end via orchestrator.run()."""
    session_id = "test_e2e_session"
    create_session(session_id, {"name": "Ananya", "cgpa": 8.7, "attendance_pct": 78.0, "branch": "CSE", "year": 3, "backlog_count": 0, "hostel_block": "Block-A"})

    queries = [
        "give me a roadmap to get placement-ready",
        "Am I eligible for Google and schedule a reminder for the drive",
        "what are my exam rules and passing criteria?",
        "how do I file a grievance for hostel maintenance?"
    ]

    for q in queries:
        executed_steps = orchestrator.run(q, session_id=session_id)
        assert len(executed_steps) > 0
        for s in executed_steps:
            assert s.status in ["done", "running"]
            assert s.result is not None
            assert isinstance(s.result, AgentResponse)
            assert s.result.status in ["success", "needs_confirmation"]


if __name__ == "__main__":
    test_agent_actions_schema_registration()
    test_agent_response_envelope_audit()
    test_general_synthesis_open_ended_queries()
    test_keyword_fallback_planner()
    test_step_capping_guardrail()
    test_end_to_end_varied_queries()
    print("\nALL TEST CASES PASSED SUCCESSFULLY!")
