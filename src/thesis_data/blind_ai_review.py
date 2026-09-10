"""Strict, arm-blinded AI-assisted review contracts."""

from __future__ import annotations

import json
from typing import Any


REVIEW_DIMENSIONS = (
    "factual_correctness",
    "calculation_correctness",
    "evidence_completeness",
    "citation_correctness",
    "coverage_discipline",
    "cross_level_consistency",
    "anomaly_classification",
)
REVIEW_STATUSES = ("scored", "unscorable")


def successful_blind_ids(records: list[dict[str, Any]]) -> set[str]:
    """Return only records that contain a validated review result."""

    return {
        record["blind_id"]
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("blind_id"), str)
        and not record.get("error")
    }


def review_response_schema() -> dict[str, Any]:
    decision = {
        "type": "object",
        "properties": {
            "dimension": {"type": "string", "enum": list(REVIEW_DIMENSIONS)},
            "review_status": {"type": "string", "enum": list(REVIEW_STATUSES)},
            "score": {"anyOf": [{"type": "integer", "enum": [0, 1]}, {"type": "null"}]},
            "reason_code": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": ["dimension", "review_status", "score", "reason_code", "rationale"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"reviews": {"type": "array", "items": decision}},
        "required": ["reviews"],
        "additionalProperties": False,
    }


def parse_review_decisions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the model's review object before it becomes a score record."""

    if not isinstance(payload, dict) or not isinstance(payload.get("reviews"), list):
        raise ValueError("review_output_shape_invalid")
    decisions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for decision in payload["reviews"]:
        if not isinstance(decision, dict):
            raise ValueError("review_decision_shape_invalid")
        dimension = decision.get("dimension")
        status = decision.get("review_status")
        score = decision.get("score")
        reason = decision.get("reason_code")
        rationale = decision.get("rationale")
        if dimension not in REVIEW_DIMENSIONS or dimension in seen:
            raise ValueError("review_dimension_invalid_or_duplicate")
        if status not in REVIEW_STATUSES:
            raise ValueError("review_status_invalid")
        if status == "scored" and score not in (0, 1):
            raise ValueError("scored_review_requires_binary_score")
        if status == "unscorable":
            if score is not None:
                raise ValueError("unscorable_review_requires_null_score")
            if reason not in {"contract_failure", "review_failure", "not_applicable"}:
                raise ValueError("unscorable_reason_invalid")
        if not isinstance(reason, str) or not reason:
            raise ValueError("review_reason_missing")
        if not isinstance(rationale, str) or not rationale:
            raise ValueError("review_rationale_missing")
        seen.add(dimension)
        decisions.append(
            {
                "dimension": dimension,
                "review_status": status,
                "score": score,
                "reason_code": reason,
                "rationale": rationale,
            }
        )
    return decisions


def build_reviewer_prompt(packet: dict[str, Any], reviewer_id: str) -> str:
    """Render a reviewer prompt that contains no arm or execution identity."""

    question = packet.get("question", {})
    answer = packet.get("answer", {})
    reference = packet.get("gold_reference", {})
    return (
        "You are an independent blind evaluator for a financial-analysis thesis.\n"
        f"Reviewer: {reviewer_id}.\n"
        "The answer below has been anonymized. Do not infer or discuss which system produced it.\n"
        "Score only the dimensions supported by the question and reference. Omit a dimension when it is not applicable; use unscorable only for a genuine review or contract failure.\n"
        "Score 1 only when the answer is supported by the Gold reference and the rubric. Score 0 for a substantive error, unsupported claim, missing required disclosure, wrong period, wrong definition, or unsupported citation.\n"
        "For factual correctness, check numeric and categorical claims. For calculation correctness, check derived values and changes. For evidence completeness, require source ID plus page/table/section locator. For citation correctness, verify issuer, metric, period, and scope support. For coverage discipline, require explicit missing/conflict handling without guessing. For cross-level consistency, check period and definition alignment. For anomaly classification, use true contradiction, explainable divergence, data conflict, or insufficient evidence.\n"
        "Return only the strict JSON object requested by the schema.\n\n"
        + json.dumps(
            {
                "blind_answer_id": packet.get("blind_id"),
                "question": question,
                "answer": answer,
                "gold_reference": reference,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
