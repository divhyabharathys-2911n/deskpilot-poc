"""The orchestrator: one entry point for the whole system.

triage agent -> picks a route -> knowledge agent or ticket agent -> answer + trace.
Identity (the signed-in user) is held by the app and passed to tools; the model never supplies it.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from common import config, db
from common.clients import get_project_clients
from common.mcp_client import TicketMCP
from . import triage_agent
from .knowledge_agent import KnowledgeAgent
from .ticket_agent import TicketAgent

REFUSAL = ("I can't help with that request. I can help with IT questions, such as VPN, passwords, "
           "email, printing, and with your support tickets.")
OTHER = ("I'm the DeskPilot IT help desk assistant. Ask me an IT question, or ask me to create or "
         "check a ticket.")


@dataclass
class Session:
    user: str
    knowledge_conversation: str
    ticket_conversation: str
    history: list = field(default_factory=list)  # [{"role": "user"|"assistant", "content": str}]


@dataclass
class Reply:
    text: str
    route: str
    agent: str
    reason: str = ""
    tools: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    files: list = field(default_factory=list)
    blocked: bool = False
    error: str | None = None


def _log_blocked(user: str, text: str, why: str) -> None:
    """Keep a simple audit trail of blocked requests."""
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "user": user,
             "message": text[:500], "why": why}
    with open(config.OUTPUT_DIR / "blocked.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


class Orchestrator:
    def __init__(self, mcp: TicketMCP | None = None) -> None:
        db.init_db()
        self.project_client, self.openai_client = get_project_clients()
        self.mcp = mcp or TicketMCP()
        self.knowledge = KnowledgeAgent(self.project_client, self.openai_client)
        self.tickets = TicketAgent(self.openai_client, self.mcp)

    def new_session(self, user: str) -> Session:
        return Session(user=user,
                       knowledge_conversation=self.knowledge.new_conversation(),
                       ticket_conversation=self.tickets.new_conversation())

    def _ticket_request(self, session: Session, text: str) -> str:
        """Give the ticket agent a little context, so 'open a ticket for that' makes sense."""
        recent = session.history[-4:]
        if not recent:
            return text
        context = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in recent)
        return f"Recent conversation, for context only:\n{context}\n\nUser request: {text}"

    def handle(self, session: Session, text: str) -> Reply:
        try:
            decision = triage_agent.classify(self.openai_client, text, session.history)
            route, reason = decision["route"], decision["reason"]

            # TODO 3.1.c: Dispatch on route. "unsafe": call _log_blocked(session.user, text,
            # reason) and return Reply(REFUSAL, route, "triage", reason, blocked=True).
            # "other": return Reply(OTHER, ...). "ticket": turn =
            # self.tickets.ask(session.ticket_conversation, self._ticket_request(session,
            # text), session.user), agent name "ticket". Otherwise (knowledge): turn =
            # self.knowledge.ask(session.knowledge_conversation, text). Build the Reply from
            # turn.text, turn.tools, turn.citations and turn.files
            if route == "unsafe":
                _log_blocked(session.user, text, reason)
                reply = Reply(REFUSAL, route, "triage", reason, blocked=True)
            elif route == "other":
                reply = Reply(OTHER, route, "triage", reason)
            else:
                if route == "ticket":
                    turn = self.tickets.ask(session.ticket_conversation, self._ticket_request(session, text),
                        session.user)
                    agent = "ticket"
                else:
                    turn = self.knowledge.ask(session.knowledge_conversation, text)
                    agent = "knowledge"
                reply = Reply(turn.text, route, agent, reason, turn.tools, turn.citations, turn.files)
        except Exception as ex:  # keep the UI alive; show the problem instead of crashing
            if "content_filter" in str(ex).lower():
                _log_blocked(session.user, text, "Blocked by the Foundry content filter")
                reply = Reply(REFUSAL, "unsafe", "content filter", "Blocked by the Foundry content filter", blocked=True)
            else:
                reply = Reply("Sorry, something went wrong while handling that request.", "error", "none",
                              error=f"{type(ex).__name__}: {ex}")
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": reply.text})
        return reply
