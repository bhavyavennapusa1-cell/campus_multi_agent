import os
import sys

PROJECT_ROOT = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from orchestrator.orchestrator import run, synthesize_response
from knowledge.memory import get_history, get_student_memory, create_session

session_id = "test_google_workflow_001"
profile = {
    "name": "Bhavya Vennapusa",
    "branch_year": "CSE - 3rd Year",
    "cgpa": 8.8,
    "backlog_count": 0,
    "attendance": "88%",
    "hostel_block": "Block B"
}

create_session(session_id, profile)

print("=" * 80)
print("TEST 1: Primary Query Execution")
print("Query: 'Am I eligible for the Google internship? If yes, register me and calendar it.'")
print("=" * 80)

user_msg_1 = "Am I eligible for the Google internship? If yes, register me and calendar it."
steps_1 = run(user_msg_1, session_id=session_id, profile=profile)

print(f"\nTotal Plan Steps Executed: {len(steps_1)}")
for s in steps_1:
    res = s.result
    print(f"\nStep {s.id}: Agent='{s.agent}', Action='{s.action}', Status='{s.status}'")
    print(f"  Params  : {s.params}")
    print(f"  Message : {res.message if res else ''}")
    print(f"  Citation: {res.citation if res else 'None'}")
    if res and res.data:
        print(f"  Data Keys: {list(res.data.keys())}")

syn_1 = synthesize_response(user_msg_1, steps_1, profile=profile)
print("\n" + "-" * 40)
print("SYNTHESIZED RESPONSE (Turn 1):")
print(syn_1)
print("-" * 40)

print("\n" + "=" * 80)
print("TEST 2: Follow-up Memory Query")
print("Query: 'What did you register me for again?'")
print("=" * 80)

user_msg_2 = "What did you register me for again?"
steps_2 = run(user_msg_2, session_id=session_id, profile=profile)

print(f"\nTotal Plan Steps Executed: {len(steps_2)}")
for s in steps_2:
    res = s.result
    print(f"\nStep {s.id}: Agent='{s.agent}', Action='{s.action}', Status='{s.status}'")
    print(f"  Message : {res.message if res else ''}")

syn_2 = synthesize_response(user_msg_2, steps_2, profile=profile)
print("\n" + "-" * 40)
print("SYNTHESIZED RESPONSE (Turn 2 - From Memory):")
print(syn_2)
print("-" * 40)
