"""Store source-disclosed KPI candidates in a separate, non-gold snapshot."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3

from .schema import EvidenceSnippet, MetricObservation, QualityStatus, SourceRecord
from .storage import create_gold_snapshot_schema


def import_kpi_candidates(
    candidates_path: Path,
    source_manifest_path: Path,
    output_db: Path,
    evidence_path: Path | None = None,
) -> int:
    """Import extracted KPI observations without promoting their quality status."""
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite output database: {output_db}")
    candidate_rows = [
        MetricObservation.model_validate(json.loads(line))
        for line in candidates_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not candidate_rows:
        raise ValueError("candidate file is empty")
    manifest_rows = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    manifest_by_id = {item["source_id"]: item for item in manifest_rows}
    required_source_ids = {row.source_id for row in candidate_rows}
    missing = sorted(required_source_ids - set(manifest_by_id))
    if missing:
        raise ValueError(f"source manifest missing candidate sources: {missing}")
    evidence_rows = []
    if evidence_path is not None:
        evidence_rows = [
            EvidenceSnippet.model_validate(json.loads(line))
            for line in evidence_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        evidence_source_ids = {row.source_id for row in evidence_rows}
        if not evidence_source_ids.issubset(required_source_ids):
            raise ValueError("evidence contains a source not used by candidates")

    sources: list[SourceRecord] = []
    status_map = {
        "retrieved_pending_validation": QualityStatus.PENDING_VALIDATION,
        "retrieved_pending_document_validation": QualityStatus.PENDING_VALIDATION,
        "failed": QualityStatus.INVALID,
    }
    for source_id in sorted(required_source_ids):
        item = manifest_by_id[source_id]
        sources.append(
            SourceRecord(
                source_id=source_id,
                source_type=item["source_type"],
                source_tier=item["source_tier"],
                source_url=item["url"],
                retrieved_at=datetime.fromisoformat(
                    item["retrieved_at_utc"].replace("Z", "+00:00")
                ),
                local_path=item["local_path"],
                content_hash=item["content_hash"],
                publisher=item["publisher"],
                license_note=item["license_note"],
                quality_status=status_map.get(
                    item["quality_status"], item["quality_status"]
                ),
                notes=(
                    f"published_at_utc={item.get('published_at_utc', 'unknown')}; "
                    "imported from official KPI extraction"
                ),
            )
        )

    output_db.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)
    connection = sqlite3.connect(output_db)
    try:
        tickers = sorted({row.ticker for row in candidate_rows})
        periods = sorted({row.period for row in candidate_rows})
        metrics = sorted({row.metric for row in candidate_rows})
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                output_db.stem,
                datetime.utcnow().isoformat() + "Z",
                "normalized_candidate_pending_validation",
                json.dumps(
                    {
                        "tickers": tickers,
                        "periods": periods,
                        "required_metrics": metrics,
                        "source_strategy": "official_kpi_first",
                    },
                    sort_keys=True,
                ),
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
                for source in sources
            ],
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row.observation_id,
                    row.ticker,
                    row.sector,
                    row.metric,
                    row.value,
                    row.unit,
                    row.period,
                    row.as_of_date.isoformat() if row.as_of_date else None,
                    row.period_basis.value,
                    row.source_id,
                    row.source_locator,
                    row.quality_status.value,
                    row.reason,
                )
                for row in candidate_rows
            ],
        )
        if evidence_rows:
            connection.executemany(
                "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row.evidence_id,
                        row.source_id,
                        row.source_document,
                        row.page_number,
                        row.section_name,
                        row.period,
                        row.ticker,
                        row.quote,
                        row.retrieval_score,
                        row.parser_status,
                        int(row.is_paginated),
                    )
                    for row in evidence_rows
                ],
            )
        connection.commit()
    finally:
        connection.close()
    return len(candidate_rows)
