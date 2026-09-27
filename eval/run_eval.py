"""Evaluate the triage agent over the labelled tickets with mlflow.genai.evaluate.

Usage: uv run python eval/run_eval.py
"""

import asyncio
import csv
import json
import os
import re
import sys
import threading
from pathlib import Path

import mlflow
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from mlflow.entities import Feedback
from mlflow.genai import evaluate, scorer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agent  # noqa: E402
from triage_schema import validate_decision  # noqa: E402

LABELS_PATH = ROOT / "eval" / "labelled_tickets.csv"
REPORT_PATH = ROOT / "eval" / "latest_report.json"
SCORERS = ["valid_schema", "category_match", "priority_match", "tool_order", "rationale_judge"]

JUDGE_PROMPT = """You are grading the rationale of a support-ticket triage decision.

Reviewer notes for this ticket (the ground truth reasoning):
{judge_notes}

Agent decision: category={category}, priority={priority}, route={route}
Agent rationale: {rationale}

Escalation to a person happens through a separate approval tool and is not part of the decision, so do not fail a rationale for not mentioning escalation.
The rationale is sound if it is consistent with the reviewer notes and justifies the decision.
Reply with only a JSON object: {{"verdict": "pass" or "fail", "reason": "<one line>"}}"""

_escalations = 0
_escalations_lock = threading.Lock()


def _auto_approve(action: dict) -> bool:
    """Approve every escalation so the eval never waits on a person."""
    global _escalations
    with _escalations_lock:
        _escalations += 1
    return True


def load_rows() -> list[dict]:
    with LABELS_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@mlflow.trace(name="triage_eval", span_type="AGENT")
def predict(ticket_id: str) -> dict:
    """Run the agent once. One trace covers the initial call and any approved resume."""
    return asyncio.run(agent.triage(ticket_id))


@scorer
def valid_schema(outputs) -> int:
    try:
        validate_decision(outputs)
    except (ValueError, TypeError):
        return 0
    return 1


@scorer
def category_match(outputs, expectations) -> int:
    return int(isinstance(outputs, dict) and outputs.get("category") == expectations["expected_category"])


@scorer
def priority_match(outputs, expectations) -> int:
    return int(isinstance(outputs, dict) and outputs.get("priority") == expectations["expected_priority"])


@scorer
def tool_order(trace) -> int:
    def first_start(name: str) -> int | None:
        starts = [s.start_time_ns for s in trace.search_spans(name=name)]
        return min(starts) if starts else None

    ticket, customer = first_start("get_ticket"), first_start("get_customer_history")
    return int(ticket is not None and customer is not None and ticket < customer)


def _judge_model() -> ChatGroq:
    """Judge on Groq only; never reads GEMINI_API_KEY."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for rationale_judge")
    return ChatGroq(model=os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b"), api_key=api_key, temperature=0)


@scorer
def rationale_judge(outputs, expectations) -> Feedback:
    if not isinstance(outputs, dict):
        return Feedback(value="fail", rationale="No decision to judge.")
    prompt = JUDGE_PROMPT.format(judge_notes=expectations["judge_notes"], **{
        k: outputs.get(k, "") for k in ("category", "priority", "route", "rationale")
    })
    text = _judge_model().invoke(prompt).text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    verdict = json.loads(match.group(0)) if match else {}
    if verdict.get("verdict") not in {"pass", "fail"}:
        raise ValueError(f"Judge returned an unusable verdict: {text[:200]!r}")
    return Feedback(value=verdict["verdict"], rationale=str(verdict.get("reason", "")).strip())


def build_report(run_id: str, experiment_id: str) -> dict:
    """Scorer means and agent token total, read back from the run's MLflow traces."""
    traces = mlflow.search_traces(experiment_ids=[experiment_id], run_id=run_id, return_type="list")
    values: dict[str, list[float]] = {name: [] for name in SCORERS}
    total_tokens = 0
    for trace in traces:
        if trace.data.spans[0].name != "triage_eval" and not any(
            s.parent_id is None and s.name == "triage_eval" for s in trace.data.spans
        ):
            continue  # judge calls are not agent spend
        total_tokens += (trace.info.token_usage or {}).get("total_tokens", 0)
        for a in trace.info.assessments:
            if a.name in values and a.feedback is not None and a.feedback.value is not None:
                v = a.feedback.value
                values[a.name].append(float(v == "pass") if isinstance(v, str) else float(v))
    return {
        "scorer_means": {n: (sum(v) / len(v) if v else None) for n, v in values.items()},
        "scored_tickets": {n: len(v) for n, v in values.items()},
        "total_agent_tokens": total_tokens,
        "auto_approved_escalations": _escalations,
    }


def main() -> None:
    load_dotenv()
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()

    # Unattended run: swap only the terminal prompt; the agent's escalation logic is untouched.
    agent._ask_approval = _auto_approve

    data = [
        {
            "inputs": {"ticket_id": row["ticket_id"]},
            "expectations": {
                "expected_category": row["expected_category"],
                "expected_priority": row["expected_priority"],
                "judge_notes": row["judge_notes"],
            },
        }
        for row in load_rows()
    ]

    results = evaluate(
        data=data,
        predict_fn=predict,
        scorers=[valid_schema, category_match, priority_match, tool_order, rationale_judge],
    )
    experiment_id = mlflow.get_experiment_by_name("triage-agent").experiment_id
    report = build_report(results.run_id, experiment_id)
    for name in SCORERS:
        print(f"{name}: {report['scorer_means'][name]}")
    print(f"total agent tokens: {report['total_agent_tokens']}")
    print(f"auto-approved escalations: {report['auto_approved_escalations']}")
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
