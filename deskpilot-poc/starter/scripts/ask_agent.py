"""Talk to one of the agents from the terminal (used to test steps 2.1 to 3.1).

Run:  python scripts/ask_agent.py --agent knowledge
      python scripts/ask_agent.py --agent ticket --user aarav.shah
      python scripts/ask_agent.py --agent deskpilot --user it.admin     (triage + routing, step 3.1)
Type `exit` to stop.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config, db
from common.clients import get_project_clients


def show_trace(tools, citations, files) -> None:
    for tool in tools:
        print(f"   [tool] {tool['name']} ({tool['type']})")
    for citation in citations:
        print(f"   [source] {citation.get('title') or citation.get('url')}")
    for path in files:
        print(f"   [file] {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["knowledge", "ticket", "deskpilot"], required=True)
    parser.add_argument("--user", default="aarav.shah", choices=list(config.USERS))
    args = parser.parse_args()
    config.require("PROJECT_ENDPOINT", "AZURE_OPENAI_ENDPOINT")
    db.init_db()

    if args.agent == "deskpilot":
        from agents.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        session = orchestrator.new_session(args.user)
        ask = lambda text: orchestrator.handle(session, text)  # noqa: E731
        close = orchestrator.mcp.close
    else:
        project_client, openai_client = get_project_clients()
        if args.agent == "knowledge":
            from agents.knowledge_agent import KnowledgeAgent
            agent = KnowledgeAgent(project_client, openai_client)
            conversation = agent.new_conversation()
            ask = lambda text: agent.ask(conversation, text)  # noqa: E731
            close = lambda: None  # noqa: E731
        else:
            from agents.ticket_agent import TicketAgent
            mcp = _start_mcp()
            agent = TicketAgent(openai_client, mcp)
            conversation = agent.new_conversation()
            ask = lambda text: agent.ask(conversation, text, args.user)  # noqa: E731
            close = mcp.close if mcp else (lambda: None)

    print(f"Talking to '{args.agent}' as {args.user}. Type exit to stop.")
    try:
        while True:
            text = input("\nYou: ").strip()
            if text.lower() in ("exit", "quit", ""):
                break
            result = ask(text)
            print("Agent:", result.text)
            show_trace(result.tools, result.citations, result.files)
            if hasattr(result, "route"):
                print(f"   [route] {result.route} -> {result.agent}")
    finally:
        close()


def _start_mcp():
    """Start the local ticket MCP server. Before step 2.3 it is not implemented yet, so continue without it."""
    try:
        from common.mcp_client import TicketMCP
        return TicketMCP()
    except Exception as ex:  # noqa: BLE001
        print(f"(MCP server not available yet: {type(ex).__name__}. Continuing with custom functions only.)")
        return None


if __name__ == "__main__":
    main()
