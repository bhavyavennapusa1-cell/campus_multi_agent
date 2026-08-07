"""
Shared Data Store for Smart Campus Multi-Agent System.
Loads and caches structured JSON datasets from data/ once at import time.
Provides generic get_by_id(collection, id) helper and domain-specific query helpers.
Fails gracefully with logging and empty/None returns if any file is missing or malformed.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("data_store")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Primary key field preference order when matching by ID
PK_FIELDS = [
    "student_id",
    "faculty_id",
    "course_id",
    "company_id",
    "event_id",
    "exam_id",
    "scholarship_id",
    "group_id",
    "class_id",
]

_CACHE: Dict[str, Any] = {}


def _load_json_file(file_path: Path) -> Any:
    """Safely loads a JSON file, returning empty dict/list if missing or invalid."""
    if not file_path.exists():
        logger.warning(f"Data file missing: {file_path}")
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error parsing JSON file {file_path}: {e}")
        return None


def init_data_store() -> None:
    """Loads and caches all structured datasets from data/ directory."""
    global _CACHE
    _CACHE.clear()

    # 1. Students dataset
    students_data = _load_json_file(DATA_DIR / "students.json")
    _CACHE["students"] = students_data.get("students", []) if isinstance(students_data, dict) else []

    # 2. Academic datasets
    courses_data = _load_json_file(DATA_DIR / "academic" / "courses.json")
    _CACHE["courses"] = courses_data.get("courses", []) if isinstance(courses_data, dict) else []

    timetables_data = _load_json_file(DATA_DIR / "academic" / "timetables.json")
    _CACHE["timetables"] = timetables_data.get("timetables", []) if isinstance(timetables_data, dict) else []

    exams_data = _load_json_file(DATA_DIR / "academic" / "exam_schedules.json")
    _CACHE["exam_schedules"] = exams_data.get("exam_schedules", []) if isinstance(exams_data, dict) else []

    electives_data = _load_json_file(DATA_DIR / "academic" / "electives.json")
    _CACHE["electives"] = electives_data.get("electives", []) if isinstance(electives_data, dict) else []

    regs_data = _load_json_file(DATA_DIR / "academic" / "regulations.json")
    _CACHE["regulations"] = regs_data if isinstance(regs_data, dict) else {}

    # 3. Placement datasets
    companies_data = _load_json_file(DATA_DIR / "placement" / "companies.json")
    _CACHE["companies"] = companies_data.get("companies", []) if isinstance(companies_data, dict) else []

    internships_file = DATA_DIR / "placement" / "internships.json"
    if not internships_file.exists():
        internships_file = DATA_DIR / "internships.json"
    internships_data = _load_json_file(internships_file)
    _CACHE["internships"] = internships_data.get("internships", []) if isinstance(internships_data, dict) else []

    # 4. Communication datasets
    faculty_data = _load_json_file(DATA_DIR / "communication" / "faculty_directory.json")
    _CACHE["faculty"] = faculty_data.get("faculty", []) if isinstance(faculty_data, dict) else []

    student_dir_data = _load_json_file(DATA_DIR / "communication" / "student_directory.json")
    _CACHE["student_directory"] = student_dir_data.get("students", []) if isinstance(student_dir_data, dict) else []

    groups_data = _load_json_file(DATA_DIR / "communication" / "groups.json") or {}
    _CACHE["classrooms"] = groups_data.get("classrooms", [])
    _CACHE["project_groups"] = groups_data.get("project_groups", [])

    # 5. Campus datasets
    for campus_item in ["hostel", "library", "transport", "scholarships", "grievance", "faqs"]:
        item_data = _load_json_file(DATA_DIR / "campus" / f"{campus_item}.json")
        _CACHE[campus_item] = item_data if item_data else {}

    # 6. Events dataset
    events_file = DATA_DIR / "events" / "events.json"
    if not events_file.exists():
        events_file = DATA_DIR / "events.json"
    events_data = _load_json_file(events_file)
    _CACHE["events"] = events_data.get("events", []) if isinstance(events_data, dict) else []

    logger.info("DataStore initialized and all datasets cached.")


# Run automatic initialization on import
init_data_store()


def get_collection(collection: str) -> Any:
    """Returns raw collection dataset from cache, or empty list/dict."""
    return _CACHE.get(collection, [] if collection not in ["regulations", "hostel", "library", "transport", "scholarships", "grievance", "faqs"] else {})


def get_by_id(collection: str, entity_id: str) -> Optional[Dict[str, Any]]:
    """
    Generic lookup: finds an item in the specified collection matching entity_id
    across known primary key fields.
    """
    if not entity_id:
        return None

    data = _CACHE.get(collection)
    if not data or not isinstance(data, list):
        return None

    target_str = str(entity_id).strip().lower()

    for item in data:
        if not isinstance(item, dict):
            continue
        for pk in PK_FIELDS:
            if pk in item:
                val = str(item[pk]).strip().lower()
                if val == target_str:
                    return item

    return None


def get_student(student_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Finds a student record by student_id or full name."""
    if not student_id_or_name:
        return None

    target = str(student_id_or_name).strip().lower()

    # Try student_id exact match first
    res = get_by_id("students", student_id_or_name)
    if res:
        return res

    # Search by student_id or name
    for stu in _CACHE.get("students", []):
        if stu.get("student_id", "").lower() == target or stu.get("name", "").lower() == target:
            return stu
        if target in stu.get("name", "").lower():
            return stu

    return None


