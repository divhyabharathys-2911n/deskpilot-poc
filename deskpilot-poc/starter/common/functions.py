"""Custom functions the ticket agent can call (they run inside this app).

Pattern from the official "custom function" lab:
  1. Write the Python function.
  2. Describe it to the model with a FunctionTool (a JSON schema).
  3. When the model returns a `function_call`, run the function and send back the output.

Identity rule: `requester` is NEVER part of the schema the model sees. The app
injects the signed-in user, so the model cannot act as someone else.
"""
import json

from azure.ai.projects.models import FunctionTool

from . import db
from .config import CATEGORIES, PRIORITIES


def create_ticket(requester: str, title: str, description: str, category: str, priority: str) -> str:
    """Create a ticket for the requester and return it as JSON."""
    # TODO 2.2.b: Call db.create_ticket(...) and return json.dumps({"status": "created",
    # "ticket": ticket}). Catch ValueError and db.PermissionDenied and return
    # json.dumps({"error": str(ex)})
    raise NotImplementedError("TODO 2.2.b")


def get_ticket(requester: str, ticket_id: str) -> str:
    """Return one ticket as JSON, if the requester is allowed to see it."""
    # TODO 2.2.c: Call db.get_ticket(...) and return json.dumps({"ticket": ticket}). Catch
    # ValueError and db.PermissionDenied and return json.dumps({"error": str(ex)})
    raise NotImplementedError("TODO 2.2.c")


# TODO 2.2.d: Define create_ticket_tool = FunctionTool(...) with name, description, a JSON-
# schema "parameters" object (title, description, category enum, priority enum; all required;
# additionalProperties False) and strict=True
raise NotImplementedError("TODO 2.2.d")

# TODO 2.2.e: Define get_ticket_tool = FunctionTool(...) with one required string parameter
# "ticket_id" (for example INC-1042) and strict=True
raise NotImplementedError("TODO 2.2.e")

FUNCTION_TOOLS = [create_ticket_tool, get_ticket_tool]
HANDLERS = {"create_ticket": create_ticket, "get_ticket": get_ticket}


def run_function(name: str, arguments_json: str, requester: str) -> str:
    """Run one function the model asked for. Returns a JSON string."""
    handler = HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown function '{name}'."})
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "Arguments were not valid JSON."})
    arguments.pop("requester", None)  # never trust an identity supplied by the model
    try:
        return handler(requester=requester, **arguments)
    except TypeError as ex:
        return json.dumps({"error": f"Bad arguments: {ex}"})
