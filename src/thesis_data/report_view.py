"""Build a user-facing report view from a run manifest and a Gold snapshot."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable


METRIC_LABELS = {
    "bank.npl_g35": "NPL nhóm 3–5",
    "bank.llr_coverage": "LLR Coverage",
    "bank.roa": "ROA",
    "bank.roe": "ROE",
    "bank.cir": "CIR",
    "bank.nim": "NIM",
}


def _connection(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def metric_label(metric_id: str) -> str:
    return METRIC_LABELS.get(metric_id, metric_id.removeprefix("bank.").replace("_", " ").upper())


def format_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        suffix = unit or ""
        return f"{value:.4f}{suffix}"
    return str(value)


def _period_key(period: str) -> tuple[int, int, str]:
    try:
        year, quarter = period.split("_Q")
        return int(year), int(quarter), period
    except ValueError:
        return 9999, 9, period


def _row_status(row: dict[str, Any] | None) -> str:
    if row is None:
        return "missing"
    return str(row["quality_status"])


def _choose_observation(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    # A valid observation is authoritative when a scope contains retained variants.
    priority = {"valid": 0, "missing": 1, "conflicting": 2, "pending_validation": 3, "invalid": 4}
    return sorted(rows, key=lambda row: (priority.get(row["quality_status"], 9), row["observation_id"]))[0]


def _locator_pages(locator: str | None) -> set[int]:
    """Extract explicit PDF/page ranges from a source locator.

    Evidence is stored by source/ticker/period, so attaching every snippet from
    a source to every metric would overstate claim support.  Page-aware
    locators let the report layer retain only snippets that can plausibly
    support that metric.  Locators without an explicit page remain unfiltered
    for non-paginated/API sources.
    """

    if not locator:
        return set()
    pages: set[int] = set()
    for match in re.finditer(r"(?:pdf_|printed_)?pages?\s*[:=]\s*([^;]+)", locator, flags=re.IGNORECASE):
        pages.update(int(value) for value in re.findall(r"\d+", match.group(1)))
    return pages


def _evidence_for_metric(
    candidates: list[dict[str, Any]],
    source_locator: str | None,
) -> list[dict[str, Any]]:
    locator_pages = _locator_pages(source_locator)
    if not locator_pages:
        return candidates
    filtered = [
        item for item in candidates
        if item.get("page_number") is None or item.get("page_number") in locator_pages
    ]
    row_match = re.search(r"(?:^|;)row\s*:\s*([^;]+)", source_locator or "", flags=re.IGNORECASE)
    if row_match:
        row_term = " ".join(row_match.group(1).lower().split())
        filtered = [
            item for item in filtered
            if row_term in " ".join(
                " ".join(str(item.get(field) or "").lower().split())
                for field in ("evidence_id", "section_name", "quote")
            )
        ]
    return filtered


def load_report_view(manifest_path: Path, db_path: Path) -> dict[str, Any]:
    """Create a deterministic ReportView without modifying either input."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    payload = manifest.get("final_payload") or {}
    issuers = tuple(manifest.get("issuers") or payload.get("issuers") or ())
    periods = tuple(manifest.get("periods") or payload.get("periods") or ())
    metric_ids = tuple(manifest.get("metric_ids") or payload.get("metric_ids") or ())
    if not issuers or not periods or not metric_ids:
        raise ValueError("manifest must declare issuers, periods and metric_ids")

    connection = _connection(db_path)
    connection.row_factory = sqlite3.Row
    try:
        observations: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            """
            SELECT observation_id, ticker, metric, value, unit, period, period_basis,
                   source_id, source_locator, quality_status, reason
            FROM metric_observations
            WHERE ticker IN ({issuers}) AND period IN ({periods}) AND metric IN ({metrics})
            ORDER BY ticker, period, metric, observation_id
            """.format(
                issuers=",".join("?" for _ in issuers),
                periods=",".join("?" for _ in periods),
                metrics=",".join("?" for _ in metric_ids),
            ),
            (*issuers, *periods, *metric_ids),
        ):
            item = dict(row)
            observations[(item["ticker"], item["period"], item["metric"])].append(item)

        sources = {
            row["source_id"]: dict(row)
            for row in connection.execute(
                "SELECT source_id, source_type, source_tier, source_url, publisher, quality_status FROM source_records"
            )
        }
        evidence_by_scope: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            """
            SELECT evidence_id, source_id, source_document, page_number, section_name,
                   period, ticker, quote, retrieval_score, parser_status, is_paginated
            FROM evidence_snippets
            WHERE source_id IN (SELECT source_id FROM source_records WHERE quality_status = 'valid')
            ORDER BY ticker, period, source_id, page_number, evidence_id
            """
        ):
            item = dict(row)
            evidence_by_scope[(item.get("ticker") or "", item.get("period") or "", item["source_id"])].append(item)
    finally:
        connection.close()

    matrix: list[dict[str, Any]] = []
    missing_cells: list[dict[str, str]] = []
    evidence_linked = 0
    valid_count = 0
    total_count = len(issuers) * len(periods) * len(metric_ids)

    for ticker in issuers:
        for period in sorted(periods, key=_period_key):
            metrics: list[dict[str, Any]] = []
            row_status = "success"
            for metric_id in metric_ids:
                observation = _choose_observation(observations.get((ticker, period, metric_id), []))
                status = _row_status(observation)
                if status != "valid":
                    row_status = "partial"
                else:
                    valid_count += 1
                if observation is None or status != "valid":
                    missing_cells.append({"ticker": ticker, "period": period, "metric": metric_id, "reason": (observation or {}).get("reason") or "no valid Gold observation"})
                source = sources.get((observation or {}).get("source_id"))
                evidence = []
                if observation and observation.get("source_id"):
                    exact_candidates = evidence_by_scope.get((ticker, period, observation["source_id"]), [])
                    wildcard_candidates = evidence_by_scope.get((ticker, "", observation["source_id"]), [])
                    # A source such as a FY presentation may contain a
                    # multi-quarter table and therefore intentionally has
                    # period=NULL in the evidence record.  Merge it with any
                    # exact-period snippets, then rely on locator/page
                    # matching to keep the metric scope precise.
                    candidates = list({
                        item["evidence_id"]: item
                        for item in (*exact_candidates, *wildcard_candidates)
                    }.values())
                    evidence = _evidence_for_metric(
                        candidates,
                        (observation or {}).get("source_locator"),
                    )
                if evidence:
                    evidence_linked += 1
                metrics.append(
                    {
                        "metric_id": metric_id,
                        "label": metric_label(metric_id),
                        "value": observation.get("value") if observation else None,
                        "display_value": format_value((observation or {}).get("value"), (observation or {}).get("unit")),
                        "unit": (observation or {}).get("unit"),
                        "period_basis": (observation or {}).get("period_basis"),
                        "status": status,
                        "reason": (observation or {}).get("reason"),
                        "observation_id": (observation or {}).get("observation_id"),
                        "source_id": (observation or {}).get("source_id"),
                        "source_locator": (observation or {}).get("source_locator"),
                        "source": {
                            "source_id": source.get("source_id"),
                            "source_type": source.get("source_type"),
                            "source_tier": source.get("source_tier"),
                            "source_url": source.get("source_url"),
                            "publisher": source.get("publisher"),
                        } if source else None,
                        "evidence_ids": [item["evidence_id"] for item in evidence],
                        "evidence": evidence,
                    }
                )
            matrix.append({"ticker": ticker, "period": period, "status": row_status, "metrics": metrics})

    payload_findings = payload.get("findings", []) if isinstance(payload, dict) else []
    payload_claims = payload.get("claims", []) if isinstance(payload, dict) else []
    payload_flags = payload.get("quality_flags", []) if isinstance(payload, dict) else []
    analysis = {
        "findings": _unique(str(item) for item in payload_findings),
        "anomaly_classifications": _unique(str(item) for item in payload.get("anomaly_classifications", []) if isinstance(payload, dict)),
        "missing_conflict_register": _unique(str(item) for item in payload.get("missing_conflict_register", []) if isinstance(payload, dict)),
        "quality_flags": _unique(str(item) for item in payload_flags),
        "model_claims": payload_claims if isinstance(payload_claims, list) else [],
    }
    status = str(payload.get("status") or ("success" if not missing_cells else "partial"))
    return {
        "contract_version": "report-view-v1",
        "run": {
            "run_id": manifest.get("run_id"),
            "job_id": manifest.get("job_id"),
            "snapshot_id": manifest.get("snapshot_id"),
            "question_id": manifest.get("question_id"),
            "question_set_id": manifest.get("question_set_id"),
            "arm": manifest.get("arm"),
            "model_id": manifest.get("model_id"),
            "status": status,
            "recorded_at_utc": manifest.get("recorded_at_utc"),
            "telemetry": {
                "call_count": manifest.get("call_count", 0),
                "tool_calls": manifest.get("total_tool_calls", 0),
                "input_tokens": manifest.get("total_input_tokens", 0),
                "output_tokens": manifest.get("total_output_tokens", 0),
                "cost_estimate_usd": manifest.get("total_cost_estimate"),
                "wall_clock_latency_ms": manifest.get("wall_clock_latency_ms"),
            },
        },
        "scope": {
            "issuers": list(issuers),
            "periods": sorted(periods, key=_period_key),
            "metrics": [{"metric_id": metric_id, "label": metric_label(metric_id), "unit": "%"} for metric_id in metric_ids],
        },
        "summary": {
            "total_cells": total_count,
            "valid_cells": valid_count,
            "missing_or_unaccepted_cells": total_count - valid_count,
            "cells_with_stored_evidence": evidence_linked,
            "source_count": len({item["source_id"] for row in matrix for item in row["metrics"] if item.get("source_id")}),
            "partial": status == "partial" or bool(missing_cells),
        },
        "matrix": matrix,
        "missing_cells": missing_cells,
        "analysis": analysis,
        "database": {"path": str(db_path), "authority": "gold_snapshot"},
    }
