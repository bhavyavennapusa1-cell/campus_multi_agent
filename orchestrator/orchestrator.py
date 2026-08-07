"""
Orchestrator for Smart Campus Multi-Agent System.
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
from knowledge.memory import resolve_context, add_turn, get_profile, create_session

logger = logging.getLogger("orchestrator")

AGENT_REGISTRY = {
    "academic": academic_agent,
    "placement": placement_agent,
    "campus": campus_agent,
    "communication": communication_agent,
    "navigator": navigator_agent,
    "events": events_agent,
}

RAW_LLM_PLAN_LOGS: List[Dict[str, Any]] = []

PLANNING_SYSTEM_PROMPT = f"""You are the intelligent planner module of a Smart Campus Multi-Agent System.
Given a user request, break it into a JSON list of steps. Each step must use one of these registered agents and actions:

{json.dumps(AGENT_ACTIONS, indent=2)}

FEW-SHOT MULTI-STEP EXAMPLES:
1. "Am I eligible for Google placement drive?" ->
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "check_eligibility", "params": {{"company": "Google"}}, "depends_on": []}},
    {{"id": 2, "agent": "events", "action": "get_events", "params": {{"query": "Google placement workshops"}}, "depends_on": [1]}},
    {{"id": 3, "agent": "communication", "action": "schedule_reminder", "params": {{"event": "Google Drive Prep"}}, "depends_on": [2]}}
  ]
}}

2. "I have a DBMS exam in 10 days" ->
{{
  "steps": [
    {{"id": 1, "agent": "academic", "action": "create_study_plan", "params": {{"subject": "DBMS", "days_remaining": 10}}, "depends_on": []}}
  ]
}}

3. "Give me a roadmap for placements and summarize my situation" ->
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "general_synthesis", "params": {{"query": "placement preparation roadmap and eligibility"}}, "depends_on": []}}
  ]
}}

4. "How do I navigate to central library?" ->
{{
  "steps": [
    {{"id": 1, "agent": "navigator", "action": "get_directions", "params": {{"destination": "Central Library"}}, "depends_on": []}}
  ]
}}

