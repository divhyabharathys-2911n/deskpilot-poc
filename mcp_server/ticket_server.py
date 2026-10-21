"""DeskPilot ticket MCP server.

Exposes the ticket store as MCP tools. It runs as a separate process and talks
to the app over stdio (the same pattern as the official MCP lab). Run it by
itself with:  python mcp_server/ticket_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# TODO 2.3.a: Import FastMCP from fastmcp and create the server: mcp =
# FastMCP(name="DeskPilotTickets")
raise NotImplementedError("TODO 2.3.a")

from common import db  # noqa: E402  (imported after the sys.path change above)


# TODO 2.3.b: Register the function below as an MCP tool with the @mcp.tool() decorator
def list_tickets(requester: str, status: str | None = None, category: str | None = None,
                 limit: int = 50) -> dict:
    """List support tickets. Employees see their own tickets; IT admins see all tickets.
    Optional filters: status (Open, In Progress, Resolved, Closed) and category (VPN, Password,
    MFA, Printer, Email, WiFi, Software, Laptop, Access, Security). Returns up to `limit` tickets."""
    try:
        tickets = db.list_tickets(requester, status=status, category=category, limit=limit)
        return {"count": len(tickets), "tickets": tickets}
    except (ValueError, db.PermissionDenied) as ex:
        return {"error": str(ex)}


# TODO 2.3.c: Register the function below as an MCP tool with the @mcp.tool() decorator
def update_ticket(requester: str, ticket_id: str, status: str | None = None,
                  note: str | None = None) -> dict:
    """Update a ticket: add a note and/or change its status. Employees may add notes to their own
    tickets and may close them. Only IT admins can set other statuses."""
    try:
        return {"status": "updated", "ticket": db.update_ticket(requester, ticket_id, status=status, note=note)}
    except (ValueError, db.PermissionDenied) as ex:
        return {"error": str(ex)}


if __name__ == "__main__":
    # TODO 2.3.d: Start the server with mcp.run(show_banner=False). The banner must be off
    # because it would corrupt the stdio protocol
    raise NotImplementedError("TODO 2.3.d")
