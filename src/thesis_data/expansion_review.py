"""Build a non-Gold expansion candidate and a human review register."""

from __future__ import annotations

from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import sqlite3
from typing import Sequence

from .storage import create_gold_snapshot_schema


CORE_METRICS = (
    "bank.npl_g35",
    "bank.llr_coverage",
    "bank.roa",
    "bank.roe",
)


def audit_expansion_candidate(
    candidate_db: Path,
    *,
    added_tickers: Sequence[str] = ("MBB", "VCB"),
    periods: Sequence[str] = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
    metrics: Sequence[str] = CORE_METRICS,
) -> dict[str, object]:
    """Audit a non-Gold expansion candidate without changing it.

    This is deliberately stricter than a row-count check.  A candidate can
    have all target cells represented while still being unusable because its
    source is pending, its source tier is only an accelerator, or a metric
    violates an invariant implied by its definition.  In particular,
    reserve-coverage cannot be negative under the frozen definition; a
    negative vendor value must be reconciled, not converted with ``abs``.
    """

    if not candidate_db.exists():
        raise FileNotFoundError(candidate_db)
    expected = len(added_tickers) * len(periods) * len(metrics)
    period_marks = _marks(tuple(periods))
    ticker_marks = _marks(tuple(added_tickers))
    metric_marks = _marks(tuple(metrics))
    con = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    try:
        status_row = con.execute(
            "SELECT status FROM snapshot_metadata ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
        target_rows = con.execute(
            f"""
            SELECT mo.observation_id, mo.ticker, mo.period, mo.metric, mo.value,
                   mo.unit, mo.period_basis, mo.quality_status, mo.reason,
                   mo.source_id, sr.source_tier, sr.quality_status
            FROM metric_observations AS mo
            LEFT JOIN source_records AS sr ON sr.source_id = mo.source_id
            WHERE mo.ticker IN ({ticker_marks})
              AND mo.period IN ({period_marks})
              AND mo.metric IN ({metric_marks})
            ORDER BY mo.ticker, mo.period, mo.metric, mo.observation_id
            """,
            (*added_tickers, *periods, *metrics),
        ).fetchall()
    finally:
        con.close()

    target_keys = {(row[1], row[2], row[3]) for row in target_rows}
    pending_rows = [row for row in target_rows if row[7] == "pending_validation"]
    accelerator_rows = [row for row in target_rows if row[10] == "accelerator"]
    negative_llr_rows = [
        row for row in target_rows
        if row[3] == "bank.llr_coverage" and row[4] is not None and row[4] < 0
    ]
    missing_target_keys = [
        f"{ticker}:{period}:{metric}"
        for ticker in added_tickers
        for period in periods
        for metric in metrics
        if (ticker, period, metric) not in target_keys
    ]

    blockers: list[str] = []
    if status_row is None or status_row[0] != "candidate_pending_human_review":
        blockers.append("unexpected_candidate_snapshot_status")
    if len(target_keys) != expected:
        blockers.append("incomplete_target_cells")
    if pending_rows:
        blockers.append("pending_validation_rows")
    if accelerator_rows:
        blockers.append("accelerator_source_rows")
    if negative_llr_rows:
        blockers.append("negative_llr_coverage_values")
    if missing_target_keys:
        blockers.append("missing_target_cells")

    return {
        "candidate_db": str(candidate_db),
        "snapshot_status": status_row[0] if status_row else None,
        "expected_target_cells": expected,
        "represented_target_cells": len(target_keys),
        "candidate_observation_rows": len(target_rows),
        "pending_validation_rows": len(pending_rows),
        "accelerator_source_rows": len(accelerator_rows),
        "negative_llr_coverage_values": [
            {
                "ticker": row[1],
                "period": row[2],
                "value": row[4],
                "unit": row[5],
                "period_basis": row[6],
                "source_id": row[9],
                "source_tier": row[10],
                "source_quality_status": row[11],
            }
            for row in negative_llr_rows
        ],
        "missing_target_cells": missing_target_keys,
        "blockers": blockers,
        "ready_for_gold": not blockers,
    }


def _marks(values: Sequence[str]) -> str:
    return ",".join("?" for _ in values)


def _copy_base_tables(base: sqlite3.Connection, output: sqlite3.Connection) -> None:
    metadata = base.execute(
        "SELECT snapshot_id, created_at_utc, status, config_json FROM snapshot_metadata"
    ).fetchone()
    if metadata is None:
        raise ValueError("base Gold snapshot metadata is missing")
    base_config = json.loads(metadata[3])
    output.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        (metadata[0], metadata[1], metadata[2], metadata[3]),
    )
    for table in ("source_records", "metric_observations", "derived_metrics", "macro_observations", "evidence_snippets", "gold_labels", "evaluation_questions"):
        rows = base.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue
        columns = len(rows[0])
        output.executemany(
            f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(columns))})",
            rows,
        )


