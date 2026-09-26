"""Tests for load_seed.py."""

import importlib.util
import sqlite3
from pathlib import Path

from load_seed import load_seed

ROOT = Path(__file__).resolve().parent.parent


def _load_triage_server():
    """Import mcp/triage_server.py by path (the `mcp` name collides with the installed library)."""
    spec = importlib.util.spec_from_file_location("triage_server", ROOT / "mcp" / "triage_server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_load_seed_creates_tables(tmp_path):
    db = tmp_path / "app.db"
    load_seed(db)
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"tickets", "customers"} <= tables
        assert conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 24
        assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 20


def test_load_seed_is_idempotent(tmp_path):
    db = tmp_path / "app.db"
    load_seed(db)
    with sqlite3.connect(db) as conn:
        tickets_before = conn.execute("SELECT * FROM tickets ORDER BY ticket_id").fetchall()
        customers_before = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    load_seed(db)
    with sqlite3.connect(db) as conn:
        tickets_after = conn.execute("SELECT * FROM tickets ORDER BY ticket_id").fetchall()
        customers_after = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    assert tickets_before == tickets_after
    assert customers_before == customers_after


def test_load_seed_columns_match_csv(tmp_path):
    db = tmp_path / "app.db"
    load_seed(db)
    with sqlite3.connect(db) as conn:
        ticket_cols = [r[1] for r in conn.execute("PRAGMA table_info(tickets)")]
        customer_cols = [r[1] for r in conn.execute("PRAGMA table_info(customers)")]
    assert ticket_cols == ["ticket_id", "customer_id", "created_at", "text"]
    assert customer_cols == ["customer_id", "name", "plan", "open_tickets"]


def test_mcp_server_reads_loaded_db(tmp_path, monkeypatch):
    db = tmp_path / "app.db"
    load_seed(db)
    server = _load_triage_server()
    monkeypatch.setattr(server, "DB_PATH", db)

    ticket = server.get_ticket("T-1042")
    assert ticket["customer_id"] == "C-77"

    customer = server.get_customer_history(ticket["customer_id"])
    assert customer["name"] == "Northwind"
    assert customer["plan"] == "Enterprise"
    assert customer["ticket_ids"] == ["T-1042", "T-1047"]