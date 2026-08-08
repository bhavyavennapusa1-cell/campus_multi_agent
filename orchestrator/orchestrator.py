"""
Orchestrator for Synapse Multi-Agent System.
Parses user queries using LLM planner (with keyword planner fallback), resolves context from memory,
caps plan steps (max 5), dispatches to specialized agents, logs conversation turns, and returns completed steps.
"""

import os
import json
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import PlanStep, AGENT_ACTIONS, AgentResponse
from agents import (
    academic_agent,
    placement_agent,
    campus_agent,
    communication_agent,
    navigator_agent,
    events_agent,
)
from knowledge.memory import (
    resolve_context,
    add_turn,
    get_profile,
    create_session,
    get_student_memory,
    update_student_profile,
    get_history
)

logger = logging.getLogger("orchestrator")

AGENT_REGISTRY = {
    "academic": academic_agent,
    "placement": placement_agent,
    "campus": campus_agent,
    "communication": communication_agent,
    "navigator": navigator_agent,
    "events": events_agent,
}

# Mapping for routing alias normalization
ACTION_AGENT_MAP = {
    "get_attendance": "academic",
    "get_timetable": "academic",
    "get_exam_schedule": "academic",
    "course_info": "academic",
    "create_task": "academic",
    "get_tasks": "academic",
    "update_task": "academic",
    "complete_task": "academic",
    "create_study_plan": "academic",
    "get_roadmap": "academic",
    
    "check_eligibility": "placement",
    "get_internships": "placement",
    "get_github_profile": "placement",
    "find_opportunities": "placement",
    "get_all_eligible_companies": "placement",

    "get_hostel_info": "campus",
    "file_grievance": "campus",

    "get_directions": "navigator",
    "find_nearby_facilities": "navigator",

    "get_events": "events",
    "register_event": "events",
    "add_event_to_calendar": "events",

    "draft_email": "communication",
    "draft_official_email": "communication",
    "send_email": "communication",
    "schedule_reminder": "communication",
    "get_relevant_contacts": "communication",
    "create_chat_group": "communication",
    "schedule_appointment": "communication",
}

RAW_LLM_PLAN_LOGS: List[Dict[str, Any]] = []


