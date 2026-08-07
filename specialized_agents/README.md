# Smart Campus Multi-Agent System — 4 Specialized Backend Agents

Backend infrastructure for 4 specialized agents in a Smart Campus Multi-Agent AI System built for the **AgentX Hackathon**. This package implements real, non-simulated agent-to-agent (A2A) function calls with structured JSON trace logs, depth capping, graceful degradation, standard IO envelopes, and decoupled swappable repository layers.

---

## Deliverable Structure

```
agents/
├── common/
│   ├── envelope.py          # TaskRequest & ResponseEnvelope schemas + AgentClient Protocol
│   └── registry.py          # AgentRegistry, A2A Proxy, call depth guard (cap=3), JSON trace logger
├── fixtures/
│   ├── academic_data.json   # Attendance, timetables, regulations, courses
│   ├── placement_data.json  # Companies, eligibility specs, resume benchmarks
│   ├── campus_data.json     # Events, student services, navigator locations
│   └── comms_data.json      # Communications shared log (emails, notifications, reminders)
├── academic_agent/
│   ├── repo.py              # AcademicRepo Protocol + InMemoryAcademicRepo fallback
│   └── agent.py             # AcademicAgent implementation
├── placement_agent/
│   ├── repo.py              # PlacementRepo Protocol + InMemoryPlacementRepo fallback
│   └── agent.py             # PlacementAgent implementation
├── campus_agent/
│   ├── repo.py              # CampusRepo Protocol + InMemoryCampusRepo fallback
│   └── agent.py             # CampusAgent mini-orchestrator (Events, Services, Navigator)
├── communication_agent/
│   ├── repo.py              # CommsRepo Protocol + InMemoryCommsRepo fallback
│   └── agent.py             # CommunicationAgent implementation (Leaf Node)
├── tests/
│   └── test_workflows.py   # Executable integration tests for the 3 demo workflows
├── requirements.txt
└── README.md
```

---

## Key Architectural Highlights & Judging Criteria Alignment

> [!IMPORTANT]
> **1. Swappable Repositories & Databases**:
> Agents do NOT own hardcoded dataset logic. Each agent depends strictly on a Python Protocol / ABC (`AcademicRepo`, `PlacementRepo`, `CampusRepo`, `CommsRepo`). The `InMemory<Name>Repo` classes load sample JSON data from `fixtures/` solely for standalone demo execution. Wiring a teammate's SQL database requires swapping one constructor parameter (`repo=PostgreSQLAcademicRepo()`), leaving agent business logic 100% untouched.

> [!TIP]
> **2. Swappable Agent-to-Agent (A2A) / MCP Transport**:
> All agents expose a single entrypoint: `async def handle(self, task: TaskRequest) -> ResponseEnvelope`.
> In-process agent calls are routed via `AgentRegistry` which wraps invocations in `A2AClientProxy`. The `AgentClient` protocol allows replacing the in-process registry with an HTTP/REST microservice, gRPC, or MCP message bus without modifying agent logic.

> [!NOTE]
> **3. Structured JSON Trace Logs & Depth Guard**:
> Every A2A call emits structured JSON trace lines containing `trace_id`, `caller`, `target`, `tool`, `input`, `output_status`, and `latency_ms`. Call depth is capped at 3 to prevent accidental circular loops.

---

## Agent Tool Registry Summary

