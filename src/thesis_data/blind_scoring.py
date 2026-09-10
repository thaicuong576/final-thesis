"""Blind scoring helpers for the frozen provider pilot.

The module deliberately separates answer selection, arm blinding, Gold
reference construction, and scoring. It never mutates the Gold database or
provider manifests.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .query import EvidenceQuery, get_company_metrics, get_evidence, get_sector_benchmarks
from .run_manifest import ExperimentRunManifest


PUBLISHED_AGENT_BY_ARM = {
    "single_agent": "single_agent",
    "hierarchical_no_critique": "orchestrator",
    "hierarchical_bounded_critique": "orchestrator",
}


def blind_id_for(job_id: str, seed: str) -> str:
    """Return a deterministic reviewer-facing ID without exposing the job ID."""

    digest = hashlib.sha256(f"{seed}:{job_id}".encode("utf-8")).hexdigest()[:12]
    return f"answer-{digest}"


def select_published_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Select the answer that would be published for one experiment job.

    Verification payloads are process traces, not a final answer. Hierarchical
    arms therefore use their last orchestrator payload, even when a later
    verification payload exists.
    """

    arm = manifest.get("arm")
    preferred_agent = PUBLISHED_AGENT_BY_ARM.get(arm)
    if preferred_agent is None:
        raise ValueError("unknown_arm")
    payloads = manifest.get("payloads")
    if not isinstance(payloads, list) or not payloads:
        raise ValueError("manifest_payloads_missing")
    matches = [
        payload
        for payload in payloads
        if isinstance(payload, dict) and payload.get("agent_id") == preferred_agent
    ]
    if not matches:
        raise ValueError(f"published_payload_missing:{preferred_agent}")
    return deepcopy(matches[-1])


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove architecture identity from a reviewer-facing answer payload."""

    sanitized = deepcopy(payload)
    sanitized["agent_id"] = "answer"
    for key in ("arm", "run_id", "job_id", "filename", "model_id"):
        sanitized.pop(key, None)
    return sanitized


def load_provider_manifests(run_dir: Path) -> list[dict[str, Any]]:
    """Load and validate provider manifests, excluding the failure ledger."""

    paths = sorted(
        path
        for path in run_dir.glob("*.json")
        if path.name not in {"failures.json", "recovery-map.json"}
    )
    if not paths:
        raise ValueError("provider_manifests_missing")
    manifests: list[dict[str, Any]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            ExperimentRunManifest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid_manifest:{path.name}") from exc
        payload["_manifest_filename"] = path.name
        manifests.append(payload)

    job_ids = [manifest.get("job_id") for manifest in manifests]
    if any(not isinstance(job_id, str) or not job_id for job_id in job_ids):
        raise ValueError("manifest_job_id_missing")
    if len(set(job_ids)) != len(job_ids):
        raise ValueError("duplicate_job_ids")
    if len(manifests) != 39:
        raise ValueError(f"expected_39_manifests:{len(manifests)}")

    binding_fields = ("snapshot_id", "question_set_sha256", "rubric_version", "prompt_version", "model_id")
    for field in binding_fields:
        if len({manifest.get(field) for manifest in manifests}) != 1:
            raise ValueError(f"mixed_{field}")
    if {manifest.get("arm") for manifest in manifests} != set(PUBLISHED_AGENT_BY_ARM):
        raise ValueError("arm_set_mismatch")
    return manifests


CORE_METRICS = (
    "bank.npl_g35",
    "bank.llr_coverage",
    "bank.roa",
    "bank.roe",
)
TREND_METRICS = (
    "bank.npl_g35",
    "bank.roa",
    "bank.roe",
)
DEFAULT_PEERS = ("ACB", "TCB", "VPB")


def _question_metric_ids(question: dict[str, Any]) -> tuple[str, ...]:
    question_type = question.get("type")
    if question_type == "company_trend":
        return TREND_METRICS
    if question_type == "known_missing_or_conflict":
        target = question.get("target_cell", {})
        metric = target.get("metric")
        if isinstance(metric, str) and metric:
            return (metric,)
    return CORE_METRICS


def _question_periods(question: dict[str, Any]) -> tuple[str, ...]:
    periods = question.get("periods")
    if isinstance(periods, list) and periods:
        return tuple(periods)
    period = question.get("period")
    if isinstance(period, str) and period:
        return (period,)
    raise ValueError(f"question_period_missing:{question.get('id')}")


def _payload_dict(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return deepcopy(payload)


def _gold_reference(db_path: Path, question: dict[str, Any]) -> dict[str, Any]:
    ticker = question.get("issuer")
    if not isinstance(ticker, str) or not ticker:
        raise ValueError(f"question_issuer_missing:{question.get('id')}")
    metric_ids = _question_metric_ids(question)
    periods = _question_periods(question)
    company_by_period: dict[str, dict[str, Any]] = {}
    evidence: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for period in periods:
        company = get_company_metrics(
            db_path,
            ticker,
            period,
            metric_ids,
            source_tiers=("primary",),
        )
        company_dict = _payload_dict(company)
        company_by_period[period] = company_dict
        source_ids.update(company_dict.get("source_ids", []))

    question_type = question.get("type")
    sector_dict: dict[str, Any] | None = None
    if question_type in {"peer_comparison", "anomaly_review"}:
        period = periods[-1]
        sector = get_sector_benchmarks(
            db_path,
            "bank",
            period,
            CORE_METRICS,
            tickers=tuple(question.get("peer_set") or DEFAULT_PEERS),
            source_tiers=("primary",),
        )
        sector_dict = _payload_dict(sector)
        source_ids.update(sector_dict.get("source_ids", []))

    for period in periods:
        evidence.extend(
            item.model_dump(mode="json")
            for item in get_evidence(
                db_path,
                sorted(source_ids),
                EvidenceQuery(ticker=ticker, period=period),
                source_tiers=("primary",),
            )
        )

    return {
        "issuer": ticker,
        "periods": list(periods),
        "metric_ids": list(metric_ids),
        "company_by_period": company_by_period,
        "sector": sector_dict,
        "evidence": evidence,
        "source_ids": sorted(source_ids),
        "case_kind": question.get("case_kind"),
    }


def build_blind_packets(
    run_dir: Path,
    db_path: Path,
    question_set_path: Path,
    *,
    seed: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build reviewer packets and a private identity map for a frozen run."""

    manifests = load_provider_manifests(run_dir)
    question_set = json.loads(question_set_path.read_text(encoding="utf-8"))
    questions = {
        question["id"]: question
        for question in question_set.get("questions", [])
        if isinstance(question, dict) and isinstance(question.get("id"), str)
    }
    packets: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        question = questions.get(manifest.get("question_id"))
        if question is None:
            raise ValueError(f"question_missing:{manifest.get('question_id')}")
        blind_id = blind_id_for(manifest["job_id"], seed)
        if blind_id in private_map:
            raise ValueError("blind_id_collision")
        packet_question = {
            key: deepcopy(question[key])
            for key in (
                "id",
                "type",
                "issuer",
                "period",
                "periods",
                "peer_set",
                "target_cell",
                "case_kind",
                "prompt",
            )
            if key in question
        }
        packet = {
            "blind_id": blind_id,
            "question": packet_question,
            "answer": sanitize_payload(select_published_payload(manifest)),
            "gold_reference": _gold_reference(db_path, question),
        }
        packets.append(packet)
        private_map[blind_id] = {
            "job_id": manifest["job_id"],
            "run_id": manifest["run_id"],
            "arm": manifest["arm"],
            "question_id": manifest["question_id"],
            "manifest_filename": manifest["_manifest_filename"],
        }
    packets.sort(key=lambda packet: packet["blind_id"])
    return packets, private_map