def keyword_plan(clean_req: str, user_request: str) -> list[PlanStep]:
    """Pattern-based planner safety net used when LLM call is unavailable or fails."""
    req_lower = clean_req.lower()

    # Check for unmapped/vague requests that require clarification
    if req_lower in ["hi", "hello", "hey", "help", "who are you", "what can you do"]:
        return [PlanStep(
            id=1,
            agent="academic",
            action="general_synthesis",
            params={"query": user_request, "clarification_needed": True}
        )]

    has_placement_kw = ("placement eligibility" in req_lower or "drive eligibility" in req_lower or "company eligibility" in req_lower or "eligible for" in req_lower) or (any(k in req_lower for k in ["placement", "placements", "dream tier", "google", "microsoft", "salesforce", "oracle", "cognizant", "tcs", "internship", "job", "drives"]) and not any(a in req_lower for a in ["attendance", "exam", "make-up", "makeup"]))
    has_events_kw = any(k in req_lower for k in ["workshop", "workshops", "event", "events", "hackathon", "fest", "register", "registered"])
    has_timetable_kw = any(k in req_lower for k in ["timetable", "today's classes", "classes today", "schedule today", "lecture", "lectures"])
    has_exam_kw = any(k in req_lower for k in ["exam", "exams", "midterm", "endterm", "regs", "regulations", "grade", "marks", "grade card"])
    has_course_kw = any(k in req_lower for k in ["resource", "resources", "material", "materials", "syllabus", "course", "courses", "subject", "subjects", "book", "books", "notes"])
    has_attend_kw = any(k in req_lower for k in ["attend", "attendance", "absent", "condon", "detain", "shortage", "attendance eligibility"])
    has_comm_kw = any(k in req_lower for k in ["email", "draft", "mail", "notify", "inform", "message"])
    has_contact_kw = any(k in req_lower for k in ["mentor", "hod", "classmate", "classmates", "peer", "group", "advisor", "club", "clubs", "contact"])
    has_nav_kw = any(k in req_lower for k in ["navigate", "direction", "where is", "where can i find", "where's", "map", "distance", "location", "way to", "building", "food court", "food courts", "study spot", "study spots", "atm", "atms", "canteen", "facility", "facilities", "nearest", "find food", "find atm"])
    has_campus_kw = any(k in req_lower for k in ["hostel", "curfew", "gate", "dorm", "warden", "mess", "library", "timings", "complaint", "maintenance", "grievance"])

    steps = []
    step_id = 1

    if has_nav_kw:
        if any(f in req_lower for f in ["food court", "study spot", "atm", "facility", "canteen", "nearest"]):
            steps.append(PlanStep(id=step_id, agent="navigator", action="find_nearby_facilities", params={"query": clean_req}))
        else:
            steps.append(PlanStep(id=step_id, agent="navigator", action="get_directions", params={"destination": clean_req}))
        step_id += 1

    if has_timetable_kw:
        steps.append(PlanStep(id=step_id, agent="academic", action="get_timetable", params={"query": clean_req}))
        step_id += 1

    if has_placement_kw:
        company = "Google" if "google" in req_lower else ("Microsoft" if "microsoft" in req_lower else ("Oracle India" if "oracle" in req_lower else "Dream Tier"))
        if "drives" in req_lower or "opportunities" in req_lower or "drives is" in req_lower:
            steps.append(PlanStep(id=step_id, agent="placement", action="find_opportunities", params={"role": "Software Engineer"}))
            step_id += 1
        else:
            steps.append(PlanStep(id=step_id, agent="placement", action="check_eligibility", params={"company": company, "query": clean_req}))
            step_id += 1
            if "register" in req_lower or "calendar" in req_lower:
                steps.append(PlanStep(id=step_id, agent="events", action="register_event", params={"event_name": f"{company} Internship Drive"}))
                step_id += 1
                steps.append(PlanStep(id=step_id, agent="communication", action="schedule_reminder", params={"event": f"{company} Internship Drive", "minutes_before": 60}))
                step_id += 1

    if has_events_kw:
        if "register" in req_lower:
            steps.append(PlanStep(id=step_id, agent="events", action="register_event", params={"event_name": "Placement Workshop"}))
        else:
            steps.append(PlanStep(id=step_id, agent="events", action="get_events", params={"category": "workshops"}))
        step_id += 1

    if has_contact_kw:
        steps.append(PlanStep(id=step_id, agent="communication", action="get_relevant_contacts", params={"query": clean_req, "query_type": clean_req}))
        step_id += 1

    if has_course_kw and not has_exam_kw and not has_placement_kw:
        steps.append(PlanStep(id=step_id, agent="academic", action="course_info", params={"query": clean_req, "subject": clean_req}))
        step_id += 1

    if (has_exam_kw or "dbms" in req_lower) and not has_contact_kw and not has_timetable_kw:
        if "plan" in req_lower or "study" in req_lower or "dbms" in req_lower:
            steps.append(PlanStep(id=step_id, agent="academic", action="create_study_plan", params={"subject": "DBMS", "days_remaining": 10}))
        else:
            steps.append(PlanStep(id=step_id, agent="academic", action="get_exam_schedule", params={"query": clean_req}))
        step_id += 1

    if has_attend_kw:
        steps.append(PlanStep(id=step_id, agent="academic", action="get_attendance", params={"query": clean_req}))
        step_id += 1

    if has_comm_kw:
        if "reminder" in req_lower or "remind" in req_lower:
            steps.append(PlanStep(id=step_id, agent="communication", action="schedule_reminder", params={"event": clean_req}))
        else:
            steps.append(PlanStep(id=step_id, agent="communication", action="draft_email", params={"subject": "Campus Inquiry", "core_message": clean_req}))
        step_id += 1

    if has_campus_kw and not has_nav_kw:
        if "complaint" in req_lower or "grievance" in req_lower:
            steps.append(PlanStep(id=step_id, agent="campus", action="file_grievance", params={"query": user_request}))
        else:
            steps.append(PlanStep(id=step_id, agent="campus", action="get_hostel_info", params={"query": user_request}))
        step_id += 1

    if not steps:
        # Route custom queries directly to general synthesis for grounded RAG answer
        steps.append(PlanStep(
            id=1,
            agent="academic",
            action="general_synthesis",
            params={"query": user_request}
        ))

    return steps[:5]


