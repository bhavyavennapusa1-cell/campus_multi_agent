from typing import Optional, List, Dict, Any
from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.placement_agent.repo import PlacementRepo, InMemoryPlacementRepo
from agents.adapters.github_adapter import GitHubAdapter
from agents.adapters.jobs_adapter import JobsAdapter


class PlacementAgent:
    """
    Placement Agent
    
    Owns placement dataset & job/profile integrations.
    Tools: list_opportunities, check_eligibility, check_all_company_eligibility, analyze_resume,
           get_interview_prep, get_placement_notifications, get_github_profile, get_coding_platforms, get_courses.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        repo: Optional[PlacementRepo] = None,
        github_adapter: Optional[GitHubAdapter] = None,
        jobs_adapter: Optional[JobsAdapter] = None
    ):
        self.agent_name = "placement_agent"
        self.registry = registry
        self.repo: PlacementRepo = repo or InMemoryPlacementRepo()
        self.github_adapter = github_adapter or GitHubAdapter()
        self.jobs_adapter = jobs_adapter or JobsAdapter()

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        tool_name = task.task.lower()
        student_id = task.student_id or task.params.get("student_id")
        a2a_calls: List[Dict[str, Any]] = []

        if tool_name in ["list_opportunities", "find_opportunities"]:
            query = task.params.get("query", "Software Engineering")
            jobs_res = await self.jobs_adapter.find_opportunities(query=query)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"opportunities": jobs_res.get("opportunities", []), "source": jobs_res.get("source", "mock")},
                message=f"Found {len(jobs_res.get('opportunities', []))} placement opportunities (Source: {jobs_res.get('source')})",
                trace_id=task.trace_id
            )

        elif tool_name == "get_github_profile":
            username = task.params.get("username") or task.params.get("github_username") or "octocat"
            gh_res = await self.github_adapter.get_github_profile(username)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=gh_res,
                message=f"Retrieved GitHub developer profile for '{username}' (Source: {gh_res.get('source')})",
                trace_id=task.trace_id
            )

        elif tool_name == "get_coding_platforms":
            coding_data = {
                "source": "mock",
                "student_id": student_id or "STU001",
                "platforms": [
                    {"platform": "LeetCode", "username": f"{student_id}_coder", "problems_solved": 245, "rating": 1820},
                    {"platform": "CodeChef", "username": f"{student_id}_chef", "rating": 1740, "stars": "3-Star"},
                    {"platform": "HackerRank", "username": f"{student_id}_hr", "badges": ["5-Star Problem Solving", "4-Star Python"]}
                ]
            }
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=coding_data,
                message="Retrieved coding platform profiles",
                trace_id=task.trace_id
            )

        elif tool_name == "get_courses":
            courses_data = {
                "source": "mock",
                "student_id": student_id or "STU001",
                "courses": [
                    {"course": "Deep Learning Specialization", "platform": "Coursera", "status": "Completed", "progress_pct": 100},
                    {"course": "Full-Stack Web Development", "platform": "Udemy", "status": "In-Progress", "progress_pct": 75},
                    {"course": "Database Management Systems", "platform": "NPTEL", "status": "Completed", "progress_pct": 100}
                ]
            }
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=courses_data,
                message="Retrieved online course tracking details",
                trace_id=task.trace_id
            )

        elif tool_name == "check_eligibility":
            company_query = task.params.get("company_id") or task.params.get("company_name") or task.params.get("company")
            if not company_query or not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "company_id and student_id required"},
                    message="Missing parameters for check_eligibility",
                    trace_id=task.trace_id
                )

            opportunity = self.repo.get_opportunity(company_query)
            if not opportunity:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": f"Company/Opportunity '{company_query}' not found"},
                    message=f"Unknown opportunity: '{company_query}'",
                    trace_id=task.trace_id
                )

            academic_proxy = self.registry.get("academic_agent", caller_name=self.agent_name)
            acad_req = TaskRequest(
                trace_id=task.trace_id,
                task="check_attendance_eligibility",
                params={"student_id": student_id},
                student_id=student_id,
                context=task.context
            )
            acad_resp = await academic_proxy.handle(acad_req)

            a2a_calls.append({
                "caller": self.agent_name,
                "target": "academic_agent",
                "tool": "check_attendance_eligibility",
                "params": {"student_id": student_id},
                "status": acad_resp.status,
                "response_data": acad_resp.data,
                "sub_a2a_calls": acad_resp.a2a_calls
            })

            if acad_resp.status in ["error", "partial"]:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status=acad_resp.status,
                    data={"error": f"Failed attendance check from Academic Agent: {acad_resp.message}", **acad_resp.data},
                    message=f"Could not verify student eligibility due to downstream service issue: {acad_resp.message}",
                    a2a_calls=a2a_calls,
                    trace_id=task.trace_id
                )

            acad_data = acad_resp.data
            attendance_eligible = acad_data.get("eligible", False)
            attendance_pct = acad_data.get("attendance_pct", 0.0)

            student_cgpa = task.params.get("cgpa")
            student_branch = task.params.get("branch")
            student_backlogs = task.params.get("backlogs")

            reasons: List[str] = []
            cgpa_ok = True
            branch_ok = True
            backlogs_ok = True

            min_cgpa = opportunity.get("min_cgpa", 0.0)
            allowed_branches = opportunity.get("allowed_branches", [])
            max_backlogs = opportunity.get("max_backlogs", 0)

            if student_cgpa is not None and float(student_cgpa) < min_cgpa:
                cgpa_ok = False
                reasons.append(f"CGPA ({student_cgpa}) below required minimum ({min_cgpa}).")

            if student_branch and allowed_branches and student_branch not in allowed_branches:
                branch_ok = False
                reasons.append(f"Branch '{student_branch}' not in eligible branches: {allowed_branches}.")

            if student_backlogs is not None and int(student_backlogs) > max_backlogs:
                backlogs_ok = False
                reasons.append(f"Active backlogs ({student_backlogs}) exceed maximum allowed ({max_backlogs}).")

            if not attendance_eligible:
                reasons.append(f"Attendance ({attendance_pct}%) is below minimum academic threshold ({acad_data.get('min_attendance_required', 75.0)}%).")

            overall_eligible = attendance_eligible and cgpa_ok and branch_ok and backlogs_ok

            result_data = {
                "source": "mock",
                "student_id": student_id,
                "company_id": opportunity.get("company_id"),
                "company_name": opportunity.get("company_name"),
                "role": opportunity.get("role"),
                "eligible": overall_eligible,
                "attendance_check": {
                    "eligible": attendance_eligible,
                    "attendance_pct": attendance_pct,
                    "required_pct": acad_data.get("min_attendance_required", 75.0)
                },
                "criteria_checks": {
                    "cgpa_ok": cgpa_ok,
                    "branch_ok": branch_ok,
                    "backlogs_ok": backlogs_ok
                },
                "rejection_reasons": reasons if not overall_eligible else []
            }

            msg = (
                f"Student {student_id} IS ELIGIBLE for {opportunity.get('company_name')} ({opportunity.get('role')})."
                if overall_eligible
                else f"Student {student_id} IS NOT ELIGIBLE for {opportunity.get('company_name')}. Reasons: {'; '.join(reasons)}"
            )

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=result_data,
                message=msg,
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "check_all_company_eligibility":
            if not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "student_id parameter is required"},
                    message="Missing student_id for check_all_company_eligibility",
                    trace_id=task.trace_id
                )

            all_opps = self.repo.list_opportunities()
            evaluations = []

            for opp in all_opps:
                sub_task = TaskRequest(
                    trace_id=task.trace_id,
                    task="check_eligibility",
                    params={"company_id": opp["company_id"], "cgpa": task.params.get("cgpa"), "branch": task.params.get("branch")},
                    student_id=student_id,
                    context=task.context
                )
                res = await self.handle(sub_task)
                evaluations.append(res.data)
                a2a_calls.extend(res.a2a_calls)

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"student_id": student_id, "evaluations": evaluations, "source": "mock"},
                message=f"Evaluated student {student_id} against {len(all_opps)} placement opportunities.",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name in ["register_for_opportunity", "register_for_drive"]:
            company_query = task.params.get("company_id") or task.params.get("company_name")
            if not company_query or not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "company_id and student_id required"},
                    message="Missing parameters for drive registration",
                    trace_id=task.trace_id
                )

            eligibility_req = TaskRequest(
                trace_id=task.trace_id,
                task="check_eligibility",
                params={"company_id": company_query, "cgpa": task.params.get("cgpa"), "branch": task.params.get("branch")},
                student_id=student_id,
                context=task.context
            )
            eligibility_resp = await self.handle(eligibility_req)
            a2a_calls.extend(eligibility_resp.a2a_calls)

            if not eligibility_resp.data.get("eligible", False):
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "Student ineligible for drive registration", "details": eligibility_resp.data},
                    message=f"Registration failed: Student {student_id} is ineligible for {company_query}.",
                    a2a_calls=a2a_calls,
                    trace_id=task.trace_id
                )

            reg_result = self.repo.register_student_for_placement(student_id, company_query)
            comms_proxy = self.registry.get("communication_agent", caller_name=self.agent_name)

            notif_req = TaskRequest(
                trace_id=task.trace_id,
                task="send_notification",
                params={
                    "channel": "email",
                    "recipient": f"{student_id}@campus.edu",
                    "subject": f"Registration Confirmed: {eligibility_resp.data.get('company_name')} Drive",
                    "content": f"You have successfully registered for the {eligibility_resp.data.get('company_name')} recruitment drive."
                },
                student_id=student_id,
                context=task.context
            )
            notif_resp = await comms_proxy.handle(notif_req)
            a2a_calls.append({
                "caller": self.agent_name,
                "target": "communication_agent",
                "tool": "send_notification",
                "params": notif_req.params,
                "status": notif_resp.status
            })

            rem_req = TaskRequest(
                trace_id=task.trace_id,
                task="schedule_reminder",
                params={
                    "title": f"Reminder: {eligibility_resp.data.get('company_name')} Placement Drive",
                    "event_time": "2026-08-25 09:00:00",
                    "lead_time_minutes": 60,
                    "target_user": student_id
                },
                student_id=student_id,
                context=task.context
            )
            rem_resp = await comms_proxy.handle(rem_req)
            a2a_calls.append({
                "caller": self.agent_name,
                "target": "communication_agent",
                "tool": "schedule_reminder",
                "params": rem_req.params,
                "status": rem_resp.status
            })

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={
                    "registration": reg_result,
                    "company_name": eligibility_resp.data.get("company_name"),
                    "notification": notif_resp.data,
                    "reminder": rem_resp.data,
                    "source": "mock"
                },
                message=f"Successfully registered student {student_id} for {eligibility_resp.data.get('company_name')} drive with confirmation and reminder scheduled.",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "analyze_resume":
            skills = task.params.get("skills", [])
            analysis = self.repo.analyze_resume(skills)
            analysis["source"] = "mock"
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=analysis,
                message=f"Resume analyzed. Score: {analysis.get('score_pct')}%",
                trace_id=task.trace_id
            )

        elif tool_name == "get_interview_prep":
            topic = task.params.get("topic")
            prep = self.repo.get_interview_prep(topic)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"interview_prep": prep, "source": "mock"},
                message=f"Retrieved interview preparation tips for '{topic or 'all'}'",
                trace_id=task.trace_id
            )

        elif tool_name == "get_placement_notifications":
            notifs = self.repo.get_placement_notifications()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"notifications": notifs, "source": "mock"},
                message=f"Retrieved {len(notifs)} placement notifications",
                trace_id=task.trace_id
            )

        else:
            return ResponseEnvelope(
                agent=self.agent_name,
                status="error",
                data={"error": f"Unknown tool '{task.task}' for PlacementAgent"},
                message=f"Tool '{task.task}' is not supported by PlacementAgent",
                trace_id=task.trace_id
            )
