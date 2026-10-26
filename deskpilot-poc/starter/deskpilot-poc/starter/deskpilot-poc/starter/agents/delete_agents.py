"""Delete the agents created by code (clean-up). Add --all to also delete the portal-built knowledge agent.

Run:  python agents/delete_agents.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config
from common.clients import get_project_clients

if __name__ == "__main__":
    project_client, _ = get_project_clients()
    names = [config.TICKET_AGENT_NAME, config.TRIAGE_AGENT_NAME]
    if "--all" in sys.argv:
        names.append(config.KNOWLEDGE_AGENT_NAME)
    for name in names:
        try:
            project_client.agents.delete(agent_name=name)
            print("Deleted", name)
        except Exception as ex:
            print(f"Could not delete {name}: {ex}")
