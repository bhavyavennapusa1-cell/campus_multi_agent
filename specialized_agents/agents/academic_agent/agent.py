from typing import Optional, List, Dict, Any
from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.academic_agent.repo import AcademicRepo, InMemoryAcademicRepo


class AcademicAgent:
    """
    Academic Agent
    
    Owns academic dataset (courses, attendance %, exam schedule, min-attendance rules).
    Tools: get_course_info, get_timetable, check_attendance_eligibility, get_exam_schedule, get_regulations, recommend_electives.
    
    A2A Interactions:
    - Called by Placement Agent: check_eligibility -> calls check_attendance_eligibility.
    - Called by Campus Agent (Events sub-module): register_for_event -> calls get_timetable to check for clashes.
    - Calls Communication Agent: check_attendance_eligibility proactively calls draft_email if attendance < 75%.
    """

    def __init__(self, registry: AgentRegistry, repo: Optional[AcademicRepo] = None):
        self.agent_name = "academic_agent"
        self.registry = registry
        self.repo: AcademicRepo = repo or InMemoryAcademicRepo()

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        tool_name = task.task.lower()
        student_id = task.student_id or task.params.get("student_id")
        a2a_calls: List[Dict[str, Any]] = []

        # Validate student existence for student-specific tools
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
                data={"courses": info},
                message=f"Retrieved course info for '{course_id or 'all'}'",
                trace_id=task.trace_id
            )

        elif tool_name == "get_timetable":
            timetable = self.repo.get_timetable(student_id)
            exams = self.repo.get_exam_schedule(student_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={
                    "student_id": student_id,
                    "timetable": timetable,
                    "exams": exams
                },
                message=f"Retrieved timetable and exam schedule for student {student_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "check_attendance_eligibility":
            student = self.repo.get_student(student_id)
            attendance_pct = float(student.get("attendance_pct", 0.0))
            regulations = self.repo.get_regulations()
            min_threshold = float(regulations.get("min_attendance_threshold", 75.0))
            is_eligible = attendance_pct >= min_threshold

            res_data: Dict[str, Any] = {
                "student_id": student_id,
                "student_name": student.get("name"),
                "attendance_pct": attendance_pct,
                "min_attendance_required": min_threshold,
                "eligible": is_eligible
            }

            # REQUIREMENT: If attendance < 75%, proactively call Communication Agent to draft makeup email
            if not is_eligible:
                shortfall = round(min_threshold - attendance_pct, 1)
                res_data["shortfall_pct"] = shortfall
                res_data["status_note"] = f"Attendance ({attendance_pct}%) below regulation threshold ({min_threshold}%)."

                # Proactive A2A call to Communication Agent to draft email
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
                data={"student_id": student_id, "exams": exams},
                message=f"Retrieved exam schedule for student {student_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "get_regulations":
            regs = self.repo.get_regulations()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"regulations": regs},
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
                data={"branch": branch, "recommended_electives": recs},
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
