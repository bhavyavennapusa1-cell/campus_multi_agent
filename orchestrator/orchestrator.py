"""
Person A owns this file. This is the core of the whole project.

Two jobs:
  1. plan() - one LLM call that turns a user request into a list of PlanSteps
  2. dispatch() - executes those steps in dependency order, calling into
     agents/*.py, and re-plans if a step fails

Fill in the TODO where the actual LLM call goes - use whichever you have
an API key for (Anthropic or OpenAI both work fine here).
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared.schemas import PlanStep, AGENT_ACTIONS

from agents import academic_agent, placement_agent, campus_agent, communication_agent

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
    TODO Person A: replace this with a real API call. Example using Anthropic:

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

    Below is a hardcoded fallback so the rest of the team can build against
    something real today, before the LLM call is wired in.
    """
    if "eligib" in user_request.lower() or "google" in user_request.lower():
        return [
            PlanStep(id=1, agent="placement", action="check_eligibility",
                      params={"company": "Google", "student_id": "S001"}, depends_on=[]),
            PlanStep(id=2, agent="campus", action="get_events", params={}, depends_on=[1]),
            PlanStep(id=3, agent="communication", action="schedule_reminder",
                      params={"event": "placement workshop", "minutes_before": 60}, depends_on=[2]),
        ]

    return [PlanStep(id=1, agent="academic", action="get_timetable", params={}, depends_on=[])]


def dispatch(steps: list[PlanStep], on_step_update=None) -> list[PlanStep]:
    """
    Executes steps in dependency order. on_step_update(step) is an optional
    callback - Person D's frontend passes this in to update the trace panel
    live as each step runs.
    """
    completed_ids = set()

    while len(completed_ids) < len(steps):
        made_progress = False

        for step in steps:
            if step.id in completed_ids:
                continue
            if not all(dep in completed_ids for dep in step.depends_on):
                continue  # waiting on a dependency

            step.status = "running"
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

            # if this step depends on an earlier one, pass its result forward
            for dep_id in step.depends_on:
                dep_step = next(s for s in steps if s.id == dep_id)
                if dep_step.result:
                    step.params["_previous_result"] = dep_step.result.data

            result = agent_module.handle(step.action, step.params)
            step.result = result
            step.status = "failed" if result.status == "error" else "done"

            if on_step_update:
                on_step_update(step)

            completed_ids.add(step.id)
            made_progress = True

        if not made_progress:
            break  # circular dependency or stuck - avoid infinite loop

    return steps


def run(user_request: str, on_step_update=None) -> list[PlanStep]:
    steps = plan(user_request)
    return dispatch(steps, on_step_update=on_step_update)


if __name__ == "__main__":
    # quick manual test - run this file directly to check the loop works
    result = run("Am I eligible for the Google internship?")
    for s in result:
        print(s.id, s.agent, s.action, "->", s.status, "-", s.result.message if s.result else "")
