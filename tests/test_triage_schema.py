"""Tests for triage decision validation."""

import pytest

from triage_schema import validate_decision


@pytest.mark.parametrize(
    "decision",
    [
        {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "The customer was charged twice."},
        {"category": "bug", "priority": "P4", "route": "bug-team", "rationale": "The login flow fails only on Safari."},
    ],
)
def test_validate_decision_accepts_valid_objects(decision):
    assert validate_decision(decision) == decision


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "unknown"),
        ("category", "Billing"),
        ("priority", "P9"),
        ("priority", "p2"),
        ("route", "wrong-team"),
        ("rationale", ""),
        ("rationale", "This is sentence one. This is sentence two."),
    ],
)
def test_validate_decision_rejects_malformed_values(field, value):
    decision = {
        "category": "billing",
        "priority": "P2",
        "route": "billing-team",
        "rationale": "The charge was refunded correctly.",
    }
    decision[field] = value

    with pytest.raises(ValueError, match=field):
        validate_decision(decision)