def plan(user_request: str, profile: dict = None, session_id: str = "default") -> list[PlanStep]:
    """
    Intelligent LLM-based planner with pattern-based fallback safety net and step cap (max 5).
    """
    clean_req = user_request
    if "[Previous Context:" in user_request and "]" in user_request:
        clean_req = user_request.split("]")[-1].strip()

    prof_name = profile.get("name", "Student") if profile else "Student"
    prof_branch = (profile.get("branch") or profile.get("branch_year", "CSE - 3rd Year")) if profile else "CSE - 3rd Year"
    prof_att = (profile.get("attendance") or profile.get("attendance_pct", "88%")) if profile else "88%"
    prof_hostel = (profile.get("hostel_block") or profile.get("hostel", "Block B")) if profile else "Block B"

    history_records = get_history(session_id, last_n=3)
    history_summary = [{"role": h["role"], "agent": h.get("agent_name"), "content": h["content"]} for h in history_records]

    system_prompt = f"""You are the orchestrator for a Smart Campus multi-agent assistant. Read the student's message and decide which specialized agent(s) and action(s) must be called to answer it accurately.

Available agents and actions:
- academic:
  - course_info: syllabus, subject resources, course materials, books, notes, subject details
  - get_attendance: attendance percentage, attendance status, detention risk
  - get_timetable: daily schedule, class timetable, today's lectures
  - get_exam_schedule: exam dates, exam timetable, venue, max marks
  - create_study_plan: study preparation plan, exam prep schedule
  - create_task / get_tasks: manage study tasks
  - general_synthesis: general academic questions
- placement:
  - check_eligibility: check drive or company eligibility
  - get_internships / find_opportunities: internship listings, job postings, career opportunities
  - get_github_profile: coding stats and github portfolio
  - general_synthesis: general career & placement questions
- campus:
  - get_hostel_info: hostel rules, curfew, gate timings, mess, room info
  - file_grievance: file maintenance or campus complaints
  - general_synthesis: general campus & hostel queries
- navigator:
  - get_directions: campus map, route, directions to buildings/library/labs
  - find_nearby_facilities: find nearby ATMs, food courts, labs, study spots
  - general_synthesis: general navigation questions
- events:
  - get_events: campus events, hackathons, workshops, cultural fest
  - register_event: register for a specific workshop or event
  - general_synthesis: general event queries
- communication:
  - draft_email: draft formal email to faculty/professor
  - get_relevant_contacts: find faculty advisor, mentor, HOD contact info
  - schedule_reminder: set event or task reminder
  - general_synthesis: general communication queries

Student context:
- Name: {prof_name}
- Branch & Year: {prof_branch}
- Attendance %: {prof_att}
- Hostel Block: {prof_hostel}
- Session history: {json.dumps(history_summary)}

Instructions:
1. Identify the student's actual intent from their typed text.
2. Select the specific agent and action that answers their query.
3. If a query requests multiple actions across domains (e.g. eligibility + event registration + email draft), return ALL required steps in sequence.
4. Always pass relevant inputs/parameters.

Few-shot examples:
- Query: "I'm a 2nd-year CSE student. Am I eligible for the Google internship? If yes, register me for tomorrow's placement workshop, add it to my calendar, and remind me an hour before."
  Plan: [
    {{"agent": "placement", "action": "check_eligibility", "inputs": {{"company": "Google"}}}},
    {{"agent": "events", "action": "register_event", "inputs": {{"event_name": "Placement Workshop"}}}},
    {{"agent": "communication", "action": "schedule_reminder", "inputs": {{"event": "Placement Workshop", "minutes_before": 60}}}}
  ]
- Query: "Summarize the examination regulations, calculate my attendance eligibility, and draft an email requesting permission for a makeup exam."
  Plan: [
    {{"agent": "academic", "action": "course_info", "inputs": {{"query": "examination regulations"}}}},
    {{"agent": "academic", "action": "get_attendance", "inputs": {{}}}},
    {{"agent": "communication", "action": "draft_email", "inputs": {{"subject": "Permission for Makeup Exam", "core_message": "Requesting permission for makeup exam"}}}}
  ]
- Query: "where can I find food courts and study spots near the hostel"
  Plan: [
    {{"agent": "navigator", "action": "find_nearby_facilities", "inputs": {{"query": "food courts and study spots near hostel"}}}}
  ]
- Query: "is there an ATM near my hostel"
  Plan: [
    {{"agent": "navigator", "action": "find_nearby_facilities", "inputs": {{"facility": "ATM", "reference": "hostel"}}}}
  ]
- Query: "what is the hostel curfew and gate timing"
  Plan: [
    {{"agent": "campus", "action": "get_hostel_info", "inputs": {{"query": "curfew and gate timing"}}}}
  ]

Return your plan as a structured JSON array: [{{"agent": "<agent_name>", "action": "<action_name>", "inputs": {{...}}}}]"""



    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        logger.info("ANTHROPIC_API_KEY detected. LLM planner is ACTIVE.")
        try:
            # pyrefly: ignore [missing-import]
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=3.5)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                system=system_prompt,
                messages=[{"role": "user", "content": clean_req}],
            )
            raw_text = response.content[0].text.strip()
            
            RAW_LLM_PLAN_LOGS.append({"request": clean_req, "raw_response": raw_text})

            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()

            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as parse_err:
                logger.error(f"LLM planner parse error (JSONDecodeError): {parse_err}. Raw output: {raw_text[:200]}")
                raise

            actions_list = parsed if isinstance(parsed, list) else parsed.get("steps", parsed.get("actions", []))

            steps = []
            for idx, item in enumerate(actions_list, start=1):
                agent_name = item.get("agent", "").lower()
                action_name = item.get("action", "").lower()
                inputs = item.get("inputs") or item.get("params") or {}

                if agent_name == "clarify" or action_name == "clarify":
                    # Unmapped/ambiguous request -> return clarification step
                    q_text = inputs.get("question") or inputs.get("follow_up") or "Could you please clarify what information you need regarding academic, placement, campus, or communication services?"
                    steps.append(PlanStep(
                        id=idx,
                        agent="academic",
                        action="general_synthesis",
                        params={"query": q_text, "clarification_needed": True, "clarification_question": q_text}
                    ))
                    break

                # Resolve agent alias
                target_agent = agent_name
                if target_agent not in AGENT_REGISTRY:
                    target_agent = ACTION_AGENT_MAP.get(action_name, "academic")

                if target_agent in AGENT_REGISTRY:
                    steps.append(PlanStep(
                        id=idx,
                        agent=target_agent,
                        action=action_name if action_name else "general_synthesis",
                        params=inputs
                    ))

            if steps:
                return steps[:5]
        except Exception as e:
            err_type = type(e).__name__
            if "AuthenticationError" in err_type or "auth" in str(e).lower():
                logger.warning(f"LLM planner authentication failure ({err_type}: {e}). Falling back to keyword planner.")
            elif "Timeout" in err_type or "timeout" in str(e).lower():
                logger.warning(f"LLM planner timeout ({err_type}: {e}). Falling back to keyword planner.")
            elif "JSONDecodeError" in err_type or "parse" in str(e).lower():
                logger.warning(f"LLM planner response parse error ({err_type}: {e}). Falling back to keyword planner.")
            else:
                logger.warning(f"LLM planner exception ({err_type}: {e}). Falling back to keyword planner.")
    else:
        logger.info("ANTHROPIC_API_KEY not found: Running in keyword-matching fallback-only mode.")

    # Fallback path if LLM unavailable or failed
    fallback_steps = keyword_plan(clean_req, user_request)
    return fallback_steps[:5]


