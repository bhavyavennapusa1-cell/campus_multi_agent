"""
Tool Manifest for Orchestrator Integration.
Exposes complete list of tools across all agents with parameters and descriptions.
Used by Uday's Orchestrator to dynamically register and plan tool invocations.
"""
from typing import Dict, Any, List

TOOL_MANIFEST: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # ACADEMIC AGENT TOOLS
    # -------------------------------------------------------------------------
    {
        "agent": "academic_agent",
        "tool": "get_course_info",
        "description": "Retrieves course details, credits, instructor, and slot by course_id.",
        "params": {"course_id": "Optional string, e.g. CS101"}
    },
    {
        "agent": "academic_agent",
        "tool": "get_timetable",
        "description": "Retrieves class timetable and upcoming exam schedule for a student.",
        "params": {"student_id": "Required string, e.g. STU001"}
    },
    {
        "agent": "academic_agent",
        "tool": "check_attendance_eligibility",
        "description": "Checks student attendance % against regulation threshold (75%). Drafts makeup email if shortfall occurs.",
        "params": {"student_id": "Required string, e.g. STU001"}
    },
    {
        "agent": "academic_agent",
        "tool": "get_exam_schedule",
        "description": "Retrieves scheduled exams for a student.",
        "params": {"student_id": "Required string, e.g. STU001"}
    },
    {
        "agent": "academic_agent",
        "tool": "get_regulations",
        "description": "Retrieves academic rules, grading policies, and attendance thresholds.",
        "params": {}
    },
    {
        "agent": "academic_agent",
        "tool": "recommend_electives",
        "description": "Recommends elective courses based on branch and academic record.",
        "params": {"branch": "Optional branch string"}
    },
    {
        "agent": "academic_agent",
        "tool": "create_task",
        "description": "Creates a study/academic task via Todoist API integration.",
        "params": {"content": "Task title string", "due_string": "Due date string", "priority": "Integer 1-4"}
    },
    {
        "agent": "academic_agent",
        "tool": "get_tasks",
        "description": "Retrieves active academic study tasks via Todoist integration.",
        "params": {}
    },
    {
        "agent": "academic_agent",
        "tool": "create_study_plan",
        "description": "Generates a structured multi-day study plan, materializing tasks in Todoist and Google Calendar.",
        "params": {"subject": "Subject name", "days_left": "Number of days", "exam_date": "YYYY-MM-DD"}
    },
    {
        "agent": "academic_agent",
        "tool": "get_roadmap",
        "description": "Returns interactive developer learning roadmap link (roadmap.sh).",
        "params": {"domain": "Developer domain, e.g. backend, frontend, ai"}
    },

    # -------------------------------------------------------------------------
    # PLACEMENT AGENT TOOLS
    # -------------------------------------------------------------------------
    {
        "agent": "placement_agent",
        "tool": "list_opportunities",
        "description": "Lists placement drives and internship opportunities via Jobs API adapter.",
        "params": {"query": "Search query"}
    },
    {
        "agent": "placement_agent",
        "tool": "check_eligibility",
        "description": "Checks student eligibility for a company. Calls Academic Agent for attendance check first.",
        "params": {"company_id": "Company ID or name", "student_id": "Required student ID"}
    },
    {
        "agent": "placement_agent",
        "tool": "get_github_profile",
        "description": "Fetches developer profile, public repos, and top skills via GitHub REST API.",
        "params": {"username": "GitHub username string"}
    },
    {
        "agent": "placement_agent",
        "tool": "get_coding_platforms",
        "description": "Retrieves student competitive coding profiles (LeetCode, CodeChef, HackerRank).",
        "params": {"student_id": "Student ID"}
    },
    {
        "agent": "placement_agent",
        "tool": "get_courses",
        "description": "Retrieves online course progress tracking (Coursera, Udemy, NPTEL).",
        "params": {"student_id": "Student ID"}
    },
    {
        "agent": "placement_agent",
        "tool": "analyze_resume",
        "description": "Analyzes resume skill list against target benchmarks.",
        "params": {"skills": "List of skill strings"}
    },

    # -------------------------------------------------------------------------
    # CAMPUS AGENT TOOLS (Events, Student Services, Navigator)
    # -------------------------------------------------------------------------
    {
        "agent": "campus_agent",
        "tool": "discover_events",
        "description": "Lists campus events, hackathons, and workshops.",
        "params": {"category": "Optional category string"}
    },
    {
        "agent": "campus_agent",
        "tool": "register_for_event",
        "description": "Registers for an event. Performs timetable clash check via Academic Agent first.",
        "params": {"event_id": "Event ID", "student_id": "Student ID"}
    },
    {
        "agent": "campus_agent",
        "tool": "get_hostel_info",
        "description": "Retrieves student hostel room, warden contact, and mess timings.",
        "params": {"student_id": "Student ID"}
    },
    {
        "agent": "campus_agent",
        "tool": "raise_grievance",
        "description": "Creates a grievance ticket and dispatches confirmation notification.",
        "params": {"student_id": "Student ID", "category": "Category", "description": "Details"}
    },
    {
        "agent": "campus_agent",
        "tool": "get_directions",
        "description": "Calculates directions between locations (uses Campus DB for indoor, Google Maps API for outdoor/off-campus).",
        "params": {"origin": "Origin location", "destination": "Destination location"}
    },

    # -------------------------------------------------------------------------
    # COMMUNICATION AGENT TOOLS
    # -------------------------------------------------------------------------
    {
        "agent": "communication_agent",
        "tool": "get_relevant_contacts",
        "description": "Searches campus contacts (classmates, faculty, HOD, subject teachers) via read-only ContactsRepo interface.",
        "params": {"student_id": "Student ID", "query_type": "'classmates'|'faculty'|'hod'|'subject_teacher'", "subject": "Optional subject string"}
    },
    {
        "agent": "communication_agent",
        "tool": "create_chat_group",
        "description": "Creates a temporary or permanent chat group in operational SQLite database.",
        "params": {"group_name": "Group title", "member_ids": "List of member IDs", "group_type": "'temporary'|'permanent'", "duration_hours": "Optional hours"}
    },
    {
        "agent": "communication_agent",
        "tool": "draft_official_email",
        "description": "Drafts an official email with student context. Returns draft with requires_user_approval: True for human approval.",
        "params": {"recipient_email": "Recipient email", "subject": "Subject line", "core_message": "Core message text"}
    },
    {
        "agent": "communication_agent",
        "tool": "schedule_appointment",
        "description": "Schedules a calendar appointment with Google Calendar API sync.",
        "params": {"title": "Title", "date": "YYYY-MM-DD", "time": "HH:MM-HH:MM", "location": "Location"}
    },
    {
        "agent": "communication_agent",
        "tool": "schedule_reminder",
        "description": "Schedules an event reminder with lead time and Google Calendar sync.",
        "params": {"title": "Title", "event_time": "YYYY-MM-DD HH:MM:SS", "lead_time_minutes": "Lead time integer"}
    }
]


def get_tool_manifest() -> List[Dict[str, Any]]:
    """Returns full tool manifest array for Orchestrator registration."""
    return TOOL_MANIFEST
