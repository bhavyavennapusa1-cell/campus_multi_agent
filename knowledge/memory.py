import os
import random
import re
import json
import sqlite3
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

SAMPLE_NAMES = ["Priya Kumar", "Arjun Reddy", "Ananya Rao", "Siddharth Verma", "Priya Reddy", "Vikram Patel", "Sneha Kulkarni", "Karthik Nair"]
SAMPLE_BRANCHES = ["CSE", "ECE", "EEE", "MECH", "CIVIL", "IT"]
SAMPLE_HOSTEL_BLOCKS = ["Block-A", "Block-B", "Block-C", "Day Scholar"]
SAMPLE_PLACEMENT_STATUSES = ["not_placed", "not_placed", "not_placed", "placed_core", "placed_mass"]

VAGUE_TERMS = {
    "it", "this", "that", "those", "these", "one", "he", "she", "him", "her",
    "them", "they", "its", "his", "hers", "what about", "how about", "tell me more",
    "what if", "late", "what happens", "if i", "and if", "again", "what did", "registered", "did you"
}


def get_db_connection():
    """Establishes an SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates conversation_history, student_profile, and retrieval_log tables if they do not exist and runs column migrations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Table 1: conversation_history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                agent_name TEXT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)

        # Table 2: student_profile
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_profile (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                year INTEGER NOT NULL,
                branch TEXT NOT NULL,
                cgpa REAL NOT NULL,
                backlog_count INTEGER NOT NULL,
                attendance_pct REAL NOT NULL,
                hostel_block TEXT NOT NULL,
                placement_status TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                career_goal TEXT DEFAULT 'Software Engineer at Tier-1 Tech Company',
                skills TEXT DEFAULT '["Python", "Java", "Data Structures", "SQL"]',
                academic_interests TEXT DEFAULT '["Artificial Intelligence", "Distributed Systems"]',
                courses_in_progress TEXT DEFAULT '["CS301", "CS302", "CS303"]',
                current_projects TEXT DEFAULT '["Synapse Multi-Agent System"]',
                events_interested_in TEXT DEFAULT '["Axiom AI Hackathon", "Google Resume Workshop"]',
                learning_goals TEXT DEFAULT '["Master System Design", "Build LLM Agent Workflows"]'
            );
        """)

        # Migration check: ensure extended student memory columns exist
        cursor.execute("PRAGMA table_info(student_profile);")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        new_columns = {
            "student_id": "TEXT DEFAULT 'STU001'",
            "semester": "INTEGER DEFAULT 6",
            "section": "TEXT DEFAULT 'A'",
            "mentor_id": "TEXT DEFAULT 'FAC101'",
            "hod_id": "TEXT DEFAULT 'FAC100'",
            "career_goal": "TEXT DEFAULT 'Software Engineer at Tier-1 Tech Company'",
            "skills": "TEXT DEFAULT '[\"Python\", \"Java\", \"Data Structures\", \"SQL\"]'",
            "academic_interests": "TEXT DEFAULT '[\"Artificial Intelligence\", \"Distributed Systems\"]'",
            "courses_in_progress": "TEXT DEFAULT '[\"CS301\", \"CS302\", \"CS303\"]'",
            "current_projects": "TEXT DEFAULT '[\"Synapse Multi-Agent System\"]'",
            "events_interested_in": "TEXT DEFAULT '[\"Axiom AI Hackathon\", \"Google Resume Workshop\"]'",
            "learning_goals": "TEXT DEFAULT '[\"Master System Design\", \"Build LLM Agent Workflows\"]'"
        }

        for col_name, col_def in new_columns.items():
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE student_profile ADD COLUMN {col_name} {col_def};")

        # Table 3: retrieval_log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                top_doc_ids TEXT NOT NULL,
                top_scores TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)

        conn.commit()


