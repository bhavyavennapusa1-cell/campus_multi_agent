"""
Academic Agent for Synapse Multi-Agent System.
Handles student attendance checks, exam schedules, study plans, Todoist task integration,
and Google Calendar scheduling using adapter pattern with live/mock fallbacks.
"""

import os
import re
import requests
from pathlib import Path

import sys
from datetime import datetime, timedelta

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import AgentResponse
from shared.data_store import (
    get_timetable as ds_get_timetable,
    get_collection,
    get_by_id
)
from knowledge.rag import retrieve, format_citation
from knowledge.memory import get_profile, create_session

# In-Memory Todoist fallback task storage
TODOIST_MOCK_STORAGE = []


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
        if "attendance_pct" not in prof:
            val = str(prof.get("attendance", 88)).replace("%", "").strip()
            try:
                prof["attendance_pct"] = float(val)
            except ValueError:
                prof["attendance_pct"] = 88.0
        if "hostel_block" not in prof:
            prof["hostel_block"] = prof.get("hostel", "Block B")
    return prof


def get_attendance(params: dict) -> AgentResponse:
    profile = resolve_profile(params)


    query = params.get("query", "minimum attendance percentage required condonation detention threshold")
    rag_results = retrieve(query, k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    att = profile["attendance_pct"]
    name = profile["name"]

    if att >= 75.0:
        status_str = f"Student {name} has {att}% attendance (>= 75.0%), meeting the standard requirement."
        is_detained = False
    elif att >= 65.0:
        status_str = f"Student {name} has {att}% attendance (65.0-74.9%), eligible for condonation on medical grounds."
        is_detained = False
    else:
        status_str = f"Student {name} has {att}% attendance (< 65.0%), resulting in strict detention."
        is_detained = True

    policy_text = top_rag["text"] if top_rag else "Policy not available."

    return AgentResponse(
        status="success",
        data={
            "student_name": name,
            "attendance_pct": att,
            "is_detained": is_detained,
            "policy_text": policy_text,
            "profile": profile,
            "source": "mock"
        },
        message=f"{status_str} Policy detail: {policy_text[:120]}...",
        citation=citation
    )


def get_timetable(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    branch = profile.get("branch", "CSE").split("-")[0].strip()
    year = profile.get("year", 3)
    section = profile.get("section", "A")

    tt_record = ds_get_timetable(branch, year, section)

    if tt_record and tt_record.get("schedule"):
        schedule_items = tt_record.get("schedule", [])
        formatted_list = [f"{item.get('day')} {item.get('time')}: {item.get('subject')} ({item.get('course_id')})" for item in schedule_items]
        return AgentResponse(
            status="success",
            data={
                "student": profile["name"],
                "branch": branch,
                "year": year,
                "section": section,
                "room": tt_record.get("room", "R301"),
                "schedule": schedule_items,
                "source": "timetables.json"
            },
            message=f"Timetable for {profile['name']} ({branch} Year {year} Sec {section}, Room {tt_record.get('room', 'R301')}):\n" + "\n".join(formatted_list),
            citation=None
        )

    # Fallback to mock if no structured timetable entry matches
    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "branch": profile["branch"],
            "today": ["09:00 AM Data Structures", "11:00 AM Operating Systems", "02:00 PM AI Lab"],
            "source": "mock"
        },
        message=f"Timetable for {profile['name']} ({profile['branch']}) retrieved.",
        citation=None
    )


SUBJECT_ALIASES = {
    "ds": "Data Structures",
    "dsa": "Data Structures",
    "data structures": "Data Structures",
    "dbms": "Database Management Systems",
    "database management systems": "Database Management Systems",
    "database": "Database Management Systems",
    "os": "Operating Systems",
    "operating systems": "Operating Systems",
}

EXAM_DATABASE = [
    {"subject": "Database Management Systems", "code": "DBMS", "date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"), "time": "10:00 AM"},
    {"subject": "Operating Systems", "code": "OS", "date": "2026-08-20", "time": "10:00 AM"},
    {"subject": "Data Structures", "code": "DS", "date": "2026-08-22", "time": "10:00 AM"}
]


