import os
import sys
import time

# Set project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from orchestrator.orchestrator import run as run_orchestrator
from knowledge.memory import create_session, get_profile, get_history, get_session_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_integration_tests():
    ts = int(time.time())
    print("=" * 85)
    print("END-TO-END INTEGRATION TEST SUITE")
    print("Orchestrator -> Agent -> RAG (retrieve) -> Memory (SQLite)")
    print("=" * 85 + "\n")

    scenarios_passed = 0
    total_scenarios = 4

    # -------------------------------------------------------------------------
    # SCENARIO 1: Pure RAG / Policy Query (Attendance)
    # -------------------------------------------------------------------------
    s1_session = f"integ_sess_001_{ts}"
    s1_query = "What's the minimum attendance percentage?"
    
    print("SCENARIO 1: General Policy Query")
    print(f"  Query      : \"{s1_query}\"")
    print(f"  Session ID : {s1_session}")
    
    steps_1 = run_orchestrator(s1_query, session_id=s1_session)
    step_1 = steps_1[0]
    res_1 = step_1.result

    s1_agent_ok = step_1.agent == "academic"
    s1_rag_ok = res_1.citation is not None and "Attendance Policy" in res_1.citation
    s1_mem_ok = len(get_history(s1_session)) >= 2
    s1_pass = s1_agent_ok and s1_rag_ok and s1_mem_ok and res_1.status == "success"

    if s1_pass:
        scenarios_passed += 1

    print(f"  Agent Handled : {step_1.agent} ({step_1.action})")
    print(f"  Retrieve Used : {'YES (' + str(res_1.citation) + ')' if s1_rag_ok else 'NO'}")
    print(f"  Memory Logged : {'YES (Turns: ' + str(len(get_history(s1_session))) + ')' if s1_mem_ok else 'NO'}")
    print(f"  Response Msg  : {res_1.message[:110]}...")
    print(f"  Status        : {'PASS' if s1_pass else 'FAIL'}")
    print("-" * 85 + "\n")

    # -------------------------------------------------------------------------
    # SCENARIO 2: Personalized Eligibility Check (Eligible Student)
    # -------------------------------------------------------------------------
    s2_session = f"integ_sess_eligible_{ts}"
    create_session(s2_session, {
        "name": "Bhavya (Eligible)",
        "cgpa": 8.5,
        "backlog_count": 0,
        "attendance_pct": 88.0
    })
    s2_query = "Am I eligible for a dream company?"

    print("SCENARIO 2: Personalized Eligibility Check (Eligible Student)")
    print(f"  Query      : \"{s2_query}\"")
    print(f"  Session ID : {s2_session} (CGPA: 8.5, Backlogs: 0)")

    steps_2 = run_orchestrator(s2_query, session_id=s2_session)
    step_2 = steps_2[0]
    res_2 = step_2.result

    s2_agent_ok = step_2.agent == "placement"
    s2_elig_ok = res_2.data.get("eligible") is True and "YES" in res_2.message
    s2_rag_ok = res_2.citation is not None
    s2_mem_ok = get_profile(s2_session)["cgpa"] == 8.5
    s2_pass = s2_agent_ok and s2_elig_ok and s2_rag_ok and s2_mem_ok

    if s2_pass:
        scenarios_passed += 1

    print(f"  Agent Handled : {step_2.agent} ({step_2.action})")
    print(f"  Eligible Result: {res_2.data.get('eligible')} (Message: '{res_2.message[:70]}...')")
    print(f"  Retrieve Used : {'YES (' + str(res_2.citation) + ')' if s2_rag_ok else 'NO'}")
    print(f"  Memory Read   : YES (Student: {get_profile(s2_session)['name']})")
    print(f"  Status        : {'PASS' if s2_pass else 'FAIL'}")
    print("-" * 85 + "\n")

    # -------------------------------------------------------------------------
    # SCENARIO 3: Personalized Eligibility Check (At-Risk Student)
    # -------------------------------------------------------------------------
    s3_session = f"integ_sess_atrisk_{ts}"
    create_session(s3_session, {
        "name": "Rahul (At Risk)",
        "cgpa": 6.2,
        "backlog_count": 2,
        "attendance_pct": 61.0
    })
    s3_query = "Am I eligible for a dream company?"

    print("SCENARIO 3: Personalized Eligibility Check (At-Risk Student)")
    print(f"  Query      : \"{s3_query}\"")
    print(f"  Session ID : {s3_session} (CGPA: 6.2, Backlogs: 2)")

    steps_3 = run_orchestrator(s3_query, session_id=s3_session)
    step_3 = steps_3[0]
    res_3 = step_3.result

    s3_agent_ok = step_3.agent == "placement"
    s3_elig_ok = res_3.data.get("eligible") is False and "NO" in res_3.message
    s3_rag_ok = res_3.citation is not None
    s3_diff_ok = res_3.message != res_2.message  # Must be different from Scenario 2!
    s3_pass = s3_agent_ok and s3_elig_ok and s3_rag_ok and s3_diff_ok

    if s3_pass:
        scenarios_passed += 1

    print(f"  Agent Handled : {step_3.agent} ({step_3.action})")
    print(f"  Eligible Result: {res_3.data.get('eligible')} (Message: '{res_3.message[:70]}...')")
    print(f"  Retrieve Used : {'YES (' + str(res_3.citation) + ')' if s3_rag_ok else 'NO'}")
    print(f"  Diff from S2  : {'YES (S2=Eligible, S3=Not Eligible)' if s3_diff_ok else 'NO'}")
    print(f"  Status        : {'PASS' if s3_pass else 'FAIL'}")
    print("-" * 85 + "\n")

    # -------------------------------------------------------------------------
    # SCENARIO 4: 2-Turn Multi-Turn Conversation with Context Resolution
    # -------------------------------------------------------------------------
    s4_session = f"integ_sess_multiturn_{ts}"
    s4_t1_query = "What's the hostel curfew?"
    s4_t2_query = "what if I'm late?"

    print("SCENARIO 4: 2-Turn Multi-Turn Conversation with Context Resolution")
    print(f"  Session ID  : {s4_session}")
    print(f"  Turn 1 Query: \"{s4_t1_query}\"")

    steps_4_t1 = run_orchestrator(s4_t1_query, session_id=s4_session)
    res_4_t1 = steps_4_t1[0].result
    print(f"  Turn 1 Agent: {steps_4_t1[0].agent} | Citation: {res_4_t1.citation}")

    print(f"  Turn 2 Query: \"{s4_t2_query}\" (vague follow-up)")
    steps_4_t2 = run_orchestrator(s4_t2_query, session_id=s4_session)
    res_4_t2 = steps_4_t2[0].result

    # pyrefly: ignore [unexpected-keyword]
    s4_history = get_history(s4_session, last_n=10)
    # Check if turn 2 user query in history was context-resolved
    last_user_turn = [t for t in s4_history if t["role"] == "user"][-1]
    s4_context_ok = "[Previous Context:" in last_user_turn["content"] and "hostel" in last_user_turn["content"].lower()
    s4_agent_ok = steps_4_t2[0].agent == "campus"
    s4_rag_ok = res_4_t2.citation is not None and "Hostel" in res_4_t2.citation
    s4_pass = s4_context_ok and s4_agent_ok and s4_rag_ok

    if s4_pass:
        scenarios_passed += 1

    print(f"  Turn 2 Agent: {steps_4_t2[0].agent} ({steps_4_t2[0].action})")
    print(f"  Context Res : {'YES (' + last_user_turn['content'][:90] + '...)' if s4_context_ok else 'NO'}")
    print(f"  Retrieve Used: {'YES (' + str(res_4_t2.citation) + ')' if s4_rag_ok else 'NO'}")
    print(f"  Turn 2 Res  : {res_4_t2.message[:110]}...")
    print(f"  Status      : {'PASS' if s4_pass else 'FAIL'}")
    print("-" * 85 + "\n")

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("=" * 85)
    print("INTEGRATION TEST SUMMARY REPORT")
    print("=" * 85)
    print(f"Total Scenarios Tested : {total_scenarios}")
    print(f"Scenarios Passed       : {scenarios_passed}")
    print(f"Scenarios Failed       : {total_scenarios - scenarios_passed}")
    print(f"Final Score            : {scenarios_passed}/{total_scenarios} scenarios passing")
    print("=" * 85)


if __name__ == "__main__":
    run_integration_tests()
