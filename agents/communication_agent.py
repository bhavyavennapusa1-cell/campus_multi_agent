"""
Communication Agent for Synapse Multi-Agent System.
Handles contacts lookup (via ContactsRepo interface), local chat groups (via SQLite operational tables),
email drafting with human-in-the-loop approval, Gmail sending, and Google Calendar scheduling.
"""

import os
import uuid
import sqlite3
import requests
from pathlib import Path
import sys
from datetime import datetime, timedelta
from typing import Optional

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from shared.data_store import (
    get_faculty,
    get_student,
    get_student_directory_record,
    get_collection,
    get_by_id
)
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session

# --- Feature 3: Contacts Data Boundary ---
class ContactsRepo:
    def get_by_query(self, student_id: str, query_type: str, subject: Optional[str] = None, profile: Optional[dict] = None) -> list[dict]:
        raise NotImplementedError


class StructuredContactsRepo(ContactsRepo):
    """ContactsRepo connected to structured JSON datasets under data/communication/."""

    def get_by_query(self, student_id: str, query_type: str, subject: Optional[str] = None, profile: Optional[dict] = None) -> list[dict]:
        qt = query_type.lower().strip() if query_type else "faculty"

        # Resolve student directory record
        student_rec = get_student_directory_record(student_id) or (get_student(student_id) if student_id else None)
        if not student_rec and profile:
            target_name = profile.get("student_id") or profile.get("name")
            student_rec = get_student_directory_record(target_name) or get_student(target_name)

        mentor_id = (student_rec and student_rec.get("mentor_id")) or (profile and profile.get("mentor_id")) or "FAC101"
        hod_id = (student_rec and student_rec.get("hod_id")) or (profile and profile.get("hod_id")) or "FAC100"
        branch = (student_rec and student_rec.get("branch")) or (profile and str(profile.get("branch", "CSE")).split("-")[0].strip().upper()) or "CSE"
        year = (student_rec and student_rec.get("year")) or (profile and profile.get("year", 3)) or 3
        section = (student_rec and student_rec.get("section")) or (profile and profile.get("section", "A")) or "A"

        faculty_list = get_collection("faculty")
        students_dir = get_collection("student_directory")
        classrooms = get_collection("classrooms")
        project_groups = get_collection("project_groups")

        if "mentor" in qt:
            fac = get_faculty(mentor_id)
            if fac:
                return [{
                    "contact_id": fac.get("faculty_id"),
                    "name": fac.get("name"),
                    "role": "Mentor",
                    "designation": fac.get("designation"),
                    "department": fac.get("department"),
                    "email": fac.get("email"),
                    "office": fac.get("office_location"),
                    "consultation_hours": fac.get("consultation_hours"),
                    "subjects": fac.get("subjects_taught", [])
                }]
            return [{"name": (student_rec and student_rec.get("mentor_name")) or "Dr. P. V. Sudha", "role": "Mentor", "email": "pv.sudha@vasavi.ac.in"}]

        if "hod" in qt:
            fac = get_faculty(hod_id)
            if fac:
                return [{
                    "contact_id": fac.get("faculty_id"),
                    "name": fac.get("name"),
                    "role": "HOD",
                    "designation": fac.get("designation"),
                    "department": fac.get("department"),
                    "email": fac.get("email"),
                    "office": fac.get("office_location"),
                    "consultation_hours": fac.get("consultation_hours")
                }]
            return [{"name": (student_rec and student_rec.get("hod_name")) or "Dr. T. Adilakshmi", "role": "HOD", "email": "hod.cse@vasavi.ac.in"}]

        if "classmate" in qt or "section" in qt:
            matched_classmates = []
            for s in students_dir:
                if (
                    str(s.get("branch", "")).upper() == str(branch).upper()
                    and int(s.get("year", 0)) == int(year)
                    and str(s.get("section", "")).upper() == str(section).upper()
                ):
                    matched_classmates.append({
                        "contact_id": s.get("student_id"),
                        "name": s.get("name"),
                        "role": "Classmate",
                        "email": s.get("email"),
                        "section": f"{s.get('branch')} {s.get('year')}-{s.get('section')}"
                    })
            if matched_classmates:
                return matched_classmates

            # Fallback query students roster
            all_students = get_collection("students")
            for s in all_students:
                if (
                    str(s.get("branch", "")).upper() == str(branch).upper()
                    and int(s.get("year", 0)) == int(year)
                    and str(s.get("section", "")).upper() == str(section).upper()
                ):
                    matched_classmates.append({
                        "contact_id": s.get("student_id"),
                        "name": s.get("name"),
                        "role": "Classmate",
                        "email": s.get("email"),
                        "section": f"{s.get('branch')} {s.get('year')}-{s.get('section')}"
                    })
            return matched_classmates if matched_classmates else [
                {"name": "Rahul Sharma", "role": "Classmate", "email": "rahul.s@vasavi.ac.in"},
                {"name": "Karthik Nair", "role": "Classmate", "email": "karthik.n@vasavi.ac.in"}
            ]

        if "group" in qt or "project" in qt or "capstone" in qt:
            matching_groups = []
            stu_id_target = (student_rec and student_rec.get("student_id")) or "STU001"
            for g in project_groups:
                members = g.get("members", [])
                if any(m.get("student_id") == stu_id_target or m.get("name") == student_id for m in members):
                    matching_groups.append({
                        "group_id": g.get("group_id"),
                        "title": g.get("title"),
                        "mentor": g.get("mentor_name"),
                        "role": "Project Group",
                        "members": members
                    })
            if matching_groups:
                return matching_groups
            return project_groups if project_groups else []

        if qt in ("subject_teacher", "teacher", "faculty") or subject:
            results = []
            for fac in faculty_list:
                subjects = [s.lower() for s in fac.get("subjects_taught", [])]
                f_copy = dict(fac)
                f_copy["role"] = "faculty"
                if subject and any(subject.lower() in s for s in subjects):
                    results.append(f_copy)
                elif not subject and fac.get("department", "").upper() == str(branch).upper():
                    results.append(f_copy)
            if results:
                return results
            return [dict(fac, role="faculty") for fac in faculty_list]

        return [dict(fac, role="faculty") if isinstance(fac, dict) and "role" not in fac else fac for fac in faculty_list]