def _close_enough(actual: Any, expected: Any, tolerance: float = 1e-6) -> bool:
    if actual is None or expected is None:
        return actual is expected
    try:
        return math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return False


def _answer_text(answer: dict[str, Any]) -> str:
    return json.dumps(answer, ensure_ascii=False).lower()


def _missing_reason_present(answer: dict[str, Any]) -> bool:
    text = _answer_text(answer)
    return any(
        marker in text
        for marker in (
            "missing",
            "unavailable",
            "unaccepted",
            "conflict",
            "unresolved",
            "excluded",
            "not available",
        )
    )


def _claim_rows(
    packet: dict[str, Any],
    *,
    expected: dict[str, Any],
    actual: dict[str, Any],
    field_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    expected_values = expected.get(field_name, {})
    actual_values = actual.get(field_name, {})
    valid_expected = 0
    factual_score = 0
    coverage_score = 0
    for metric, expected_value in expected_values.items():
        actual_value = actual_values.get(metric)
        if expected_value is None:
            correct_missing = actual_value is None and _missing_reason_present(actual)
            factual_score += int(correct_missing)
            coverage_score += int(correct_missing)
        else:
            valid_expected += 1
            correct = _close_enough(actual_value, expected_value)
            factual_score += int(correct)
            coverage_score += int(actual_value is not None)
    total = len(expected_values)
    if total:
        rows.append(
            {
                "blind_id": packet["blind_id"],
                "dimension": "factual_correctness",
                "score": int(factual_score == total),
                "reason_code": f"{field_name}_gold_match:{factual_score}/{total}",
            }
        )
        rows.append(
            {
                "blind_id": packet["blind_id"],
                "dimension": "coverage_discipline",
                "score": int(coverage_score == total),
                "reason_code": f"{field_name}_coverage:{coverage_score}/{total}",
            }
        )
        if valid_expected:
            rows.append(
                {
                    "blind_id": packet["blind_id"],
                    "dimension": "calculation_correctness",
                    "score": int(factual_score == total),
                    "reason_code": f"{field_name}_numeric_match:{factual_score}/{total}",
                }
            )
    return rows


def score_structured_answer(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Score structured numeric/provenance fields without reading arm identity."""

    question = packet["question"]
    answer = packet["answer"]
    reference = packet["gold_reference"]
    period = question.get("period") or (question.get("periods") or reference["periods"])[-1]
    expected_company = reference.get("company_by_period", {}).get(
        period, reference.get("company", {})
    )
    rows = _claim_rows(
        packet,
        expected=expected_company,
        actual=answer,
        field_name="metrics",
    )
    if reference.get("sector") is not None:
        rows.extend(
            _claim_rows(
                packet,
                expected=reference["sector"],
                actual=answer,
                field_name="sector_benchmarks",
            )
        )

    non_null_claims = [
        value
        for field in ("metrics", "sector_benchmarks")
        for value in answer.get(field, {}).values()
        if value is not None
    ]
    evidence = answer.get("evidence", [])
    if non_null_claims:
        has_locator = all(
            isinstance(item, dict)
            and item.get("source_id")
            and (item.get("page_number") or item.get("section_name"))
            for item in evidence
        )
        rows.append(
            {
                "blind_id": packet["blind_id"],
                "dimension": "evidence_completeness",
                "score": int(bool(evidence) and has_locator),
                "reason_code": "all_numeric_claims_have_located_evidence"
                if bool(evidence) and has_locator
                else "numeric_claims_missing_located_evidence",
            }
        )
        source_ids = set(answer.get("source_ids", []))
        observation_ids = answer.get("observation_ids", [])
        cited = any(
            isinstance(item, dict)
            and item.get("source_id") in source_ids
            and (item.get("period") in {None, period})
            for item in evidence
        )
        bound = all(
            any(str(metric) in str(observation_id) and str(period) in str(observation_id)
                for observation_id in observation_ids)
            for metric, value in answer.get("metrics", {}).items()
            if value is not None
        )
        rows.append(
            {
                "blind_id": packet["blind_id"],
                "dimension": "citation_correctness",
                "score": int(cited and bound),
                "reason_code": "provenance_and_locator_bound"
                if cited and bound
                else "provenance_or_locator_not_bound",
            }
        )

    if question.get("type") in {"company_trend", "peer_comparison", "anomaly_review"}:
        target_period = period
        metric_periods = answer.get("metric_periods", {})
        period_ok = all(
            value == target_period
            for metric, value in metric_periods.items()
            if metric in reference["metric_ids"]
        )
        rows.append(
            {
                "blind_id": packet["blind_id"],
                "dimension": "cross_level_consistency",
                "score": int(period_ok),
                "reason_code": "structured_periods_aligned"
                if period_ok
                else "structured_period_mismatch",
            }
        )
    return rows


def load_complexity_manifests(run_dir: Path) -> list[dict[str, Any]]:
    """Load composite manifests without imposing the Tier 1 39-job count."""

    paths = sorted(
        path
        for path in run_dir.glob("*.json")
        if path.name not in {"failures.json", "recovery-map.json"}
    )
    if not paths:
        raise ValueError("provider_manifests_missing")
    manifests: list[dict[str, Any]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            manifest = ExperimentRunManifest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid_manifest:{path.name}") from exc
        if manifest.workload_tier is None or manifest.complexity_vector is None:
            raise ValueError(f"composite_fields_missing:{path.name}")
        payload["_manifest_filename"] = path.name
        manifests.append(payload)
    job_ids = [manifest.get("job_id") for manifest in manifests]
    if any(not isinstance(job_id, str) or not job_id for job_id in job_ids):
        raise ValueError("manifest_job_id_missing")
    if len(set(job_ids)) != len(job_ids):
        raise ValueError("duplicate_job_ids")
    if {manifest.get("arm") for manifest in manifests} != set(PUBLISHED_AGENT_BY_ARM):
        raise ValueError("arm_set_mismatch")
    return manifests


def _composite_gold_reference(db_path: Path, question: dict[str, Any]) -> dict[str, Any]:
    workload = question.get("workload")
    if not isinstance(workload, dict):
        raise ValueError(f"composite_workload_missing:{question.get('id')}")
    issuers = tuple(workload.get("issuers") or ())
    periods = tuple(workload.get("periods") or ())
    metric_ids = tuple(workload.get("metric_ids") or ())
    tasks = tuple(workload.get("analysis_tasks") or ())
    peers = tuple(workload.get("peer_tickers") or issuers)
    cells: dict[str, dict[str, Any]] = {}
    source_ids: set[str] = set()
    for issuer in issuers:
        for period in periods:
            company = _payload_dict(
                get_company_metrics(db_path, issuer, period, metric_ids, source_tiers=("primary",))
            )
            source_ids.update(company.get("source_ids", []))
            sector = None
            if "peer_comparison" in tasks:
                sector = _payload_dict(
                    get_sector_benchmarks(
                        db_path,
                        "bank",
                        period,
                        metric_ids,
                        tickers=peers,
                        source_tiers=("primary",),
                    )
                )
                source_ids.update(sector.get("source_ids", []))
            for task in tasks:
                key = f"{issuer}|{period}|{task}"
                if task == "peer_comparison" and sector is not None:
                    cells[key] = {
                        "sector_benchmarks": sector.get("sector_benchmarks", {}),
                        "metric_units": sector.get("metric_units", {}),
                        "metric_periods": sector.get("metric_periods", {}),
                        "observation_ids": sector.get("observation_ids", []),
                        "source_ids": sector.get("source_ids", []),
                    }
                else:
                    cells[key] = {
                        "metrics": company.get("metrics", {}),
                        "metric_units": company.get("metric_units", {}),
                        "metric_periods": company.get("metric_periods", {}),
                        "observation_ids": company.get("observation_ids", []),
                        "source_ids": company.get("source_ids", []),
                        "findings": company.get("findings", []),
                    }
    evidence: list[dict[str, Any]] = []
    for issuer in issuers:
        for period in periods:
            evidence.extend(
                item.model_dump(mode="json")
                for item in get_evidence(
                    db_path,
                    sorted(source_ids),
                    EvidenceQuery(ticker=issuer, period=period),
                    source_tiers=("primary",),
                )
            )
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    for cell in cells.values():
        cell["evidence_ids"] = sorted(evidence_by_id)
    return {
        "workload_tier": workload.get("tier"),
        "issuers": list(issuers),
        "periods": list(periods),
        "metric_ids": list(metric_ids),
        "analysis_tasks": list(tasks),
        "cells": cells,
        "evidence": list(evidence_by_id.values()),
        "source_ids": sorted(source_ids),
    }


def _failed_composite_answer(manifest: dict[str, Any], question: dict[str, Any]) -> dict[str, Any]:
    """Create a blind-safe empty answer for an explicit failed provider job."""

    workload = question.get("workload") or {}
    return {
        "agent_id": "answer",
        "status": "failed",
        "question_id": question.get("id", manifest.get("question_id", "unknown")),
        "tier": workload.get("tier", manifest.get("workload_tier")),
        "issuers": list(workload.get("issuers") or []),
        "periods": list(workload.get("periods") or []),
        "metric_ids": list(workload.get("metric_ids") or []),
        "data_slices": [],
        "subreports": [],
        "missing_conflict_register": [],
        "anomaly_classifications": [],
        "findings": [],
        "quality_flags": ["provider_run_failed"],
        "observation_ids": [],
        "source_ids": [],
        "evidence_ids": [],
    }


def build_composite_blind_packets(
    run_dir: Path,
    db_path: Path,
    question_set_path: Path,
    *,
    seed: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build arm-blind packets for composite manifests."""

    manifests = load_complexity_manifests(run_dir)
    question_set = json.loads(question_set_path.read_text(encoding="utf-8"))
    questions = {
        question["id"]: question
        for question in question_set.get("questions", [])
        if isinstance(question, dict) and isinstance(question.get("id"), str)
    }
    packets: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        question = questions.get(manifest.get("question_id"))
        if question is None or question.get("type") != "composite_workload":
            raise ValueError(f"composite_question_missing:{manifest.get('question_id')}")
        blind_id = blind_id_for(manifest["job_id"], seed)
        if blind_id in private_map:
            raise ValueError("blind_id_collision")
        try:
            answer = sanitize_payload(select_published_payload(manifest))
        except ValueError as exc:
            if manifest.get("failure_status") is None:
                raise
            answer = _failed_composite_answer(manifest, question)
        packet = {
            "blind_id": blind_id,
            "question": {
                "id": question["id"],
                "type": question["type"],
                "prompt": question["prompt"],
                "workload": deepcopy(question["workload"]),
            },
            "answer": answer,
            "gold_reference": _composite_gold_reference(db_path, question),
        }
        packets.append(packet)
        private_map[blind_id] = {
            "job_id": manifest["job_id"],
            "run_id": manifest["run_id"],
            "arm": manifest["arm"],
            "workload_tier": manifest["workload_tier"],
            "question_id": manifest["question_id"],
            "manifest_filename": manifest["_manifest_filename"],
        }
    packets.sort(key=lambda packet: packet["blind_id"])
    return packets, private_map


def _composite_actual_cells(answer: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    data_slices: dict[tuple[str, str], dict[str, Any]] = {}
    for data_slice in answer.get("data_slices", []):
        if not isinstance(data_slice, dict):
            continue
        ticker = data_slice.get("ticker")
        period = data_slice.get("period")
        if isinstance(ticker, str) and isinstance(period, str):
            data_slices[(ticker, period)] = data_slice
    for item in answer.get("subreports", []):
        if not isinstance(item, dict):
            continue
        key = (item.get("issuer"), item.get("period"), item.get("task"))
        if all(isinstance(value, str) and value for value in key):
            resolved = dict(item)
            if not isinstance(resolved.get("payload"), dict):
                payload_ref = resolved.get("payload_ref")
                if isinstance(payload_ref, str) and "|" in payload_ref:
                    ticker, period = payload_ref.split("|", 1)
                    if (ticker, period) in data_slices:
                        resolved["_resolved_payload"] = data_slices[(ticker, period)]
            cells[key] = resolved
    return cells


def score_composite_answer(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Score composite coverage, facts, missing discipline, and provenance."""

    reference = packet["gold_reference"]
    answer = packet["answer"]
    expected_keys = {
        tuple(key.split("|", 2)) for key in reference.get("cells", {})
    }
    actual = _composite_actual_cells(answer)
    rows: list[dict[str, Any]] = []
    coverage_ok = set(actual) == expected_keys
    rows.append({
        "blind_id": packet["blind_id"],
        "dimension": "task_coverage",
        "score": int(coverage_ok),
        "reason_code": f"subreport_keys:{len(set(actual))}/{len(expected_keys)}",
    })
    scope_ok = (
        tuple(answer.get("issuers", ())) == tuple(reference.get("issuers", ()))
        and tuple(answer.get("periods", ())) == tuple(reference.get("periods", ()))
        and tuple(answer.get("metric_ids", ())) == tuple(reference.get("metric_ids", ()))
    )
    rows.append({
        "blind_id": packet["blind_id"],
        "dimension": "cross_issuer_consistency",
        "score": int(scope_ok and set(actual).issubset(expected_keys)),
        "reason_code": "composite_scope_bound" if scope_ok else "composite_scope_mismatch",
    })

    factual_ok = True
    missing_ok = True
    evidence_ok = True
    citation_ok = True
    slice_expected_observations: dict[tuple[str, str], set[str]] = {}
    slice_expected_sources: dict[tuple[str, str], set[str]] = {}
    for key, expected in reference.get("cells", {}).items():
        issuer, period, _task = tuple(key.split("|", 2))
        slice_expected_observations.setdefault((issuer, period), set()).update(
            expected.get("observation_ids", [])
        )
        slice_expected_sources.setdefault((issuer, period), set()).update(
            expected.get("source_ids", [])
        )
    for key, expected in reference.get("cells", {}).items():
        cell_key = tuple(key.split("|", 2))
        item = actual.get(cell_key)
        if item is None:
            factual_ok = False
            missing_ok = False
            continue
        payload = (
            item.get("payload")
            if isinstance(item.get("payload"), dict)
            else item.get("_resolved_payload", {})
        )
        if not isinstance(payload, dict):
            payload = {}
        field = "sector_benchmarks" if "sector_benchmarks" in expected else "metrics"
        expected_values = expected.get(field, {})
        actual_values = payload.get(field, {})
        for metric, expected_value in expected_values.items():
            actual_value = actual_values.get(metric)
            if expected_value is None:
                if actual_value is not None or not _missing_reason_present(item):
                    missing_ok = False
            elif not _close_enough(actual_value, expected_value):
                factual_ok = False
        numeric_values = [value for value in actual_values.values() if value is not None]
        if numeric_values:
            if not (
                payload.get("observation_ids")
                or payload.get("source_ids")
                or item.get("evidence_ids")
                or payload.get("evidence")
            ):
                evidence_ok = False
        issuer, period, _task = cell_key
        if item.get("_resolved_payload") is not None:
            expected_observations = slice_expected_observations.get((issuer, period), set())
            expected_sources = slice_expected_sources.get((issuer, period), set())
        else:
            expected_observations = set(expected.get("observation_ids", []))
            expected_sources = set(expected.get("source_ids", []))
        if not set(payload.get("observation_ids", [])).issubset(expected_observations):
            citation_ok = False
        if not set(payload.get("source_ids", [])).issubset(expected_sources):
            citation_ok = False

    rows.extend([
        {
            "blind_id": packet["blind_id"],
            "dimension": "factual_correctness",
            "score": int(factual_ok),
            "reason_code": "composite_gold_values_match" if factual_ok else "composite_gold_value_mismatch",
        },
        {
            "blind_id": packet["blind_id"],
            "dimension": "missing_conflict_discipline",
            "score": int(missing_ok),
            "reason_code": "missing_conflict_explicit" if missing_ok else "missing_conflict_not_explicit",
        },
        {
            "blind_id": packet["blind_id"],
            "dimension": "evidence_completeness",
            "score": int(evidence_ok),
            "reason_code": "numeric_subreports_have_provenance" if evidence_ok else "numeric_subreports_unbound",
        },
        {
            "blind_id": packet["blind_id"],
            "dimension": "citation_correctness",
            "score": int(citation_ok),
            "reason_code": "provenance_ids_in_gold" if citation_ok else "provenance_ids_outside_gold",
        },
    ])
    return rows


def operational_summary(manifests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate runtime telemetry without relying on reviewer-visible identity."""

    summary: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        arm = manifest["arm"]
        item = summary.setdefault(
            arm,
            {
                "jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "timeout_jobs": 0,
                "runtime_calls": 0,
                "tool_calls": 0,
                "tool_rejections": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_estimate_usd": 0.0,
                "latency_ms_total": 0.0,
                "wall_clock_latency_ms_total": 0.0,
                "payload_status_counts": {},
            },
        )
        item["jobs"] += 1
        if manifest.get("failure_status") is None:
            item["completed_jobs"] += 1
        else:
            item["failed_jobs"] += 1
            failure_text = " ".join(str(value) for value in manifest.get("failure_blockers", []))
            if "Timeout" in failure_text or "timeout" in failure_text.lower():
                item["timeout_jobs"] += 1
        calls = manifest.get("calls", [])
        item["runtime_calls"] += len(calls)
        for call in calls:
            item["tool_calls"] += len(call.get("tool_calls", []))
            item["tool_rejections"] += sum(
                1 for tool_call in call.get("tool_calls", [])
                if tool_call.get("status") == "rejected"
            )
            item["input_tokens"] += int(call.get("input_tokens") or 0)
            item["output_tokens"] += int(call.get("output_tokens") or 0)
            item["cost_estimate_usd"] += float(call.get("cost_estimate") or 0.0)
            item["latency_ms_total"] += float(call.get("latency_ms") or 0.0)
        item["wall_clock_latency_ms_total"] += float(manifest.get("wall_clock_latency_ms") or 0.0)
        for payload in manifest.get("payloads", []):
            status = payload.get("status", "unknown")
            counts = item["payload_status_counts"]
            counts[status] = counts.get(status, 0) + 1
    for item in summary.values():
        item["cost_estimate_usd"] = round(item["cost_estimate_usd"], 8)
        item["latency_ms_total"] = round(item["latency_ms_total"], 3)
        item["wall_clock_latency_ms_total"] = round(item["wall_clock_latency_ms_total"], 3)
        completed = item["completed_jobs"]
        item["timeout_rate"] = round(item["timeout_jobs"] / item["jobs"], 6) if item["jobs"] else 0.0
        item["cost_per_completed_job_usd"] = round(
            item["cost_estimate_usd"] / completed, 8
        ) if completed else None
        item["throughput_completed_jobs_per_minute"] = round(
            completed / (item["wall_clock_latency_ms_total"] / 60000), 6
        ) if completed and item["wall_clock_latency_ms_total"] > 0 else None
    return dict(sorted(summary.items()))


def operational_summary_by_tier(
    manifests: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Aggregate composite telemetry by workload tier and arm."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for manifest in manifests:
        tier = manifest.get("workload_tier")
        if isinstance(tier, str) and tier:
            grouped.setdefault(tier, []).append(manifest)
    return {
        tier: operational_summary(items)
        for tier, items in sorted(grouped.items())
    }