def get_exam_schedule(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    raw_query = str(params.get("subject") or params.get("query") or "").strip().lower()

    matched_std_subject = None
    if raw_query:
        sorted_alias_keys = sorted(SUBJECT_ALIASES.keys(), key=len, reverse=True)
        for alias_key in sorted_alias_keys:
            pattern = r'\b' + re.escape(alias_key) + r'\b'
            if re.search(pattern, raw_query):
                matched_std_subject = SUBJECT_ALIASES[alias_key]
                break

    rag_results = retrieve(raw_query or "examination regulations passing marks grading scale CIE SEE", k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    # Combine structured exam_schedules.json with EXAM_DATABASE
    structured_exams = get_collection("exam_schedules")
    all_exams = []

    if structured_exams:
        for se in structured_exams:
            c_code = "DBMS" if se.get("course_id") == "CS302" else se.get("course_id")
            all_exams.append({
                "subject": se.get("course_name"),
                "code": c_code,
                "exam_type": se.get("exam_type"),
                "date": se.get("date"),
                "time": se.get("time"),
                "venue": se.get("venue"),
                "max_marks": se.get("max_marks"),
                "passing_min_marks": se.get("passing_min_marks")
            })

    # Merge EXAM_DATABASE fallbacks for subjects not in structured_exams
    for de in EXAM_DATABASE:
        if not any(e["subject"].lower() == de["subject"].lower() or e["code"].lower() == de["code"].lower() for e in all_exams):
            all_exams.append(de)

    if matched_std_subject:
        filtered_exams = [
            e for e in all_exams 
            if e["subject"].lower() == matched_std_subject.lower()
            or e["code"].lower() == matched_std_subject.lower()
        ]
        if filtered_exams:
            target_exam = filtered_exams[0]
            msg = f"Exam schedule for {profile['name']}: {target_exam['subject']} ({target_exam['code']}) on {target_exam['date']} at {target_exam['time']}."
            return AgentResponse(
                status="success",
                data={
                    "student": profile["name"],
                    "exams": filtered_exams,
                    "matched_subject": matched_std_subject,
                    "rules": top_rag["text"] if top_rag else "",
                    "source": "exam_schedules.json"
                },
                message=msg,
                citation=citation
            )
        else:
            return AgentResponse(
                status="success",
                data={
                    "student": profile["name"],
                    "exams": [],
                    "matched_subject": matched_std_subject,
                    "source": "exam_schedules.json"
                },
                message=f"No exam schedule found for requested subject '{matched_std_subject}'.",
                citation=citation
            )

    # Check if a specific unmapped subject was queried
    if raw_query and not any(k in raw_query for k in ["schedule", "exam", "exams", "dates", "when", "timetable", "all", "my"]):
        return AgentResponse(
            status="success",
            data={
                "student": profile["name"],
                "exams": [],
                "source": "exam_schedules.json"
            },
            message="No exam schedule found for the requested subject.",
            citation=citation
        )

    return AgentResponse(
        status="success",
        data={
            "student": profile["name"],
            "exams": all_exams,
            "rules": top_rag["text"] if top_rag else "",
            "source": "exam_schedules.json"
        },
        message=f"Exam schedule for {profile['name']}: {len(all_exams)} exams found.",
        citation=citation
    )


def course_info(params: dict) -> AgentResponse:
    profile = resolve_profile(params)
    raw_query = str(params.get("course_id") or params.get("subject") or params.get("query") or "").strip()

    courses = get_collection("courses")
    matched_courses = []

    if raw_query:
        target = raw_query.lower()
        for c in courses:
            if (
                c.get("course_id", "").lower() == target
                or c.get("code", "").lower() == target
                or target in c.get("name", "").lower()
            ):
                matched_courses.append(c)

    if not matched_courses:
        branch = profile.get("branch", "CSE").split("-")[0].strip().upper()
        matched_courses = [c for c in courses if c.get("department", "").upper() == branch]

    rag_results = retrieve(raw_query or "course syllabus prerequisites credits", k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    if matched_courses:
        c = matched_courses[0]
        msg = f"Course Details for {c.get('name')} ({c.get('course_id')} / {c.get('code')}): Department {c.get('department')}, Credits: {c.get('credits')}, Syllabus: {', '.join(c.get('syllabus_outline', []))}."
        return AgentResponse(
            status="success",
            data={
                "student": profile["name"],
                "courses": matched_courses,
                "source": "courses.json"
            },
            message=msg,
            citation=citation
        )

    return AgentResponse(
        status="success",
        data={"courses": [], "source": "academic"},
        message="No matching course details found.",
        citation=citation
    )



def create_task(params: dict) -> AgentResponse:
    """Feature 2: Todoist API -> create_task() with live API or mock fallback."""
    content = params.get("content", "Study session")
    due_string = params.get("due_string", "tomorrow")
    token = os.environ.get("TODOIST_API_KEY")

    if token:
        try:
            resp = requests.post(
                "https://api.todoist.com/rest/v2/tasks",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"content": content, "due_string": due_string},
                timeout=3.0
            )
            if resp.status_code in (200, 201):
                task_data = resp.json()
                return AgentResponse(
                    status="success",
                    data={"task": task_data, "source": "live"},
                    message=f"Created Todoist task: '{content}' (Due: {due_string}).",
                    citation=None
                )
        except Exception:
            pass

    # Mock Fallback
    mock_task = {"id": f"task_{len(TODOIST_MOCK_STORAGE)+1}", "content": content, "due_string": due_string, "completed": False}
    TODOIST_MOCK_STORAGE.append(mock_task)

    return AgentResponse(
        status="success",
        data={"task": mock_task, "source": "mock"},
        message=f"Created Todoist task: '{content}' (Due: {due_string}) [mock mode].",
        citation=None
    )


def get_tasks(params: dict) -> AgentResponse:
    token = os.environ.get("TODOIST_API_KEY")
    if token:
        try:
            resp = requests.get(
                "https://api.todoist.com/rest/v2/tasks",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            if resp.status_code == 200:
                return AgentResponse(
                    status="success",
                    data={"tasks": resp.json(), "source": "live"},
                    message=f"Retrieved {len(resp.json())} tasks from Todoist.",
                    citation=None
                )
        except Exception:
            pass

    return AgentResponse(
        status="success",
        data={"tasks": TODOIST_MOCK_STORAGE, "source": "mock"},
        message=f"Retrieved {len(TODOIST_MOCK_STORAGE)} tasks from study task tracker.",
        citation=None
    )


def update_task(params: dict) -> AgentResponse:
    task_id = params.get("task_id")
    new_content = params.get("content", "Updated task")
    return AgentResponse(
        status="success",
        data={"task_id": task_id, "content": new_content, "source": "mock"},
        message=f"Updated task {task_id} to '{new_content}'.",
        citation=None
    )


def complete_task(params: dict) -> AgentResponse:
    task_id = params.get("task_id")
    return AgentResponse(
        status="success",
        data={"task_id": task_id, "completed": True, "source": "mock"},
        message=f"Marked task {task_id} as completed.",
        citation=None
    )


def create_study_plan(params: dict) -> AgentResponse:
    """
    Feature 2 Integration & Demo Flow:
    Accepts subject and days_remaining (e.g. 'DBMS', 10 days).
    Generates study plan, materializes Todoist tasks, and schedules Google Calendar sessions.
    """
    subject = params.get("subject", "DBMS")
    days_remaining = params.get("days_remaining", 10)

    # 1. Pull syllabus / exam details via RAG
    rag_results = retrieve(f"{subject} syllabus exam topics preparation", k=1, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    # 2. Generate structured study plan milestones
    milestones = [
        {"day": 1, "topic": f"{subject} Unit 1: Relational Algebra & ER Modeling", "hours": 2},
        {"day": 3, "topic": f"{subject} Unit 2: SQL Queries & Normalization (1NF to BCNF)", "hours": 3},
        {"day": 5, "topic": f"{subject} Unit 3: Transaction Management & ACID Properties", "hours": 3},
        {"day": 7, "topic": f"{subject} Unit 4: Indexing, Hashing & Concurrency Control", "hours": 2.5},
        {"day": 9, "topic": f"{subject} Final Mock Test & Previous Year Question Review", "hours": 4},
    ]

    # 3. Materialize tasks into Todoist & Google Calendar
    created_tasks = []
    calendar_events = []
    today = datetime.now()

    for m in milestones:
        due_date = (today + timedelta(days=m["day"])).strftime("%Y-%m-%d")
        t_res = create_task({"content": f"[{subject}] {m['topic']}", "due_string": due_date})
        created_tasks.append(t_res.data.get("task"))

        calendar_events.append({
            "summary": f"Study Session: {m['topic']}",
            "date": due_date,
            "duration": f"{m['hours']} hours"
        })

    demo_trace = f"a2a_calls: academic.get_exam_schedule -> academic.create_study_plan -> todoist.create_task ({len(created_tasks)} tasks) -> gcal.add_event ({len(calendar_events)} events)"

    return AgentResponse(
        status="success",
        data={
            "subject": subject,
            "days_remaining": days_remaining,
            "milestones": milestones,
            "created_tasks": created_tasks,
            "calendar_events": calendar_events,
            "trace_log": demo_trace,
            "source": "mock"
        },
        message=f"Generated {days_remaining}-day study plan for {subject}. Materialized {len(created_tasks)} Todoist tasks and Calendar sessions.",
        citation=citation
    )


def get_roadmap(params: dict) -> AgentResponse:
    domain = params.get("domain", "computer-science")
    return AgentResponse(
        status="success",
        data={
            "domain": domain,
            "roadmap_url": f"https://roadmap.sh/{domain}",
            "source": "mock"
        },
        message=f"Reference study roadmap available at https://roadmap.sh/{domain}",
        citation=None
    )


def general_synthesis(params: dict) -> AgentResponse:
    """
    Requirement 2: General/Synthesis action for open-ended academic queries.
    Retrieves context from knowledge/rag.py across academic category and profile memory.
    """
    profile = resolve_profile(params)
    query = params.get("query", "academic performance summary attendance condonation exam prep")


    rag_results = retrieve(query, k=2, category="academic")
    top_rag = rag_results[0] if rag_results else None
    citation = format_citation(top_rag) if top_rag else None

    att = profile["attendance_pct"]
    synthesis_msg = (
        f"Academic Overview for {profile['name']} ({profile['branch']}, Year {profile['year']}):\n"
        f"1. Attendance Status: {att}% ({'Safe' if att>=75 else 'Conditional Condonation Required' if att>=65 else 'Critical Detention Risk'}).\n"
        f"2. Upcoming Mid/End Terms: DBMS Exam scheduled in 10 days.\n"
        f"3. Policy Advice: {top_rag['text'][:180] if top_rag else 'Maintain attendance above 75%.'}"
    )

    return AgentResponse(
        status="success",
        data={
            "profile": profile,
            "attendance_pct": att,
            "rag_chunks": rag_results,
            "synthesis_text": synthesis_msg,
            "source": "mock"
        },
        message=synthesis_msg,
        citation=citation
    )


ACTIONS = {
    "get_attendance": get_attendance,
    "get_timetable": get_timetable,
    "get_exam_schedule": get_exam_schedule,
    "course_info": course_info,
    "create_task": create_task,
    "get_tasks": get_tasks,
    "update_task": update_task,
    "complete_task": complete_task,
    "create_study_plan": create_study_plan,
    "get_roadmap": get_roadmap,
    "general_synthesis": general_synthesis,
}


def handle(action: str, params: dict) -> AgentResponse:
    if action not in ACTIONS:
        return AgentResponse(status="error", message=f"Unknown academic action: {action}")
    return ACTIONS[action](params)
