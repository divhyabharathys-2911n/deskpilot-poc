"""Custom functions the ticket agent can call (they run inside this app).

Pattern from the official "custom function" lab:
  1. Write the Python function.
  2. Describe it to the model with a FunctionTool (a JSON schema).
  3. When the model returns a `function_call`, run the function and send back the output.

Identity rule: `requester` is NEVER part of the schema the model sees. The app
injects the signed-in user, so the model cannot act as someone else.
"""
import json
from unicodedata import category

from azure.ai.projects.models import FunctionTool
from streamlit import title

from . import db
from .config import CATEGORIES, PRIORITIES


def create_ticket(requester: str, title: str, description: str, category: str, priority: str) -> str:
    """Create a ticket for the requester and return it as JSON."""
    # TODO 2.2.b: Call db.create_ticket(...) and return json.dumps({"status": "created",
    # "ticket": ticket}). Catch ValueError and db.PermissionDenied and return
    # json.dumps({"error": str(ex)})
    try:
        ticket = db.create_ticket(requester, title, description, category, priority)
        return json.dumps({"status": "created", "ticket": ticket})
    except (ValueError, db.PermissionDenied) as ex:
        return json.dumps({"error": str(ex)})


def get_ticket(requester: str, ticket_id: str) -> str:
    """Return one ticket as JSON, if the requester is allowed to see it."""
    # TODO 2.2.c: Call db.get_ticket(...) and return json.dumps({"ticket": ticket}). Catch
    # ValueError and db.PermissionDenied and return json.dumps({"error": str(ex)})
    try:
        ticket = db.get_ticket(requester, ticket_id)
        return json.dumps({"ticket": ticket})
    except (ValueError, db.PermissionDenied) as ex:
        return json.dumps({"error": str(ex)})


# TODO 2.2.d: Define create_ticket_tool = FunctionTool(...) with name, description, a JSON-
# schema "parameters" object (title, description, category enum, priority enum; all required;
# additionalProperties False) and strict=True
create_ticket_tool = FunctionTool(
    name="create_ticket",
    description="Create a new IT support ticket for the signed-in user. Ask for any missing detail before calling.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short summary of the problem (under 80 characters)."},
            "description": {"type": "string", "description": "What is happening, since when, and what was already tried."},
            "category": {"type": "string", "enum": CATEGORIES, "description": "Ticket category."},
            "priority": {
                "type": "string",
                "enum": PRIORITIES,
                "description": "Low, Medium, High or Critical. Use High if the user cannot work; Critical for security incidents.",
                },
        },
        "required": ["title", "description", "category", "priority"],
        "additionalProperties": False,
    },
    strict=True,
)
# TODO 2.2.e: Define get_ticket_tool = FunctionTool(...) with one required string parameter
# "ticket_id" (for example INC-1042) and strict=True
get_ticket_tool = FunctionTool(
    name="get_ticket",
    description="Get the details and status of one ticket by its ID, for example INC-1042.",
    parameters={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Ticket ID such as INC-1042."},
        },
        "required": ["ticket_id"],
        "additionalProperties": False,
    },
    strict=True,
)

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
