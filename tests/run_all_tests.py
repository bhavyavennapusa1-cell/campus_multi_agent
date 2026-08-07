"""
Master test execution runner for Sivani's backend extensions.
Runs Feature 1, Feature 2, Feature 3, and Orchestrator/Synthesis test suites.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_transcribe import (
    test_transcribe_audio_fixture_contract,
    test_transcribe_empty_file_returns_400,
    test_transcribe_invalid_content_type_returns_400
)
from tests.test_adapters_fallback import (
    test_github_fallback,
    test_jobs_api_fallback,
    test_todoist_fallback,
    test_google_maps_fallback,
    test_google_calendar_fallback,
    test_gmail_fallback
)
from tests.test_communication_approval import (
    test_contacts_repo_lookup,
    test_chat_group_creation_in_sqlite,
    test_draft_email_and_approve_action_flow,
    test_reject_action_flow
)
from tests.test_llm_planner_and_synthesis import (
    test_batch_varied_open_ended_queries,
    test_dbms_10_day_demo_flow_tracing
)

def run_all():
    print("==================================================")
    print(" RUNNING ALL SIVANI BACKEND TEST SUITES ")
    print("==================================================")

    print("\n--- 1. Testing Voice Transcription Endpoint ---")
    test_transcribe_audio_fixture_contract()
    test_transcribe_empty_file_returns_400()
    test_transcribe_invalid_content_type_returns_400()
    print("✔ Feature 1 Voice Transcription tests passed!")

    print("\n--- 2. Testing Integration Fallbacks (Unset API Keys) ---")
    test_github_fallback()
    test_jobs_api_fallback()
    test_todoist_fallback()
    test_google_maps_fallback()
    test_google_calendar_fallback()
    test_gmail_fallback()
    print("✔ Feature 2 Integration Fallback tests passed!")

    print("\n--- 3. Testing Communication Agent & Approval Flow ---")
    test_contacts_repo_lookup()
    test_chat_group_creation_in_sqlite()
    test_draft_email_and_approve_action_flow()
    test_reject_action_flow()
    print("✔ Feature 3 Communication & Approval tests passed!")

    print("\n--- 4. Testing LLM Planner & General Synthesis ---")
    test_batch_varied_open_ended_queries()
    test_dbms_10_day_demo_flow_tracing()
    print("✔ LLM Planner & General Synthesis tests passed!")

    print("\n==================================================")
    print(" ALL BACKEND TEST SUITES COMPLETED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_all()
