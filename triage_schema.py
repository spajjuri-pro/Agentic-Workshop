"""Validate triage decision objects against the Epic 1 schema."""

from __future__ import annotations

import re
from typing import Any

VALID_CATEGORIES = {"billing", "bug", "access", "performance", "how-to"}
VALID_PRIORITIES = {"P1", "P2", "P3", "P4"}
VALID_ROUTES = {
    "billing-team",
    "bug-team",
    "access-team",
    "performance-team",
    "how-to-team",
}
EXPECTED_KEYS = {"category", "priority", "route", "rationale"}


def _validate_rationale(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid rationale: must be a string")

    rationale = value.strip()
    if not rationale:
        raise ValueError("invalid rationale: cannot be empty")

    if len(re.findall(r"[.!?]", rationale)) != 1:
        raise ValueError("invalid rationale: must be exactly one sentence")

    if not rationale.endswith((".", "!", "?")):
        raise ValueError("invalid rationale: must end with sentence punctuation")

    return rationale


def validate_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Validate a triage decision payload and return it unchanged on success."""
    if not isinstance(decision, dict):
        raise ValueError("invalid decision: must be a dictionary")

    missing = sorted(EXPECTED_KEYS - set(decision))
    extra = sorted(set(decision) - EXPECTED_KEYS)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise ValueError("invalid decision: " + "; ".join(details))

    category = decision["category"]
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"invalid category: {category!r}. Expected one of {sorted(VALID_CATEGORIES)}."
        )

    priority = decision["priority"]
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"invalid priority: {priority!r}. Expected one of {sorted(VALID_PRIORITIES)}."
        )

    route = decision["route"]
    if route not in VALID_ROUTES:
        raise ValueError(
            f"invalid route: {route!r}. Expected one of {sorted(VALID_ROUTES)}."
        )

    decision["rationale"] = _validate_rationale(decision["rationale"])
    return decision
