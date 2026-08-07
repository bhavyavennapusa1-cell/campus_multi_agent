import os
import sys

# Set project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge.memory import (
    create_session,
    get_profile,
    update_profile,
    add_turn,
    get_history,
    resolve_context,
    get_session_summary
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_memory_tests():
    print("=" * 85)
    print("MULTI-AGENT MEMORY LAYER TEST REPORT")
    print("=" * 85 + "\n")

    passed_count = 0
    total_tests = 0

    # 1. Create Session A (Eligible Student)
    total_tests += 1
    session_a = "session_eligible_001"
    profile_a = create_session(session_a, {
        "name": "Bhavya (Eligible)",
        "year": 4,
        "branch": "CSE",
        "cgpa": 8.5,
        "backlog_count": 0,
        "attendance_pct": 88.0,
        "hostel_block": "Block-A",
        "placement_status": "not_placed"
    })

    # 2. Create Session B (At-Risk Student)
    total_tests += 1
    session_b = "session_at_risk_002"
    profile_b = create_session(session_b, {
        "name": "Rahul (At Risk)",
        "year": 3,
        "branch": "ECE",
        "cgpa": 6.2,
        "backlog_count": 2,
        "attendance_pct": 61.0,
        "hostel_block": "Block-C",
        "placement_status": "not_placed"
    })

    # Test Session Independence (Isolation)
    fetched_a = get_profile(session_a)
    fetched_b = get_profile(session_b)

    isolation_passed = (
        fetched_a["name"] == "Bhavya (Eligible)" and
        fetched_b["name"] == "Rahul (At Risk)" and
        fetched_a["cgpa"] == 8.5 and
        fetched_b["cgpa"] == 6.2
    )

    if isolation_passed:
        passed_count += 2
        print(f"TEST 1 [PASS]: Session A Profile Created (Name: {fetched_a['name']}, CGPA: {fetched_a['cgpa']})")
        print(f"TEST 2 [PASS]: Session B Profile Created (Name: {fetched_b['name']}, CGPA: {fetched_b['cgpa']})")
    else:
        print("TEST 1 & 2 [FAIL]: Profile isolation failed between Session A and B.")

    print("-" * 85 + "\n")

    # 3. Add Conversation Turns
    total_tests += 1
    # Session A Turns
    add_turn(session_a, "user", "Can I apply for Google Dream tier drive?")
    add_turn(session_a, "assistant", "Yes, with CGPA 8.5 and 0 backlogs you meet all Dream Tier criteria.", "placement_agent")
    add_turn(session_a, "user", "What is the fee for transport?")
    add_turn(session_a, "assistant", "The annual bus pass fee is ₹32,000 per academic year.", "transport_agent")

    # Session B Turns
    add_turn(session_b, "user", "Am I eligible for end-semester exams?")
    add_turn(session_b, "assistant", "Warning: Your attendance is 61.0% (<65.0%). You are currently detained.", "academic_agent")
    add_turn(session_b, "user", "What about hostel curfew hours?")
    add_turn(session_b, "assistant", "Hostel curfew is 10:30 PM on weekdays and 11:30 PM on weekends.", "hostel_agent")

    history_a = get_history(session_a, last_n=5)
    history_b = get_history(session_b, last_n=5)

    turns_passed = (len(history_a) == 4 and len(history_b) == 4)
    if turns_passed:
        passed_count += 1
        print(f"TEST 3 [PASS]: Multi-turn history recorded (Session A: {len(history_a)} turns, Session B: {len(history_b)} turns)")
    else:
        print(f"TEST 3 [FAIL]: Turn count mismatch (Session A: {len(history_a)}, Session B: {len(history_b)})")

    print("-" * 85 + "\n")

    # 4. Context Resolution (Vague Query Test)
    total_tests += 1
    vague_query = "What about its fee and rules?"
    resolved_q = resolve_context(session_a, vague_query)
    
    context_resolved = "[Previous Context:" in resolved_q and "transport_agent" in resolved_q
    if context_resolved:
        passed_count += 1
        print(f"TEST 4 [PASS]: Context Resolution Succeeded")
        print(f"       Raw Query      : \"{vague_query}\"")
        print(f"       Resolved Query : \"{resolved_q}\"")
    else:
        print(f"TEST 4 [FAIL]: Context Resolution failed to attach context: \"{resolved_q}\"")

    print("-" * 85 + "\n")

    # 5. Profile Update Test
    total_tests += 1
    updated_b = update_profile(session_b, placement_status="placed_mass")
    update_passed = updated_b["placement_status"] == "placed_mass"
    if update_passed:
        passed_count += 1
        print(f"TEST 5 [PASS]: Profile Update Succeeded (Session B placement_status updated to '{updated_b['placement_status']}')")
    else:
        print(f"TEST 5 [FAIL]: Profile Update failed.")

    print("-" * 85 + "\n")

    # 6. Session Summary Test
    total_tests += 1
    summary_a = get_session_summary(session_a)
    summary_passed = summary_a["turn_count"] == 4 and summary_a["profile"]["name"] == "Bhavya (Eligible)"
    if summary_passed:
        passed_count += 1
        print(f"TEST 6 [PASS]: Session Summary Verified for '{session_a}' (Turns: {summary_a['turn_count']})")
    else:
        print("TEST 6 [FAIL]: Session summary mismatch.")

    print("\n" + "=" * 85)
    print("MEMORY SYSTEM TEST SUMMARY")
    print("=" * 85)
    print(f"Total Tests Run : {total_tests}")
    print(f"Passed          : {passed_count}")
    print(f"Failed          : {total_tests - passed_count}")
    print("=" * 85)


if __name__ == "__main__":
    run_memory_tests()