def log_retrieval(session_id: str, query: str, top_doc_ids: list[str], top_scores: list[float]) -> None:
    """Passively logs every retrieval call into SQLite retrieval_log table."""
    now_iso = datetime.now(timezone.utc).isoformat()
    doc_ids_str = json.dumps(top_doc_ids or [])
    scores_str = json.dumps([round(s, 4) for s in (top_scores or [])])

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO retrieval_log (
                    session_id, query, top_doc_ids, top_scores, timestamp
                ) VALUES (?, ?, ?, ?, ?);
            """, (session_id or "global_retrieval", query, doc_ids_str, scores_str, now_iso))
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to log retrieval turn: {e}")


def get_retrieval_logs(session_id: str = None, limit: int = 10) -> list[dict]:
    """Returns recent passive retrieval logs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute("SELECT * FROM retrieval_log WHERE session_id = ? ORDER BY id DESC LIMIT ?;", (session_id, limit))
        else:
            cursor.execute("SELECT * FROM retrieval_log ORDER BY id DESC LIMIT ?;", (limit,))
        return [dict(row) for row in cursor.fetchall()]


# Initialize database automatically at module import
init_db()


def normalize_profile_dict(overrides: dict) -> dict:
    """Normalizes frontend profile keys (branch_year, attendance, hostel) into standard DB columns."""
    if not overrides:
        return {}
    norm = dict(overrides)

    if "branch_year" in norm and "branch" not in norm:
        norm["branch"] = norm.pop("branch_year")
    elif "branch" in norm and "branch_year" in norm:
        norm["branch"] = norm["branch_year"]

    if "attendance" in norm and "attendance_pct" not in norm:
        val = norm.pop("attendance")
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            try:
                norm["attendance_pct"] = float(val)
            except ValueError:
                norm["attendance_pct"] = 88.0
        elif isinstance(val, (int, float)):
            norm["attendance_pct"] = float(val)
    elif "attendance_pct" in norm:
        val = norm["attendance_pct"]
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            try:
                norm["attendance_pct"] = float(val)
            except ValueError:
                norm["attendance_pct"] = 88.0

    if "hostel" in norm and "hostel_block" not in norm:
        norm["hostel_block"] = norm.pop("hostel")

    return norm


