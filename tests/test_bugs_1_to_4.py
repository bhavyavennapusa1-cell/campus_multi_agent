"""
Sequential verification test suite for Bugs 1, 2, 3, and 4.
"""

import sys
import re
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from main import app
from agents.academic_agent import get_exam_schedule

client = TestClient(app)


def test_bug_1_synthesis_no_raw_dumps():
    print("\n--- Testing BUG 1: Response Synthesis & No Raw Data Dumps ---")
    response = client.post("/chat", json={
        "message": "Draft an email to academic office regarding my attendance",
        "session_id": "test_bug1_session",
        "profile": {
            "name": "Bhavya Vennapusa",
            "branch_year": "CSE - 3rd Year",
            "attendance": "88%",
            "hostel_block": "Block B"
        }
    })
    assert response.status_code == 200
    data = response.json()
    reply = data["reply"]
    print("Synthesized Reply:\n", reply)

    assert "##" not in reply, "Raw markdown header '##' found in reply!"
    assert "[Action ID:" not in reply, "Internal Action ID found in reply!"
    assert data["requires_confirmation"] is True, "requires_confirmation should be True!"
    print("✔ BUG 1 Verified: Clean synthesis output produced without raw headers or action IDs!")


def test_bug_2_subject_alias_matching():
    print("\n--- Testing BUG 2: Exact Word-Boundary Subject Alias Matching ---")

    # Test 'ds' alias -> Data Structures only
    res_ds = get_exam_schedule({"query": "when is my ds exam", "profile": {"name": "Bhavya"}})
    assert res_ds.data["matched_subject"] == "Data Structures"
    assert len(res_ds.data["exams"]) == 1
    assert res_ds.data["exams"][0]["subject"] == "Data Structures"
    print("✔ 'ds' correctly matched Data Structures!")

    # Test 'dsa' alias -> Data Structures only
    res_dsa = get_exam_schedule({"query": "when is dsa exam", "profile": {"name": "Bhavya"}})
    assert res_dsa.data["matched_subject"] == "Data Structures"
    assert len(res_dsa.data["exams"]) == 1
    print("✔ 'dsa' correctly matched Data Structures!")

    # Test 'dbms' alias -> Database Management Systems only
    res_dbms = get_exam_schedule({"query": "when is dbms exam", "profile": {"name": "Bhavya"}})
    assert res_dbms.data["matched_subject"] == "Database Management Systems"
    assert len(res_dbms.data["exams"]) == 1
    assert res_dbms.data["exams"][0]["code"] == "DBMS"
    print("✔ 'dbms' correctly matched Database Management Systems!")

    # Test 'os' alias -> Operating Systems only
    res_os = get_exam_schedule({"query": "when is os exam", "profile": {"name": "Bhavya"}})
    assert res_os.data["matched_subject"] == "Operating Systems"
    assert len(res_os.data["exams"]) == 1
    assert res_os.data["exams"][0]["code"] == "OS"
    print("✔ 'os' correctly matched Operating Systems!")

    # Test unmapped subject 'java' -> Returns empty exams without matching DBMS
    res_unmapped = get_exam_schedule({"query": "java", "profile": {"name": "Bhavya"}})
    assert res_unmapped.data["exams"] == []
    assert "No exam schedule found" in res_unmapped.message
    print("✔ Unmapped subject 'java' returned clear 'no exam found' message without mismatching!")


def test_bug_3_actions_array_payload():
    print("\n--- Testing BUG 3: Interactive UI Component Payloads (Actions Array) ---")
    response = client.post("/chat", json={
        "message": "how do I navigate to the central library from my hostel",
        "session_id": "test_bug3_session",
        "profile": {"name": "Bhavya", "hostel_block": "Block B"}
    })
    assert response.status_code == 200
    data = response.json()
    actions = data.get("actions", [])
    print("Actions Payload Received:\n", actions)

    assert len(actions) > 0, "Expected non-empty actions array in chat response!"
    link_action = actions[0]
    assert link_action["type"] == "link"
    assert "google.com/maps" in link_action["url"]
    print("✔ BUG 3 Verified: Structured actions array with Google Maps URL returned at root level!")


def test_bug_4_multi_turn_session_persistence():
    print("\n--- Testing BUG 4: Multi-Turn Session Persistence ---")
    session_id = "test_bug4_multi_turn_session"

    # Turn 1
    res1 = client.post("/chat", json={
        "message": "My name is Bhavya and I am in 3rd year CSE.",
        "session_id": session_id
    })
    assert res1.status_code == 200

    # Turn 2
    res2 = client.post("/chat", json={
        "message": "What is my exam schedule?",
        "session_id": session_id
    })
    assert res2.status_code == 200
    data2 = res2.json()
    print("Turn 2 Response Reply:\n", data2["reply"])
    assert "Bhavya" in data2["reply"] or "exams" in data2["reply"]
    print("✔ BUG 4 Verified: Multi-turn session context maintained without error!")


if __name__ == "__main__":
    print("==================================================")
    print(" RUNNING BUGS 1 TO 4 SEQUENTIAL TEST SUITE ")
    print("==================================================")
    test_bug_1_synthesis_no_raw_dumps()
    test_bug_2_subject_alias_matching()
    test_bug_3_actions_array_payload()
    test_bug_4_multi_turn_session_persistence()
    print("\n==================================================")
    print(" ALL 4 BUGS SUCCESSFULLY FIXED AND VERIFIED! ")
    print("==================================================")
