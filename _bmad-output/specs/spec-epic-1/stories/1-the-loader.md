---
title: 'The loader'
type: 'feature'
created: '2026-09-26'
status: 'done'
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
- Declared `open_tickets` as an integer and converted the CSV value so the MCP customer-history tool returns a numeric count.
- Verified: `uv run python load_seed.py` twice → `(24,) (20,)`; `uv run pytest` → 13 passed, including all 4 loader tests.
- Verified `mcp/triage_server.py` reads `app.db` correctly (get_ticket T-1042 → C-77; get_customer_history → Northwind, ticket_ids [T-1042, T-1047]).

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries. -->

## Review Triage Log

- `medium` — `tests/test_load_seed.py` did not check the idempotency of `customers` and therefore missed a real regression risk. Fixed by asserting both tables match before/after reloads.
- `medium` — the story's success signal requires `mcp/triage_server.py` to read the database correctly, but there was no automated contract test for it. Fixed by importing the server by file path and asserting `get_ticket("T-1042")` and `get_customer_history("C-77")` return the expected rows.
- `low` — `load_seed.py` had no explicit handling for empty CSVs; this is not a real issue in the current trusted dataset and would be a separate robustness improvement, so it was deferred.
- `low` — no primary-key or foreign-key constraints were added; the dataset is trusted and the schema must match the CSV contract, so this is deferred rather than altered.
- `low` — SQL identifier interpolation from CSV headers is not an active exploit here because the seed is read-only; it remains a future hardening consideration, not a required fix for this story.
- `medium` — `get_customer_history` returned `open_tickets` as a string because SQLite inferred no column type; declared and converted the field to integer, with a regression assertion for the full customer row.
- `low` — MCP compatibility test asserted only selected fields; expanded it to compare the complete ticket and customer rows.
- `false` — header validation is unnecessary for the supported read-only seed inputs; the checked-in headers match the MCP contract, and changing them is outside this story's supported operation.
- `low` — empty or headerless CSV handling remains deferred because the seed files are trusted, read-only inputs and this invalid state is not part of the story contract.
- `low` — the prior implementation note's test total was stale; corrected it to the verified full-suite result of 13 passed.

## Verification

**Commands:**
- `uv run python load_seed.py` -- expected: creates `app.db`; running twice yields the same database.
- `uv run python -c "import sqlite3; c=sqlite3.connect('app.db'); print(c.execute('select count(*) from tickets').fetchone(), c.execute('select count(*) from customers').fetchone())"` -- expected: `(24,) (20,)`.
- `uv run pytest` -- expected: all 13 tests pass.