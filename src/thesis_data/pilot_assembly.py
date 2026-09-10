"""Assemble official pilot candidates into a single non-gold snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping, Sequence

from .schema import EvidenceSnippet, MetricObservation, QualityStatus, SourceRecord
from .storage import create_gold_snapshot_schema


_METRIC_FIELDS = {
    "observation_id",
    "ticker",
    "sector",
    "metric",
    "value",
    "unit",
    "period",
    "as_of_date",
    "period_basis",
    "source_id",
    "source_locator",
    "quality_status",
    "reason",
}


@dataclass(frozen=True)
class PilotAssemblyResult:
    output_path: str
    snapshot_id: str
    candidate_count: int
    placeholder_count: int
    unique_candidate_cells: int
    source_count: int
    evidence_count: int


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid source manifest JSON: {path}") from exc
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise ValueError(f"source manifest must contain an array of objects: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read JSONL input: {path}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _source_quality_status(raw_status: str) -> QualityStatus:
    if raw_status in {
        "retrieved_pending_validation",
        "retrieved_pending_document_validation",
        "pending_validation",
    }:
        return QualityStatus.PENDING_VALIDATION
    if raw_status in {"failed", "invalid"}:
        return QualityStatus.INVALID
    try:
        return QualityStatus(raw_status)
    except ValueError as exc:
        raise ValueError(f"unknown source quality status: {raw_status}") from exc


def _source_record(item: Mapping[str, Any], manifest_path: Path) -> SourceRecord:
    required = {
        "source_id",
        "source_type",
        "source_tier",
        "publisher",
        "url",
        "retrieved_at_utc",
        "local_path",
        "content_hash",
        "license_note",
        "quality_status",
    }
    missing = sorted(field for field in required if not item.get(field))
    if missing:
        raise ValueError(f"source manifest missing fields in {manifest_path}: {missing}")
    try:
        retrieved_at = datetime.fromisoformat(
            str(item["retrieved_at_utc"]).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            f"invalid retrieved_at_utc for source {item.get('source_id')}"
        ) from exc
    return SourceRecord(
        source_id=str(item["source_id"]),
        source_type=str(item["source_type"]),
        source_tier=str(item["source_tier"]),
        source_url=str(item["url"]),
        retrieved_at=retrieved_at,
        local_path=str(item["local_path"]),
        content_hash=str(item["content_hash"]),
        publisher=str(item["publisher"]),
        license_note=str(item["license_note"]),
        quality_status=_source_quality_status(str(item["quality_status"])),
        notes=(
            f"published_at_utc={item.get('published_at_utc', 'unknown')}; "
            f"assembled_from={manifest_path.as_posix()}"
        ),
    )


def _metric_observation(item: Mapping[str, Any], candidate_path: Path) -> MetricObservation:
    fields = {key: item.get(key) for key in _METRIC_FIELDS if key in item}
    try:
        observation = MetricObservation.model_validate(fields)
    except ValueError as exc:
        raise ValueError(
            f"invalid candidate observation in {candidate_path}: {exc}"
        ) from exc
    if observation.quality_status is not QualityStatus.PENDING_VALIDATION:
        raise ValueError(
            f"candidate_not_pending:{observation.observation_id}:"
            f"{observation.quality_status.value}"
        )
    return observation


def _evidence_snippet(item: Mapping[str, Any], evidence_path: Path) -> EvidenceSnippet:
    try:
        return EvidenceSnippet.model_validate(item)
    except ValueError as exc:
        raise ValueError(f"invalid evidence in {evidence_path}: {exc}") from exc


def _input_file_hashes(paths: Iterable[Path]) -> dict[str, str]:
    return {str(path): _file_hash(path) for path in paths}


def assemble_official_pilot_candidates(
    candidate_paths: Sequence[Path],
    source_manifest_paths: Sequence[Path],
    evidence_paths: Sequence[Path],
    output_db: Path,
    *,
    tickers: Sequence[str],
    periods: Sequence[str],
    required_metrics: Sequence[str],
) -> PilotAssemblyResult:
    """Build a versioned pending candidate DB from official input artifacts.

    Multiple observations for one cell are allowed because competing variants
    must remain visible until independent review. Duplicate observation IDs,
    unknown source IDs, invalid statuses, and out-of-scope rows fail closed.
    """
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite output database: {output_db}")
    if not candidate_paths or not source_manifest_paths:
        raise ValueError("candidate_paths and source_manifest_paths must not be empty")
    if not tickers or not periods or not required_metrics:
        raise ValueError("tickers, periods, and required_metrics must not be empty")

    candidate_paths = tuple(candidate_paths)
    source_manifest_paths = tuple(source_manifest_paths)
    evidence_paths = tuple(evidence_paths)
    source_records: dict[str, SourceRecord] = {}
    for manifest_path in source_manifest_paths:
        for item in _read_json_array(manifest_path):
            source = _source_record(item, manifest_path)
            if source.source_id in source_records:
                raise ValueError(f"duplicate_source_id:{source.source_id}")
            if source.quality_status is QualityStatus.VALID:
                raise ValueError(f"candidate_source_already_valid:{source.source_id}")
            source_records[source.source_id] = source

    observations: list[tuple[MetricObservation, dict[str, Any], Path]] = []
    seen_observation_ids: set[str] = set()
    for candidate_path in candidate_paths:
        for item in _read_jsonl(candidate_path):
            observation = _metric_observation(item, candidate_path)
            if observation.observation_id in seen_observation_ids:
                raise ValueError(f"duplicate_observation_id:{observation.observation_id}")
            if observation.source_id not in source_records:
                raise ValueError(
                    f"candidate_source_missing_from_manifests:{observation.source_id}"
                )
            if observation.ticker not in tickers or observation.period not in periods:
                raise ValueError(
                    f"candidate_out_of_scope:{observation.observation_id}"
                )
            seen_observation_ids.add(observation.observation_id)
            observations.append((observation, item, candidate_path))
    if not observations:
        raise ValueError("candidate files are empty")

    official_candidate_count = len(observations)
    official_candidate_cells = {
        (observation.ticker, observation.period, observation.metric)
        for observation, _, _ in observations
    }
    placeholder_count = 0
    for ticker in tickers:
        for period in periods:
            for metric in required_metrics:
                cell = (ticker, period, metric)
                if cell in official_candidate_cells:
                    continue
                placeholder = MetricObservation(
                    observation_id=f"missing:{ticker}:{period}:{metric}",
                    ticker=ticker,
                    sector="bank",
                    metric=metric,
                    value=None,
                    unit=None,
                    period=period,
                    as_of_date=None,
                    period_basis=None,
                    source_id=None,
                    source_locator=None,
                    quality_status=QualityStatus.MISSING,
                    reason="no official candidate route in the bounded pilot source pass",
                )
                observations.append(
                    (
                        placeholder,
                        {
                            "variant": "no_official_candidate_route",
                            "extraction_status": "no_official_candidate_route",
                            "input_facts": {},
                        },
                        Path("coverage-gap"),
                    )
                )
                placeholder_count += 1

    evidence_rows: list[EvidenceSnippet] = []
    seen_evidence_ids: set[str] = set()
    candidate_source_ids = {
        observation.source_id
        for observation, _, _ in observations
        if observation.source_id is not None
    }
    for evidence_path in evidence_paths:
        for item in _read_jsonl(evidence_path):
            evidence = _evidence_snippet(item, evidence_path)
            if evidence.evidence_id in seen_evidence_ids:
                raise ValueError(f"duplicate_evidence_id:{evidence.evidence_id}")
            if evidence.source_id not in source_records:
                raise ValueError(
                    f"evidence_source_missing_from_manifests:{evidence.source_id}"
                )
            if evidence.source_id not in candidate_source_ids:
                raise ValueError(
                    f"evidence_source_not_used_by_candidates:{evidence.source_id}"
                )
            seen_evidence_ids.add(evidence.evidence_id)
            evidence_rows.append(evidence)

    all_input_paths = (*candidate_paths, *source_manifest_paths, *evidence_paths)
    candidate_metrics = sorted(
        {
            observation.metric
            for observation, _, _ in observations
            if observation.quality_status is QualityStatus.PENDING_VALIDATION
        }
    )
    snapshot_id = output_db.stem
    config = {
        "tickers": list(tickers),
        "periods": list(periods),
        "required_metrics": list(required_metrics),
        "candidate_metrics": candidate_metrics,
        "candidate_row_count": official_candidate_count,
        "missing_placeholder_count": placeholder_count,
        "observation_row_count": len(observations),
        "unique_candidate_cells": len(official_candidate_cells),
        "source_strategy": "official_candidate_union",
        "input_file_hashes": _input_file_hashes(all_input_paths),
    }

    output_db.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)
    connection = sqlite3.connect(output_db)
    try:
        connection.execute(
            """
            CREATE TABLE candidate_metadata (
                observation_id TEXT PRIMARY KEY,
                candidate_file TEXT NOT NULL,
                variant TEXT,
                formula_version TEXT,
                input_facts_json TEXT NOT NULL,
                extraction_status TEXT,
                FOREIGN KEY(observation_id) REFERENCES metric_observations(observation_id)
            )
            """
        )
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                snapshot_id,
                datetime.utcnow().isoformat() + "Z",
                "normalized_candidate_pending_validation",
                json.dumps(config, ensure_ascii=False, sort_keys=True),
            ),
        )
        connection.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    source.source_id,
                    source.source_type.value,
                    source.source_tier.value,
                    source.source_url,
                    source.retrieved_at.isoformat(),
                    source.local_path,
                    source.content_hash,
                    source.publisher,
                    source.license_note,
                    source.quality_status.value,
                    source.notes,
                )
                for source in source_records.values()
            ],
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    observation.observation_id,
                    observation.ticker,
                    observation.sector,
                    observation.metric,
                    observation.value,
                    observation.unit,
                    observation.period,
                    observation.as_of_date.isoformat() if observation.as_of_date else None,
                    observation.period_basis.value if observation.period_basis else None,
                    observation.source_id,
                    observation.source_locator,
                    observation.quality_status.value,
                    observation.reason,
                )
                for observation, _, _ in observations
            ],
        )
        connection.executemany(
            "INSERT INTO candidate_metadata VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    observation.observation_id,
                    str(candidate_path),
                    item.get("variant"),
                    item.get("formula_version"),
                    json.dumps(item.get("input_facts", {}), ensure_ascii=False, sort_keys=True),
                    item.get("extraction_status"),
                )
                for observation, item, candidate_path in observations
            ],
        )
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    evidence.evidence_id,
                    evidence.source_id,
                    evidence.source_document,
                    evidence.page_number,
                    evidence.section_name,
                    evidence.period,
                    evidence.ticker,
                    evidence.quote,
                    evidence.retrieval_score,
                    evidence.parser_status,
                    int(evidence.is_paginated),
                )
                for evidence in evidence_rows
            ],
        )
        coverage_rows = []
        for ticker in tickers:
            for metric in required_metrics:
                periods_present = {
                    observation.period
                    for observation, _, _ in observations
                    if observation.ticker == ticker
                    and observation.metric == metric
                    and observation.quality_status is QualityStatus.PENDING_VALIDATION
                }
                missing_periods = {
                    observation.period
                    for observation, _, _ in observations
                    if observation.ticker == ticker
                    and observation.metric == metric
                    and observation.quality_status is QualityStatus.MISSING
                }
                coverage_rows.append(
                    (
                        f"{snapshot_id}:{ticker}:{metric}",
                        snapshot_id,
                        ticker,
                        metric,
                        len(periods),
                        len(periods_present) + len(missing_periods),
                        0,
                        len(missing_periods),
                        0.0,
                    )
                )
        connection.executemany(
            "INSERT INTO coverage_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            coverage_rows,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        output_db.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    return PilotAssemblyResult(
        output_path=str(output_db),
        snapshot_id=snapshot_id,
        candidate_count=official_candidate_count,
        placeholder_count=placeholder_count,
        unique_candidate_cells=len(official_candidate_cells),
        source_count=len(source_records),
        evidence_count=len(evidence_rows),
    )