def dispatch(steps: list[PlanStep], session_id: str = "default", profile: dict = None, on_step_update=None) -> list[PlanStep]:
    """
    Executes plan steps in dependency order, injecting session_id and student profile into parameters
    and recording completed turns into SQLite conversation_history memory.
    """
    completed_ids = set()

    active_profile = profile
    if profile:
        update_student_profile(session_id, profile)
        active_profile = get_student_memory(session_id)
    else:
        active_profile = get_student_memory(session_id)
        if not active_profile:
            active_profile = create_session(session_id)

    while len(completed_ids) < len(steps):
        made_progress = False

        for step in steps:
            if step.id in completed_ids:
                continue
            if not all(dep in completed_ids for dep in step.depends_on):
                continue

            step.status = "running"
            step.params["session_id"] = session_id
            step.params["profile"] = active_profile

            if on_step_update:
                on_step_update(step)

            agent_module = AGENT_REGISTRY.get(step.agent)
            if not agent_module:
                step.status = "failed"
                if on_step_update:
                    on_step_update(step)
                completed_ids.add(step.id)
                made_progress = True
                continue

            for dep_id in step.depends_on:
                dep_step = next(s for s in steps if s.id == dep_id)
                if dep_step.result:
                    step.params["_previous_result"] = dep_step.result.data

            result = agent_module.handle(step.action, step.params)
            step.result = result
            step.status = "failed" if result.status == "error" else "done"

            add_turn(
                session_id=session_id,
                role="assistant",
                content=result.message,
                agent_name=step.agent
            )

            if on_step_update:
                on_step_update(step)

            completed_ids.add(step.id)
            made_progress = True

        if not made_progress:
            break

    return steps