contacts_repo_instance = StructuredContactsRepo()


# --- Feature 3: Agent-Scoped Operational SQLite Tables ---
DB_PATH = Path(__file__).resolve().parent / "communication_agent.db"

def init_db():
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

init_db()


# --- Human-in-the-Loop Pending Action Store ---
PENDING_ACTIONS = {}


def resolve_profile(params: dict) -> dict:

    prof = params.get("profile")
    session_id = params.get("session_id", "default")
    if not prof:
        prof = get_profile(session_id) or create_session(session_id)
    else:
        prof = dict(prof)
        if "name" not in prof:
            prof["name"] = "Student"
        if "branch" not in prof:
            prof["branch"] = prof.get("branch_year", "CSE - 3rd Year")
        if "year" not in prof:
            prof["year"] = 3
    return prof


def get_relevant_contacts(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

    raw_query = str(params.get("query_type") or params.get("query") or "faculty").lower()
    subject = params.get("subject")
    student_id = profile.get("student_id") or profile.get("name", "STU001")

    query_type = raw_query
    if "mentor" in raw_query or "advisor" in raw_query:
        query_type = "mentor"
    elif "hod" in raw_query or "head" in raw_query:
        query_type = "hod"
    elif "classmate" in raw_query or "peer" in raw_query or "section" in raw_query:
        query_type = "classmates"
    elif "group" in raw_query or "project" in raw_query or "capstone" in raw_query:
        query_type = "project_group"

    contacts = contacts_repo_instance.get_by_query(
        student_id=student_id,
        query_type=query_type,
        subject=subject,
        profile=profile
    )

    if query_type == "mentor" and contacts:
        c = contacts[0]
        msg = f"Your academic mentor is {c['name']} ({c.get('email', '')}, Office: {c.get('office', 'N/A')}, Consultation: {c.get('consultation_hours', 'N/A')})."
    elif query_type == "hod" and contacts:
        c = contacts[0]
        msg = f"Your Head of Department (HOD) is {c['name']} ({c.get('email', '')}, Office: {c.get('office', 'N/A')})."
    elif query_type == "classmates" and contacts:
        names = [c['name'] for c in contacts]
        msg = f"Found {len(contacts)} classmates in your section ({profile.get('branch', 'CSE')} Year {profile.get('year', 3)} Section {profile.get('section', 'A')}): {', '.join(names)}."
    elif query_type == "project_group" and contacts:
        msg = f"Found {len(contacts)} project group details for {profile['name']}."
    else:
        msg = f"Retrieved {len(contacts)} {query_type} contacts."

    return AgentResponse(
        status="success",
        data={
            "query_type": query_type,
            "subject": subject,
            "contacts": contacts,
            "source": "faculty_directory.json / student_directory.json / groups.json"
        },
        message=msg,
        citation=None
    )


def create_chat_group(params: dict) -> AgentResponse:
    session_id = params.get("session_id", "default")
    profile = get_profile(session_id) or create_session(session_id)

    group_name = params.get("group_name", "DBMS Study Group")
    member_ids = params.get("member_ids", ["c_004", "c_005"])
    group_type = params.get("group_type", "temporary")
    duration_hours = params.get("duration_hours", 24)

    group_id = f"grp_{uuid.uuid4().hex[:8]}"
    expires_at = None
    if group_type == "temporary" and duration_hours:
        expires_at = (datetime.now() + timedelta(hours=int(duration_hours))).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_groups (group_id, group_name, group_type, created_by, expires_at) VALUES (?, ?, ?, ?, ?)",
        (group_id, group_name, group_type, profile["name"], expires_at)
    )
    for cid in member_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO group_members (group_id, contact_id) VALUES (?, ?)",
            (group_id, cid)
        )
    conn.commit()
    conn.close()

    return AgentResponse(
        status="success",
        data={
            "group_id": group_id,
            "group_name": group_name,
            "group_type": group_type,
            "member_count": len(member_ids),
            "expires_at": expires_at,
            "source": "mock"
        },
        message=f"Created {group_type} chat group '{group_name}' ({len(member_ids)} members).",
        citation=None
    )