def create_session(session_id: str, profile_overrides: dict = None) -> dict:
    """Creates or resets a session with a student profile seeded from data/students.json when available."""
    from shared.data_store import get_student
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Check if student_id or student name is provided in overrides or session_id
    lookup_id = None
    if profile_overrides:
        lookup_id = profile_overrides.get("student_id") or profile_overrides.get("name")
    if not lookup_id and session_id:
        lookup_id = session_id

    matched_student = get_student(lookup_id) if lookup_id else None

    if matched_student:
        default_profile = {
            "session_id": session_id,
            "student_id": matched_student.get("student_id", "STU001"),
            "name": matched_student.get("name", "Priya Kumar"),
            "year": matched_student.get("year", 3),
            "semester": matched_student.get("semester", 6),
            "branch": matched_student.get("branch", "CSE"),
            "section": matched_student.get("section", "A"),
            "cgpa": matched_student.get("cgpa", 8.8),
            "backlog_count": matched_student.get("backlog_count", 0),
            "attendance_pct": matched_student.get("attendance_pct", 88.0),
            "hostel_block": matched_student.get("hostel_block", "Block-B"),
            "placement_status": matched_student.get("placement_status", "not_placed"),
            "mentor_id": matched_student.get("mentor_id", "FAC101"),
            "hod_id": matched_student.get("hod_id", "FAC100"),
            "last_updated": now_iso,
            "career_goal": "Software Engineer at Tier-1 Tech Company",
            "skills": json.dumps(["Python", "Java", "Data Structures", "SQL"]),
            "academic_interests": json.dumps(["Artificial Intelligence", "Distributed Systems"]),
            "courses_in_progress": json.dumps(["CS301", "CS302", "CS303"]),
            "current_projects": json.dumps(["Synapse Multi-Agent System"]),
            "events_interested_in": json.dumps(["Axiom AI Hackathon", "Google Resume Workshop"]),
            "learning_goals": json.dumps(["Master System Design", "Build LLM Agent Workflows"])
        }
    else:
        # Fallback to random profile creation when no student_id / matching student is available
        default_profile = {
            "session_id": session_id,
            "student_id": "STU001",
            "name": random.choice(SAMPLE_NAMES),
            "year": 3,
            "semester": 6,
            "section": "A",
            "branch": "CSE",
            "cgpa": round(random.uniform(7.5, 9.5), 1),
            "backlog_count": 0,
            "attendance_pct": round(random.uniform(78.0, 92.0), 1),
            "hostel_block": "Block-B",
            "placement_status": "not_placed",
            "mentor_id": "FAC101",
            "hod_id": "FAC100",
            "last_updated": now_iso,
            "career_goal": "Software Engineer at Tier-1 Tech Company",
            "skills": json.dumps(["Python", "Java", "Data Structures", "SQL"]),
            "academic_interests": json.dumps(["Artificial Intelligence", "Distributed Systems"]),
            "courses_in_progress": json.dumps(["CS301", "CS302", "CS303"]),
            "current_projects": json.dumps(["Synapse Multi-Agent System"]),
            "events_interested_in": json.dumps(["Axiom AI Hackathon", "Google Resume Workshop"]),
            "learning_goals": json.dumps(["Master System Design", "Build LLM Agent Workflows"])
        }

    if profile_overrides:
        norm_overrides = normalize_profile_dict(profile_overrides)
        for k, v in norm_overrides.items():
            if isinstance(v, (list, dict)):
                default_profile[k] = json.dumps(v)
            else:
                default_profile[k] = v
        default_profile["session_id"] = session_id
        default_profile["last_updated"] = now_iso

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO student_profile (
                session_id, student_id, name, year, semester, branch, section, cgpa, backlog_count,
                attendance_pct, hostel_block, placement_status, mentor_id, hod_id, last_updated,
                career_goal, skills, academic_interests, courses_in_progress,
                current_projects, events_interested_in, learning_goals
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            default_profile["session_id"],
            default_profile.get("student_id", "STU001"),
            default_profile["name"],
            default_profile["year"],
            default_profile.get("semester", 6),
            default_profile["branch"],
            default_profile.get("section", "A"),
            default_profile["cgpa"],
            default_profile["backlog_count"],
            default_profile["attendance_pct"],
            default_profile["hostel_block"],
            default_profile["placement_status"],
            default_profile.get("mentor_id", "FAC101"),
            default_profile.get("hod_id", "FAC100"),
            default_profile["last_updated"],
            default_profile["career_goal"],
            default_profile["skills"],
            default_profile["academic_interests"],
            default_profile["courses_in_progress"],
            default_profile["current_projects"],
            default_profile["events_interested_in"],
            default_profile["learning_goals"]
        ))
        conn.commit()

    return get_student_memory(session_id)



