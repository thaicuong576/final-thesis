"""Normalize supported vendor ratios into an explicitly non-gold candidate store."""

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Sequence

from .periods import validate_period_bounds
from .schema import (
    MetricObservation,
    PeriodBasis,
    QualityStatus,
    SourceRecord,
    SourceTier,
    SourceType,
)
from .storage import create_gold_snapshot_schema


_RATIO_METRICS = {
    "npl": "bank.npl_g35",
    "loansLossReservesToNPLs": "bank.llr_coverage",
    "cir": "bank.cir",
    "roa": "bank.roa",
    "roe": "bank.roe",
}


def _quality_status(raw_status: str) -> QualityStatus:
    if raw_status == "valid":
        return QualityStatus.VALID
    if raw_status == "failed":
        return QualityStatus.INVALID
    return QualityStatus.PENDING_VALIDATION


def _source_type(raw_type: str) -> SourceType:
    if "issuer_ir" in raw_type.lower() or "investor" in raw_type.lower():
        return SourceType.ISSUER_IR
    return SourceType.MARKET_DATA if "eod" in raw_type.lower() else SourceType.API


def _retrieved_at(raw_value: str) -> datetime:
    normalized = raw_value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _open_staging(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)


def normalize_vendor_snapshot(
    staging_db: Path,
    output_db: Path,
    *,
    tickers: Sequence[str],
    periods: Sequence[str],
) -> int:
    """Create a pending normalized candidate snapshot from vendor ratio rows.

    The adapter intentionally preserves vendor units, TTM basis, sign conventions,
    and pending quality status. It is an input to reconciliation, never a gold
    promotion shortcut.
    """
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite existing database: {output_db}")
    if not staging_db.exists():
        raise FileNotFoundError(staging_db)
    if not tickers or not periods:
        raise ValueError("tickers and periods must not be empty")

    for period in periods:
        validate_period_bounds(period)

    source_rows: dict[str, tuple] = {}
    ratio_rows: list[tuple] = []
    connection = _open_staging(staging_db)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required_tables = {"source_records", "ratio_observations"}
        missing = required_tables - tables
        if missing:
            raise ValueError(f"missing tables: {sorted(missing)}")

        ticker_marks = ",".join("?" for _ in tickers)
        period_marks = ",".join("?" for _ in periods)
        field_marks = ",".join("?" for _ in _RATIO_METRICS)
        ratio_rows = connection.execute(
            f"""
            SELECT id, ticker, sector, period, field_code, value, unit,
                   source_id, source_locator, quality_status
            FROM ratio_observations
            WHERE ticker IN ({ticker_marks})
              AND period IN ({period_marks})
              AND ratio_type = 'RATIO_TTM'
              AND field_code IN ({field_marks})
            ORDER BY ticker, period, field_code, id
            """,
            (*tickers, *periods, *_RATIO_METRICS),
        ).fetchall()
        if not ratio_rows:
            raise ValueError("no supported RATIO_TTM rows in requested scope")

        source_ids = sorted({row[7] for row in ratio_rows})
        source_marks = ",".join("?" for _ in source_ids)
        for row in connection.execute(
            f"""
            SELECT source_id, source_type, publisher, source_url,
                   retrieved_at_utc, local_path, content_hash, bytes,
                   quality_status, notes
            FROM source_records
            WHERE source_id IN ({source_marks})
            ORDER BY source_id
            """,
            tuple(source_ids),
        ):
            source_rows[row[0]] = row
    finally:
        connection.close()

    missing_sources = sorted({row[7] for row in ratio_rows} - set(source_rows))
    if missing_sources:
        raise ValueError(f"missing source records: {missing_sources}")

    source_models: list[SourceRecord] = []
    for source_id in sorted(source_rows):
        (
            _source_id,
            raw_type,
            publisher,
            source_url,
            retrieved_at,
            local_path,
            content_hash,
            _bytes,
            raw_status,
            notes,
        ) = source_rows[source_id]
        source_models.append(
            SourceRecord(
                source_id=source_id,
                source_type=_source_type(raw_type),
                source_tier=SourceTier.ACCELERATOR,
                source_url=source_url,
                retrieved_at=_retrieved_at(retrieved_at),
                local_path=local_path,
                content_hash=content_hash,
                publisher=publisher,
                license_note="pending vendor license validation",
                quality_status=_quality_status(raw_status),
                notes=notes,
            )
        )

    metric_models: list[MetricObservation] = []
    for (
        row_id,
        ticker,
        sector,
        period,
        field_code,
        value,
        unit,
        source_id,
        source_locator,
        raw_status,
    ) in ratio_rows:
        quality_status = _quality_status(raw_status)
        reason = (
            "vendor ratio pending unit, sign, period-basis, and primary-source "
            "reconciliation"
        )
        metric_models.append(
            MetricObservation(
                observation_id=f"vendor-ratio-{row_id}",
                ticker=ticker,
                sector=sector,
                metric=_RATIO_METRICS[field_code],
                value=value,
                unit=unit,
                period=period,
                as_of_date=validate_period_bounds(period)[1],
                period_basis=PeriodBasis.TTM,
                source_id=source_id,
                source_locator=source_locator,
                quality_status=quality_status,
                reason=reason,
            )
        )

    output_db.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)
    output = sqlite3.connect(output_db)
    try:
        output.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                output_db.stem,
                datetime.utcnow().isoformat() + "Z",
                "normalized_candidate_pending_validation",
                json.dumps(
                    {
                        "tickers": list(tickers),
                        "periods": list(periods),
                        "ratio_basis": "RATIO_TTM",
                    },
                    sort_keys=True,
                ),
            ),
        )
        output.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    model.source_id,
                    model.source_type.value,
                    model.source_tier.value,
                    model.source_url,
                    model.retrieved_at.isoformat(),
                    model.local_path,
                    model.content_hash,
                    model.publisher,
                    model.license_note,
                    model.quality_status.value,
                    model.notes,
                )
                for model in source_models
            ],
        )
        output.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    model.observation_id,
                    model.ticker,
                    model.sector,
                    model.metric,
                    model.value,
                    model.unit,
                    model.period,
                    model.as_of_date.isoformat() if model.as_of_date else None,
                    model.period_basis.value,
                    model.source_id,
                    model.source_locator,
                    model.quality_status.value,
                    model.reason,
                )
                for model in metric_models
            ],
        )
        output.commit()
    finally:
        output.close()
    return len(metric_models)