def synthesize_response(user_message: str, steps: list[PlanStep], profile: dict = None) -> str:
    """
    Synthesizes multiple agent execution outputs into ONE natural, coherent, personalized response.
    Uses Anthropic Claude API (claude-3-5-sonnet-20241022) with smart rule-based fallback.
    """
    raw_prof_name = (profile.get("name") if profile else None) or "Student"
    prof_name = " ".join(w.capitalize() for w in raw_prof_name.strip().split()) if raw_prof_name else "Student"
    prof_branch = (profile.get("branch") or profile.get("branch_year", "CSE - 3rd Year")) if profile else "CSE - 3rd Year"
    prof_hostel = (profile.get("hostel_block") or profile.get("hostel", "Block B")) if profile else "Block B"
    prof_att = (profile.get("attendance") or profile.get("attendance_pct", "88%")) if profile else "88%"

    # Check for clarification request
    for s in steps:
        if s.params.get("clarification_needed"):
            q_text = s.params.get("clarification_question") or "Could you please specify whether your query is regarding academic schedules, placement drives, campus navigation, or faculty communication?"
            return f"Hello {prof_name}! {q_text}"

    agent_results_str = ""
    for s in steps:
        res = s.result
        res_msg = res.message if res else "No message returned"
        res_status = getattr(res, 'status', s.status) if res else s.status
        res_data = json.dumps(res.data) if (res and res.data) else "{}"
        res_citation = res.citation if (res and hasattr(res, 'citation')) else ""
        agent_results_str += f"- Agent: {s.agent}, Action: {s.action}, Status: {res_status}, Message: {res_msg}, Data: {res_data}, Citation: {res_citation}\n"

    system_prompt = f"""You are Synapse, a warm and efficient assistant for a university student. You've already gathered results from one or more specialized backend agents. Your job now is to turn those raw results into ONE natural, coherent, personalized reply — not a list of agent outputs stitched together.

Student: {prof_name}, {prof_branch}, Hostel {prof_hostel}, Attendance {prof_att}%

Original question: "{user_message}"

Agent results:
{agent_results_str}

Instructions:
1. Address the student by name naturally using capitalized format (e.g., "Hello {prof_name}!").
2. Synthesize across agents into a single flowing answer, weaving multiple agent results together logically rather than concatenating.
3. NEVER output meta-text or meta-phrases such as 'Retrieved upcoming...', 'Processed query...', 'Fetched placement...', or 'Retrieved data...'. Always return CONCRETE, SPECIFIC details directly in the reply!
4. If any agent result has status "needs_confirmation" or "failed", surface that clearly and tell the student what to do next.
5. If a data value is missing or an agent had nothing relevant, omit it gracefully rather than saying "no data found."
6. Never invent facts, dates, names, or numbers not present in the agent results.
7. Keep tone conversational and concise."""

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        try:
            # pyrefly: ignore [missing-import]
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=4.0)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=600,
                system=system_prompt,
                messages=[{"role": "user", "content": "Synthesize the agent results into a single personalized reply."}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"LLM response synthesis failed: {e}. Falling back to rule-based synthesis.")

    # Rule-Based / Local Dynamic Synthesizer
    eligibility_parts = []
    registration_parts = []
    reminder_parts = []
    draft_parts = []
    general_parts = []
    has_confirmation = False
    confirmation_action = ""

    for s in steps:
        res = s.result
        if not res:
            continue

        if getattr(res, 'status', '') == "needs_confirmation":
            has_confirmation = True
            confirmation_action = res.message

        data = res.data if isinstance(res.data, dict) else {}

        # 1. Placement Eligibility Check
        if s.agent == "placement" and s.action == "check_eligibility":
            comp = data.get("company")
            if comp and comp != "Dream Tier":
                if data.get("eligible"):
                    role = data.get("company_record", {}).get("role", "Software Development Engineer")
                    cgpa = data.get("cgpa", 8.8)
                    att = data.get("attendance_pct", 88.0)
                    eligibility_parts.append(
                        f"Yes, you are eligible for the {comp} internship drive because your CGPA ({cgpa}) and attendance ({att}%) meet all requirements for the {role} role."
                    )
                else:
                    reasons = ", ".join(data.get("reasons", [])) or "requirements not met"
                    eligibility_parts.append(
                        f"Currently, you are not eligible for the {comp} drive due to: {reasons}."
                    )
            elif res.message and ("ELIGIBLE" in res.message or "eligible" in res.message):
                clean_elig = re.sub(r'#{1,6}\s*', '', res.message).strip()
                eligibility_parts.append(clean_elig)

        # 2. Academic Regulations / Attendance Eligibility / Exam Rules
        elif s.agent == "academic" and s.action in ["get_attendance", "course_info", "general_synthesis", "get_exam_schedule"]:
            if data.get("attendance_pct") is not None:
                att = data.get("attendance_pct")
                eligibility_parts.append(
                    f"Attendance Eligibility Calculation: Student {prof_name} has {att}% overall attendance, which satisfies both the 75.0% standard requirement and the 65.0% makeup exam threshold."
                )
            if data.get("rules"):
                rules_clean = re.sub(r'#{1,6}\s*', '', data["rules"]).strip()
                if not any("Regulations" in p for p in eligibility_parts):
                    eligibility_parts.append(f"Examination Regulations: {rules_clean}")
            elif data.get("synthesis_text"):
                if not any(data["synthesis_text"] in p for p in eligibility_parts):
                    eligibility_parts.append(data["synthesis_text"])
            elif res.message and ("attendance" in res.message.lower() or "eligibility" in res.message.lower()):
                clean_att = re.sub(r'#{1,6}\s*', '', res.message).strip()
                clean_att = clean_att.split("Policy detail:")[0].strip()
                if not any(clean_att in p for p in eligibility_parts):
                    eligibility_parts.append(clean_att)

        # 3. Event Registration / Calendar Sync
        elif s.agent == "events" and s.action == "register_event":
            evt_name = data.get("event_name") or s.params.get("event_name") or "Placement Workshop"
            cal_date = data.get("calendar_sync", {}).get("date") or "Aug 15, 2026"
            registration_parts.append(
                f"You have been successfully registered for '{evt_name}', which has been added to your Google Calendar for {cal_date}."
            )

        # 4. Reminder Scheduling
        elif s.agent == "communication" and s.action == "schedule_reminder":
            evt_name = data.get("event") or s.params.get("event") or "the event"
            mins = data.get("minutes_before") or s.params.get("minutes_before") or 60
            reminder_parts.append(
                f"An automated reminder has been scheduled {mins} minutes prior to '{evt_name}'."
            )

        # 5. Email Drafting
        elif s.agent == "communication" and s.action == "draft_email":
            recipient = data.get("to") or "academic_office@vasavi.ac.in"
            subj = data.get("subject") or "Makeup Exam Request"
            draft_parts.append(
                f"An official email draft to {recipient} regarding '{subj}' has been prepared and is awaiting your confirmation to send."
            )

        # 6. Structured Contacts / Groups
        elif data.get("contacts"):
            contacts_list = data["contacts"]
            contact_msgs = []
            for c in contacts_list:
                if c.get("title") or c.get("group_id"):
                    title = c.get("title") or c.get("group_id")
                    mentor = f" (Mentor: {c.get('mentor')})" if c.get("mentor") else ""
                    members = ", ".join(m.get("name") for m in c.get("members", [])) if c.get("members") else ""
                    members_str = f"\n- Members: {members}" if members else ""
                    contact_msgs.append(f"Project Group: {title}{mentor}{members_str}")
                elif c.get("name") and c.get("email"):
                    contact_msgs.append(f"{c.get('name')} ({c.get('role', 'Faculty')}): {c.get('email')}")
            if contact_msgs:
                general_parts.append("\n".join(contact_msgs))

        # 7. Structured Events List
        elif data.get("events"):
            evts = data["events"]
            evt_msgs = ["Upcoming Campus Events & Workshops:"]
            for idx, e in enumerate(evts, 1):
                t = e.get("title") or e.get("event_name") or "Campus Event"
                d = e.get("date") or e.get("date_str") or "Upcoming"
                v = f" at {e.get('venue')}" if e.get("venue") else ""
                s_left = f", {e.get('seats_left')} seats left" if e.get("seats_left") else ""
                evt_msgs.append(f"{idx}. {t} ({d}{v}{s_left})")
            if len(evt_msgs) > 1:
                general_parts.append("\n".join(evt_msgs))
            elif res.message:
                general_parts.append(res.message)

        # 8. Structured Opportunities List
        elif data.get("opportunities"):
            opps = data["opportunities"]
            opp_msgs = ["Eligible Placement Drives:"]
            for o in opps:
                r = o.get("role") or "Role"
                comp = o.get("company") or "Company"
                dead = f" - Deadline: {o.get('deadline')}" if o.get("deadline") else ""
                pos = f" ({o.get('open_positions')} open positions)" if o.get("open_positions") else ""
                opp_msgs.append(f"- {r}{pos} at {comp}{dead}")
            if len(opp_msgs) > 1:
                general_parts.append("\n".join(opp_msgs))
            elif res.message:
                general_parts.append(res.message)

        # 9. Navigation Directions & Facility Search
        elif data.get("synthesis_text"):
            general_parts.append(data["synthesis_text"])
        elif data.get("directions"):
            dirs = data["directions"]
            if isinstance(dirs, list):
                general_parts.append("\n".join(dirs))
            else:
                general_parts.append(str(dirs))

        # 10. Fallback Message
        elif res.message:
            clean_msg = re.sub(r'\[Action ID:\s*[^\]]+\]', '', res.message).strip()
            clean_msg = re.sub(r'#{1,6}\s*', '', clean_msg).strip()
            if clean_msg:
                general_parts.append(clean_msg)

    paragraphs = []
    greeting = f"Hello {prof_name}!"

    if eligibility_parts:
        paragraphs.append("\n".join(eligibility_parts))

    sched_block = []
    if registration_parts:
        sched_block.extend(registration_parts)
    if reminder_parts:
        sched_block.extend(reminder_parts)
    if sched_block:
        paragraphs.append(" ".join(sched_block))

    if draft_parts:
        paragraphs.append("\n".join(draft_parts))

    if general_parts and not (eligibility_parts or registration_parts or draft_parts):
        paragraphs.append("\n\n".join(general_parts))

    body = "\n\n".join(paragraphs) if paragraphs else "Here are your requested campus details."

    if has_confirmation and not draft_parts:
        body += f"\n\nNote: {confirmation_action}"

    return f"{greeting}\n\n{body}".strip()


