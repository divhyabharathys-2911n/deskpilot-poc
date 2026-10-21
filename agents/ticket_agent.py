"""Ticket agent: creates, reads and updates tickets, and builds reports.

Tools:
  * custom functions  create_ticket, get_ticket       (run inside this app)
  * MCP tools         list_tickets, update_ticket     (run in the ticket MCP server)
  * code interpreter  charts and counts on ticket data (runs in the Foundry sandbox)
"""
import json

from azure.ai.projects.models import CodeInterpreterTool, PromptAgentDefinition, RaiConfig

from common import config, functions
from common.mcp_client import TicketMCP
from .runtime import TurnResult, run_agent_turn

INSTRUCTIONS = """You are the DeskPilot ticket agent for an IT help desk.

Rules:
- You only handle tickets: create, look up, list, update, and reports about tickets.
- Before calling create_ticket you need a clear title, a description, a category and a priority.
  If something is missing, ask the user one short question. Do not invent details.
- Priority guide: Low = minor or cosmetic, Medium = degraded but workable, High = the user cannot work,
  Critical = security incident (clicked a phishing link, malware, lost or stolen device) or a safety risk.
- Use get_ticket when the user gives a ticket ID such as INC-1042.
- Use list_tickets to list tickets or when a report is requested.
- Reports and charts: call list_tickets with limit 200, then use the code interpreter on the rows it
  returned (copy them into Python). Keep charts simple: a title, labelled axes, one chart per request.
  Then say in one or two sentences what the chart shows.
- Only say an action is done if the tool result confirms it. If a tool returns an error, tell the user
  plainly what happened. The tools enforce permissions, so never try to work around them.
- Keep answers short."""


def create_ticket_agent(project_client, mcp: TicketMCP | None = None):
    """Create a new version of the ticket agent. Pass mcp=None for functions only (step 2.2)."""
    # TODO 2.2.g: Start with tools = list(functions.FUNCTION_TOOLS)
    raise NotImplementedError("TODO 2.2.g")
    if mcp is not None:
        # TODO 2.3.i: Add the MCP tools and the code interpreter: tools +=
        # mcp.function_tools() + [CodeInterpreterTool()]
        raise NotImplementedError("TODO 2.3.i")
    options = {}
    if config.RAI_POLICY_NAME:
        options["rai_config"] = RaiConfig(rai_policy_name=config.RAI_POLICY_NAME)
    # TODO 2.2.h: Create the agent:
    # project_client.agents.create_version(agent_name=config.TICKET_AGENT_NAME,
    # definition=PromptAgentDefinition(model=config.MODEL_DEPLOYMENT,
    # instructions=INSTRUCTIONS, tools=tools, **options)). Return it
    raise NotImplementedError("TODO 2.2.h")


class TicketAgent:
    def __init__(self, openai_client, mcp: TicketMCP | None = None) -> None:
        self.openai_client = openai_client
        self.mcp = mcp
        self.name = config.TICKET_AGENT_NAME

    def new_conversation(self) -> str:
        return self.openai_client.conversations.create(items=[]).id

    def _dispatch(self, name: str, arguments_json: str, requester: str) -> str:
        """Run a tool the agent asked for, always as the signed-in user."""
        if name in functions.HANDLERS:
            return functions.run_function(name, arguments_json, requester)
        if self.mcp is not None and self.mcp.has_tool(name):
            try:
                arguments = json.loads(arguments_json or "{}")
            except json.JSONDecodeError:
                return json.dumps({"error": "Arguments were not valid JSON."})
            return self.mcp.call(name, arguments, requester)
        return json.dumps({"error": f"Unknown tool '{name}'."})

    def ask(self, conversation_id: str, text: str, requester: str) -> TurnResult:
        return run_agent_turn(
            self.openai_client, self.name, conversation_id, text,
            function_handler=lambda name, args: self._dispatch(name, args, requester),
        )
