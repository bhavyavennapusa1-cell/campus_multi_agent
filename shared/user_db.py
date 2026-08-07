"""
SQLite Database Module for User Authentication and Profile Persistence.
"""

import sqlite3
import hashlib
import os
import secrets
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "users.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                branch TEXT DEFAULT 'CSE - 3rd Year',
                attendance TEXT DEFAULT '100%',
                hostel TEXT DEFAULT 'Block B',
                career_goal TEXT DEFAULT 'Backend Developer',
                token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + '$' + pwd_hash.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_hash.hex() == hash_hex
    except Exception:
        return False


def create_user(email: str, password: str, name: str, branch: str = "CSE - 3rd Year", attendance: str = "100%", hostel: str = "Block B", career_goal: str = "Backend Developer") -> dict:
    init_db()
    email_clean = email.strip().lower()
    pwd_hash = hash_password(password)
    token = secrets.token_hex(32)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        if cursor.fetchone():
            raise ValueError("An account with this email or roll number already exists.")
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, branch, attendance, hostel, career_goal, token)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (email_clean, pwd_hash, name, branch, attendance, hostel, career_goal, token))
        conn.commit()
        user_id = cursor.lastrowid
        
    return {
        "id": user_id,
        "email": email_clean,
        "name": name,
        "branch": branch,
        "attendance": attendance,
        "hostel": hostel,
        "career_goal": career_goal,
        "token": token
    }


def authenticate_user(email: str, password: str) -> dict:
    init_db()
    email_clean = email.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid email/roll number or password.")
        
        if not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid email/roll number or password.")
        
        token = secrets.token_hex(32)
        cursor.execute("UPDATE users SET token = ? WHERE id = ?", (token, row["id"]))
        conn.commit()

        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "branch": row["branch"],
            "attendance": row["attendance"],
            "hostel": row["hostel"],
            "career_goal": row["career_goal"],
            "token": token
        }


def get_user_by_token(token: str) -> dict:
    if not token:
        return None
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "branch": row["branch"],
            "attendance": row["attendance"],
            "hostel": row["hostel"],
            "career_goal": row["career_goal"],
            "token": row["token"]
        }


def update_user_profile(token: str, name: str, branch: str, attendance: str, hostel: str, career_goal: str) -> dict:
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users WHERE token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Unauthorized session. Please log in again.")
        
        cursor.execute("""
            UPDATE users
            SET name = ?, branch = ?, attendance = ?, hostel = ?, career_goal = ?
            WHERE id = ?
        """, (name, branch, attendance, hostel, career_goal, row["id"]))
        conn.commit()

        return {
            "id": row["id"],
            "email": row["email"],
            "name": name,
            "branch": branch,
            "attendance": attendance,
            "hostel": hostel,
            "career_goal": career_goal,
            "token": token
        }


def logout_user(token: str):
    if not token:
        return
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET token = NULL WHERE token = ?", (token,))
        conn.commit()

# Initialize DB table automatically on module import
init_db()
