"""
Test suite for BUG 1 (Profile threading/persistence), BUG 2 (Response Synthesis),
and MISSING CAPABILITY (LLM Multi-Domain Intent Routing & Clarification).
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from main import app
from orchestrator.orchestrator import run, synthesize_response

client = TestClient(app)


def test_custom_profile_personalization():
    print("\n--- Test 1: Profile Threading & Personalization (BUG 1) ---")
    custom_profile = {
        "name": "Siddharth Verma",
        "branch_year": "ECE - 4th Year",
        "attendance": "92%",
        "hostel_block": "Block C"
    }
    
    response = client.post("/chat", json={
        "message": "What is my current attendance requirement and timetable?",
        "session_id": "test_session_siddharth",
        "profile": custom_profile
    })
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    reply = data.get("reply", "")
    
    print("Response Reply:\n", reply)
    assert "Siddharth Verma" in reply or "Siddharth" in reply, f"Expected student name in reply, got: {reply}"
    print("✔ Custom profile successfully passed and personalized!")


def test_multi_domain_query():
    print("\n--- Test 2: Multi-Domain Query Spanning Multiple Agents ---")
    custom_profile = {
        "name": "Ananya Rao",
        "branch_year": "CSE - 3rd Year",
        "attendance": "85%",
        "hostel_block": "Block A"
    }
    
    response = client.post("/chat", json={
        "message": "register me for the Google internship and remind me of my exam dates",
        "session_id": "test_session_ananya",
        "profile": custom_profile
    })
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    agents_used = data.get("agents_used", [])
    reply = data.get("reply", "")
    
    print("Agents Used:", agents_used)
    print("Response Reply:\n", reply)
    
    assert len(agents_used) >= 2, f"Expected multi-agent routing (>= 2 agents), got: {agents_used}"
    assert "Ananya" in reply, f"Expected personalized reply for Ananya, got: {reply}"
    print("✔ Multi-domain query successfully dispatched across multiple agents!")


def test_unmapped_clarification_query():
    print("\n--- Test 3: Unmapped Query Clarification ---")
    response = client.post("/chat", json={
        "message": "hi",
        "session_id": "test_session_vague",
        "profile": {"name": "Priya Reddy"}
    })
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    reply = data.get("reply", "")
    
    print("Response Reply:\n", reply)
    assert "clarify" in reply.lower() or "specify" in reply.lower() or "help" in reply.lower(), f"Expected clarification prompt, got: {reply}"
    print("✔ Unmapped query successfully returned clarification request instead of hallucinating!")


if __name__ == "__main__":
    print("==================================================")
    print(" RUNNING BUGS & ROUTING VERIFICATION TEST SUITE ")
    print("==================================================")
    test_custom_profile_personalization()
    test_multi_domain_query()
    test_unmapped_clarification_query()
    print("\n==================================================")
    print(" ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")