RULES:
- Return ONLY valid JSON with top-level key "steps".
- Maximum 5 steps per plan.
- Use "depends_on": [step_ids] when a step relies on earlier outputs.
"""


def keyword_plan(clean_req: str, user_request: str) -> list[PlanStep]:
    """Pattern-based planner safety net used when LLM call is unavailable or fails."""
    req_lower = clean_req.lower()

    has_placement_kw = any(k in req_lower for k in ["eligib", "placement", "dream", "company", "google", "microsoft", "salesforce", "oracle", "cognizant", "tcs", "internship"])
    has_action_kw = any(k in req_lower for k in ["register", "workshop", "calendar", "remind", "reminder", "event", "schedule"])
    has_exam_kw = any(k in req_lower for k in ["exam", "regs", "regulations", "grade", "marks"])
    has_attend_kw = any(k in req_lower for k in ["attend", "attendance", "absent", "condon", "detain", "shortage"])
    has_comm_kw = any(k in req_lower for k in ["email", "draft", "mail", "notify", "inform"])
    has_nav_kw = any(k in req_lower for k in ["navigate", "direction", "where is", "map", "distance", "location", "way to"])

    # Synthesis request check
    if any(k in req_lower for k in ["roadmap", "summarize", "situation", "overview", "guidance", "recommend"]):
        if has_placement_kw:
            return [PlanStep(id=1, agent="placement", action="general_synthesis", params={"query": clean_req})]
        elif has_exam_kw or has_attend_kw:
            return [PlanStep(id=1, agent="academic", action="general_synthesis", params={"query": clean_req})]
        elif has_nav_kw:
            return [PlanStep(id=1, agent="navigator", action="general_synthesis", params={"query": clean_req})]
        else:
            return [PlanStep(id=1, agent="campus", action="general_synthesis", params={"query": clean_req})]

    # Navigation query
    if has_nav_kw:
        return [PlanStep(id=1, agent="navigator", action="get_directions", params={"destination": clean_req})]

    # DBMS Exam study plan query
    if "dbms" in req_lower or ("exam" in req_lower and ("day" in req_lower or "plan" in req_lower or "study" in req_lower)):
        return [PlanStep(id=1, agent="academic", action="create_study_plan", params={"subject": "DBMS", "days_remaining": 10})]

    # Placement + Event + Reminder chain
    if has_placement_kw and has_action_kw:
        company = "Google" if "google" in req_lower else ("Microsoft" if "microsoft" in req_lower else "Dream Tier")
        return [
            PlanStep(id=1, agent="placement", action="check_eligibility", params={"company": company, "query": clean_req}),
            PlanStep(id=2, agent="events", action="get_events", params={"query": f"workshops for {company}"}, depends_on=[1]),
            PlanStep(id=3, agent="communication", action="schedule_reminder", params={"event": f"{company} Placement Drive"}, depends_on=[2])
        ]

    # Exam / Attendance + Email chain
    if (has_exam_kw or has_attend_kw) and (has_comm_kw or "eligibility" in req_lower):
        return [
            PlanStep(id=1, agent="academic", action="get_attendance", params={"query": clean_req}),
            PlanStep(id=2, agent="academic", action="get_exam_schedule", params={"query": clean_req}, depends_on=[1]),
            PlanStep(id=3, agent="communication", action="draft_email", params={"subject": "Academic Attendance & Exam Inquiry"}, depends_on=[2])
        ]

    # Attendance standalone
    if has_attend_kw:
        return [PlanStep(id=1, agent="academic", action="get_attendance", params={"query": clean_req})]

    # Placement standalone
    if has_placement_kw:
        company = "Google" if "google" in req_lower else ("Microsoft" if "microsoft" in req_lower else "Dream Tier")
        return [PlanStep(id=1, agent="placement", action="check_eligibility", params={"company": company, "query": clean_req})]

    # Hostel / Campus standalone
    if any(k in req_lower for k in ["hostel", "curfew", "gate", "dorm", "warden", "mess"]):
        return [PlanStep(id=1, agent="campus", action="get_hostel_info", params={"query": user_request})]

    # Default fallback to academic synthesis
    return [PlanStep(id=1, agent="academic", action="general_synthesis", params={"query": user_request})]


def plan(user_request: str) -> list[PlanStep]:
    """
    Intelligent LLM-based planner with pattern-based fallback safety net and step cap (max 5).
    """
    clean_req = user_request
    if "[Previous Context:" in user_request and "]" in user_request:
        clean_req = user_request.split("]")[-1].strip()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        try:
            # pyrefly: ignore [missing-import]
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=3.5)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                system=PLANNING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": clean_req}],
            )
            raw_text = response.content[0].text.strip()
            
            # Log raw output for debugging
            RAW_LLM_PLAN_LOGS.append({"request": clean_req, "raw_response": raw_text})

            # Clean JSON fences if present
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()

            parsed = json.loads(raw_text)
            step_dicts = parsed.get("steps", [])

            steps = [PlanStep(**s) for s in step_dicts if s.get("agent") in AGENT_REGISTRY]
            if steps:
                # Guardrail: Cap steps to max 5
                steps = steps[:5]
                return steps
        except Exception as e:
            logger.warning(f"LLM planner failed or timed out: {e}. Falling back to keyword planner.")

    # Fallback path if LLM unavailable or failed
    fallback_steps = keyword_plan(clean_req, user_request)
    return fallback_steps[:5]


def dispatch(steps: list[PlanStep], session_id: str = "default", on_step_update=None) -> list[PlanStep]:
    """
    Executes plan steps in dependency order, injecting session_id into parameters
    and recording completed turns into SQLite conversation_history memory.
    """
    completed_ids = set()

    if not get_profile(session_id):
        create_session(session_id)

    while len(completed_ids) < len(steps):
        made_progress = False

        for step in steps:
            if step.id in completed_ids:
                continue
            if not all(dep in completed_ids for dep in step.depends_on):
                continue

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


def run(user_request: str, session_id: str = "default", on_step_update=None) -> list[PlanStep]:
    resolved_request = resolve_context(session_id, user_request)
    add_turn(session_id=session_id, role="user", content=resolved_request)
    steps = plan(resolved_request)
    return dispatch(steps, session_id=session_id, on_step_update=on_step_update)


if __name__ == "__main__":
    test_session = "demo_session_001"
    create_session(test_session, {"cgpa": 8.5, "backlog_count": 0, "attendance_pct": 88.0})

    print("--- Running Orchestrator Test ---")
    results = run("make me a roadmap for placements and summarize my situation", session_id=test_session)
    for s in results:
        res = s.result
        print(f"Step {s.id} [{s.agent}.{s.action}] -> Status: {s.status}")
        print(f"  Message : {res.message if res else ''}")
        print(f"  Citation: {res.citation if res else ''}")