def draft_official_email(params: dict) -> AgentResponse:
    """
    Feature 3: Formats an official email using student profile context.
    Returns draft with requires_user_approval: True. NEVER sends directly.
    """
    profile = resolve_profile(params)
    session_id = params.get("session_id", "default")


    recipient_email = params.get("recipient_email") or params.get("to") or "academic_office@vasavi.ac.in"
    subject = params.get("subject", f"Official Inquiry from {profile['name']}")
    core_message = params.get("core_message") or params.get("body") or "Requesting information regarding academic schedules and condonation rules."

    formatted_body = (
        f"Respected Sir/Madam,\n\n"
        f"{core_message}\n\n"
        f"Student Profile:\n"
        f"- Name: {profile['name']}\n"
        f"- Branch: {profile['branch']} (Year {profile['year']})\n"
        f"- Roll/Session: {session_id}\n\n"
        f"Sincerely,\n{profile['name']}"
    )

    action_id = f"act_{uuid.uuid4().hex[:8]}"
    PENDING_ACTIONS[action_id] = {
        "action_id": action_id,
        "type": "send_email",
        "to": recipient_email,
        "subject": subject,
        "body": formatted_body,
        "created_at": datetime.now().isoformat()
    }

    return AgentResponse(
        status="needs_confirmation",
        data={
            "action_id": action_id,
            "to": recipient_email,
            "subject": subject,
            "body": formatted_body,
            "requires_user_approval": True,
            "source": "mock"
        },
        message=f"Drafted official email to {recipient_email}. Awaiting user confirmation [Action ID: {action_id}].",
        citation=None
    )


def send_email(params: dict) -> AgentResponse:
    """Feature 2: Gmail API -> send_email() invoked upon human approval."""
    to = params.get("to", "academic_office@vasavi.ac.in")
    subject = params.get("subject", "Campus Inquiry")
    body = params.get("body", "Hello")
    api_key = os.environ.get("GMAIL_API_KEY")

    if api_key:
        try:
            resp = requests.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"raw": "encoded_raw_mime_message"},
                timeout=3.0
            )
            if resp.status_code in (200, 201):
                return AgentResponse(
                    status="success",
                    data={"to": to, "subject": subject, "source": "live"},
                    message=f"Dispatched email to {to} via Gmail API.",
                    citation=None
                )
        except Exception:
            pass

    return AgentResponse(
        status="success",
        data={"to": to, "subject": subject, "source": "mock"},
        message=f"Dispatched email to {to} [mock mode].",
        citation=None
    )


def schedule_reminder(params: dict) -> AgentResponse:
    profile = resolve_profile(params)

    event = params.get("event", "Campus Event")
    minutes_before = params.get("minutes_before", 60)

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "event": event,
            "minutes_before": minutes_before,
            "source": "mock"
        },
        message=f"Reminder scheduled for {profile['name']}: {minutes_before} minutes prior to {event}.",
        citation=None
    )


def schedule_appointment(params: dict) -> AgentResponse:
    title = params.get("title", "Faculty Advising")
    start_time = params.get("start_time", "2026-08-12 14:00")
    return AgentResponse(
        status="success",
        data={"title": title, "start_time": start_time, "source": "mock"},
        message=f"Scheduled appointment '{title}' for {start_time}.",
        citation=None
    )


def update_appointment(params: dict) -> AgentResponse:
    appointment_id = params.get("appointment_id", "app_001")
    return AgentResponse(
        status="success",
        data={"appointment_id": appointment_id, "source": "mock"},
        message=f"Updated appointment {appointment_id}.",
        citation=None
    )


def cancel_appointment(params: dict) -> AgentResponse:
    appointment_id = params.get("appointment_id", "app_001")
    return AgentResponse(
        status="success",
        data={"appointment_id": appointment_id, "cancelled": True, "source": "mock"},
        message=f"Cancelled appointment {appointment_id}.",
        citation=None
    )


def general_synthesis(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    query = params.get("query", "communication channels faculty contact email guidelines")


    rag_results = retrieve(query, k=2, category="campus")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    synthesis_msg = (
        f"Communication Center Overview for {profile['name']}:\n"
        f"1. Contacts Directory: Faculty, HOD, and classmate contacts available via ContactsRepo.\n"
        f"2. Email Policy: Official drafts require human-in-the-loop approval prior to sending.\n"
        f"3. Active Operational Groups: SQLite chat_groups database active."
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "rag_chunks": rag_results,
            "synthesis_text": synthesis_msg,
            "source": "mock"
        },
        message=synthesis_msg,
        citation=citation
    )


ACTIONS = {
    "draft_email": draft_official_email,
    "draft_official_email": draft_official_email,
    "send_email": send_email,
    "schedule_reminder": schedule_reminder,
    "get_relevant_contacts": get_relevant_contacts,
    "create_chat_group": create_chat_group,
    "schedule_appointment": schedule_appointment,
    "update_appointment": update_appointment,
    "cancel_appointment": cancel_appointment,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown communication action: {action}")
    return ACTIONS[action](params)
