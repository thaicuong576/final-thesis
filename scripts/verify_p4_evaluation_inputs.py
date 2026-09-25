#!/usr/bin/env python3
"""Verify immutable P4 candidate inputs, Gold provenance, and peer probes.

Ignored Gold and source evidence is read only from an explicit evidence root:

    python scripts/verify_p4_evaluation_inputs.py --evidence-root <project-root>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
AUDIT_REL = Path("data/evaluation/gold-v5-peer-input-audit-v1.json")
SCOPE_REL = Path("data/evaluation/gold-v5-reporting-scope-authority-v1.json")
QUESTIONS_REL = Path("data/evaluation/p4-questions-v1.jsonl")
TASKS_REL = Path("data/evaluation/p4-task-specs-v1.json")
COVERAGE_REL = Path("data/evaluation/p4-expected-coverage-v1.json")
GOLD_REL = Path("data/processed/gold-bank-2025-expanded-v5-evidence.sqlite")
METRIC_ORDER = ("bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe")
PERIOD_ORDER = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
PEER_AGGREGATION_VERSION = "peer_median_v1"
VERIFIER_VERSION = "p4-evaluation-inputs-v1"


class VerificationError(ValueError):
    """An immutable input or verification record does not match its authority."""


def _fail(message: str) -> None:
    raise VerificationError(message)


def _canonical_bytes(raw: bytes) -> bytes:
    text = raw.decode("utf-8", errors="strict")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha256(raw: bytes) -> str:
    return _sha256(_canonical_bytes(raw))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        _fail(f"expected JSON object: {path}")
    return payload


def verify_candidate_question_bindings(repository_root: Path) -> dict[str, Any]:
    """Check canonical question text, task eligibility, and linked manifest hashes."""

    repository_root = Path(repository_root).resolve()
    audit = _read_json(repository_root / AUDIT_REL)
    specs = _read_json(repository_root / TASKS_REL)
    coverage = _read_json(repository_root / COVERAGE_REL)
    question_bytes = (repository_root / QUESTIONS_REL).read_bytes()
    specs_bytes = (repository_root / TASKS_REL).read_bytes()
    coverage_bytes = (repository_root / COVERAGE_REL).read_bytes()
    evaluation_inputs = audit.get("evaluation_inputs", {})

    question_hash = _canonical_sha256(question_bytes)
    specs_hash = _canonical_sha256(specs_bytes)
    coverage_hash = _canonical_sha256(coverage_bytes)
    if (
        evaluation_inputs.get("question_set_hash_mode") != "canonical_lf_utf8_sha256"
        or specs.get("question_set", {}).get("hash_mode") != "canonical_lf_utf8_sha256"
        or coverage.get("question_set_hash_mode") != "canonical_lf_utf8_sha256"
    ):
        _fail("question set hash mode must be canonical_lf_utf8_sha256")
    expected_hashes = (
        (evaluation_inputs.get("question_set_canonical_lf_utf8_sha256"), question_hash, "question set"),
        (evaluation_inputs.get("task_specs_canonical_lf_utf8_sha256"), specs_hash, "task specs"),
        (evaluation_inputs.get("expected_coverage_canonical_lf_utf8_sha256"), coverage_hash, "expected coverage"),
        (specs.get("question_set", {}).get("canonical_lf_utf8_sha256"), question_hash, "task question reference"),
        (coverage.get("question_set_canonical_lf_utf8_sha256"), question_hash, "coverage question reference"),
        (coverage.get("task_specs_canonical_lf_utf8_sha256"), specs_hash, "coverage task-spec reference"),
    )
    for expected, actual, label in expected_hashes:
        if expected != actual:
            _fail(f"{label} hash mismatch")
    dataset_identity = (
        audit["dataset"]["dataset_id"],
        audit["dataset"]["snapshot_id"],
    )
    if (
        specs["dataset"].get("dataset_id"),
        specs["dataset"].get("snapshot_id"),
    ) != dataset_identity or (
        coverage.get("dataset_id"),
        coverage.get("snapshot_id"),
    ) != dataset_identity:
        _fail("dataset/snapshot identity differs across candidate manifests")

    if specs.get("status") != "immutable_candidate_question_set_not_final_experiment_freeze":
        _fail("task specs do not identify a pre-freeze candidate question set")
    if specs.get("question_set", {}).get("status") != "immutable_candidate_questions":
        _fail("question set is not marked immutable candidate input")
    if specs.get("freeze_condition", {}).get("protocol_final_freeze_ready") is not False:
        _fail("task specs incorrectly claim final protocol freeze readiness")
    if coverage.get("final_protocol_freeze_ready") is not False:
        _fail("coverage manifest incorrectly claims final protocol freeze readiness")
    if coverage.get("scoring_eligible_now") is not False:
        _fail("candidate coverage manifest incorrectly permits scoring")
    if specs.get("scoring_runs_created") is not False or specs.get("ab_c_results_created") is not False:
        _fail("candidate task specs claim evaluation outcomes exist")
    if evaluation_inputs.get("final_protocol_freeze_ready") is not False:
        _fail("audit incorrectly claims final protocol freeze readiness")
    if evaluation_inputs.get("completed_ab_c_results_created") is not False:
        _fail("audit incorrectly claims A/B/C outcomes exist")
    if evaluation_inputs.get("macro_tasks_included") is not False:
        _fail("candidate audit unexpectedly includes macro tasks")
    if evaluation_inputs.get("task_count") != 10:
        _fail("audit candidate task count changed")
    if evaluation_inputs.get("question_set_status") != specs["status"]:
        _fail("audit candidate question-set status mismatch")

    question_rows: list[dict[str, str]] = []
    for line_number, line in enumerate(question_bytes.splitlines(), start=1):
        row = json.loads(line.decode("utf-8", errors="strict"))
        if not isinstance(row, dict) or not isinstance(row.get("task_id"), str) or not isinstance(
            row.get("question_text"), str
        ):
            _fail(f"invalid question JSONL row at line {line_number}")
        question_rows.append(row)
    if len(question_rows) != 10 or len(specs.get("tasks", ())) != 10 or len(
        coverage.get("tasks", ())
    ) != 10:
        _fail("candidate task/question/coverage count must be ten")

    questions_by_id = {item["task_id"]: item for item in question_rows}
    coverage_by_id = {item.get("task_id"): item for item in coverage["tasks"]}
    if len(questions_by_id) != 10 or len(coverage_by_id) != 10:
        _fail("duplicate candidate task IDs")
    for task in specs["tasks"]:
        task_id = task.get("task_id")
        question = questions_by_id.get(task_id)
        coverage_task = coverage_by_id.get(task_id)
        if question is None or coverage_task is None:
            _fail(f"task is missing its question or expected coverage: {task_id}")
        expected_coverage = coverage_task.get("expected_coverage", {})
        question_hash_for_task = _sha256(question["question_text"].encode("utf-8"))
        if question_hash_for_task != task.get("question_sha256_utf8"):
            _fail(f"exact question text hash mismatch: {task_id}")
        if coverage_task.get("question_sha256_utf8") != question_hash_for_task:
            _fail(f"coverage question hash mismatch: {task_id}")
        status = task.get("current_eligibility_status")
        if expected_coverage.get("current_eligibility_status") != status:
            _fail(f"task eligibility status mismatch: {task_id}")
        if task.get("scoring_eligible_now") is not False or expected_coverage.get(
            "scoring_eligible_now"
        ) is not False:
            _fail(f"candidate task is marked scoring-eligible: {task_id}")
        if task_id in {"T04", "T05", "T08"}:
            required_blockers = {
                "T04": "ineligible_until_multi_period_runtime_contract",
                "T05": "ineligible_until_multi_period_runtime_contract",
                "T08": "ineligible_until_multi_period_peer_and_revision_e2e",
            }
            if status != required_blockers[task_id]:
                _fail(f"multi-period task is not ineligible: {task_id}")
            if task.get("current_runtime_behavior_or_blocker") != "multi_period_unsupported":
                _fail(f"multi-period task blocker is missing: {task_id}")
            if expected_coverage.get("expected_current_runtime_behavior_or_blocker") != "multi_period_unsupported":
                _fail(f"multi-period coverage blocker is missing: {task_id}")

    recorded_statuses = evaluation_inputs.get("task_eligibility_statuses")
    actual_statuses = {
        item["task_id"]: item["current_eligibility_status"] for item in specs["tasks"]
    }
    if recorded_statuses != actual_statuses:
        _fail("audit task eligibility map differs from task specs")

    return {
        "question_set_canonical_lf_utf8_sha256": question_hash,
        "task_specs_canonical_lf_utf8_sha256": specs_hash,
        "expected_coverage_canonical_lf_utf8_sha256": coverage_hash,
        "task_count": len(question_rows),
        "final_protocol_freeze_ready": False,
        "scoring_eligible_now": False,
    }


def peer_probe_record(observation: Any) -> dict[str, Any]:
    """Project a provider benchmark into the stable audit record shape."""

    metadata = observation.metadata
    return {
        "period_id": observation.period_id,
        "metric_id": observation.metric_id,
        "benchmark_observation_id": observation.observation_id,
        "validation_status": getattr(observation.validation_status, "value", observation.validation_status),
        "value": observation.value,
        "unit": observation.unit,
        "period_basis": observation.period_basis,
        "reporting_scope": observation.reporting_scope,
        "requested_peer_entity_ids": metadata.get("requested_peer_entity_ids"),
        "eligible_peer_entity_ids": metadata.get("eligible_peer_entity_ids"),
        "requested_denominator": metadata.get("requested_denominator"),
        "eligible_denominator": metadata.get("eligible_denominator"),
        "input_observation_ids": list(observation.input_observation_ids),
        "missing_members": metadata.get("missing_members"),
    }


def verify_peer_probe_records(
    actual_records: Sequence[Mapping[str, Any]],
    expected_records: Sequence[Mapping[str, Any]],
) -> None:
    """Require exact reproducibility of the 16 recorded provider probes."""

    key = lambda item: (item.get("period_id"), item.get("metric_id"))
    actual = sorted((dict(item) for item in actual_records), key=key)
    expected = sorted((dict(item) for item in expected_records), key=key)
    if len(actual) != 16 or len(expected) != 16:
        _fail("P4 peer probe record count must be sixteen")
    if len({key(item) for item in actual}) != 16 or len({key(item) for item in expected}) != 16:
        _fail("P4 peer probe records contain duplicate period/metric keys")
    if actual != expected:
        _fail("P4 peer provider outputs differ from the bound audit records")


def _safe_relative_path(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    candidate_ref = Path(normalized)
    if candidate_ref.is_absolute() or ".." in candidate_ref.parts:
        _fail(f"evidence reference is not a safe relative path: {relative}")
    resolved_root = Path(root).resolve()
    candidate = (resolved_root / candidate_ref).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        _fail(f"evidence reference escapes its root: {relative}")
    return candidate


def verify_gold_evidence(
    repository_root: Path,
    evidence_root: Path,
    audit: dict[str, Any],
    specs: dict[str, Any],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    """Verify the exact Gold snapshot, scope sidecar, sources, and peer probes."""

    repository_root = Path(repository_root).resolve()
    evidence_root = Path(evidence_root).resolve()
    gold_path = _safe_relative_path(evidence_root, GOLD_REL.as_posix())
    if not gold_path.is_file():
        _fail(f"missing ignored Gold snapshot; pass --evidence-root explicitly: {GOLD_REL}")
    gold_hash = _sha256(gold_path.read_bytes())
    expected_gold_hash = audit["dataset"]["sqlite_sha256_raw_file_bytes"]
    if gold_hash != expected_gold_hash or gold_hash != specs["dataset"]["sqlite_sha256_raw_file_bytes"]:
        _fail("Gold SQLite raw SHA-256 mismatch")
    if gold_hash != coverage["snapshot_sha256_raw_file_bytes"]:
        _fail("expected coverage references a different Gold SQLite hash")

    connection = sqlite3.connect(f"file:{gold_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok" or integrity != audit["dataset"]["integrity_check"]:
            _fail(f"Gold SQLite integrity check failed: {integrity}")
        snapshot = connection.execute(
            "SELECT snapshot_id FROM snapshot_metadata LIMIT 1"
        ).fetchone()
        if snapshot is None or snapshot["snapshot_id"] != audit["dataset"]["snapshot_id"]:
            _fail("Gold snapshot identity mismatch")
        rows = connection.execute(
            """SELECT observation_id,ticker,period,metric,value,unit,period_basis,
                      source_id,source_locator,quality_status,reason
               FROM metric_observations ORDER BY ticker,period,metric,observation_id"""
        ).fetchall()
        source_rows = connection.execute(
            "SELECT source_id,source_tier,quality_status,local_path,content_hash FROM source_records"
        ).fetchall()
    finally:
        connection.close()

    if len(rows) != 80:
        _fail(f"Gold observation cell count changed: {len(rows)}")
    rows_by_id = {str(row["observation_id"]): row for row in rows}
    if len(rows_by_id) != 80:
        _fail("Gold observation IDs are ambiguous")
    valid_rows = [row for row in rows if row["quality_status"] == "valid"]
    missing_rows = [row for row in rows if row["quality_status"] == "missing"]
    if len(valid_rows) != 76 or len(missing_rows) != 4 or len(valid_rows) + len(missing_rows) != 80:
        _fail("Gold valid/missing observation counts changed")
    expected_missing = {
        ("ACB", "2024_Q1", metric)
        for metric in METRIC_ORDER
    }
    actual_missing = {
        (row["ticker"], row["period"], row["metric"])
        for row in missing_rows
    }
    if actual_missing != expected_missing:
        _fail("Gold missing-cell coverage changed")
    if any(row["value"] is not None or not row["reason"] for row in missing_rows):
        _fail("Gold missing cells must keep a null value and original reason")
    for row in valid_rows:
        expected_basis = "point_in_time" if row["metric"] in METRIC_ORDER[:2] else "ttm"
        if row["unit"] != "%" or row["period_basis"] != expected_basis:
            _fail(f"Gold valid unit or period basis mismatch: {row['observation_id']}")
        if row["value"] is None or row["source_id"] is None or row["source_locator"] is None:
            _fail(f"Gold valid row lacks value/source locator: {row['observation_id']}")

    scope_authority_path = repository_root / SCOPE_REL
    scope_hash = _canonical_sha256(scope_authority_path.read_bytes())
    scope_record = audit["scope_authority"]
    if scope_hash != scope_record["canonical_lf_utf8_sha256"]:
        _fail("reporting-scope authority sidecar hash mismatch")
    if scope_hash != specs["dataset"]["authority_sidecar_sha256_canonical_lf_utf8"]:
        _fail("task specs reference a different reporting-scope authority")

    sys.path.insert(0, str(repository_root / "src"))
    from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
    from thesis_data.gold_scope_authority import VerifiedGoldObservationScopeAuthority

    authority = VerifiedGoldObservationScopeAuthority.load(
        scope_authority_path,
        expected_canonical_sha256=scope_hash,
    )
    if (
        authority.authority.dataset_id != audit["dataset"]["dataset_id"]
        or authority.authority.snapshot_id != audit["dataset"]["snapshot_id"]
        or authority.authority.gold_snapshot_sha256 != gold_hash
    ):
        _fail("scope authority dataset/snapshot/Gold hash identity mismatch")
    entries = authority.entries_by_observation_id
    if set(entries) != {str(row["observation_id"]) for row in valid_rows}:
        _fail("scope authority must contain every and only accepted Gold observation ID")
    for row in valid_rows:
        entry = entries[str(row["observation_id"])]
        actual_tuple = (
            entry.entity_id,
            entry.period_id,
            entry.metric_id,
            float(entry.value),
            entry.unit,
            entry.period_basis,
            entry.source_ref,
            entry.source_locator,
            entry.reporting_scope,
            entry.review_status,
        )
        expected_tuple = (
            row["ticker"],
            row["period"],
            row["metric"],
            float(row["value"]),
            row["unit"],
            row["period_basis"],
            row["source_id"],
            row["source_locator"],
            "consolidated",
            "accepted",
        )
        if actual_tuple != expected_tuple:
            _fail(f"scope authority does not exactly match Gold row: {row['observation_id']}")

    ledger_path = _safe_relative_path(evidence_root, authority.authority.source_review_ledger_ref)
    if not ledger_path.is_file() or _sha256(ledger_path.read_bytes()) != authority.authority.source_review_ledger_raw_file_bytes_sha256:
        _fail("scope authority source review ledger raw hash mismatch")
    source_authority_ref = authority.authority.source_authority_manifest_ref
    source_authority_path = (repository_root / source_authority_ref).resolve()
    if not source_authority_path.is_file():
        source_authority_path = _safe_relative_path(evidence_root, source_authority_ref)
    if not source_authority_path.is_file() or _canonical_sha256(source_authority_path.read_bytes()) != authority.authority.source_authority_manifest_canonical_lf_utf8_sha256:
        _fail("scope authority upstream manifest canonical hash mismatch")

    audit_records = audit["observation_audit_records"]
    if len(audit_records) != 80 or {item["observation_id"] for item in audit_records} != set(rows_by_id):
        _fail("observation audit record set does not match all 80 Gold cells")
    source_rows_by_id = {str(row["source_id"]): row for row in source_rows}
    records_by_id = {item["observation_id"]: item for item in audit_records}
    for row in rows:
        observation_id = str(row["observation_id"])
        record = records_by_id[observation_id]
        is_valid = row["quality_status"] == "valid"
        source = source_rows_by_id.get(str(row["source_id"])) if is_valid else None
        expected_record = {
            "entity_id": row["ticker"],
            "period_id": row["period"],
            "metric_id": row["metric"],
            "unit": row["unit"],
            "period_basis": row["period_basis"],
            "source_ref": row["source_id"],
            "source_locator": row["source_locator"],
            "validation_status": row["quality_status"],
            "source_tier": source["source_tier"] if source else None,
            "source_status": source["quality_status"] if source else None,
            "reporting_scope": "consolidated" if is_valid else None,
            "scope_review_status": "accepted" if is_valid else None,
            "scope_authority_ref": scope_record["path"] if is_valid else None,
            "scope_authority_sha256": scope_hash if is_valid else None,
            "missing_reason": row["reason"],
        }
        if any(record.get(key) != value for key, value in expected_record.items()):
            _fail(f"observation audit record differs from Gold/authority: {observation_id}")

    source_manifest = audit["source_artifact_hashes"]
    source_records = source_manifest["records"]
    if source_manifest["hash_mode"] != "raw_file_bytes_sha256":
        _fail("source artifacts use the wrong hash mode")
    used_source_ids = {str(row["source_id"]) for row in valid_rows}
    if len(source_records) != 17 or source_manifest["source_records_checked"] != 17:
        _fail("source artifact audit must contain all 17 source records")
    if {item["source_id"] for item in source_records} != used_source_ids:
        _fail("source artifact audit does not match the Gold valid-cell sources")
    if source_manifest["matches"] != 17 or source_manifest["mismatches"] != 0:
        _fail("source artifact audit reports a mismatch")
    source_audit_by_id = {item["source_id"]: item for item in source_records}
    verified_sources: dict[str, str] = {}
    for source_id in sorted(used_source_ids):
        source = source_rows_by_id.get(source_id)
        source_record = source_audit_by_id[source_id]
        if source is None or source["source_tier"] != "primary" or source["quality_status"] != "valid":
            _fail(f"Gold observation source is not an accepted primary source: {source_id}")
        if source_record.get("status") != "match":
            _fail(f"source artifact audit status is not match: {source_id}")
        stored_hash = str(source["content_hash"])
        if not stored_hash.startswith("sha256:"):
            _fail(f"Gold source record lacks a SHA-256 content hash: {source_id}")
        source_path = _safe_relative_path(evidence_root, str(source["local_path"]))
        if not source_path.is_file():
            missing_source_path = source["local_path"]
            _fail(f"missing ignored source artifact; pass --evidence-root explicitly: {missing_source_path}")
        actual_source_hash = _sha256(source_path.read_bytes())
        expected_source_hash = source_record.get("sha256")
        if actual_source_hash != expected_source_hash or stored_hash[7:] != expected_source_hash:
            _fail(f"raw source artifact hash mismatch: {source_id}")
        verified_sources[source_id] = actual_source_hash

    actual_missing_records = [
        {
            "observation_id": str(row["observation_id"]),
            "entity_id": row["ticker"],
            "period_id": row["period"],
            "metric_id": row["metric"],
            "reason": row["reason"],
        }
        for row in missing_rows
    ]
    if actual_missing_records != audit["coverage"]["missing_observations"]:
        _fail("Gold missing observation reasons differ from audit")

    for item in coverage["tasks"]:
        expected = item["expected_coverage"]
        required_ids = expected.get("required_observation_ids", [])
        missing_ids = expected.get("missing_observation_ids", [])
        if expected.get("result") == "negative_scope_control_not_executed":
            if expected.get("required_observations") != 0:
                _fail(f"negative control unexpectedly requires Gold observations: {item['task_id']}")
            continue
        if expected.get("result") != "expected_gold_coverage_not_runtime_result":
            _fail(f"unexpected candidate coverage status: {item['task_id']}")
        if (
            len(required_ids) != expected.get("required_observation_count")
            or len(missing_ids) != expected.get("missing_count")
            or expected.get("valid_count") + expected.get("missing_count")
            != expected.get("required_observation_count")
        ):
            _fail(f"candidate task coverage counts mismatch: {item['task_id']}")
        if len(set(required_ids)) != len(required_ids) or not set(missing_ids).issubset(
            required_ids
        ):
            _fail(f"inconsistent Gold observation IDs in candidate coverage: {item['task_id']}")
        valid_ids = set(required_ids) - set(missing_ids)
        if len(valid_ids) != expected.get("valid_count"):
            _fail(f"candidate task valid-cell count mismatch: {item['task_id']}")
        for observation_id in required_ids:
            row = rows_by_id.get(observation_id)
            if row is None:
                _fail(f"candidate task requires an absent Gold cell: {item['task_id']}/{observation_id}")
        for observation_id in missing_ids:
            row = rows_by_id.get(observation_id)
            if row is None or row["quality_status"] != "missing":
                _fail(f"candidate task missing-cell reference changed: {item['task_id']}/{observation_id}")
        for observation_id in valid_ids:
            row = rows_by_id[observation_id]
            if row["quality_status"] != "valid":
                _fail(f"candidate task valid-cell reference changed: {item['task_id']}/{observation_id}")

    from thesis_data.dataset_contract import DatasetRef, QualityStatus

    dataset_ref = DatasetRef(
        dataset_id=audit["dataset"]["dataset_id"],
        dataset_snapshot_id=audit["dataset"]["snapshot_id"],
    )
    provider = GoldSqliteDatasetProvider(
        gold_path,
        dataset_id=dataset_ref.dataset_id,
        scope_authority=authority,
    )
    provider_ref = provider.current_dataset_ref()
    if provider_ref != dataset_ref:
        _fail("Gold provider dataset reference differs from audit identity")
    peer_ids = tuple(audit["peer_universe"]["entity_ids"])
    if len(peer_ids) != 5 or peer_ids != tuple(sorted(peer_ids)):
        _fail("peer universe is not the exact sorted five-bank set")
    actual_peer_observations = provider.get_peer_benchmark(
        provider_ref,
        audit["peer_universe"]["peer_universe_id"],
        PERIOD_ORDER[0],
        METRIC_ORDER,
        peer_entity_ids=peer_ids,
    )
    peer_observations = list(actual_peer_observations)
    for period_id in PERIOD_ORDER[1:]:
        peer_observations.extend(
            provider.get_peer_benchmark(
                provider_ref,
                audit["peer_universe"]["peer_universe_id"],
                period_id,
                METRIC_ORDER,
                peer_entity_ids=peer_ids,
            )
        )
    if len(peer_observations) != 16:
        _fail(f"Gold peer provider returned {len(peer_observations)} probes, expected 16")
    peer_observations.sort(key=lambda item: (item.period_id, METRIC_ORDER.index(item.metric_id)))
    actual_probes = [peer_probe_record(item) for item in peer_observations]

    peer_manifest = audit["peer_provider_probe"]
    if peer_manifest.get("result") != "PASS" or peer_manifest.get("aggregation_version") != PEER_AGGREGATION_VERSION:
        _fail("peer provider probe does not identify the supported aggregation")
    expected_keys = {
        "denominator_key": "eligible_denominator",
        "requested_denominator_key": "requested_denominator",
        "requested_members_key": "requested_peer_entity_ids",
        "eligible_members_key": "eligible_peer_entity_ids",
        "member_lineage_key": "input_observation_ids",
        "missing_reasons_key": "missing_members",
    }
    if any(peer_manifest.get(key) != value for key, value in expected_keys.items()):
        _fail("peer provider probe metadata-key contract changed")
    verify_peer_probe_records(actual_probes, peer_manifest.get("probes", ()))

    expected_denominators = [
        {
            "period_id": record["period_id"],
            "metric_id": record["metric_id"],
            "requested_denominator": record["requested_denominator"],
            "eligible_denominator": record["eligible_denominator"],
            "missing_entity_ids": [item["entity_id"] for item in record["missing_members"]],
        }
        for record in actual_probes
    ]
    if expected_denominators != peer_manifest.get("period_metric_denominators"):
        _fail("peer provider denominator matrix mismatch")
    for item, record in zip(peer_observations, actual_probes, strict=True):
        if item.validation_status is not QualityStatus.VALID or item.value is None:
            _fail(f"peer probe unexpectedly has no accepted values: {item.period_id}/{item.metric_id}")
        input_rows = [rows_by_id[observation_id] for observation_id in item.input_observation_ids]
        expected_input_ids = [
            str(row["observation_id"])
            for entity_id in peer_ids
            for row in rows
            if row["ticker"] == entity_id
            and row["period"] == item.period_id
            and row["metric"] == item.metric_id
            and row["quality_status"] == "valid"
        ]
        if list(item.input_observation_ids) != expected_input_ids:
            _fail(f"peer probe input order/denominator mismatch: {item.period_id}/{item.metric_id}")
        if item.metadata["requested_peer_entity_ids"] != list(peer_ids):
            _fail(f"peer probe requested peer set mismatch: {item.period_id}/{item.metric_id}")
        if item.metadata["eligible_peer_entity_ids"] != [row["ticker"] for row in input_rows]:
            _fail(f"peer probe eligible peer set mismatch: {item.period_id}/{item.metric_id}")
        if item.metadata["eligible_denominator"] != len(input_rows):
            _fail(f"peer probe accepted denominator mismatch: {item.period_id}/{item.metric_id}")
        if item.reporting_scope != "consolidated":
            _fail(f"peer probe lacks authority-backed consolidated scope: {item.period_id}/{item.metric_id}")
        if any(row["period_basis"] != item.period_basis or row["unit"] != item.unit for row in input_rows):
            _fail(f"peer probe mixes basis or units: {item.period_id}/{item.metric_id}")
        median_value = float(statistics.median(float(row["value"]) for row in input_rows))
        if not math.isclose(float(item.value), median_value, rel_tol=0.0, abs_tol=1e-12):
            _fail(f"peer probe median cannot be reproduced: {item.period_id}/{item.metric_id}")

    if _sha256(gold_path.read_bytes()) != gold_hash:
        _fail("Gold SQLite bytes changed during read-only verification")

    return {
        "gold_snapshot_raw_sha256": gold_hash,
        "gold_integrity_check": "ok",
        "gold_cells_checked": len(rows),
        "valid_cells": len(valid_rows),
        "missing_cells": len(missing_rows),
        "scope_authority_canonical_lf_utf8_sha256": scope_hash,
        "source_artifacts_checked": len(verified_sources),
        "source_artifacts_matched": len(verified_sources),
        "peer_probes_reproduced": len(peer_observations),
    }


def verify(repository_root: Path, evidence_root: Path) -> dict[str, Any]:
    repository_root = Path(repository_root).resolve()
    audit = _read_json(repository_root / AUDIT_REL)
    specs = _read_json(repository_root / TASKS_REL)
    coverage = _read_json(repository_root / COVERAGE_REL)
    if audit.get("audit_status") != "PASS":
        _fail("P4 peer-input audit is not marked PASS")
    verifier_record = audit.get("p4_input_verifier", {})
    if (
        verifier_record.get("script") != "scripts/verify_p4_evaluation_inputs.py"
        or verifier_record.get("version") != VERIFIER_VERSION
        or verifier_record.get("command")
        != "python scripts/verify_p4_evaluation_inputs.py --evidence-root <explicit-root>"
        or verifier_record.get("result") != "PASS"
    ):
        _fail("audit does not name the P4 input verifier and exact command/version")
    upstream_scope = audit.get("upstream_vpb_authority_verifier", {}).get("scope", "")
    if "does not verify the P4 reporting-scope sidecar" not in upstream_scope:
        _fail("upstream VPB verifier scope does not clearly exclude P4 verification")
    binding_report = verify_candidate_question_bindings(repository_root)
    gold_report = verify_gold_evidence(repository_root, evidence_root, audit, specs, coverage)
    return {
        "verifier": VERIFIER_VERSION,
        "result": "PASS",
        "repository_root": str(repository_root),
        "evidence_root": str(Path(evidence_root).resolve()),
        "candidate_bindings": binding_report,
        "gold_and_peer_evidence": gold_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-root",
        required=True,
        type=Path,
        help="explicit root for ignored Gold SQLite, source PDFs, and the review ledger",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(verify(ROOT, args.evidence_root), ensure_ascii=False, indent=2, sort_keys=True))
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"P4_EVALUATION_INPUTS_VERIFY: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
