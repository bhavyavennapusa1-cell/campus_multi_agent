import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "comms_operational.db")


def init_db():
    """Initializes local agent-scoped SQLite operational database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_groups (
        group_id VARCHAR PRIMARY KEY,
        group_name VARCHAR,
        group_type VARCHAR,
        created_by VARCHAR,
        expires_at TIMESTAMP NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        group_id VARCHAR,
        contact_id VARCHAR,
        PRIMARY KEY (group_id, contact_id)
    );
    """)

    conn.commit()
    conn.close()


def create_group(group_id: str, group_name: str, member_ids: List[str], group_type: str, created_by: str, duration_hours: Optional[int] = None) -> Dict[str, Any]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    expires_at = None
    if group_type.lower() == "temporary" and duration_hours:
        expires_at = (datetime.now() + timedelta(hours=duration_hours)).isoformat()

    cursor.execute(
        "INSERT OR REPLACE INTO chat_groups (group_id, group_name, group_type, created_by, expires_at) VALUES (?, ?, ?, ?, ?)",
        (group_id, group_name, group_type, created_by, expires_at)
    )

    for mid in member_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO group_members (group_id, contact_id) VALUES (?, ?)",
            (group_id, mid)
        )

    conn.commit()
    conn.close()

    return {
        "group_id": group_id,
        "group_name": group_name,
        "group_type": group_type,
        "created_by": created_by,
        "member_count": len(member_ids),
        "expires_at": expires_at,
        "status": "active"
    }


def get_active_groups() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT group_id, group_name, group_type, created_by, expires_at FROM chat_groups")
    rows = cursor.fetchall()

    groups = []
    for r in rows:
        gid = r[0]
        cursor.execute("SELECT contact_id FROM group_members WHERE group_id = ?", (gid,))
        members = [m[0] for m in cursor.fetchall()]
        groups.append({
            "group_id": gid,
            "group_name": r[1],
            "group_type": r[2],
            "created_by": r[3],
            "expires_at": r[4],
            "member_count": len(members),
            "members": members
        })

    conn.close()
    return groups
