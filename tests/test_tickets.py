"""Offline tests for the ticket rules. They need no Azure access.

Run:  pytest -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import db, functions  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "tickets.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db(reset=True)
    return path


def test_seed_loads_30_tickets(tmp_db):
    assert len(db.list_tickets("it.admin", limit=200)) == 30


def test_employee_sees_only_own_tickets(tmp_db):
    tickets = db.list_tickets("aarav.shah", limit=200)
    assert tickets and all(t["requester"] == "aarav.shah" for t in tickets)


def test_employee_cannot_read_someone_elses_ticket(tmp_db):
    with pytest.raises(db.PermissionDenied):
        db.get_ticket("aarav.shah", "INC-1002")  # INC-1002 belongs to diya.patel


def test_admin_can_read_any_ticket(tmp_db):
    assert db.get_ticket("it.admin", "INC-1002")["requester"] == "diya.patel"


def test_create_ticket_validates_category_and_priority(tmp_db):
    with pytest.raises(ValueError):
        db.create_ticket("aarav.shah", "t", "d", "Coffee", "Low")
    with pytest.raises(ValueError):
        db.create_ticket("aarav.shah", "t", "d", "VPN", "Urgent")


def test_new_ticket_gets_next_id(tmp_db):
    ticket = db.create_ticket("aarav.shah", "Test", "Test description", "VPN", "Low")
    assert ticket["id"] == "INC-1031" and ticket["status"] == "Open"


def test_employee_can_close_own_ticket_but_not_set_other_status(tmp_db):
    assert db.update_ticket("aarav.shah", "INC-1001", status="Closed")["status"] == "Closed"
    with pytest.raises(db.PermissionDenied):
        db.update_ticket("aarav.shah", "INC-1007", status="Resolved")


def test_model_cannot_supply_another_identity(tmp_db):
    # The model tries to pass requester="diya.patel". The function layer ignores it.
    out = json.loads(functions.run_function(
        "get_ticket", json.dumps({"ticket_id": "INC-1002", "requester": "diya.patel"}), "aarav.shah"))
    assert "error" in out


def test_mcp_server_injects_requester(tmp_db):
    from common.mcp_client import TicketMCP

    mcp = TicketMCP(env={"DESKPILOT_DB": str(tmp_db)})
    try:
        names = {t.name for t in mcp.tools}
        assert {"list_tickets", "update_ticket"} <= names
        for tool in mcp.function_tools():
            assert "requester" not in tool.parameters["properties"]
        # The model tries to pass requester="it.admin" - the client overrides it with the real user.
        out = json.loads(mcp.call("list_tickets", {"requester": "it.admin", "limit": 200}, "aarav.shah"))
        assert out["count"] == 6
    finally:
        mcp.close()
