"""Deterministic compact context contracts for composite agent stages."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class ContextBudgetError(ValueError):
    """Prepared context cannot cross the configured bounded-context boundary."""

    def __init__(self, actual_chars: int, budget_chars: int):
        self.actual_chars = actual_chars
        self.budget_chars = budget_chars
        self.blockers = (
            "context_budget_exceeded",
            f"context_chars={actual_chars}",
            f"context_budget_chars={budget_chars}",
        )
        super().__init__("context budget exceeded")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def json_chars(value: Any) -> int:
    return len(canonical_json(value))


def _compact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep facts, scope, and provenance while removing repeated prose."""

    data_slices: list[dict[str, Any]] = []
    for raw in payload.get("data_slices", ()) or ():
        if not isinstance(raw, Mapping):
            continue
        data_slices.append(
            {
                key: raw[key]
                for key in (
                    "agent_id", "status", "ticker", "period", "metrics",
                    "sector_benchmarks", "metric_units", "metric_periods",
                    "observation_ids", "source_ids", "evidence",
                    "quality_flags",
                )
                if key in raw
            }
        )

    subreports: dict[str, Any] = {}
    raw_subreports = payload.get("subreports", ()) or ()
    if isinstance(raw_subreports, Mapping):
        items = raw_subreports.items()
    else:
        items = (
            (
                f"{item.get('issuer')}|{item.get('period')}|{item.get('task')}",
                item,
            )
            for item in raw_subreports
            if isinstance(item, Mapping)
        )
    for key, raw in items:
        if not isinstance(raw, Mapping):
            continue
        compact = {
            field: raw[field]
            for field in (
                "status", "payload_ref", "missing_reasons", "observation_ids",
                "source_ids", "evidence_ids",
            )
            if field in raw
        }
        # A legacy payload may inline a task-specific payload. Preserve only
        # its factual/provenance fields; never silently turn it into prose.
        inline = raw.get("payload")
        if isinstance(inline, Mapping):
            compact["payload"] = _compact_payload(inline)
        subreports[str(key)] = compact

    return {
        key: payload[key]
        for key in (
            "agent_id", "status", "question_id", "tier", "issuers", "periods",
            "metric_ids", "missing_conflict_register", "anomaly_classifications",
            "observation_ids", "source_ids", "evidence_ids",
        )
        if key in payload
    } | {
        "data_slices": data_slices,
        "subreports": subreports,
    }


def compact_composite_context(
    context: Mapping[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    """Create bounded worker context and fail closed if it cannot fit.

    The compactor removes duplicated task prose, but never removes numeric
    values or their observation/source/evidence provenance. A context that is
    still too large is rejected instead of being truncated silently.
    """

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    compact: dict[str, Any] = {}
    for key, value in context.items():
        if key in {"worker_payloads", "orchestrator_payload"}:
            if isinstance(value, Mapping):
                compact[key] = {
                    str(role): _compact_payload(payload)
                    for role, payload in value.items()
                    if isinstance(payload, Mapping)
                } if key == "worker_payloads" else _compact_payload(value)
            else:
                compact[key] = value
        else:
            compact[key] = value
    compact["_context_contract"] = {
        "version": "compact-composite-context-v1",
        "facts_preserved": True,
        "provenance_preserved": True,
        "repeated_task_prose_removed": True,
    }
    actual_chars = json_chars(compact)
    if actual_chars > max_chars:
        raise ContextBudgetError(actual_chars, max_chars)
    return compact