def build_expansion_review(
    base_gold_db: Path,
    candidate_db: Path,
    output_db: Path,
    review_dir: Path,
    *,
    added_tickers: Sequence[str] = ("MBB", "VCB"),
    periods: Sequence[str] = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
    metrics: Sequence[str] = CORE_METRICS,
) -> dict[str, object]:
    """Materialize a larger candidate DB without promoting pending facts.

    The output is deliberately non-Gold. Existing accepted pilot rows are
    copied unchanged. New rows retain ``pending_validation`` and their
    accelerator source tier, while a CSV register exposes every new target
    cell for independent source review.
    """

    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite {output_db}")
    if not base_gold_db.exists() or not candidate_db.exists():
        raise FileNotFoundError("base Gold or candidate database is missing")
    if not added_tickers or not periods or not metrics:
        raise ValueError("expansion scope must not be empty")
    candidate_snapshot_id = output_db.stem
    output_db.parent.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)

    base = sqlite3.connect(f"file:{base_gold_db.resolve()}?mode=ro", uri=True)
    candidate = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    output = sqlite3.connect(output_db)
    try:
        output.execute("BEGIN")
        _copy_base_tables(base, output)
        candidate_source_ids: set[str] = set()
        target_marks = _marks(tuple(added_tickers))
        period_marks = _marks(tuple(periods))
        metric_marks = _marks(tuple(metrics))
        candidate_rows = candidate.execute(
            f"""
            SELECT observation_id, ticker, sector, metric, value, unit, period,
                   as_of_date, period_basis, source_id, source_locator,
                   quality_status, reason
            FROM metric_observations
            WHERE ticker IN ({target_marks})
              AND period IN ({period_marks})
              AND metric IN ({metric_marks})
            ORDER BY ticker, period, metric, observation_id
            """,
            (*added_tickers, *periods, *metrics),
        ).fetchall()
        candidate_source_metadata = {
            row[0]: {"source_tier": row[1], "quality_status": row[2]}
            for row in candidate.execute(
                "SELECT source_id, source_tier, quality_status FROM source_records ORDER BY source_id"
            ).fetchall()
        }
        review_rows: list[dict[str, object]] = []
        inserted_observation_ids: set[str] = set()
        for row in candidate_rows:
            original_id = row[0]
            new_id = f"expansion:{original_id}"
            source_id = f"expansion:{row[9]}" if row[9] else None
            inserted_observation_ids.add(new_id)
            if source_id:
                candidate_source_ids.add(row[9])
            copied = (new_id, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], source_id, row[10], row[11], row[12])
            output.execute("INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", copied)
            review_rows.append({
                "target_id": f"{row[1]}:{row[6]}:{row[3]}",
                "ticker": row[1],
                "period": row[6],
                "metric": row[3],
                "candidate_observation_id": new_id,
                "candidate_value": row[4],
                "candidate_unit": row[5],
                "candidate_period_basis": row[8],
                "candidate_source_id": source_id,
                "candidate_source_tier": candidate_source_metadata.get(row[9], {}).get("source_tier", "unknown"),
                "candidate_source_quality_status": candidate_source_metadata.get(row[9], {}).get("quality_status", "unknown"),
                "candidate_status": row[11],
                "source_locator": row[10],
                "reviewer_decision": "",
                "checker_id": "",
                "review_notes": "",
            })

        source_rows = candidate.execute(
            f"""
            SELECT source_id, source_type, source_tier, source_url, retrieved_at,
                   local_path, content_hash, publisher, license_note,
                   quality_status, notes
            FROM source_records
            WHERE source_id IN ({_marks(tuple(candidate_source_ids))})
            ORDER BY source_id
            """,
            tuple(candidate_source_ids),
        ).fetchall() if candidate_source_ids else []
        for row in source_rows:
            output.execute(
                "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"expansion:{row[0]}", row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]),
            )

        # Recompute the coverage table for the combined candidate scope.
        output.execute("DELETE FROM coverage_summary")
        all_tickers = tuple(dict.fromkeys(["ACB", "TCB", "VPB", *added_tickers]))
        all_periods = tuple(periods)
        for ticker in all_tickers:
            for metric in metrics:
                expected = len(all_periods)
                candidate_count, valid_count, missing_count = output.execute(
                    f"""
                    SELECT
                      COUNT(DISTINCT CASE WHEN period IN ({period_marks}) THEN period END),
                      COUNT(DISTINCT CASE WHEN period IN ({period_marks}) AND quality_status='valid' AND value IS NOT NULL THEN period END),
                      COUNT(DISTINCT CASE WHEN period IN ({period_marks}) AND quality_status='missing' THEN period END)
                    FROM metric_observations
                    WHERE ticker=? AND metric=?
                    """,
                    (*periods, *periods, *periods, ticker, metric),
                ).fetchone()
                output.execute(
                    "INSERT INTO coverage_summary VALUES (?,?,?,?,?,?,?,?,?)",
                    (f"{candidate_snapshot_id}:{ticker}:{metric}", candidate_snapshot_id, ticker, metric, expected, candidate_count, valid_count, missing_count, valid_count / expected if expected else 0.0),
                )
        source_tier_values = sorted(
            {metadata["source_tier"] for metadata in candidate_source_metadata.values()}
        )
        source_policy = (
            "_and_".join(source_tier_values) + "_pending_validation"
            if source_tier_values
            else "unknown_source_tier_pending_validation"
        )
        config = {
            "base_gold_snapshot": "gold-bank-2025-pilot-v1-adjudicated-v2",
            "candidate_snapshot": candidate_db.stem,
            "tickers": list(all_tickers),
            "periods": list(all_periods),
            "required_metrics": list(metrics),
            "min_metric_coverage": 0.9,
            "status_note": f"candidate_pending_human_review; pending {source_policy} rows are not Gold",
        }
        output.execute("DELETE FROM snapshot_metadata")
        output.execute(
            "INSERT INTO snapshot_metadata VALUES (?,?,?,?)",
            (candidate_snapshot_id, datetime.now(timezone.utc).isoformat(), "candidate_pending_human_review", json.dumps(config, sort_keys=True)),
        )
        output.commit()
    except Exception:
        output.rollback()
        raise
    finally:
        base.close()
        candidate.close()
        output.close()

    review_path = review_dir / "review-register.csv"
    fields = list(review_rows[0]) if review_rows else [
        "target_id", "ticker", "period", "metric", "candidate_observation_id",
        "candidate_value", "candidate_unit", "candidate_period_basis",
        "candidate_source_id", "candidate_source_tier",
        "candidate_source_quality_status", "candidate_status", "source_locator",
        "reviewer_decision", "checker_id", "review_notes",
    ]
    with review_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review_rows)

    summary = {
        "candidate_snapshot_id": candidate_snapshot_id,
        "status": "candidate_pending_human_review",
        "base_gold_cells": 48,
        "expanded_target_cells": len(all_tickers) * len(all_periods) * len(metrics),
        "added_tickers": list(added_tickers),
        "added_candidate_rows": len(inserted_observation_ids),
        "new_rows_are_gold": False,
        "candidate_source_policy": source_policy,
        "review_register": str(review_path),
        "database": str(output_db),
    }
    (review_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (review_dir / "README.md").write_text(
        "# Gold expansion review\n\n"
        "This packet adds MBB and VCB to the 2024 four-quarter, four-metric scope. "
        f"It is not Gold: every new row is copied from a {source_policy} source with "
        "`pending_validation`. An independent reviewer must verify official source, "
        "definition, period basis, unit, value, and provenance before any row can "
        "be promoted. Fill `review-register.csv`; do not edit the candidate DB.\n",
        encoding="utf-8",
    )
    return summary
