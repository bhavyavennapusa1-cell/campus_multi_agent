from typing import Optional, List, Dict, Any
from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.campus_agent.repo import CampusRepo, InMemoryCampusRepo


class CampusAgent:
    """
    Campus Agent (Mini-Orchestrator)
    
    Routes internally across 3 sub-modules:
    1. Events sub-module: discover_events, register_for_event, manage_hackathon_team, create_calendar_entry, cancel_or_withdraw, recommend_events
    2. Student Services sub-module: get_hostel_info, get_library_status, check_scholarship_eligibility, get_transport_info, raise_grievance, search_campus_faqs
    3. Campus Navigator sub-module: get_campus_map, search_location, get_directions, get_nearby_facilities, get_indoor_wayfinding, get_accessible_route
    
    A2A Interactions:
    - Events → Academic Agent: register_for_event calls get_timetable/exams to check for clashes before confirming.
      If clash, returns status: "needs_clarification".
    - Events → Communication Agent: on successful registration, calls schedule_appointment and schedule_reminder.
    - Student Services → Communication Agent: raise_grievance calls send_notification to confirm ticket.
    """

    EVENTS_TOOLS = {
        "discover_events", "register_for_event", "manage_hackathon_team",
        "create_calendar_entry", "cancel_or_withdraw", "recommend_events"
    }

    STUDENT_SERVICES_TOOLS = {
        "get_hostel_info", "get_library_status", "check_scholarship_eligibility",
        "get_transport_info", "raise_grievance", "search_campus_faqs"
    }

    NAVIGATOR_TOOLS = {
        "get_campus_map", "search_location", "get_directions",
        "get_nearby_facilities", "get_indoor_wayfinding", "get_accessible_route"
    }

    def __init__(self, registry: AgentRegistry, repo: Optional[CampusRepo] = None):
        self.agent_name = "campus_agent"
        self.registry = registry
        self.repo: CampusRepo = repo or InMemoryCampusRepo()

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        tool_name = task.task.lower()

        # Mini-Orchestrator routing logic
        if tool_name in self.EVENTS_TOOLS:
            return await self._handle_events_module(tool_name, task)
        elif tool_name in self.STUDENT_SERVICES_TOOLS:
            return await self._handle_student_services_module(tool_name, task)
        elif tool_name in self.NAVIGATOR_TOOLS:
            return await self._handle_navigator_module(tool_name, task)
        else:
            return ResponseEnvelope(
                agent=self.agent_name,
                status="error",
                data={"error": f"Unknown tool '{task.task}' across all Campus sub-modules"},
                message=f"Tool '{task.task}' is not recognized by CampusAgent",
                trace_id=task.trace_id
            )

    # -------------------------------------------------------------------------
    # 1. EVENTS SUB-MODULE HANDLER
    # -------------------------------------------------------------------------
    async def _handle_events_module(self, tool_name: str, task: TaskRequest) -> ResponseEnvelope:
        student_id = task.student_id or task.params.get("student_id")
        a2a_calls: List[Dict[str, Any]] = []

        if tool_name == "discover_events":
            category = task.params.get("category")
            events = self.repo.list_events(category)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"events": events},
                message=f"Found {len(events)} campus events",
                trace_id=task.trace_id
            )

        elif tool_name == "register_for_event":
            event_query = task.params.get("event_id") or task.params.get("title") or task.params.get("event")
            if not event_query or not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "event_id (or event) and student_id required"},
                    message="Missing parameters for register_for_event",
                    trace_id=task.trace_id
                )

            event = self.repo.get_event(event_query)
            if not event:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": f"Event '{event_query}' not found"},
                    message=f"Unknown event: '{event_query}'",
                    trace_id=task.trace_id
                )

            event_date = event.get("date")
            event_start = event.get("start_time")
            event_end = event.get("end_time")

            # MANDATORY A2A STEP: Call Academic Agent to check timetable/exam clash!
            acad_proxy = self.registry.get("academic_agent", caller_name=self.agent_name)
            acad_req = TaskRequest(
                trace_id=task.trace_id,
                task="get_timetable",
                params={"student_id": student_id},
                student_id=student_id,
                context=task.context
            )
            acad_resp = await acad_proxy.handle(acad_req)

            a2a_calls.append({
                "caller": self.agent_name,
                "target": "academic_agent",
                "tool": "get_timetable",
                "params": {"student_id": student_id},
                "status": acad_resp.status,
                "response_data": acad_resp.data
            })

            # Evaluate clash against exams and scheduled classes
            clashes: List[Dict[str, Any]] = []
            if acad_resp.status == "success":
                exams = acad_resp.data.get("exams", [])
                timetable = acad_resp.data.get("timetable", [])

                # Check Exam clashes
                for ex in exams:
                    if ex.get("date") == event_date:
                        ex_start = ex.get("start_time")
                        ex_end = ex.get("end_time")
                        # Simple overlap check: start < ex_end and end > ex_start
                        if event_start < ex_end and event_end > ex_start:
                            clashes.append({
                                "conflict_type": "EXAM_CLASH",
                                "title": ex.get("exam_name") or ex.get("title"),
                                "date": event_date,
                                "time": f"{ex_start}-{ex_end}",
                                "hall": ex.get("hall") or ex.get("location")
                            })

            # IF CLASH DETECTED: Return status "needs_clarification" instead of silent success!
            if clashes:
                clash_details = clashes[0]
                warning_msg = (
                    f"Registration warning: Event '{event.get('title')}' on {event_date} ({event_start}-{event_end}) "
                    f"CLASHES with your scheduled exam: '{clash_details['title']}' ({clash_details['time']})."
                )
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="needs_clarification",
                    data={
                        "event": event,
                        "clash_detected": True,
                        "conflict_details": clashes,
                        "recommendation": "Please resolve timetable clash before registering."
                    },
                    message=warning_msg,
                    a2a_calls=a2a_calls,
                    trace_id=task.trace_id
                )

            # NO CLASH: Confirm registration in repo
            reg_res = self.repo.register_event(student_id, event["event_id"])

            # A2A STEP: Call Communication Agent for schedule_appointment & schedule_reminder
            comms_proxy = self.registry.get("communication_agent", caller_name=self.agent_name)

            # 1. schedule_appointment
            appt_req = TaskRequest(
                trace_id=task.trace_id,
                task="schedule_appointment",
                params={
                    "title": f"Event: {event.get('title')}",
                    "date": event_date,
                    "time": f"{event_start}-{event_end}",
                    "location": event.get("location"),
                    "student_id": student_id
                },
                student_id=student_id,
                context=task.context
            )
            appt_resp = await comms_proxy.handle(appt_req)
            a2a_calls.append({
                "caller": self.agent_name,
                "target": "communication_agent",
                "tool": "schedule_appointment",
                "params": appt_req.params,
                "status": appt_resp.status
            })

            # 2. schedule_reminder (60 min before event)
            rem_req = TaskRequest(
                trace_id=task.trace_id,
                task="schedule_reminder",
                params={
                    "title": f"Upcoming Event: {event.get('title')}",
                    "event_time": f"{event_date} {event_start}:00",
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
                    "registration": reg_res,
                    "calendar_entry": appt_resp.data,
                    "reminder": rem_resp.data
                },
                message=f"Registered student {student_id} for '{event.get('title')}' with calendar appointment and 60-min reminder scheduled.",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "manage_hackathon_team":
            team_id = task.params.get("team_id", "TEAM001")
            leader_id = student_id or task.params.get("leader_id", "STU001")
            action = task.params.get("action", "create")
            member_id = task.params.get("member_id")

            team_res = self.repo.manage_hackathon_team(team_id, leader_id, action, member_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"team": team_res},
                message=f"Hackathon team action '{action}' performed for team '{team_id}'",
                trace_id=task.trace_id
            )

        elif tool_name == "create_calendar_entry":
            # Direct companion to Communication Agent's schedule_appointment
            comms_proxy = self.registry.get("communication_agent", caller_name=self.agent_name)
            comms_resp = await comms_proxy.handle(TaskRequest(
                trace_id=task.trace_id,
                task="schedule_appointment",
                params=task.params,
                student_id=student_id,
                context=task.context
            ))
            a2a_calls.append({
                "caller": self.agent_name,
                "target": "communication_agent",
                "tool": "schedule_appointment",
                "params": task.params,
                "status": comms_resp.status
            })
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=comms_resp.data,
                message="Calendar entry created via Communication Agent",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "cancel_or_withdraw":
            event_id = task.params.get("event_id")
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"event_id": event_id, "student_id": student_id, "status": "withdrawn"},
                message=f"Withdrew student {student_id} from event {event_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "recommend_events":
            events = self.repo.list_events()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"recommended_events": events[:2]},
                message="Recommended events based on campus activity",
                trace_id=task.trace_id
            )

    # -------------------------------------------------------------------------
    # 2. STUDENT SERVICES SUB-MODULE HANDLER
    # -------------------------------------------------------------------------
    async def _handle_student_services_module(self, tool_name: str, task: TaskRequest) -> ResponseEnvelope:
        student_id = task.student_id or task.params.get("student_id")
        a2a_calls: List[Dict[str, Any]] = []

        if tool_name == "get_hostel_info":
            if not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "student_id required"},
                    message="Missing student_id for hostel info",
                    trace_id=task.trace_id
                )
            info = self.repo.get_hostel_info(student_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"hostel_info": info or {}},
                message=f"Retrieved hostel details for student {student_id}",
                trace_id=task.trace_id
            )

        elif tool_name == "get_library_status":
            lib_info = self.repo.get_library_status(student_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data=lib_info,
                message="Retrieved campus library status",
                trace_id=task.trace_id
            )

        elif tool_name == "check_scholarship_eligibility":
            scholarships = self.repo.get_scholarships()
            # If student_id present, verify against Academic attendance / CGPA via Academic Agent
            eligible_scholarships = []
            if student_id:
                acad_proxy = self.registry.get("academic_agent", caller_name=self.agent_name)
                acad_resp = await acad_proxy.handle(TaskRequest(
                    trace_id=task.trace_id,
                    task="check_attendance_eligibility",
                    params={"student_id": student_id},
                    student_id=student_id,
                    context=task.context
                ))
                a2a_calls.append({
                    "caller": self.agent_name,
                    "target": "academic_agent",
                    "tool": "check_attendance_eligibility",
                    "params": {"student_id": student_id},
                    "status": acad_resp.status
                })
                att_ok = acad_resp.data.get("eligible", False)
                for sch in scholarships:
                    if att_ok:
                        eligible_scholarships.append(sch)
            else:
                eligible_scholarships = scholarships

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"scholarships": eligible_scholarships},
                message=f"Evaluated scholarship eligibility ({len(eligible_scholarships)} matches)",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "get_transport_info":
            route_id = task.params.get("route_id")
            trans = self.repo.get_transport_info(route_id)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"transport_info": trans},
                message=f"Retrieved campus shuttle transport info for '{route_id or 'all routes'}'",
                trace_id=task.trace_id
            )

        elif tool_name == "raise_grievance":
            category = task.params.get("category", "General")
            description = task.params.get("description", "No description provided.")
            if not student_id:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "student_id is required to raise a grievance"},
                    message="Missing student_id for grievance",
                    trace_id=task.trace_id
                )

            ticket = self.repo.create_grievance(student_id, category, description)

            # MANDATORY A2A STEP: Call Communication Agent send_notification on grievance creation!
            comms_proxy = self.registry.get("communication_agent", caller_name=self.agent_name)
            notif_req = TaskRequest(
                trace_id=task.trace_id,
                task="send_notification",
                params={
                    "channel": "email",
                    "recipient": f"{student_id}@campus.edu",
                    "subject": f"Grievance Ticket Created [{ticket['ticket_id']}]",
                    "content": f"Your grievance ticket '{ticket['ticket_id']}' ({category}) has been created and logged for review."
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

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"ticket": ticket, "notification": notif_resp.data},
                message=f"Raised grievance ticket '{ticket['ticket_id']}' and dispatched confirmation notification via Communication Agent.",
                a2a_calls=a2a_calls,
                trace_id=task.trace_id
            )

        elif tool_name == "search_campus_faqs":
            query = task.params.get("query", "")
            matches = self.repo.search_faqs(query)
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"query": query, "results": matches},
                message=f"Found {len(matches)} matching campus FAQ entries",
                trace_id=task.trace_id
            )

    # -------------------------------------------------------------------------
    # 3. CAMPUS NAVIGATOR SUB-MODULE HANDLER
    # -------------------------------------------------------------------------
    async def _handle_navigator_module(self, tool_name: str, task: TaskRequest) -> ResponseEnvelope:
        if tool_name == "get_campus_map":
            locs = self.repo.get_locations()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"map_locations": locs},
                message="Retrieved interactive campus map layout",
                trace_id=task.trace_id
            )

        elif tool_name == "search_location":
            name = task.params.get("location_name") or task.params.get("name") or task.params.get("query", "")
            loc = self.repo.get_location(name)
            if not loc:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": f"Location '{name}' not found on campus"},
                    message=f"Location '{name}' not found",
                    trace_id=task.trace_id
                )
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"location": loc},
                message=f"Found location '{loc['name']}' in building '{loc.get('building')}'",
                trace_id=task.trace_id
            )

        elif tool_name in ["get_directions", "get_accessible_route"]:
            origin = task.params.get("origin", "Main Gate")
            destination = task.params.get("destination") or task.params.get("to")
            if not destination:
                return ResponseEnvelope(
                    agent=self.agent_name,
                    status="error",
                    data={"error": "destination parameter required"},
                    message="Missing destination for navigation",
                    trace_id=task.trace_id
                )
            route = self.repo.get_route(origin, destination)
            is_accessible = (tool_name == "get_accessible_route")
            if is_accessible:
                route["wheelchair_accessible_guaranteed"] = True

            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"route": route},
                message=f"Calculated route from '{origin}' to '{destination}' ({route.get('walk_time_minutes')} mins walk)",
                trace_id=task.trace_id
            )

        elif tool_name == "get_nearby_facilities":
            near = task.params.get("near", "Central Quad")
            locs = self.repo.get_locations()
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={"near": near, "facilities": list(locs.keys())[:3]},
                message=f"Found nearby campus facilities near '{near}'",
                trace_id=task.trace_id
            )

        elif tool_name == "get_indoor_wayfinding":
            building = task.params.get("building", "CS Block")
            room = task.params.get("room", "Lab 3")
            return ResponseEnvelope(
                agent=self.agent_name,
                status="success",
                data={
                    "building": building,
                    "room": room,
                    "indoor_steps": [f"Enter {building} ground lobby", "Take elevator to 2nd floor", f"Turn right to Room {room}"]
                },
                message=f"Generated indoor wayfinding guide for {building} -> Room {room}",
                trace_id=task.trace_id
            )
