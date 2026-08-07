"""
Orchestrator for Smart Campus Multi-Agent System.
Parses user queries, resolves context from memory, generates execution plan steps (via live LLM planner with keyword fallback),
dispatches to specialized agents, logs conversation turns, and returns completed steps.
"""

import json
import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure root project directory is at index 0 of sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if sys.path[0] != str(PROJECT_ROOT):
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib.util

from shared.schemas import PlanStep, AGENT_ACTIONS, AgentResponse
from knowledge.memory import resolve_context, add_turn, get_profile, create_session

def _load_root_agent(name: str):
    file_path = PROJECT_ROOT / "agents" / f"{name}_agent.py"
    spec = importlib.util.spec_from_file_location(f"root_{name}_agent", file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

AGENT_REGISTRY = {
    "academic": _load_root_agent("academic"),
    "placement": _load_root_agent("placement"),
    "campus": _load_root_agent("campus"),
    "communication": _load_root_agent("communication"),
}

# Debug log list for raw LLM planner output (not shown to user)
RAW_PLANNING_LOGS: List[Dict[str, Any]] = []

MAX_PLAN_STEPS = 5  # Guardrail: cap total steps per plan to avoid runaway chains

PLANNING_SYSTEM_PROMPT = f"""You are the intelligent multi-agent planning module of a Smart Campus Assistant.
Given a user request, break it into a JSON list of step objects. Each step must use
one of these agents and actions:

{json.dumps(AGENT_ACTIONS, indent=2)}

FEW-SHOT EXAMPLES:

Example 1 (Single specific query):
User: "Am I eligible for Google placement?"
JSON:
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "check_eligibility", "params": {{"company": "Google"}}, "depends_on": []}}
  ]
}}

Example 2 (Chained multi-step query):
User: "Check if I can get into Google, then register me for the placement workshop and set a reminder."
JSON:
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "check_eligibility", "params": {{"company": "Google"}}, "depends_on": []}},
    {{"id": 2, "agent": "campus", "action": "get_events", "params": {{"query": "placement workshop"}}, "depends_on": [1]}},
    {{"id": 3, "agent": "communication", "action": "schedule_reminder", "params": {{"event": "Google placement workshop"}}, "depends_on": [2]}}
  ]
}}

Example 3 (Open-ended query / roadmap / advice):
User: "give me a roadmap to get placement-ready and summarize my situation"
JSON:
{{
  "steps": [
    {{"id": 1, "agent": "placement", "action": "general_synthesis", "params": {{"query": "give me a roadmap to get placement-ready"}}, "depends_on": []}}
  ]
}}

Example 4 (Open-ended campus / academic guidance):
User: "what are the hostel rules and how do I file a grievance?"
JSON:
{{
  "steps": [
    {{"id": 1, "agent": "campus", "action": "general_synthesis", "params": {{"query": "hostel rules and grievance guidance"}}, "depends_on": []}}
  ]
}}

Return ONLY valid JSON with a "steps" array. No conversational text outside JSON.
"""


def _llm_plan(user_request: str) -> Optional[List[PlanStep]]:
    """
    Attempts to call live LLM API (Anthropic or OpenAI) with a short timeout to generate a structured execution plan.
    Returns list of PlanStep objects or None if API key missing, timeout occurs, or parsing fails.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    raw_text = None

    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=5.0)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=PLANNING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_request}],
            )
            raw_text = response.content[0].text
        except Exception as e:
            logger.warning(f"Anthropic LLM planning call failed or timed out: {e}")

    elif openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key, timeout=5.0)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_request}
                ],
                temperature=0.0
            )
            raw_text = response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI LLM planning call failed or timed out: {e}")

    if not raw_text:
        return None

    # Log raw output for debugging
    RAW_PLANNING_LOGS.append({
        "user_request": user_request,
        "raw_response": raw_text
    })

    try:
        # Extract JSON block if wrapped in Markdown code blocks
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            parsed = json.loads(clean_json)
            steps_data = parsed.get("steps", [])

            steps = []
            for item in steps_data:
                agent = item.get("agent", "academic")
                action = item.get("action", "general_synthesis")
                # Validate agent and action against schema
                if agent not in AGENT_REGISTRY:
                    agent = "academic"
                valid_actions = AGENT_ACTIONS.get(agent, [])
                if action not in valid_actions:
                    action = "general_synthesis"

                steps.append(PlanStep(
                    id=int(item.get("id", len(steps) + 1)),
                    agent=agent,
                    action=action,
                    params=item.get("params", {}),
                    depends_on=item.get("depends_on", [])
                ))

            if steps:
                return steps
    except Exception as e:
        logger.error(f"Failed to parse LLM planning JSON output: {e}. Raw: {raw_text[:200]}")

    return None


def _keyword_plan(user_request: str) -> List[PlanStep]:
    """
    Fallback keyword-matching planner.
    Acts as the safety net when LLM API keys are not set, call times out, or parsing fails.
    """
    clean_req = user_request
    if "[Previous Context:" in user_request and "]" in user_request:
        clean_req = user_request.split("]")[-1].strip()

    req_lower = clean_req.lower()

    # Open-ended roadmap / synthesis queries
    if any(k in req_lower for k in ["roadmap", "overview", "guidance", "ready", "summarize"]):
        if any(k in req_lower for k in ["placement", "job", "career", "interview"]):
            return [PlanStep(id=1, agent="placement", action="general_synthesis", params={"query": clean_req}, depends_on=[])]
        elif any(k in req_lower for k in ["hostel", "campus", "grievance"]):
            return [PlanStep(id=1, agent="campus", action="general_synthesis", params={"query": clean_req}, depends_on=[])]
        else:
            return [PlanStep(id=1, agent="academic", action="general_synthesis", params={"query": clean_req}, depends_on=[])]

    # Academic attendance queries
    if any(k in req_lower for k in ["attend", "absent", "condon", "detain", "percentage", "shortage"]):
        return [PlanStep(id=1, agent="academic", action="get_attendance", params={"query": clean_req}, depends_on=[])]

    # Placement queries
    if any(k in req_lower for k in ["eligib", "placement", "dream", "company", "google", "microsoft", "salesforce", "oracle", "cognizant", "tcs"]):
        company = "Dream Tier"
        if "google" in req_lower: company = "Google"
        elif "microsoft" in req_lower: company = "Microsoft"
        elif "salesforce" in req_lower: company = "Salesforce"
        elif "oracle" in req_lower: company = "Oracle India"
        elif "cognizant" in req_lower: company = "Cognizant"
        elif "tcs" in req_lower: company = "TCS"

        return [PlanStep(id=1, agent="placement", action="check_eligibility", params={"company": company, "query": clean_req}, depends_on=[])]

    # Campus queries
    if any(k in req_lower for k in ["hostel", "curfew", "gate", "late", "outpass", "dorm", "warden", "mess", "visitor"]):
        return [PlanStep(id=1, agent="campus", action="get_hostel_info", params={"query": user_request}, depends_on=[])]

    if any(k in req_lower for k in ["event", "hackathon", "fest", "symposium", "coding"]):
        return [PlanStep(id=1, agent="campus", action="get_events", params={"query": user_request}, depends_on=[])]

    if any(k in req_lower for k in ["grievance", "complaint", "issue", "sla"]):
        return [PlanStep(id=1, agent="campus", action="file_grievance", params={"query": user_request, "text": user_request}, depends_on=[])]

    # Exam and Timetable
    if any(k in req_lower for k in ["exam", "grade", "marks", "revalu", "backlog", "passing"]):
        return [PlanStep(id=1, agent="academic", action="get_exam_schedule", params={"query": user_request}, depends_on=[])]

    if any(k in req_lower for k in ["timetable", "schedule", "class", "today"]):
        return [PlanStep(id=1, agent="academic", action="get_timetable", params={"query": user_request}, depends_on=[])]

    # Communication
    if any(k in req_lower for k in ["email", "draft", "mail"]):
        return [PlanStep(id=1, agent="communication", action="draft_email", params={"body": user_request}, depends_on=[])]

    if any(k in req_lower for k in ["remind", "reminder", "alarm"]):
        return [PlanStep(id=1, agent="communication", action="schedule_reminder", params={"event": user_request}, depends_on=[])]

    # Default fallback to academic general synthesis
    return [PlanStep(id=1, agent="academic", action="general_synthesis", params={"query": user_request}, depends_on=[])]


def plan(user_request: str) -> List[PlanStep]:
    """
    Primary planner entry point:
    1. Attempts live LLM planning.
    2. Falls back to keyword matching planner if LLM call fails, times out, or API key is absent.
    3. Applies guardrail: caps maximum execution steps at MAX_PLAN_STEPS (5 steps).
    """
    steps = _llm_plan(user_request)
    if not steps:
        steps = _keyword_plan(user_request)

    # GUARDRAIL: Cap total agent steps per plan (max 5)
    steps = steps[:MAX_PLAN_STEPS]
    return steps


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
                dep_step = next((s for s in steps if s.id == dep_id), None)
                if dep_step and dep_step.result:
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
    """
    Primary orchestrator entry point:
    1. Resolves context from memory.
    2. Logs the user's turn.
    3. Plans and dispatches execution steps.
    """
    resolved_request = resolve_context(session_id, user_request)
    add_turn(session_id=session_id, role="user", content=resolved_request)
    steps = plan(resolved_request)
    return dispatch(steps, session_id=session_id, on_step_update=on_step_update)


if __name__ == "__main__":
    test_session = "demo_session_001"
    create_session(test_session, {"cgpa": 8.5, "backlog_count": 0, "attendance_pct": 88.0})

    print("--- Running Orchestrator LLM Planner & Fallback Test ---")
    results = run("give me a roadmap for placements and check Google eligibility", session_id=test_session)
    for s in results:
        res = s.result
        print(f"Step {s.id} [{s.agent}.{s.action}] -> Status: {s.status}")
        print(f"  Message : {res.message if res else ''}")
        print(f"  Citation: {res.citation if res else ''}")
