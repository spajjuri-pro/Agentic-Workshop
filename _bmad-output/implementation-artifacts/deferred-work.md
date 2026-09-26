## Deferred from: code review of 1-the-loader (2026-09-26)

- CAP-2 schema contract lists category and route enums independently, allowing valid enum values to form policy-invalid category/route pairs (for example, `billing` with `bug-team`). Revisit when implementing the triage-decision schema; this is outside Story 1.
- CAP-2 requires a one-sentence rationale but omits the policy requirement that the rationale name the rule applied. Revisit when implementing the triage-decision schema; this is outside Story 1.