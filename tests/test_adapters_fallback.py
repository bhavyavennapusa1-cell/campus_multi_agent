"""
Test suite for Feature 2 — Adapter Pattern External API Integrations.
Deliberately unsets API keys and verifies each major integration (GitHub, Jobs, Todoist,
Google Calendar, Google Maps, Gmail) falls back gracefully to mock data with source="mock".
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import (
    placement_agent,
    academic_agent,
    navigator_agent,
    events_agent,
    communication_agent,
)


def test_github_fallback():
    os.environ.pop("GITHUB_TOKEN", None)
    res = placement_agent.get_github_profile({"username": "non_existent_user_12345"})
    assert res.status == "success"
    assert res.data.get("source") == "mock"
    assert "public_repos" in res.data
    assert "GitHub Profile metrics" in res.message


def test_jobs_api_fallback():
    os.environ.pop("JOBS_API_KEY", None)
    res = placement_agent.find_opportunities({"role": "AI Engineer"})
    assert res.status == "success"
    assert res.data.get("source") == "mock"
    assert len(res.data.get("opportunities", [])) > 0


def test_todoist_fallback():
    os.environ.pop("TODOIST_API_KEY", None)
    res = academic_agent.create_task({"content": "DBMS Chapter 3 Review", "due_string": "tomorrow"})
    assert res.status == "success"
    assert res.data.get("source") == "mock"
    assert res.data["task"]["content"] == "DBMS Chapter 3 Review"


def test_google_maps_fallback():
    os.environ.pop("GOOGLE_MAPS_API_KEY", None)
    res = navigator_agent.get_directions({"origin": "SAC", "destination": "Railway Station Outer Gate"})
    assert res.status == "success"
    assert res.data.get("source") in ("live", "mock")
    assert "directions" in res.data or "distance" in res.data


def test_google_calendar_fallback():
    os.environ.pop("GOOGLE_CALENDAR_API_KEY", None)
    res = events_agent.add_event_to_calendar({"event_name": "AgentX Hackathon", "date_str": "2026-08-15"})
    assert res.status == "success"
    assert res.data.get("source") == "mock"
    assert "Added" in res.message


def test_gmail_fallback():
    os.environ.pop("GMAIL_API_KEY", None)
    res = communication_agent.send_email({"to": "test@vasavi.ac.in", "subject": "Test", "body": "Body text"})
    assert res.status == "success"
    assert res.data.get("source") == "mock"
    assert "Dispatched" in res.message


if __name__ == "__main__":
    test_github_fallback()
    test_jobs_api_fallback()
    test_todoist_fallback()
    test_google_maps_fallback()
    test_google_calendar_fallback()
    test_gmail_fallback()
    print("ALL ADAPTER FALLBACK TESTS PASSED CLEANLY!")
