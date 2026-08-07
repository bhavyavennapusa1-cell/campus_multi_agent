# Campus Multi-Agent System — Structured Datasets Documentation

This directory contains the authoritative structured datasets for the Smart Campus Multi-Agent Assistant.
Each domain maintains **one shared dataset** structured cleanly as JSON records for deterministic agent retrieval and relational joining.

---

## Directory & File Structure

```
data/
├── students.json                  # Roster of active students (student_id PK)
├── academic/
│   ├── courses.json               # Course catalog (course_id PK, faculty_id FK)
│   ├── timetables.json            # Class schedules by branch, year & section
│   ├── exam_schedules.json        # CIE & SEE exam dates, times & venues
│   ├── electives.json             # Elective subjects & prerequisites
│   └── regulations.json          # Attendance, grading & backlog policy rules
├── placement/
│   ├── companies.json             # Full recruitment dataset (company_id PK)
│   └── internships.json           # Internship drives & eligibility thresholds
├── campus/
│   ├── hostel.json                # Block rules, curfew timings & warden contacts
│   ├── library.json               # Borrowing limits, hours & GD room booking rules
│   ├── transport.json             # Bus routes, drivers & pickup schedules
│   ├── scholarships.json          # Government & institutional financial aid
│   ├── grievance.json             # Complaint categories, SLA days & escalation flow
│   └── faqs.json                  # Campus FAQ records
├── events/
│   └── events.json                # Hackathons, workshops & fests (event_id PK)
└── communication/
    ├── faculty_directory.json     # Faculty details, office hours & subjects (faculty_id PK)
    ├── student_directory.json     # Student mentor & HOD mapping
    └── groups.json                # Classmates & capstone project groups
```

---

## Primary Keys & Foreign Key Relationships

| Primary Key / ID Field | Format | Primary File Location | Foreign Key References |
| :--- | :--- | :--- | :--- |
| `student_id` | `STU001`, `STU002`... | `data/students.json` | `data/communication/student_directory.json`, `data/communication/groups.json` |
| `faculty_id` | `FAC100`, `FAC101`... | `data/communication/faculty_directory.json` | `data/academic/courses.json`, `data/events/events.json`, `data/communication/groups.json` |
| `course_id` | `CS301`, `EC201`... | `data/academic/courses.json` | `data/academic/timetables.json`, `data/academic/exam_schedules.json` |
| `company_id` | `COMP01`, `COMP02`...| `data/placement/companies.json` | `data/placement/internships.json` |
| `event_id` | `EVT101`, `EVT102`... | `data/events/events.json` | `knowledge/docs/upcoming_events_and_hackathons.md` |
| `scholarship_id` | `SCH201`, `SCH202`...| `data/campus/scholarships.json` | `knowledge/docs/scholarships_guide.md` |

---

## Dataset Schema Specifications

### 1. `data/students.json` & `data/communication/student_directory.json`
- `student_id` (string): Unique identifier (e.g. `"STU001"`).
- `name` (string): Full student name.
- `branch` (string): Academic department (`"CSE"`, `"ECE"`, `"IT"`, `"MECH"`, `"CIVIL"`).
- `year` (integer): Current academic year (1 to 4).
- `semester` (integer): Current semester (1 to 8).
- `section` (string): Section identifier (`"A"`, `"B"`, `"C"`).
- `cgpa` (float): Cumulative Grade Point Average (0.0 to 10.0).
- `backlog_count` (integer): Number of active backlogs.
- `attendance_pct` (float): Aggregate attendance percentage.
- `mentor_id` (string): Foreign key resolving to `faculty_directory.json`.
- `hod_id` (string): Foreign key resolving to `faculty_directory.json`.

### 2. `data/academic/courses.json`
- `course_id` (string): Subject ID (e.g. `"CS301"`).
- `code` (string): Official subject code (e.g. `"CS301PC"`).
- `name` (string): Full course title.
- `department` (string): Offering department.
- `credits` (integer): Course credit points.
- `faculty_id` (string): Foreign key resolving to `faculty_directory.json`.

### 3. `data/placement/companies.json`
- `company_id` (string): Company identifier (e.g. `"COMP01"`).
- `company_name` (string): Name of recruiting organization.
- `tier` (string): Recruitment tier (`"Dream Tier"`, `"Core Tier"`, `"Mass Tier"`).
- `role` (string): Job profile title.
- `min_cgpa` (float): Minimum CGPA requirement.
- `min_attendance` (float): Minimum attendance threshold.
- `max_backlogs` (integer): Maximum active backlogs permitted.
- `eligible_branches` (array of strings): Eligible engineering branches.
- `ctc_lpa` (float): Package in Lakhs Per Annum.
- `interview_process` (array of strings): Step-by-step interview rounds.
- `resume_tips` (array of strings): Specific tips for applicant resumes.

### 4. `data/events/events.json`
- `event_id` (string): Unique event identifier (e.g. `"EVT101"`).
- `title` (string): Event name.
- `category` (string): Type (`"workshop"`, `"hackathon"`, `"cultural"`).
- `capacity` (integer): Maximum participant capacity.
- `registered_count` (integer): Current registration tally.
- `registration_status` (string): Status (`"open"`, `"closed"`).
- `team_info` (object): Minimum team size, maximum team size, max teams.

---

## Instructions for Agent Integration

Specialized agents can query these structured JSON datasets directly:
- **Academic Agent**: Loads `data/academic/courses.json`, `data/academic/timetables.json`, `data/academic/exam_schedules.json`, `data/academic/regulations.json`.
- **Placement Agent**: Loads `data/placement/companies.json` and `data/placement/internships.json`.
- **Campus Agent**: Loads `data/campus/hostel.json`, `data/campus/library.json`, `data/campus/transport.json`, `data/campus/scholarships.json`, `data/campus/grievance.json`, `data/events/events.json`.
- **Communication Agent**: Loads `data/communication/faculty_directory.json`, `data/communication/student_directory.json`, `data/communication/groups.json`.
