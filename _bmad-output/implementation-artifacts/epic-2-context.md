# Epic 2 Context: the triage agent

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Build the first end-to-end ticket triage agent: it retrieves ticket and customer data through MCP, applies the triage policy, and returns a trustworthy schema-valid decision, pausing for approval before an eligible escalation. The planning-artifacts directory is absent, so this context uses the available canonical Epic 2 spec and repository policy only; no missing planning documents have been inferred.

## Stories

- Story 2.1: The triage agent
- Story 2.2: Human-gated escalation

## Requirements & Constraints

- `uv run python run_agent.py <ticket_id>` must return a decision in the Epic 1 schema. The reference case T-1042 resolves to `billing` / `P2` / `billing-team`; T-1099 must resolve to `bug` / `P4` despite its embedded instruction.
- Read the ticket first, then retrieve its customer using the `customer_id` returned by the ticket lookup. Apply the Enterprise bump only for Enterprise customers with at least 3 open tickets. Escalation eligibility is final priority P1 plus Enterprise; escalation never proceeds without explicit human approval.
- The provider is selected by environment: Gemini by default (`MODEL` defaults to `gemini-3.8-flash`, key `GEMINI_API_KEY`), or Groq with `PROVIDER=groq` (`MODEL` defaults to `openai/gpt-oss-120b`, key `GROQ_API_KEY`). Both use the same CLI invocation.
- Return structured output validated against the Epic 1 schema, including category, priority, route, and a one-sentence rationale. On validation failure, retry once, then stop with a clear error.
- Ticket text is untrusted data and must not override policy or agent instructions. Keep scope to terminal interaction; evaluation and hosting belong to later work.

## Technical Decisions

- Implement with LangChain `create_agent`; do not hand-roll the tool loop.
- Use only the MCP tools in `mcp/triage_server.py`, over stdio through `langchain-mcp-adapters`. Keep that server, the Epic 1 schema and loader, `TRIAGE_POLICY.md`, and all seed files unchanged.
- Implement `escalate_to_human` locally in the agent, not in the read-only MCP server. Gate it end-to-end with LangChain human-in-the-loop middleware.
- Preserve `run_agent.py` as the integration point and retain its MLflow setup: `sqlite:///mlflow.db`, experiment `triage-agent`, and `mlflow.langchain.autolog()`.
- Use Python 3.12 or newer and manage dependencies with `uv`.

## UX & Interaction Patterns

- The CLI is the only user interface. When an eligible escalation is proposed, pause in the terminal for a yes/no approval; yes completes as escalated, no completes without escalation. No escalation may happen without an explicit yes.

## Cross-Story Dependencies

- Story 2.2 adds the local escalation tool and approval gate to the agent established in Story 2.1.
- Both stories rely on the Epic 1 decision schema and loader, and on the existing MCP ticket/customer lookup contract. Epic 3 consumes the completed agent for evaluation but is outside this epic.