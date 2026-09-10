"""Combine disjoint non-Gold candidate SQLite snapshots into a new version."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.schema import GoldConfig  # noqa: E402
from thesis_data.storage import create_gold_snapshot_schema  # noqa: E402


TABLES = (
    "source_records",
    "metric_observations",
    "derived_metrics",
    "macro_observations",
    "evidence_snippets",
    "gold_labels",
    "evaluation_questions",
)


def _rows(connection: sqlite3.Connection, table: str) -> list[tuple]:
    return connection.execute(f"SELECT * FROM {table}").fetchall()


def combine_candidate_snapshots(
    candidate_paths: list[Path],
    output_db: Path,
    *,
    snapshot_id: str = "MBB-VCB-official-candidate-2024-v2",
) -> dict[str, object]:
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite {output_db}")
    if len(candidate_paths) < 2:
        raise ValueError("at least two candidate snapshots are required")
    if any(not path.exists() for path in candidate_paths):
        missing = [str(path) for path in candidate_paths if not path.exists()]
        raise FileNotFoundError(", ".join(missing))

    all_sources: dict[str, tuple] = {}
    all_observations: dict[str, tuple] = {}
    all_derived: dict[str, tuple] = {}
    all_macro: dict[str, tuple] = {}
    all_evidence: dict[str, tuple] = {}
    all_labels: dict[str, tuple] = {}
    all_questions: dict[str, tuple] = {}
    tickers: set[str] = set()
    periods: set[str] = set()
    metrics: set[str] = set()

    for candidate_path in candidate_paths:
        connection = sqlite3.connect(f"file:{candidate_path.resolve()}?mode=ro", uri=True)
        try:
            metadata = connection.execute(
                "SELECT status FROM snapshot_metadata ORDER BY created_at_utc DESC LIMIT 1"
            ).fetchone()
            if metadata is None or metadata[0] != "candidate_pending_human_review":
                raise ValueError(f"candidate snapshot is not pending: {candidate_path}")
            for row in _rows(connection, "source_records"):
                if row[0] in all_sources:
                    raise ValueError(f"duplicate source_id across candidates: {row[0]}")
                all_sources[row[0]] = row
            for row in _rows(connection, "metric_observations"):
                if row[0] in all_observations:
                    raise ValueError(f"duplicate observation_id across candidates: {row[0]}")
                all_observations[row[0]] = row
                tickers.add(row[1])
                metrics.add(row[3])
                periods.add(row[6])
            for table, target in (
                ("derived_metrics", all_derived),
                ("macro_observations", all_macro),
                ("evidence_snippets", all_evidence),
                ("gold_labels", all_labels),
                ("evaluation_questions", all_questions),
            ):
                for row in _rows(connection, table):
                    if row[0] in target:
                        raise ValueError(f"duplicate {table} id across candidates: {row[0]}")
                    target[row[0]] = row
        finally:
            connection.close()

    config = GoldConfig(
        tickers=tuple(sorted(tickers)),
        periods=tuple(sorted(periods)),
        required_metrics=tuple(sorted(metrics)),
        min_manual_labels=40,
        min_independent_checkers=2,
        min_metric_coverage=0.9,
    )
    output_db.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(output_db)
    connection = sqlite3.connect(output_db)
    try:
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?,?,?,?)",
            (
                snapshot_id,
                datetime.now(timezone.utc).isoformat(),
                "candidate_pending_human_review",
                json.dumps(config.model_dump(mode="json"), sort_keys=True),
            ),
        )
        for table, rows in (
            ("source_records", all_sources.values()),
            ("metric_observations", all_observations.values()),
            ("derived_metrics", all_derived.values()),
            ("macro_observations", all_macro.values()),
            ("evidence_snippets", all_evidence.values()),
            ("gold_labels", all_labels.values()),
            ("evaluation_questions", all_questions.values()),
        ):
            rows = list(rows)
            if not rows:
                continue
            width = len(rows[0])
            connection.executemany(
                f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(width))})",
                rows,
            )
        for ticker in config.tickers:
            for metric in config.required_metrics:
                expected = len(config.periods)
                candidate_count = connection.execute(
                    "SELECT COUNT(DISTINCT period) FROM metric_observations WHERE ticker=? AND metric=?",
                    (ticker, metric),
                ).fetchone()[0]
                valid_count = connection.execute(
                    "SELECT COUNT(DISTINCT period) FROM metric_observations WHERE ticker=? AND metric=? AND quality_status='valid' AND value IS NOT NULL",
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
                        valid_count,
                        0,
                        valid_count / expected if expected else 0.0,
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
        "input_snapshots": [str(path) for path in candidate_paths],
        "source_rows": len(all_sources),
        "observation_rows": len(all_observations),
        "ticker_count": len(tickers),
        "period_count": len(periods),
        "metric_count": len(metrics),
        "output_db": str(output_db),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = combine_candidate_snapshots(args.candidate, args.output_db)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
