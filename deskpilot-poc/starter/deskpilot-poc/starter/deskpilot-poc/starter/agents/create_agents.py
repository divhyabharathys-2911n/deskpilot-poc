"""Create (or add a new version of) the agents that are built by code.

Run:  python agents/create_agents.py                     (ticket + triage)
      python agents/create_agents.py --only ticket --functions-only    (step 2.2)
      python agents/create_agents.py --only ticket                     (step 2.3, adds MCP + code interpreter)
      python agents/create_agents.py --only triage                     (step 3.1)
The knowledge agent is created in the Foundry portal (step 2.1), not here.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.ticket_agent import create_ticket_agent
from agents.triage_agent import create_triage_agent
from common.clients import get_project_clients
from common.mcp_client import TicketMCP


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["ticket", "triage"])
    parser.add_argument("--functions-only", action="store_true",
                        help="ticket agent with the custom functions only (no MCP, no code interpreter)")
    args = parser.parse_args()

    project_client, _ = get_project_clients()
    if args.only in (None, "ticket"):
        mcp = None if args.functions_only else TicketMCP()
        agent = create_ticket_agent(project_client, mcp)
        print(f"Ticket agent ready: {agent.name} version {agent.version}")
        if mcp:
            mcp.close()
    if args.only in (None, "triage"):
        agent = create_triage_agent(project_client)
        print(f"Triage agent ready: {agent.name} version {agent.version}")


if __name__ == "__main__":
    main()