| Agent | Module / Tools | Summary Description |
|---|---|---|
| **Academic Agent** | `get_course_info`<br>`get_timetable`<br>`check_attendance_eligibility`<br>`get_exam_schedule`<br>`get_regulations`<br>`recommend_electives` | Owns academic data (attendance %, exam schedule, course info). Proactively calls `communication_agent.draft_email` if attendance is < 75%. |
| **Placement Agent** | `list_opportunities`<br>`check_eligibility`<br>`check_all_company_eligibility`<br>`analyze_resume`<br>`get_interview_prep`<br>`get_placement_notifications` | Evaluates company drive eligibility. MUST call `academic_agent.check_attendance_eligibility` first (low attendance invalidates eligibility regardless of CGPA). Calls `communication_agent` on drive registration. |
| **Campus Agent** | *Events Sub-Module*:<br>`discover_events`, `register_for_event`, `manage_hackathon_team`, `create_calendar_entry`, `cancel_or_withdraw`, `recommend_events`<br><br>*Student Services Sub-Module*:<br>`get_hostel_info`, `get_library_status`, `check_scholarship_eligibility`, `get_transport_info`, `raise_grievance`, `search_campus_faqs`<br><br>*Campus Navigator Sub-Module*:<br>`get_campus_map`, `search_location`, `get_directions`, `get_nearby_facilities`, `get_indoor_wayfinding`, `get_accessible_route` | Mini-orchestrator that routes internally across 3 sub-modules. `register_for_event` calls `academic_agent.get_timetable` to check for exam/class clashes (returning `status: "needs_clarification"` if a clash occurs) and calls `communication_agent` for reminders. `raise_grievance` calls `communication_agent.send_notification`. |
| **Communication Agent** | `draft_email`<br>`send_notification`<br>`generate_announcement`<br>`schedule_appointment`<br>`update_or_cancel_entry`<br>`schedule_reminder` | Leaf node owning the shared communication log (drafts, sent notifications, reminders, appointments). Never makes outward calls to avoid call cycles. |

---

## Mandatory Demo Workflows

The system includes executable integration tests for all 3 demo workflows:

1. **Workflow 1: Placement Eligibility & Workshop Registration**
   - Student (`STU001`) checks Google internship eligibility -> Placement Agent calls Academic Agent for attendance check (OK: 82.5%) -> Student registers for placement workshop via Campus Events -> Events calls Academic Agent for timetable clash check (Clear) -> Events calls Communication Agent for appointment & 60-min reminder -> Single consolidated envelope returned.
2. **Workflow 2: Attendance Shortfall & Automated Email Draft**
   - Student (`STU002`, 68.0% attendance < 75%) checks exam permission -> Academic Agent detects shortfall -> Academic Agent calls Communication Agent `draft_email` -> Returns envelope with eligibility shortfall and email draft.
3. **Workflow 3: Event Registration Timetable Conflict Handling**
   - Student (`STU003`) registers for AI/ML Hackathon -> Campus Events calls Academic Agent `get_timetable` -> Detects overlap with scheduled Midterm Exam -> Returns `status: "needs_clarification"` with conflict details explained.

---

## How to Run

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All 3 Workflows & Tests via Pytest
```bash
pytest -v agents/tests/test_workflows.py
```

### Run Demo Workflows Directly (Prints JSON Traces & Envelopes)
```bash
python -m agents.tests.test_workflows
```

---

## Sample Structured JSON Trace Output

```json
{"event": "A2A_CALL", "trace_id": "trace-9a1b2c3d", "caller": "placement_agent", "target": "academic_agent", "tool": "check_attendance_eligibility", "input": {"student_id": "STU001"}, "output_status": "success", "output_data_summary": {"student_id": "STU001", "student_name": "John Doe", "attendance_pct": 82.5, "min_attendance_required": 75.0, "eligible": true}, "latency_ms": 1.25}
{"event": "A2A_CALL", "trace_id": "trace-9a1b2c3d", "caller": "campus_agent", "target": "academic_agent", "tool": "get_timetable", "input": {"student_id": "STU001"}, "output_status": "success", "output_data_summary": {"student_id": "STU001"}, "latency_ms": 0.89}
{"event": "A2A_CALL", "trace_id": "trace-9a1b2c3d", "caller": "campus_agent", "target": "communication_agent", "tool": "schedule_appointment", "input": {"title": "Event: Google Placement & Resume Workshop", "date": "2026-08-08"}, "output_status": "success", "output_data_summary": {"appointment": {"appointment_id": "APPT-401"}}, "latency_ms": 0.74}
```
