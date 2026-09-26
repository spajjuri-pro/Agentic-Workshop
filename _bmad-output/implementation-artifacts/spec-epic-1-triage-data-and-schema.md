---
title: 'Epic 1: triage data and schema'
type: 'feature'
created: '2026-09-26'
status: 'draft'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo ships `mcp/triage_server.py`, which reads `app.db` and expects `tickets` and `customers` tables with specific columns, but no loader produces that database and no schema pins the triage-decision shape. Nothing downstream (the Epic 2 agent, the Epic 3 eval) can run until this exists.

**Approach:** Build `load_seed.py` that reads `seed/tickets.csv` and `seed/customers.csv` into a local SQLite `app.db` (idempotently), and a triage-decision schema that validates a JSON decision's `category`, `priority`, `route`, and `rationale`, rejecting anything malformed with a clear error.

## Boundaries & Constraints

**Always:**
- Python 3.12 or newer, managed with uv.
- `seed/` files are read-only.
- No network calls and no API keys.
- `mcp/triage_server.py`'s table and column names must keep working: tables `tickets` and `customers`; columns `ticket_id, customer_id, created_at, text` and `customer_id, name, plan, open_tickets`.

**Never:**
- The agent, the MCP tools, evals, or any user interface.
- Modifying `seed/`, `mcp/triage_server.py`, or `TRIAGE_POLICY.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | `uv run python load_seed.py` on a fresh tree | Creates `app.db` with `tickets` and `customers` populated from the CSVs | N/A |
| IDEMPOTENT | `uv run python load_seed.py` run twice | Same database both times; no duplicate rows | N/A |
| VALID_DECISION | `{category: billing, priority: P2, route: billing-team, rationale: "..."}` | Validates successfully | N/A |
| INVALID_DECISION | `{category: "nope", priority: "P9", route: "x", rationale: "..."}` | Rejected with a clear error naming the invalid field | Clear error message |

</frozen-after-approval>

## Code Map

- `seed/tickets.csv` -- source data; columns `ticket_id, customer_id, created_at, text`; read-only.
- `seed/customers.csv` -- source data; columns `customer_id, name, plan, open_tickets`; read-only.
- `mcp/triage_server.py` -- reads `app.db`; defines the exact table/column contract the loader must satisfy; read-only.
- `pyproject.toml` -- project config; Python 3.12+, uv; no new deps needed (stdlib `sqlite3`, `csv`).

## Tasks & Acceptance

**Execution:**
- [ ] `load_seed.py` -- create a loader that reads both CSVs into `app.db` (tables `tickets`, `customers`) idempotently -- satisfies CAP-1.
- [ ] `triage_schema.py` -- define the triage-decision schema (category/priority/route enums + rationale) with a validate function that rejects malformed decisions with a clear error -- satisfies CAP-2.

**Acceptance Criteria:**
- Given a fresh tree, when `uv run python load_seed.py` runs, then `app.db` exists with `tickets` and `customers` populated from the seed CSVs.
- Given `load_seed.py` has already run, when it runs again, then the database is unchanged (no duplicate rows).
- Given a valid decision object, when validated against the schema, then it passes.
- Given a malformed decision object, when validated against the schema, then it is rejected with a clear error naming the invalid field.
- Given `app.db` is loaded, when `mcp/triage_server.py`'s `get_ticket` and `get_customer_history` run, then they return correct rows.

## Implementation Notes

<!-- Agent-owned. Append-only during implementation: decisions made, files touched, surprises encountered. Leave empty at planning time; never delete this section. -->

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on every review pass. -->

## Design Notes

<!-- If the approach is straightforward, DELETE THIS ENTIRE SECTION. -->

## Verification

**Commands:**
- `uv run python load_seed.py` -- expected: creates `app.db`; running twice yields the same database.
- `uv run pytest` -- expected: passes (tests added for loader idempotency and schema validation).
- `uv run python -c "import sqlite3; c=sqlite3.connect('app.db'); print(c.execute('select count(*) from tickets').fetchone(), c.execute('select count(*) from customers').fetchone())"` -- expected: `(24,) (20,)` (24 tickets, 20 customers).