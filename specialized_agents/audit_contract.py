import glob
import re
import asyncio
import json
import uuid

from agents.common.envelope import TaskRequest, ResponseEnvelope
from agents.common.registry import AgentRegistry
from agents.academic_agent.agent import AcademicAgent
from agents.placement_agent.agent import PlacementAgent
from agents.campus_agent.agent import CampusAgent
from agents.communication_agent.agent import CommunicationAgent
from agents.academic_agent.repo import AcademicRepo


def test_contract_compliance():
    agent_files = glob.glob('agents/*_agent/agent.py')
    valid_statuses = {'success', 'partial', 'error', 'needs_clarification'}
    found_statuses = set()

    for file_path in agent_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'async def handle(self, task: TaskRequest) -> ResponseEnvelope:' not in content:
            print(f"FAIL: Signature mismatch in {file_path}")
            return False

        matches = re.findall(r'status=["\']([^"\']+)["\']', content)
        for m in matches:
            found_statuses.add(m)
            if m not in valid_statuses:
                print(f"FAIL: Invalid status '{m}' in {file_path}")
                return False

    print("CONTRACT COMPLIANCE: PASS")
    print("Agent handle signatures verified.")
    print("Found status values assigned:", found_statuses)
    return True


if __name__ == "__main__":
    test_contract_compliance()
