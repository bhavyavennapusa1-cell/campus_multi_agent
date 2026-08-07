from typing import Optional, List, Dict, Any
from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.academic_agent.repo import AcademicRepo, InMemoryAcademicRepo
from agents.adapters.todoist_adapter import TodoistAdapter
from agents.adapters.google_calendar_adapter import GoogleCalendarAdapter


class AcademicAgent:
    """
    Academic Agent
    
    Owns academic dataset & task/calendar integrations.
    Tools: get_course_info, get_timetable, check_attendance_eligibility, get_exam_schedule,
           get_regulations, recommend_electives, create_task, get_tasks, update_task, complete_task,
           create_study_plan, get_roadmap.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        repo: Optional[AcademicRepo] = None,
        todoist_adapter: Optional[TodoistAdapter] = None,
        calendar_adapter: Optional[GoogleCalendarAdapter] = None
    ):
        self.agent_name = "academic_agent"
        self.registry = registry
        self.repo: AcademicRepo = repo or InMemoryAcademicRepo()
        self.todoist_adapter = todoist_adapter or TodoistAdapter()
        self.calendar_adapter = calendar_adapter or GoogleCalendarAdapter()

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        tool_name = task.task.lower()
        student_id = task.student_id or task.params.get("student_id")
        a2a_calls: List[Dict[str, Any]] = []

        if tool_name in ["get_timetable", "check_attendance_eligibility", "get_exam_schedule"]:
            if not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "student_id is required for this operation"},
                    message=f"Missing student_id for task '{task.task}'",
                    trace_id=task.trace_id
                )
            student = self.repo.get_student(student_id)
            if not student:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": f"Student '{student_id}' not found in academic database"},
                    message=f"Invalid student_id: '{student_id}'",
                    trace_id=task.trace_id
                )

        if tool_name == "get_course_info":
            course_id = task.params.get("course_id")
            info = self.repo.get_course_info(course_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"courses": info, "source": "mock"},
                message=f"Retrieved course info for '{course_id or 'all'}'",
                trace_id=task.trace_id
            )

        elif tool_name == "get_timetable":
            timetable = self.repo.get_timetable(student_id)
            exams = self.repo.get_exam_schedule(student_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"student_id": student_id, "timetable": timetable, "exams": exams, "source": "mock"},
                message=f"Retrieved timetable and exam schedule for student {student_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "get_tasks":
            tasks_res = await self.todoist_adapter.get_tasks()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=tasks_res,
                message=f"Retrieved {len(tasks_res.get('tasks', []))} academic tasks (Source: {tasks_res.get('source')})",
                trace_id=task.trace_id
            )

        elif tool_name == "create_task":
            content = task.params.get("content") or task.params.get("title", "Study Task")
            due_string = task.params.get("due_string", "today")
            priority = int(task.params.get("priority", 1))

            task_res = await self.todoist_adapter.create_task(content, due_string, priority)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=task_res,
                message=f"Created academic task '{content}' (Source: {task_res.get('source')})",
                trace_id=task.trace_id
            )

        elif tool_name == "update_task":
            task_id = task.params.get("task_id", "t1")
            content = task.params.get("content", "Updated Task")
            upd_res = await self.todoist_adapter.update_task(task_id, content)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=upd_res,
                message=f"Updated task '{task_id}'",
                trace_id=task.trace_id
            )

        elif tool_name == "complete_task":
            task_id = task.params.get("task_id", "t1")
            comp_res = await self.todoist_adapter.complete_task(task_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=comp_res,
                message=f"Completed task '{task_id}'",
                trace_id=task.trace_id
            )

        elif tool_name == "create_study_plan":
            subject = task.params.get("subject", "Database Management Systems")
            days_left = int(task.params.get("days_left", 10))
            exam_date = task.params.get("exam_date", "2026-08-17")

            study_plan_res = await self.todoist_adapter.create_study_plan(subject, days_left, exam_date)

            gcal_event = await self.calendar_adapter.add_event_to_calendar(
                summary=f"Study Session: {subject}",
                start_time=f"{exam_date}T10:00:00Z",
                end_time=f"{exam_date}T12:00:00Z",
                location="Main Library Study Room 4"
            )

            study_plan_res["calendar_sync"] = gcal_event

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=study_plan_res,
                message=f"Generated {days_left}-day study plan for {subject} with materialized Todoist tasks and Google Calendar study session.",
                trace_id=task.trace_id
            )

        elif tool_name == "get_roadmap":
            domain = task.params.get("domain", "backend")
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={
                    "source": "mock",
                    "domain": domain,
                    "roadmap_url": f"https://roadmap.sh/{domain}",
                    "description": f"Curated interactive developer learning roadmap for {domain}."
                },
                message=f"Retrieved learning roadmap link for {domain}",
                trace_id=task.trace_id
            )

        elif tool_name == "check_attendance_eligibility":
            student = self.repo.get_student(student_id)
            attendance_pct = float(student.get("attendance_pct", 0.0))
            regulations = self.repo.get_regulations()
            min_threshold = float(regulations.get("min_attendance_threshold", 75.0))
            is_eligible = attendance_pct >= min_threshold

            res_data: Dict[str, Any] = {
                "source": "mock",
                "student_id": student_id,
                "student_name": student.get("name"),
                "attendance_pct": attendance_pct,
                "min_attendance_required": min_threshold,
                "eligible": is_eligible
            }

            if not is_eligible:
                shortfall = round(min_threshold - attendance_pct, 1)
                res_data["shortfall_pct"] = shortfall
                res_data["status_note"] = f"Attendance ({attendance_pct}%) below regulation threshold ({min_threshold}%)."

                draft_params = {
                    "recipient": "academic_dean@campus.edu",
                    "subject": f"Permission Request: Attendance Waiver / Makeup Exam - {student.get('name')} ({student_id})",
                    "body": (
                        f"Respected Dean,\n\n"
                        f"I am writing to formally request permission for makeup exams / attendance condonation. "
                        f"My current attendance stands at {attendance_pct}%, which is below the mandatory {min_threshold}% threshold. "
                        f"I request your kind consideration for a waiver based on academic regulations.\n\n"
                        f"Sincerely,\n{student.get('name')} ({student_id})"
                    )
                }

                comms_proxy = self.registry.get("communication_agent", caller_name=self.agent_name)
                comms_req = TaskRequest(
                    trace_id=task.trace_id,
                    task="draft_email",
                    params=draft_params,
                    student_id=student_id,
                    context=task.context
                )
                comms_resp = await comms_proxy.handle(comms_req)

                a2a_calls.append({
                    "caller": self.agent_name,
                    "target": "communication_agent",
                    "tool": "draft_email",
                    "params": draft_params,
                    "status": comms_resp.status,
                    "response_data": comms_resp.data
                })

                if comms_resp.status == "success":
                    res_data["email_draft"] = comms_resp.data.get("draft")
                    message = (
                        f"Student {student_id} is ineligible due to low attendance ({attendance_pct}% < {min_threshold}%). "
                        f"A permission makeup request email draft has been prepared for review."
                    )
                else:
                    message = f"Student {student_id} is ineligible due to low attendance ({attendance_pct}% < {min_threshold}%)."
            else:
                message = f"Student {student_id} meets attendance threshold ({attendance_pct}% >= {min_threshold}%)."

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success" if is_eligible else "partial",
                data=res_data,
                message=message,
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "get_exam_schedule":
            exams = self.repo.get_exam_schedule(student_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"student_id": student_id, "exams": exams, "source": "mock"},
                message=f"Retrieved exam schedule for student {student_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "get_regulations":
            regs = self.repo.get_regulations()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"regulations": regs, "source": "mock"},
                message="Retrieved academic regulations",
                trace_id=task.trace_id
            )

        elif tool_name == "recommend_electives":
            branch = task.params.get("branch")
            if not branch and student_id:
                student = self.repo.get_student(student_id)
                if student:
                    branch = student.get("branch")
            recs = self.repo.recommend_electives(branch)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"branch": branch, "recommended_electives": recs, "source": "mock"},
                message=f"Found {len(recs)} recommended electives for branch '{branch or 'all'}'",
                trace_id=task.trace_id
            )

        else:
            return ResponseEnvelope(
                agent=self.agent_name,
                status="error",
                data={"error": f"Unknown tool '{task.task}' for AcademicAgent"},
                message=f"Tool '{task.task}' is not supported by AcademicAgent",
                trace_id=task.trace_id
            )
