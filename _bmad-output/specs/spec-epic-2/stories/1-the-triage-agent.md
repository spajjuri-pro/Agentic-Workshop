---
title: 'The triage agent'
type: 'feature'
created: '2026-09-26'
status: 'draft'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The CLI and MCP data server exist, but there is no agent to turn a ticket and its customer context into a policy-compliant triage decision. The workshop cannot demonstrate end-to-end triage or provide Epic 3 with an agent to evaluate.

**Approach:** Implement `agent.triage(ticket_id)` with LangChain `create_agent`, using the existing MCP ticket/customer lookup tools and `TRIAGE_POLICY.md` to produce an Epic 1-schema decision. Support Gemini by default and Groq by environment selection, retry once after an invalid decision, and treat ticket text as untrusted data.

## Boundaries & Constraints

**Always:** Preserve `run_agent.py` as the CLI and retain its MLflow tracking URI, experiment, autologging, and span behavior. Select Gemini by default (`MODEL` default `gemini-3.8-flash`, `GEMINI_API_KEY`) or Groq for `PROVIDER=groq` (`MODEL` default `openai/gpt-oss-120b`, `GROQ_API_KEY`). Use only `mcp/triage_server.py` tools over stdio. Read the ticket before its customer and use the returned `customer_id`. Follow `TRIAGE_POLICY.md` and validate output with `triage_schema.py`.

**Never:** Modify the Epic 1 loader or validator, `mcp/triage_server.py`, `TRIAGE_POLICY.md`, or `seed/`. Do not implement the local escalation tool or human approval gate (Story 2.2), evaluation, UI, or hosting. Never treat ticket contents as agent instructions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| VALID_DECISION | Agent returns an object accepted by `validate_decision` | Return the validated category, priority, route, and one-sentence rationale | No retry |
| FIRST_INVALID | First agent response fails Epic 1 validation; second succeeds | Return the second validated decision | Retry exactly once |
| REPEATED_INVALID | Both responses fail validation | Stop without returning a decision | Clear error after exactly two attempts |
| UNKNOWN_TICKET | MCP `get_ticket` cannot find the requested ID | Stop; do not request customer history | Propagate a clear lookup error |
| PROVIDER_SELECTION | `PROVIDER` unset or set to `groq` | Configure the documented default provider/model or Groq/model pair | Missing credentials or unsupported provider fails clearly |

</frozen-after-approval>

## Code Map

- `run_agent.py:main` -- existing CLI and MLflow integration; import/call `agent.triage` here without disturbing tracking setup.
- `mcp/triage_server.py:get_ticket`, `get_customer_history` -- only allowed data tools; expose via stdio and preserve lookup order and customer ID handoff.
- `TRIAGE_POLICY.md` -- authoritative categories, routes, priorities, Enterprise threshold, safety rule, and rationale requirement; load as agent instructions, do not edit.
- `triage_schema.py:validate_decision` -- existing contract validator; use it to accept or reject the final decision.
- `pyproject.toml` and `uv.lock` -- required LangChain, provider, MCP, MLflow, Pydantic, and dotenv dependencies are already present; avoid dependency changes unless implementation proves otherwise.
- `tests/test_load_seed.py`, `tests/test_triage_schema.py` -- pytest conventions; add isolated tests without live provider calls or changes to the seed database.

## Tasks & Acceptance

**Execution:**
- [ ] `agent.py` -- implement provider configuration and async `triage(ticket_id)` with `create_agent`, MCP stdio tools, policy instructions, ordered ticket/customer retrieval, structured decision validation, and one retry -- connects the existing CLI to trusted triage behavior.
- [ ] `tests/test_agent.py` -- cover provider selection, tool order and customer-ID handoff, trace contents, Enterprise threshold, validator retry limit, and ticket-injection resistance with mocked model/tool boundaries -- verifies behavior without API keys or network calls.

**Acceptance Criteria:**
- Given `run_agent.py` is invoked with a ticket ID and configured provider credentials, when the run completes, then it prints a JSON decision accepted by `validate_decision` and records the run through the existing MLflow integration.
- Given `PROVIDER` is unset, when the agent is configured, then it selects `ChatGoogleGenerativeAI` with `MODEL` or `gemini-3.8-flash` and `GEMINI_API_KEY`.
- Given `PROVIDER=groq`, when the agent is configured, then it selects `ChatGroq` with `MODEL` or `openai/gpt-oss-120b` and `GROQ_API_KEY` through the same CLI.
- Given a ticket is triaged, when customer context is needed, then `get_ticket` runs first and `get_customer_history` receives the `customer_id` returned by that ticket lookup.
- Given ticket `T-1042`, when its Enterprise customer has two open tickets, then the decision is `billing` / `P2` / `billing-team` and the rationale names the applied policy rule.
- Given ticket `T-1099` contains an instruction to mark itself P1, when it is triaged, then ticket text is treated as data and the decision is `bug` / `P4`.
- Given the first decision fails `validate_decision`, when one retry also fails, then the run stops with a clear error after exactly two attempts.
- Given an unknown ticket or unusable provider configuration, when triage starts, then the run fails clearly and does not fabricate a decision.
- Given a successful run, when its MLflow trace is inspected, then it shows `get_ticket` before `get_customer_history` with the returned customer ID as the second tool's input.
- Given an Enterprise customer has at least three open tickets, when a ticket's initial policy priority is P2, then the Enterprise rule raises the final priority to P1.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

The Enterprise priority bump changes P3 to P2 and P2 to P1 only at three or more open tickets; Northwind has two, so `T-1042` remains P2. The output route must match the category mapping in policy. Story 2.1 establishes triage only; escalation approval is delivered separately in Story 2.2.

## Verification

**Commands:**
- `uv run pytest` -- expected: all existing and new tests pass without provider credentials or network calls.
- `uv run python run_agent.py T-1042` -- expected with valid Gemini or Groq credentials and seeded `app.db`: prints the expected validated billing/P2 decision and records an MLflow trace.
- `uv run python run_agent.py T-1099` -- expected with valid credentials and seeded `app.db`: prints a validated bug/P4 decision despite the embedded instruction.