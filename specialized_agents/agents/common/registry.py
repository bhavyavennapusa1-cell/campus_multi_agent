import json
import logging
import sys
import time
from typing import Dict, Optional, Any
from agents.common.envelope import AgentClient, TaskRequest, ResponseEnvelope

# Configure structured logger for agent-to-agent (A2A) interactions
logger = logging.getLogger("A2A_TraceLogger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

MAX_A2A_DEPTH = 3


class A2ADepthExceededError(Exception):
    """Raised when agent-to-agent call stack exceeds maximum allowed depth."""
    pass


class A2AClientProxy:
    """
    Proxy wrapper around an AgentClient instance.
    Intercepts calls to handle() to enforce:
    1. Maximum call depth tracking (capped at 3)
    2. Latency measurement & structured JSON trace logging
    3. Graceful degradation on downstream failure
    """
    def __init__(self, target_name: str, target_agent: AgentClient, caller_name: str, registry: "AgentRegistry"):
        self.target_name = target_name
        self.target_agent = target_agent
        self.caller_name = caller_name
        self.registry = registry

    async def handle(self, task: TaskRequest) -> ResponseEnvelope:
        current_depth = task.context.get("call_depth", 0)
        
        # 1. Depth check guard
        if current_depth >= MAX_A2A_DEPTH:
            err_msg = f"A2A call depth limit ({MAX_A2A_DEPTH}) exceeded when calling '{self.target_name}' from '{self.caller_name}'."
            log_payload = {
                "event": "A2A_DEPTH_EXCEEDED",
                "trace_id": task.trace_id,
                "caller": self.caller_name,
                "target": self.target_name,
                "tool": task.task,
                "depth": current_depth,
                "error": err_msg
            }
            logger.error(json.dumps(log_payload))
            return ResponseEnvelope(
                agent=self.target_name,
                status="error",
                data={"error": err_msg, "depth_exceeded": True},
                message=err_msg,
                trace_id=task.trace_id
            )

        # Update depth counter in context
        new_context = dict(task.context)
        new_context["call_depth"] = current_depth + 1
        inner_task = TaskRequest(
            trace_id=task.trace_id,
            task=task.task,
            params=task.params,
            student_id=task.student_id,
            context=new_context
        )

        start_time = time.perf_counter()
        try:
            # 2. Invoke target agent
            response = await self.target_agent.handle(inner_task)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 3. Structured JSON trace log line
            log_payload = {
                "event": "A2A_CALL",
                "trace_id": task.trace_id,
                "caller": self.caller_name,
                "target": self.target_name,
                "tool": task.task,
                "input": task.params,
                "output_status": response.status,
                "output_data_summary": {k: v for k, v in response.data.items() if k != "full_text"},
                "latency_ms": latency_ms
            }
            logger.info(json.dumps(log_payload))

            return response

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            err_msg = f"A2A call to '{self.target_name}' failed: {str(exc)}"
            
            log_payload = {
                "event": "A2A_CALL_FAILED",
                "trace_id": task.trace_id,
                "caller": self.caller_name,
                "target": self.target_name,
                "tool": task.task,
                "latency_ms": latency_ms,
                "error": str(exc)
            }
            logger.error(json.dumps(log_payload))

            # Graceful degradation - return partial / error envelope without crashing parent
            return ResponseEnvelope(
                agent=self.target_name,
                status="partial",
                data={"error": err_msg, "degraded": True},
                message=f"Sub-agent '{self.target_name}' unavailable or encountered error: {str(exc)}",
                trace_id=task.trace_id
            )


class AgentRegistry:
    """
    Lightweight Agent Registry managing agent instances.
    Provides decoupled agent lookup and A2A communication proxies.
    """
    def __init__(self):
        self._agents: Dict[str, AgentClient] = {}

    def register(self, name: str, agent: AgentClient) -> None:
        """Register an agent instance by name."""
        self._agents[name.lower()] = agent

    def get(self, name: str, caller_name: str = "orchestrator") -> AgentClient:
        """
        Get an agent client proxy.
        If caller_name is provided, returns an A2AClientProxy that handles depth tracking,
        structured logging, and graceful error handling.
        """
        key = name.lower()
        if key not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry. Registered agents: {list(self._agents.keys())}")
        
        target_agent = self._agents[key]
        return A2AClientProxy(target_name=key, target_agent=target_agent, caller_name=caller_name, registry=self)

    async def call_agent(
        self,
        caller: str,
        target: str,
        task: str,
        params: dict,
        student_id: Optional[str],
        trace_id: str,
        context: Optional[dict] = None
    ) -> ResponseEnvelope:
        """
        Convenience helper for explicit A2A agent dispatch.
        """
        proxy = self.get(target, caller_name=caller)
        req = TaskRequest(
            trace_id=trace_id,
            task=task,
            params=params,
            student_id=student_id,
            context=context or {}
        )
        return await proxy.handle(req)
