import os
import pytest
from agents.adapters.github_adapter import GitHubAdapter
from agents.adapters.jobs_adapter import JobsAdapter
from agents.adapters.todoist_adapter import TodoistAdapter
from agents.adapters.google_calendar_adapter import GoogleCalendarAdapter
from agents.adapters.google_maps_adapter import GoogleMapsAdapter
from agents.adapters.gmail_adapter import GmailAdapter


@pytest.mark.asyncio
async def test_github_adapter_fallback():
    # Force API key unset
    adapter = GitHubAdapter(token=None)
    profile = await adapter.get_github_profile("nonexistent_test_user")
    assert profile["source"] == "mock"
    assert "top_skills" in profile
    assert profile["username"] == "nonexistent_test_user"


@pytest.mark.asyncio
async def test_jobs_adapter_fallback():
    adapter = JobsAdapter(api_key=None)
    res = await adapter.find_opportunities(query="AI Engineer")
    assert res["source"] == "mock"
    assert len(res["opportunities"]) > 0


@pytest.mark.asyncio
async def test_todoist_adapter_fallback():
    adapter = TodoistAdapter(api_key=None)
    plan_res = await adapter.create_study_plan(subject="Database Systems", days_left=10, exam_date="2026-08-17")
    assert plan_res["source"] == "mock"
    assert len(plan_res["materialized_tasks"]) == 3


@pytest.mark.asyncio
async def test_google_calendar_adapter_fallback():
    adapter = GoogleCalendarAdapter(api_key=None)
    event_res = await adapter.add_event_to_calendar(summary="DBMS Exam Session", start_time="2026-08-10T10:00:00Z", end_time="2026-08-10T12:00:00Z")
    assert event_res["source"] == "mock"
    assert event_res["status"] == "confirmed"


@pytest.mark.asyncio
async def test_google_maps_adapter_fallback():
    adapter = GoogleMapsAdapter(api_key=None)
    dirs_res = await adapter.get_directions(origin="Main Gate", destination="City Hospital")
    assert dirs_res["source"] == "mock"
    assert len(dirs_res["steps"]) >= 2


@pytest.mark.asyncio
async def test_gmail_adapter_fallback():
    adapter = GmailAdapter(token=None)
    send_res = await adapter.send_email(recipient_email="dean@campus.edu", subject="Permission Request", body="Test email content")
    assert send_res["source"] == "mock"
    assert send_res["status"] == "sent"
