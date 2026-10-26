"""SQLite ticket store plus the access rules.

Every function takes `requester` (who is asking). The rules live HERE, in code,
so they hold even if a prompt is bypassed. The model never supplies identity.
"""
import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import CATEGORIES, DB_PATH, PRIORITIES, SEED_CSV, STATUSES, USERS


class PermissionDenied(Exception):
    """Raised when a user tries to do something their role does not allow."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    category    TEXT NOT NULL,
    priority    TEXT NOT NULL,
    status      TEXT NOT NULL,
    requester   TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT ''
)
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def init_db(reset: bool = False) -> int:
    """Create the table and load data/seed_tickets.csv. Returns the ticket count."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        if reset:
            conn.execute("DROP TABLE IF EXISTS tickets")
        conn.execute(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        if count == 0:
            with open(SEED_CSV, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    conn.execute(
                        "INSERT INTO tickets (id, title, description, category, priority, status,"
                        " requester, created_at, updated_at, notes)"
                        " VALUES (:id, :title, :description, :category, :priority, :status,"
                        " :requester, :created_at, :updated_at, :notes)",
                        row,
                    )
            count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    return count


def is_admin(user: str) -> bool:
    return USERS.get(user, {}).get("role") == "admin"


def can_view(user: str, ticket: dict) -> bool:
    """Employees see only their own tickets. Admins see every ticket."""
    # TODO 1.3.b: Return True when the user is an admin or is the ticket's requester,
    # otherwise False
    return is_admin(user) or ticket["requester"] == user


def _next_id(conn) -> str:
    last = conn.execute("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM tickets").fetchone()[0]
    return f"INC-{(last or 1000) + 1}"


def create_ticket(requester: str, title: str, description: str, category: str, priority: str) -> dict:
    if requester not in USERS:
        raise PermissionDenied(f"Unknown user '{requester}'.")
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")
    if not title.strip() or not description.strip():
        raise ValueError("Title and description are required.")
    now = _now()
    with connect() as conn:
        ticket_id = _next_id(conn)
        conn.execute(
            "INSERT INTO tickets (id, title, description, category, priority, status,"
            " requester, created_at, updated_at, notes) VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?, '')",
            (ticket_id, title.strip(), description.strip(), category, priority, requester, now, now),
        )
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row)


def get_ticket(requester: str, ticket_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id.strip().upper(),)).fetchone()
    if row is None:
        raise ValueError(f"Ticket {ticket_id} was not found.")
    ticket = dict(row)
    if not can_view(requester, ticket):
        raise PermissionDenied("You can only view your own tickets.")
    return ticket


def list_tickets(requester: str, status: str | None = None, category: str | None = None,
                 limit: int = 50) -> list[dict]:
    if requester not in USERS:
        raise PermissionDenied(f"Unknown user '{requester}'.")
    query, params = "SELECT * FROM tickets WHERE 1=1", []
    if not is_admin(requester):
        query += " AND requester = ?"
        params.append(requester)
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 200)))
    with connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def update_ticket(requester: str, ticket_id: str, status: str | None = None,
                  note: str | None = None) -> dict:
    """Admins can set any status. Employees can add a note or close their own ticket."""
    ticket = get_ticket(requester, ticket_id)  # also enforces view permission
    if status and status not in STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(STATUSES)}.")
    if status and not is_admin(requester) and status != "Closed":
        raise PermissionDenied("Employees can only close their own tickets. Ask IT to change other statuses.")
    notes = ticket["notes"]
    if note:
        notes = (notes + "\n" if notes else "") + f"[{_now()} {requester}] {note.strip()}"
    with connect() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ?, updated_at = ? WHERE id = ?",
            (status or ticket["status"], notes, _now(), ticket["id"]),
        )
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket["id"],)).fetchone()
    return dict(row)