def get_profile(session_id: str) -> dict | None:
    """Returns the student profile for a given session, or None if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_profile WHERE session_id = ?;", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_student_memory(session_id: str) -> dict | None:
    """
    Returns student profile memory with JSON list fields automatically parsed into Python lists.
    """
    prof = get_profile(session_id)
    if not prof:
        return None

    json_fields = ["skills", "academic_interests", "courses_in_progress", "current_projects", "events_interested_in", "learning_goals"]
    for field in json_fields:
        raw_val = prof.get(field)
        if isinstance(raw_val, str):
            try:
                prof[field] = json.loads(raw_val)
            except Exception:
                prof[field] = [raw_val] if raw_val else []

    return prof


VALID_STUDENT_PROFILE_COLS = {
    "session_id", "student_id", "name", "year", "semester", "branch", "section",
    "cgpa", "backlog_count", "attendance_pct", "hostel_block", "placement_status",
    "mentor_id", "hod_id", "last_updated", "career_goal", "skills",
    "academic_interests", "courses_in_progress", "current_projects",
    "events_interested_in", "learning_goals"
}

def update_student_profile(session_id: str, profile_updates: dict) -> dict:
    """
    Updates specific student memory fields (serializing lists to JSON) and sets last_updated.
    """
    existing = get_profile(session_id)
    norm_updates = normalize_profile_dict(profile_updates)
    if not existing:
        create_session(session_id, norm_updates)
        return get_student_memory(session_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    fields = {"last_updated": now_iso}

    for k, v in norm_updates.items():
        if k in VALID_STUDENT_PROFILE_COLS and k != "session_id":
            if isinstance(v, (list, dict)):
                fields[k] = json.dumps(v)
            else:
                fields[k] = v

    if len(fields) > 1:
        set_clauses = [f"{k} = ?" for k in fields.keys()]
        values = list(fields.values()) + [session_id]
        sql = f"UPDATE student_profile SET {', '.join(set_clauses)} WHERE session_id = ?;"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()

    return get_student_memory(session_id)


def update_profile(session_id: str, **fields) -> dict:
    """Legacy helper updating fields in student_profile."""
    return update_student_profile(session_id, fields)


def add_turn(session_id: str, role: str, content: str, agent_name: str = None) -> None:
    """Appends a new turn to conversation_history with auto-incremented turn_id per session."""
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(turn_id) FROM conversation_history WHERE session_id = ?;", (session_id,))
        max_turn = cursor.fetchone()[0]
        next_turn = (max_turn or 0) + 1

        cursor.execute("""
            INSERT INTO conversation_history (
                session_id, turn_id, role, agent_name, content, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?);
        """, (session_id, next_turn, role, agent_name, content, now_iso))
        conn.commit()


def get_history(session_id: str, last_n: int = 5) -> list[dict]:
    """Returns the last N turns for a session, ordered chronologically (oldest first)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, turn_id, role, agent_name, content, timestamp
            FROM conversation_history
            WHERE session_id = ?
            ORDER BY turn_id DESC
            LIMIT ?;
        """, (session_id, last_n))
        rows = cursor.fetchall()
        
        history = [dict(row) for row in reversed(rows)]
        return history


def resolve_context(session_id: str, current_query: str) -> str:
    """
    Query-rewriting helper: if current_query contains pronouns, vague terms,
    or is a short follow-up, prepends context from the last 2 conversation turns.
    """
    tokens = set(re.findall(r"\b\w+\b", current_query.lower()))
    query_lower = current_query.lower()

    contains_vague = (
        any(term in query_lower for term in VAGUE_TERMS)
        or bool(tokens & VAGUE_TERMS)
        or len(current_query.split()) <= 4
    )

    if not contains_vague:
        return current_query

    history = get_history(session_id, last_n=2)
    if not history:
        return current_query

    context_snippets = []
    for turn in history:
        role_label = turn["agent_name"] if turn.get("agent_name") else turn["role"]
        context_snippets.append(f"{role_label}: {turn['content']}")

    context_str = " | ".join(context_snippets)
    resolved_query = f"[Previous Context: {context_str}] {current_query}"
    return resolved_query


def get_session_summary(session_id: str) -> dict:
    """Returns a compact dict combining profile memory, turn count, and last activity timestamp."""
    profile = get_student_memory(session_id)
    history = get_history(session_id, last_n=1)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversation_history WHERE session_id = ?;", (session_id,))
        turn_count = cursor.fetchone()[0]

    last_activity = history[-1]["timestamp"] if history else (profile["last_updated"] if profile else None)

    return {
        "session_id": session_id,
        "profile": profile,
        "turn_count": turn_count,
        "last_activity": last_activity
    }
