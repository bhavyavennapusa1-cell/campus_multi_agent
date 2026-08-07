"""
Orchestrator for Smart Campus Multi-Agent System.
Parses user queries, resolves context from memory, generates execution plan steps,
dispatches to specialized agents, logs conversation turns, and returns completed steps.
"""

import json
import re
import sys
from pathlib import Path

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import PlanStep, AGENT_ACTIONS, AgentResponse
from agents import academic_agent, placement_agent, campus_agent, communication_agent
from knowledge.memory import resolve_context, add_turn, get_profile, create_session

AGENT_REGISTRY = {
    "academic": academic_agent,
    "placement": placement_agent,
    "campus": campus_agent,
    "communication": communication_agent,
}

PLANNING_SYSTEM_PROMPT = f"""You are the planning module of a campus assistant.
Given a user request, break it into a JSON list of steps. Each step must use
one of these agents and actions:

{json.dumps(AGENT_ACTIONS, indent=2)}

Return ONLY valid JSON in this exact shape, nothing else:
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "check_eligibility", "params": {{"company": "Google"}}, "depends_on": []}}
  ]
}}

If a step needs the result of an earlier step, add its id to depends_on.
Keep plans as short as possible - only include steps genuinely needed.
"""


def plan(user_request: str) -> list[PlanStep]:
    """
    Intelligent pattern-based planner routing queries to appropriate domain agents.
    
    TODO (Future Work): Replace or augment this keyword planner with a live LLM call using PLANNING_SYSTEM_PROMPT:
        import anthropic
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=PLANNING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_request}],
        )
        raw = response.content[0].text
        parsed = json.loads(raw)
        return [PlanStep(**step) for step in parsed["steps"]]
    """
    # If query has prepended context from resolve_context(), extract actual user query
    clean_req = user_request
    if "[Previous Context:" in user_request and "]" in user_request:
        clean_req = user_request.split("]")[-1].strip()

    req_lower = clean_req.lower()

    # --- MULTI-STEP CHAINED PLANS (chained via depends_on) ---
    has_placement_kw = any(k in req_lower for k in ["eligib", "placement", "dream", "company", "google", "microsoft", "salesforce", "oracle", "cognizant", "tcs", "internship"])
    has_action_kw = any(k in req_lower for k in ["register", "workshop", "calendar", "remind", "reminder", "event", "schedule"])
    has_exam_kw = any(k in req_lower for k in ["exam", "regs", "regulations", "grade", "marks"])
    has_attend_kw = any(k in req_lower for k in ["attend", "attendance", "absent", "condon", "detain", "shortage"])
    has_comm_kw = any(k in req_lower for k in ["email", "draft", "mail", "notify", "inform"])

    # Multi-Step Pattern 1: Placement check -> Event discovery -> Reminder scheduling
    if has_placement_kw and has_action_kw:
        company = "Google" if "google" in req_lower else ("Microsoft" if "microsoft" in req_lower else "Dream Tier")
        return [
            PlanStep(
                id=1,
                agent="placement",
                action="check_eligibility",
                params={"company": company, "query": clean_req},
                depends_on=[]
            ),
            PlanStep(
                id=2,
                agent="campus",
                action="get_events",
                params={"query": f"workshops and events for {company} candidates"},
                depends_on=[1]
            ),
            PlanStep(
                id=3,
                agent="communication",
                action="schedule_reminder",
                params={"event": f"{company} Placement Drive & Workshop", "minutes_before": 60},
                depends_on=[2]
            )
        ]

    # Multi-Step Pattern 2: Exam / Attendance Check -> Email Draft Notification
    if (has_exam_kw or has_attend_kw) and (has_comm_kw or "eligibility" in req_lower):
        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_attendance",
                params={"query": clean_req},
                depends_on=[]
            ),
            PlanStep(
                id=2,
                agent="academic",
                action="get_exam_schedule",
                params={"query": clean_req},
                depends_on=[1]
            ),
            PlanStep(
                id=3,
                agent="communication",
                action="draft_email",
                params={"subject": "Academic Attendance & Exam Eligibility Inquiry"},
                depends_on=[2]
            )
        ]

    # Multi-Step Pattern 3: Today's Classes / Timetable -> Upcoming Workshops
    if any(k in req_lower for k in ["timetable", "today", "classes"]) and any(k in req_lower for k in ["workshop", "recommend", "ai", "event"]):
        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_timetable",
                params={"query": clean_req},
                depends_on=[]
            ),
            PlanStep(
                id=2,
                agent="campus",
                action="get_events",
                params={"query": "AI workshops and hackathons"},
                depends_on=[1]
            )
        ]

    # --- SINGLE-STEP FALLBACK PLANS ---
    # Academic attendance queries
    if any(k in req_lower for k in ["attend", "absent", "condon", "detain", "percentage", "shortage"]):

        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_attendance",
                params={"query": clean_req},
                depends_on=[]
            )
        ]

    # Placement queries
    if any(k in req_lower for k in ["eligib", "placement", "dream", "company", "google", "microsoft", "salesforce", "oracle", "cognizant", "tcs"]):
        company = "Dream Tier"
        if "google" in req_lower:
            company = "Google"
        elif "microsoft" in req_lower:
            company = "Microsoft"
        elif "salesforce" in req_lower:
            company = "Salesforce"
        elif "oracle" in req_lower:
            company = "Oracle India"
        elif "cognizant" in req_lower:
            company = "Cognizant"
        elif "tcs" in req_lower:
            company = "TCS"

        return [
            PlanStep(
                id=1,
                agent="placement",
                action="check_eligibility",
                params={"company": company, "query": clean_req},
                depends_on=[]
            )
        ]

    # Campus queries (Hostel, Library, Transport, Events, Grievance)
    if any(k in req_lower for k in ["hostel", "curfew", "gate", "late", "outpass", "dorm", "warden", "mess", "visitor"]):
        return [
            PlanStep(
                id=1,
                agent="campus",
                action="get_hostel_info",
                params={"query": user_request},
                depends_on=[]
            )
        ]

    if any(k in req_lower for k in ["event", "hackathon", "fest", "symposium", "coding"]):
        return [
            PlanStep(
                id=1,
                agent="campus",
                action="get_events",
                params={"query": user_request},
                depends_on=[]
            )
        ]

    if any(k in req_lower for k in ["grievance", "complaint", "issue", "sla"]):
        return [
            PlanStep(
                id=1,
                agent="campus",
                action="file_grievance",
                params={"query": user_request, "text": user_request},
                depends_on=[]
            )
        ]

    # Academic queries (Attendance, Exam, Timetable)
    if any(k in req_lower for k in ["attend", "absent", "condon", "detain", "percentage", "shortage"]):
        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_attendance",
                params={"query": user_request},
                depends_on=[]
            )
        ]

    if any(k in req_lower for k in ["exam", "grade", "marks", "revalu", "backlog", "passing"]):
        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_exam_schedule",
                params={"query": user_request},
                depends_on=[]
            )
        ]

    if any(k in req_lower for k in ["timetable", "schedule", "class", "today"]):
        return [
            PlanStep(
                id=1,
                agent="academic",
                action="get_timetable",
                params={"query": user_request},
                depends_on=[]
            )
        ]

    # Communication queries
    if any(k in req_lower for k in ["email", "draft", "mail"]):
        return [
            PlanStep(
                id=1,
                agent="communication",
                action="draft_email",
                params={"body": user_request},
                depends_on=[]
            )
        ]

    if any(k in req_lower for k in ["remind", "reminder", "alarm"]):
        return [
            PlanStep(
                id=1,
                agent="communication",
                action="schedule_reminder",
                params={"event": user_request},
                depends_on=[]
            )
        ]

    # Fallback to academic attendance query
    return [
        PlanStep(
            id=1,
            agent="academic",
            action="get_attendance",
            params={"query": user_request},
            depends_on=[]
        )
    ]


