import os
import random
import re
import sqlite3
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

SAMPLE_NAMES = ["Bhavya", "Rahul", "Ananya", "Siddharth", "Priya", "Vikram", "Sneha", "Karthik"]
SAMPLE_BRANCHES = ["CSE", "ECE", "EEE", "MECH", "CIVIL", "IT"]
SAMPLE_HOSTEL_BLOCKS = ["Block-A", "Block-B", "Block-C", "Day Scholar"]
SAMPLE_PLACEMENT_STATUSES = ["not_placed", "not_placed", "not_placed", "placed_core", "placed_mass"]

VAGUE_TERMS = {
    "it", "this", "that", "those", "these", "one", "he", "she", "him", "her",
    "them", "they", "its", "his", "hers", "what about", "how about", "tell me more",
    "what if", "late", "what happens", "if i", "and if"
}


def get_db_connection():
    """Establishes an SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates conversation_history and student_profile tables if they do not exist."""
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
                last_updated TEXT NOT NULL
            );
        """)
        conn.commit()


# Initialize database automatically at module import
init_db()


def create_session(session_id: str, profile_overrides: dict = None) -> dict:
    """Creates or resets a session with a realistic (or overridden) student profile."""
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Realistic default randomized profile
    default_profile = {
        "session_id": session_id,
        "name": random.choice(SAMPLE_NAMES),
        "year": random.randint(1, 4),
        "branch": random.choice(SAMPLE_BRANCHES),
        "cgpa": round(random.uniform(5.5, 9.5), 1),
        "backlog_count": random.choice([0, 0, 0, 0, 1, 1, 2, 3]),
        "attendance_pct": round(random.uniform(55.0, 95.0), 1),
        "hostel_block": random.choice(SAMPLE_HOSTEL_BLOCKS),
        "placement_status": random.choice(SAMPLE_PLACEMENT_STATUSES),
        "last_updated": now_iso
    }

    if profile_overrides:
        default_profile.update(profile_overrides)
        default_profile["session_id"] = session_id
        default_profile["last_updated"] = now_iso

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO student_profile (
                session_id, name, year, branch, cgpa, backlog_count,
                attendance_pct, hostel_block, placement_status, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            default_profile["session_id"],
            default_profile["name"],
            default_profile["year"],
            default_profile["branch"],
            default_profile["cgpa"],
            default_profile["backlog_count"],
            default_profile["attendance_pct"],
            default_profile["hostel_block"],
            default_profile["placement_status"],
            default_profile["last_updated"]
        ))
        conn.commit()

    return default_profile


def get_profile(session_id: str) -> dict | None:
    """Returns the student profile for a given session, or None if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_profile WHERE session_id = ?;", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_profile(session_id: str, **fields) -> dict:
    """Updates specific fields in student_profile and sets last_updated."""
    existing = get_profile(session_id)
    if not existing:
        raise ValueError(f"Session '{session_id}' does not exist.")

    now_iso = datetime.now(timezone.utc).isoformat()
    fields["last_updated"] = now_iso

    set_clauses = [f"{k} = ?" for k in fields.keys()]
    values = list(fields.values()) + [session_id]

    sql = f"UPDATE student_profile SET {', '.join(set_clauses)} WHERE session_id = ?;"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()

    return get_profile(session_id)


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
    """Returns a compact dict combining profile, turn count, and last activity timestamp."""
    profile = get_profile(session_id)
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
