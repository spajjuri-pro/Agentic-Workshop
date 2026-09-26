---
title: 'The loader'
type: 'feature'
created: '2026-09-26'
status: 'in-progress'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo ships `mcp/triage_server.py`, which reads `app.db` and expects `tickets` and `customers` tables with specific columns, but no loader produces that database. Nothing downstream can run until it exists.

**Approach:** Build `load_seed.py` that reads `seed/tickets.csv` and `seed/customers.csv` into a local SQLite `app.db` as the `tickets` and `customers` tables with the same columns, idempotently.

</frozen-after-approval>

## Implementation Notes

- Created `load_seed.py` using stdlib `csv` + `sqlite3` (no new deps). Drops and recreates tables each run for idempotency.
- Added `tests/test_load_seed.py` (4 tests: table creation + counts, idempotency, column names, MCP server compatibility).
- Added `pythonpath = ["."]` to `[tool.pytest.ini_options]` in `pyproject.toml` so tests can import `load_seed`.
- Verified: `uv run python load_seed.py` twice → `(24,) (20,)`; `uv run pytest` → 3 passed.
- Verified `mcp/triage_server.py` reads `app.db` correctly (get_ticket T-1042 → C-77; get_customer_history → Northwind, ticket_ids [T-1042, T-1047]).

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries. -->

## Review Triage Log

- `medium` — `tests/test_load_seed.py` did not check the idempotency of `customers` and therefore missed a real regression risk. Fixed by asserting both tables match before/after reloads.
- `medium` — the story's success signal requires `mcp/triage_server.py` to read the database correctly, but there was no automated contract test for it. Fixed by importing the server by file path and asserting `get_ticket("T-1042")` and `get_customer_history("C-77")` return the expected rows.
- `low` — `load_seed.py` had no explicit handling for empty CSVs; this is not a real issue in the current trusted dataset and would be a separate robustness improvement, so it was deferred.
- `low` — no primary-key or foreign-key constraints were added; the dataset is trusted and the schema must match the CSV contract, so this is deferred rather than altered.
- `low` — SQL identifier interpolation from CSV headers is not an active exploit here because the seed is read-only; it remains a future hardening consideration, not a required fix for this story.

## Verification

**Commands:**
- `uv run python load_seed.py` -- expected: creates `app.db`; running twice yields the same database.
- `uv run python -c "import sqlite3; c=sqlite3.connect('app.db'); print(c.execute('select count(*) from tickets').fetchone(), c.execute('select count(*) from customers').fetchone())"` -- expected: `(24,) (20,)`.
- `uv run pytest` -- expected: passes (loader idempotency test).