def get_company(company_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Finds a recruiting company by company_id or company_name."""
    if not company_id_or_name:
        return None

    target = str(company_id_or_name).strip().lower()

    # Try company_id match first
    res = get_by_id("companies", company_id_or_name)
    if res:
        return res

    # Match by company_name
    for comp in _CACHE.get("companies", []):
        c_name = comp.get("company_name", "").lower()
        if c_name == target or target in c_name or c_name in target:
            return comp

    return None


def get_faculty(faculty_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Finds a faculty record by faculty_id or name."""
    if not faculty_id_or_name:
        return None

    target = str(faculty_id_or_name).strip().lower()

    res = get_by_id("faculty", faculty_id_or_name)
    if res:
        return res

    for fac in _CACHE.get("faculty", []):
        f_name = fac.get("name", "").lower()
        if fac.get("faculty_id", "").lower() == target or f_name == target or target in f_name:
            return fac

    return None


def get_timetable(branch: str, year: int, section: str = "A") -> Optional[Dict[str, Any]]:
    """Finds timetable for a given branch, year, and section."""
    branch_clean = str(branch).split("-")[0].strip().upper()
    try:
        year_num = int(year)
    except (ValueError, TypeError):
        year_num = 3

    section_clean = str(section).strip().upper() if section else "A"

    for tt in _CACHE.get("timetables", []):
        if (
            tt.get("branch", "").upper() == branch_clean
            and int(tt.get("year", 0)) == year_num
            and tt.get("section", "").upper() == section_clean
        ):
            return tt

    # Fallback match by branch & year if section doesn't match
    for tt in _CACHE.get("timetables", []):
        if tt.get("branch", "").upper() == branch_clean and int(tt.get("year", 0)) == year_num:
            return tt

    return None


def get_exam_schedules_for_student(branch: str = "CSE", year: int = 3) -> List[Dict[str, Any]]:
    """Returns exam schedule records matching student courses/department."""
    exams = _CACHE.get("exam_schedules", [])
    courses = _CACHE.get("courses", [])

    branch_clean = str(branch).split("-")[0].strip().upper()

    # Find course IDs for branch
    branch_course_ids = {
        c["course_id"] for c in courses
        if c.get("department", "").upper() == branch_clean
    }

    if not branch_course_ids:
        return exams

    filtered = [e for e in exams if e.get("course_id") in branch_course_ids]
    return filtered if filtered else exams


def get_student_directory_record(student_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Gets mapping details (mentor_id, hod_id) from communication/student_directory.json."""
    if not student_id_or_name:
        return None

    target = str(student_id_or_name).strip().lower()

    for s in _CACHE.get("student_directory", []):
        if s.get("student_id", "").lower() == target or s.get("name", "").lower() == target or target in s.get("name", "").lower():
            return s

    return None
