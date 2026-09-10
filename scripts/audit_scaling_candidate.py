"""Audit a scaling candidate without mutating or promoting it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any


def audit(candidate_db: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"metric_observations", "source_records"}
        missing_tables = sorted(required - tables)
        if missing_tables:
            raise ValueError(f"candidate missing tables: {', '.join(missing_tables)}")
        rows = [dict(row) for row in connection.execute("SELECT ticker, period, metric, value, source_id, source_locator, quality_status FROM metric_observations ORDER BY ticker, period, metric")]
        statuses = {
            str(status): count
            for status, count in connection.execute("SELECT quality_status, COUNT(*) FROM metric_observations GROUP BY quality_status ORDER BY quality_status")
        }
        tickers = [row[0] for row in connection.execute("SELECT DISTINCT ticker FROM metric_observations ORDER BY ticker")]
        periods = [row[0] for row in connection.execute("SELECT DISTINCT period FROM metric_observations ORDER BY period")]
        metrics = [row[0] for row in connection.execute("SELECT DISTINCT metric FROM metric_observations ORDER BY metric")]
        source_count = connection.execute("SELECT COUNT(*) FROM source_records").fetchone()[0]
        evidence_count = connection.execute("SELECT COUNT(*) FROM evidence_snippets").fetchone()[0] if "evidence_snippets" in tables else 0
    finally:
        connection.close()

    target_count = len(tickers) * len(periods) * len(metrics)
    target_keys = {(row["ticker"], row["period"], row["metric"]) for row in rows}
    missing_source_ids = sum(1 for row in rows if not row.get("source_id"))
    missing_locators = sum(1 for row in rows if not row.get("source_locator"))
    return {
        "candidate_db": str(candidate_db),
        "snapshot_status": "candidate_pending_validation",
        "tickers": tickers,
        "periods": periods,
        "metrics": metrics,
        "expected_target_cells": target_count,
        "represented_target_cells": len(target_keys),
        "row_count": len(rows),
        "quality_status_counts": statuses,
        "source_count": source_count,
        "evidence_count": evidence_count,
        "rows_without_source_id": missing_source_ids,
        "rows_without_source_locator": missing_locators,
        "ready_for_gold": False,
        "blockers": [
            "human_review_required",
            "candidate_must_not_enter_benchmark",
            *(["missing_source_ids"] if missing_source_ids else []),
            *(["missing_source_locators"] if missing_locators else []),
            *(["evidence_snippets_not_loaded"] if evidence_count == 0 else []),
        ],
    }


def to_markdown(report: dict[str, Any]) -> str:
    statuses = ", ".join(f"{key}: {value}" for key, value in report["quality_status_counts"].items()) or "none"
    lines = [
        "# Scaling candidate audit",
        "",
        "Đây là audit read-only. Candidate không được promote hoặc dùng làm kết luận benchmark.",
        "",
        f"- Snapshot status: `{report['snapshot_status']}`",
        f"- Scope: `{len(report['tickers'])} tickers × {len(report['periods'])} periods × {len(report['metrics'])} metrics`",
        f"- Target cells: `{report['represented_target_cells']}/{report['expected_target_cells']}`",
        f"- Quality status: `{statuses}`",
        f"- Sources: `{report['source_count']}`; evidence snippets: `{report['evidence_count']}`",
        f"- Ready for Gold: `{report['ready_for_gold']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["blockers"])
    lines.extend(["", "Conclusion: mở rộng này đủ để làm workload stress-test sau khi review; hiện tại nó vẫn là candidate và không được đưa vào report chính.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_db", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.candidate_db)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "audit.md").write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
