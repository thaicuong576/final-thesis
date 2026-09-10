"""Materialize MBB official-derived candidates as a non-Gold SQLite snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.build_mbb_official_review_packet import _load_jsonl, _load_source_manifest
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


def build_candidate_db(
    candidate_jsonl: Path,
    source_manifest: Path,
    output_db: Path,
    *,
    snapshot_id: str = "MBB-official-candidate-2024-v1",
    min_manual_labels: int = 8,
) -> dict[str, object]:
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite {output_db}")
    candidates = _load_jsonl(candidate_jsonl)
    sources = _load_source_manifest(source_manifest)
    if any(row.get("ticker") != "MBB" for row in candidates):
        raise ValueError("candidate packet must contain only MBB rows")
    source_ids = {str(row.get("source_id", "")).strip() for row in candidates}
    if not source_ids.issubset(sources):
        raise ValueError(f"candidate source missing from manifest: {sorted(source_ids - set(sources))}")

    output_db.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)
    periods = tuple(sorted({str(row["period"]) for row in candidates}))
    required_metrics = tuple(sorted({str(row["metric"]) for row in candidates}))
    config = GoldConfig(
        tickers=("MBB",),
        periods=periods,
        required_metrics=required_metrics,
        min_manual_labels=min_manual_labels,
        min_independent_checkers=2,
        min_metric_coverage=0.9,
    )
    connection = sqlite3.connect(output_db)
    try:
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                snapshot_id,
                datetime.now(timezone.utc).isoformat(),
                "candidate_pending_human_review",
                json.dumps(config.model_dump(mode="json"), sort_keys=True),
            ),
        )
        for source_id in sorted(source_ids):
            source = sources[source_id]
            connection.execute(
                "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    source_id,
                    source.get("source_type", "filing"),
                    source.get("source_tier", "primary"),
                    source.get("url", ""),
                    source.get("retrieved_at_utc", ""),
                    source.get("local_path", ""),
                    source.get("content_hash", ""),
                    source.get("publisher", ""),
                    source.get("license_note", ""),
                    "pending_validation",
                    source.get("route_note", ""),
                ),
            )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["observation_id"],
                    row["ticker"],
                    row["sector"],
                    row["metric"],
                    row["value"],
                    row["unit"],
                    row["period"],
                    row.get("as_of_date"),
                    row["period_basis"],
                    row["source_id"],
                    row["source_locator"],
                    "pending_validation",
                    row.get("reason", ""),
                )
                for row in candidates
            ],
        )
        for ticker in config.tickers:
            for metric in config.required_metrics:
                expected = len(config.periods)
                candidate_count = connection.execute(
                    "SELECT COUNT(DISTINCT period) FROM metric_observations WHERE ticker=? AND metric=?",
                    (ticker, metric),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO coverage_summary VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        f"{snapshot_id}:{ticker}:{metric}",
                        snapshot_id,
                        ticker,
                        metric,
                        expected,
                        candidate_count,
                        0,
                        0,
                        0.0,
                    ),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "snapshot_id": snapshot_id,
        "status": "candidate_pending_human_review",
        "candidate_rows": len(candidates),
        "source_rows": len(source_ids),
        "gold_labels": 0,
        "output_db": str(output_db),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("output_db", type=Path)
    args = parser.parse_args()
    try:
        result = build_candidate_db(args.candidate_jsonl, args.source_manifest, args.output_db)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
