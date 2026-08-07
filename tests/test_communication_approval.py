"""
Test suite for Feature 3 — Communication Agent Expansion & Approval Flow.
Tests ContactsRepo lookup, local SQLite chat_groups database creation,
email drafting with requires_user_approval: True, and POST /communication/approve-action flow.
"""

import sys
import sqlite3
from pathlib import Path
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app
from agents import communication_agent

client = TestClient(app)


def test_contacts_repo_lookup():
    response = client.get("/communication/contacts?query_type=faculty")
    assert response.status_code == 200
    contacts = response.json()["data"]["contacts"]
    assert len(contacts) > 0
    assert any(c["role"] == "faculty" for c in contacts)


def test_chat_group_creation_in_sqlite():
    res = client.post(
        "/communication/groups",
        json={"group_name": "AI Study Squad", "member_ids": ["c_004", "c_005"], "group_type": "temporary", "duration_hours": 12}
    )
    assert res.status_code == 200
    group_id = res.json()["data"]["group_id"]
    assert group_id.startswith("grp_")

    # Direct SQLite verification
    conn = sqlite3.connect(communication_agent.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_name, group_type FROM chat_groups WHERE group_id = ?", (group_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "AI Study Squad"
    assert row[1] == "temporary"


def test_draft_email_and_approve_action_flow():
    # 1. Draft email -> requires_user_approval: True
    draft_res = client.post(
        "/communication/draft-email",
        json={
            "recipient_email": "hod_cse@vasavi.ac.in",
            "subject": "Attendance Condonation Request",
            "core_message": "Requesting condonation for 2 days medical absence."
        }
    )
    assert draft_res.status_code == 200
    data = draft_res.json()["data"]
    assert data["requires_user_approval"] is True
    action_id = data["action_id"]

    # Verify action registered in pending dictionary
    assert action_id in communication_agent.PENDING_ACTIONS

    # 2. Approve action via /communication/approve-action
    approve_res = client.post(
        "/communication/approve-action",
        json={"action_id": action_id, "status": "approved"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "done"
    assert "APPROVED" in approve_res.json()["message"]

    # Action removed after execution
    assert action_id not in communication_agent.PENDING_ACTIONS


def test_reject_action_flow():
    draft_res = client.post(
        "/communication/draft-email",
        json={"recipient_email": "test@vasavi.ac.in", "subject": "Draft", "core_message": "Message"}
    )
    action_id = draft_res.json()["data"]["action_id"]

    reject_res = client.post(
        "/communication/approve-action",
        json={"action_id": action_id, "status": "rejected"}
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert action_id not in communication_agent.PENDING_ACTIONS


if __name__ == "__main__":
    test_contacts_repo_lookup()
    test_chat_group_creation_in_sqlite()
    test_draft_email_and_approve_action_flow()
    test_reject_action_flow()
    print("ALL COMMUNICATION & APPROVAL TESTS PASSED CLEANLY!")
