"""
Person C owns this file.
Two kinds of memory:
  - short-term: conversation history for the current session (in-memory dict is fine)
  - long-term: student profile, persisted to a small SQLite table

For a 24-hour hackathon, in-memory short-term is fine (resets on restart) -
don't over-engineer this part.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"

# --- short-term: conversation history, per session_id ---
_conversations: dict[str, list[dict]] = {}


def add_message(session_id: str, role: str, content: str):
    _conversations.setdefault(session_id, []).append({"role": role, "content": content})


def get_history(session_id: str) -> list[dict]:
    return _conversations.get(session_id, [])


# --- long-term: student profile in SQLite ---
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            session_id TEXT PRIMARY KEY,
            student_id TEXT,
            year INTEGER,
            branch TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_profile(session_id: str, student_id: str, year: int, branch: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO profile (session_id, student_id, year, branch) VALUES (?, ?, ?, ?)",
        (session_id, student_id, year, branch),
    )
    conn.commit()
    conn.close()


def get_profile(session_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT student_id, year, branch FROM profile WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"student_id": row[0], "year": row[1], "branch": row[2]}


_init_db()