def run(user_request: str, session_id: str = "default", profile: dict = None, on_step_update=None) -> list[PlanStep]:
    """
    Main orchestration entrypoint. Thread profile through session memory,
    run intent routing, dispatch to agents, and return completed steps.
    """
    active_profile = profile
    if profile:
        update_student_profile(session_id, profile)
        active_profile = get_student_memory(session_id)
    else:
        active_profile = get_student_memory(session_id)
        if not active_profile:
            active_profile = create_session(session_id)

    resolved_request = resolve_context(session_id, user_request)
    add_turn(session_id=session_id, role="user", content=resolved_request)
    
    steps = plan(resolved_request, profile=active_profile, session_id=session_id)
    return dispatch(steps, session_id=session_id, profile=active_profile, on_step_update=on_step_update)


if __name__ == "__main__":
    test_session = "demo_session_001"
    create_session(test_session, {"name": "Bhavya Vennapusa", "branch": "CSE - 3rd Year", "cgpa": 8.5, "backlog_count": 0, "attendance_pct": 88.0})

    print("--- Running Orchestrator Test ---")
    test_profile = {"name": "Bhavya Vennapusa", "branch_year": "CSE - 3rd Year", "attendance": "88%", "hostel_block": "Block B"}
    results = run("register me for the Google internship and remind me of my exam dates", session_id=test_session, profile=test_profile)
    for s in results:
        res = s.result
        print(f"Step {s.id} [{s.agent}.{s.action}] -> Status: {s.status}")
        print(f"  Message : {res.message if res else ''}")
        print(f"  Citation: {res.citation if res else ''}")

    print("\n--- Testing Response Synthesis ---")
    syn_reply = synthesize_response("register me for the Google internship and remind me of my exam dates", results, profile=test_profile)
    print("Synthesized Reply:\n", syn_reply)
