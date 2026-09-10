"""Create a new candidate snapshot with additional observations.

The base snapshot is read-only. This utility is for versioning a semantic
variant (such as a parent-attributable-equity ROE) while retaining every
existing observation and source unchanged.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.storage import create_gold_snapshot_schema  # noqa: E402


TABLES = (
    "coverage_summary",
    "source_records",
    "metric_observations",
    "derived_metrics",
    "macro_observations",
    "evidence_snippets",
    "gold_labels",
    "evaluation_questions",
)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid candidate JSON at line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"candidate row at line {line_number} is not an object")
            rows.append(row)
    if not rows:
        raise ValueError("candidate JSONL is empty")
    return rows


def augment_candidate_snapshot(
    base_db: Path,
    candidate_jsonl: Path,
    output_db: Path,
    *,
    snapshot_id: str,
) -> dict[str, object]:
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite {output_db}")
    candidates = _load_jsonl(candidate_jsonl)
    base_connection = sqlite3.connect(f"file:{base_db.resolve()}?mode=ro", uri=True)
    try:
        metadata = base_connection.execute(
            "SELECT status, config_json FROM snapshot_metadata ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
        if metadata is None or metadata[0] != "candidate_pending_human_review":
            raise ValueError("base snapshot must be candidate_pending_human_review")
        source_ids = {
            row[0] for row in base_connection.execute("SELECT source_id FROM source_records")
        }
        observation_ids = {
            row[0] for row in base_connection.execute("SELECT observation_id FROM metric_observations")
        }
        for candidate in candidates:
            required = {
                "observation_id", "ticker", "sector", "metric", "value", "unit",
                "period", "as_of_date", "period_basis", "source_id", "source_locator",
            }
            missing = sorted(field for field in required if field not in candidate)
            if missing:
                raise ValueError(f"candidate missing fields: {missing}")
            observation_id = str(candidate["observation_id"])
            source_id = str(candidate["source_id"])
            if observation_id in observation_ids:
                raise ValueError(f"duplicate observation_id: {observation_id}")
            if source_id not in source_ids:
                raise ValueError(f"candidate source is not in base snapshot: {source_id}")
            observation_ids.add(observation_id)

        output_db.parent.mkdir(parents=True, exist_ok=True)
        create_gold_snapshot_schema(output_db)
        output_connection = sqlite3.connect(output_db)
        try:
            config_json = json.loads(metadata[1])
            config_json["snapshot_id"] = snapshot_id
            output_connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                (
                    snapshot_id,
                    datetime.now(timezone.utc).isoformat(),
                    "candidate_pending_human_review",
                    json.dumps(config_json, ensure_ascii=False, sort_keys=True),
                ),
            )
            for table in TABLES:
                rows = base_connection.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    continue
                width = len(rows[0])
                placeholders = ",".join("?" for _ in range(width))
                output_connection.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})",
                    rows,
                )
            output_connection.executemany(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["observation_id"], row["ticker"], row["sector"], row["metric"],
                        row["value"], row["unit"], row["period"], row["as_of_date"],
                        row["period_basis"], row["source_id"], row["source_locator"],
                        "pending_validation", row.get("reason", ""),
                    )
                    for row in candidates
                ],
            )
            output_connection.commit()
        except Exception:
            output_connection.rollback()
            raise
        finally:
            output_connection.close()
    finally:
        base_connection.close()

    return {
        "snapshot_id": snapshot_id,
        "status": "candidate_pending_human_review",
        "base_db": str(base_db),
        "added_observations": len(candidates),
        "output_db": str(output_db),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_db", type=Path)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("output_db", type=Path)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    print(json.dumps(augment_candidate_snapshot(args.base_db, args.candidate_jsonl, args.output_db, snapshot_id=args.snapshot_id), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
