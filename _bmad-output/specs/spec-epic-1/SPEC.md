---
id: SPEC-epic-1
companions: []
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage data and schema

## Why

Epic 1 is the foundation the workshop's triage agent (Epic 2) and its eval (Epic 3) build on. It is a **mandate to meet**: the repo already ships `mcp/triage_server.py`, which reads `app.db` and expects specific table and column names, and `TRIAGE_POLICY.md` reasons over a specific decision shape. Until a loader produces that database and a schema pins that decision shape, nothing downstream can run. Attendees build this live on day one, so it must be small, deterministic, and offline.

## Capabilities

- **CAP-1**
  - **intent:** A person can run `uv run python load_seed.py` and get a local SQLite database, `app.db`, holding the seed data.
  - **success:** `uv run python load_seed.py` creates `app.db` with tables `tickets` and `customers`, each with the same columns as `seed/tickets.csv` and `seed/customers.csv`. Running it twice yields the same database.

- **CAP-2**
  - **intent:** A person can represent any triage decision as a JSON object that validates against the schema.
  - **success:** A decision is a JSON object with a `category` of `billing`, `bug`, `access`, `performance`, or `how-to`; a `priority` of `P1` to `P4`; a `route` of `billing-team`, `bug-team`, `access-team`, `performance-team`, or `how-to-team`; and a one-sentence `rationale`. Anything else is rejected with a clear error.

## Constraints

- Python 3.12 or newer, managed with uv.
- The files in `seed/` are read-only.
- No network calls and no API keys in this epic.
- `mcp/triage_server.py` already reads `app.db`; its table and column names must keep working.

## Non-goals

- The agent, the MCP tools, evals, and any user interface.

## Success signal

`uv run python load_seed.py` produces `app.db` with `tickets` and `customers` populated from `seed/`, idempotently, and `mcp/triage_server.py`'s `get_ticket` and `get_customer_history` return correct rows against it — with the triage-decision schema rejecting any malformed decision.