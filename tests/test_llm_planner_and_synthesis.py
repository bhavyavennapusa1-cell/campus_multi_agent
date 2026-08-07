"""
Test suite for LLM Planner, Open-Ended Queries, and General Synthesis Actions.
Verifies batch of varied phrasing queries, step cap guardrail (max 5), RAG context retrieval,
and uniform AgentResponse envelope outputs.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator import orchestrator


def test_batch_varied_open_ended_queries():
    test_queries = [
        "make me a roadmap for placements and summarize my situation",
        "I have a DBMS exam in 10 days, prepare a study plan for me",
        "how do I navigate to the central library from my hostel",
        "what technical hackathons are happening on campus this month",
        "give me an overview of academic attendance requirements and condonation rules",
    ]

    for q in test_queries:
        steps = orchestrator.plan(q)
        assert len(steps) > 0, f"Planner returned 0 steps for query: '{q}'"
        assert len(steps) <= 5, f"Planner exceeded step cap (max 5) for query: '{q}'"

        # Execute dispatch
        executed_steps = orchestrator.dispatch(steps, session_id="test_synthesis_session")
        for s in executed_steps:
            assert s.status in ("done", "running"), f"Step {s.id} failed: {s.result}"
            res = s.result
            assert res is not None
            assert res.status in ("success", "needs_confirmation")
            assert isinstance(res.message, str) and len(res.message) > 0
            assert "data" in res.to_dict()

        print(f"PASS: Query '{q}' -> Planned {len(steps)} steps via {', '.join([s.agent for s in steps])}")


def test_dbms_10_day_demo_flow_tracing():
    steps = orchestrator.run("I have a DBMS exam in 10 days", session_id="demo_session_dbms")
    first_result = steps[0].result
    assert first_result.status == "success"
    assert "DBMS" in first_result.data.get("subject", "")
    assert len(first_result.data.get("created_tasks", [])) > 0
    assert len(first_result.data.get("calendar_events", [])) > 0
    assert "a2a_calls" in first_result.data.get("trace_log", "")


if __name__ == "__main__":
    test_batch_varied_open_ended_queries()
    test_dbms_10_day_demo_flow_tracing()
    print("ALL OPEN-ENDED & SYNTHESIS TESTS PASSED CLEANLY!")