def dispatch(steps: list[PlanStep], session_id: str = "default", on_step_update=None) -> list[PlanStep]:
    """
    Executes plan steps in dependency order, injecting session_id into parameters
    and recording completed turns into SQLite conversation_history memory.
    """
    completed_ids = set()

    # Ensure profile exists
    if not get_profile(session_id):
        create_session(session_id)

    while len(completed_ids) < len(steps):
        made_progress = False

        for step in steps:
            if step.id in completed_ids:
                continue
            if not all(dep in completed_ids for dep in step.depends_on):
                continue  # waiting on a dependency

            step.status = "running"
            step.params["session_id"] = session_id

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

            # Pass forward previous step results if needed
            for dep_id in step.depends_on:
                dep_step = next(s for s in steps if s.id == dep_id)
                if dep_step.result:
                    step.params["_previous_result"] = dep_step.result.data

            # Execute agent handler
            result = agent_module.handle(step.action, step.params)
            step.result = result
            step.status = "failed" if result.status == "error" else "done"

            # Record assistant response turn into SQLite memory
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
            break  # circular dependency or stuck - avoid infinite loop

    return steps


def run(user_request: str, session_id: str = "default", on_step_update=None) -> list[PlanStep]:
    """
    Primary orchestrator entry point:
    1. Resolves context from memory if pronouns/vague references exist.
    2. Logs the user's turn to conversation_history.
    3. Plans and dispatches execution steps.
    """
    # 1. Resolve context from previous turns
    resolved_request = resolve_context(session_id, user_request)

    # 2. Record user query turn in memory
    add_turn(session_id=session_id, role="user", content=resolved_request)

    # 3. Plan and Dispatch
    steps = plan(resolved_request)
    return dispatch(steps, session_id=session_id, on_step_update=on_step_update)


if __name__ == "__main__":
    test_session = "demo_session_001"
    create_session(test_session, {"cgpa": 8.5, "backlog_count": 0, "attendance_pct": 88.0})
    
    print("--- Running Orchestrator Test ---")
    results = run("Am I eligible for a dream company?", session_id=test_session)
    for s in results:
        res = s.result
        print(f"Step {s.id} [{s.agent}.{s.action}] -> Status: {s.status}")
        print(f"  Message : {res.message if res else ''}")
        print(f"  Citation: {res.citation if res else ''}")

