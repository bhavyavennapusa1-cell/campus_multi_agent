import pytest
from fastapi.testclient import TestClient
from server import app, PENDING_APPROVAL_ACTIONS


def test_get_contacts_endpoint():
    client = TestClient(app)
    response = client.get("/communication/contacts?student_id=STU001&query_type=faculty")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["contacts"]) > 0


def test_create_chat_group_endpoint():
    client = TestClient(app)
    response = client.get("/communication/groups")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_human_in_the_loop_approval_flow():
    client = TestClient(app)

    # Step 1: Draft official email (produces draft requiring approval)
    draft_resp = client.post(
        "/communication/draft-email",
        json={
            "student_id": "STU001",
            "recipient_email": "dean@campus.edu",
            "subject": "Makeup Exam Condonation",
            "core_message": "I request attendance waiver due to medical leave."
        }
    )
    assert draft_resp.status_code == 200
    draft_data = draft_resp.json()
    assert draft_data["status"] == "success"

    action_id = draft_data["data"]["action_id"]
    assert draft_data["data"]["requires_user_approval"] is True
    assert action_id in PENDING_APPROVAL_ACTIONS

    # Step 2: Approve action via /communication/approve-action
    approve_resp = client.post(
        "/communication/approve-action",
        json={"action_id": action_id, "status": "approved"}
    )
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["status"] == "approved"
    assert approve_data["execution"]["status"] == "sent"
    assert action_id not in PENDING_APPROVAL_ACTIONS


def test_human_in_the_loop_rejection_flow():
    client = TestClient(app)

    # Draft email
    draft_resp = client.post(
        "/communication/draft-email",
        json={
            "student_id": "STU001",
            "recipient_email": "hod@campus.edu",
            "subject": "Project Extension",
            "core_message": "Requesting 2-day extension."
        }
    )
    action_id = draft_resp.json()["data"]["action_id"]

    # Reject action
    reject_resp = client.post(
        "/communication/approve-action",
        json={"action_id": action_id, "status": "rejected"}
    )
    assert reject_resp.status_code == 200
    reject_data = reject_resp.json()
    assert reject_data["status"] == "rejected"
    assert action_id not in PENDING_APPROVAL_ACTIONS
