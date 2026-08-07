import os
import uuid
import httpx
from typing import Dict, Any, List, Optional


class TodoistAdapter:
    """
    Adapter for Todoist REST API v2.
    Provides create_task, get_tasks, update_task, complete_task, and create_study_plan.
    Falls back gracefully to mock in-memory task log if API key is missing or fails.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TODOIST_API_KEY")
        self._mock_tasks: List[Dict[str, Any]] = []

    async def get_tasks(self) -> Dict[str, Any]:
        if self.api_key:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get("https://api.todoist.com/rest/v2/tasks", headers=headers)
                    if resp.status_code == 200:
                        tasks = resp.json()
                        return {"source": "live", "tasks": tasks}
            except Exception as exc:
                print(f"[TodoistAdapter] Live API call failed ({exc}). Falling back to mock response.")

        return {"source": "mock", "tasks": self._mock_tasks}

    async def create_task(self, content: str, due_string: str = "today", priority: int = 1) -> Dict[str, Any]:
        if self.api_key:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"content": content, "due_string": due_string, "priority": priority}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post("https://api.todoist.com/rest/v2/tasks", json=payload, headers=headers)
                    if resp.status_code in [200, 201]:
                        return {"source": "live", "task": resp.json()}
            except Exception as exc:
                print(f"[TodoistAdapter] Live API call failed ({exc}). Falling back to mock response.")

        mock_task = {
            "id": f"todoist-{uuid.uuid4().hex[:8]}",
            "content": content,
            "due_string": due_string,
            "priority": priority,
            "is_completed": False
        }
        self._mock_tasks.append(mock_task)
        return {"source": "mock", "task": mock_task}

    async def update_task(self, task_id: str, content: str) -> Dict[str, Any]:
        if self.api_key:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(f"https://api.todoist.com/rest/v2/tasks/{task_id}", json={"content": content}, headers=headers)
                    if resp.status_code == 200:
                        return {"source": "live", "task": resp.json()}
            except Exception as exc:
                print(f"[TodoistAdapter] Live API call failed ({exc}). Falling back to mock response.")

        for t in self._mock_tasks:
            if t["id"] == task_id:
                t["content"] = content
                return {"source": "mock", "task": t}

        return {"source": "mock", "updated_id": task_id, "status": "updated"}

    async def complete_task(self, task_id: str) -> Dict[str, Any]:
        if self.api_key:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(f"https://api.todoist.com/rest/v2/tasks/{task_id}/close", headers=headers)
                    if resp.status_code == 204:
                        return {"source": "live", "task_id": task_id, "status": "completed"}
            except Exception as exc:
                print(f"[TodoistAdapter] Live API call failed ({exc}). Falling back to mock response.")

        for t in self._mock_tasks:
            if t["id"] == task_id:
                t["is_completed"] = True

        return {"source": "mock", "task_id": task_id, "status": "completed"}

    async def create_study_plan(self, subject: str, days_left: int, exam_date: str) -> Dict[str, Any]:
        """
        Generates a structured study plan and materializes tasks.
        """
        plan_steps = [
            f"Day 1-{max(1, days_left//3)}: Review {subject} core concepts & lecture slides",
            f"Day {max(2, days_left//3 + 1)}-{max(2, (days_left*2)//3)}: Solve {subject} previous year question papers & assignments",
            f"Day {max(3, (days_left*2)//3 + 1)}-{days_left}: Final revision & formula/definition cheat sheet practice"
        ]

        created_tasks = []
        for step in plan_steps:
            res = await self.create_task(content=f"[{subject} Study Plan] {step}", due_string=f"before {exam_date}")
            created_tasks.append(res.get("task"))

        source = "live" if any(t.get("source") == "live" for t in created_tasks if isinstance(t, dict)) else "mock"

        return {
            "source": source,
            "subject": subject,
            "days_left": days_left,
            "exam_date": exam_date,
            "plan_steps": plan_steps,
            "materialized_tasks": created_tasks
        }
