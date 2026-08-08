import os
import sys
import json
import sqlite3

PROJECT_ROOT = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import app, ChatRequest, chat

session_id = "hackathon_live_judge_demo_001"
profile = {
    "name": "Bhavya Vennapusa",
    "branch_year": "CSE - 3rd Year",
    "cgpa": 8.8,
    "backlog_count": 0,
    "attendance": "88%",
    "hostel_block": "Block B"
}

print("=" * 80)
print("TESTING MESSAGE 1")
print("Prompt: 'Am I eligible for the Google internship? If yes, register me and calendar it.'")
print("=" * 80)

req1 = ChatRequest(
    message="Am I eligible for the Google internship? If yes, register me and calendar it.",
    session_id=session_id,
    profile=profile
)
res1 = chat(req1)

print("\n--- MESSAGE 1 BACKEND RESPONSE JSON ---")
print("Reply:")
print(res1["reply"])
print("\nAgents Used:", res1["agents_used"])
print("\nRaw Trace Array Returned by Backend:")
print(json.dumps(res1["trace"], indent=2))

print("\n" + "=" * 80)
print("TESTING MESSAGE 2 (SAME SESSION)")
print("Prompt: 'What did you just register me for, and when?'")
print("=" * 80)

req2 = ChatRequest(
    message="What did you just register me for, and when?",
    session_id=session_id,
    profile=profile
)
res2 = chat(req2)

print("\n--- MESSAGE 2 BACKEND RESPONSE JSON ---")
print("Reply:")
print(res2["reply"])
print("\nAgents Used:", res2["agents_used"])
print("\nRaw Trace Array Returned for Message 2:")
print(json.dumps(res2["trace"], indent=2))

print("\n" + "=" * 80)
print("MEMORY VERIFICATION — DATABASE ROWS WRITTEN TO memory.db")
print("=" * 80)

db_path = os.path.join(PROJECT_ROOT, "knowledge", "memory.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT turn_id, role, agent_name, content, timestamp FROM conversation_history WHERE session_id = ? ORDER BY turn_id ASC", (session_id,))
turns = cursor.fetchall()

print(f"Total Turn Rows in conversation_history for session '{session_id}': {len(turns)}\n")
for t in turns:
    print(f"Turn #{t['turn_id']} [{t['role']} | Agent: {t['agent_name']}] ({t['timestamp']}):")
    print(f"  Content: {t['content'][:140]}...\n")

cursor.execute("SELECT session_id, name, year, branch, cgpa, backlog_count, attendance_pct, hostel_block, last_updated FROM student_profile WHERE session_id = ?", (session_id,))
prof_row = cursor.fetchone()
if prof_row:
    print("Student Profile Row in student_profile table:")
    print(dict(prof_row))

conn.close()
