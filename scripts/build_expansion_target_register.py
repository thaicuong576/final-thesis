"""Build a one-row-per-target register for an expansion candidate snapshot.

The register is an internal promotion contract: candidate alternatives stay
visible there, while the separately generated review ledger contains only
target identity and reviewer-owned blank fields. Existing base Gold cells can
therefore be carried forward and disjoint new ledgers can be merged safely.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    REVIEW_LEDGER_FIELDS,
    build_review_ledger,
    write_review_ledger,
)


REGISTER_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "review_status",
    "candidate_observation_ids",
    "candidate_values",
    "candidate_source_ids",
    "candidate_source_tiers",
    "candidate_quality_statuses",
)


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_register(
    candidate_db: Path,
    *,
    tickers: Sequence[str],
    periods: Sequence[str],
    metrics: Sequence[str],
    carry_forward_tickers: Sequence[str] = ("ACB", "TCB", "VPB"),
) -> list[dict[str, str]]:
    if not candidate_db.exists():
        raise FileNotFoundError(candidate_db)
    expected = {
        (ticker, period, metric)
        for ticker in tickers
        for period in periods
        for metric in metrics
    }
    connection = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT mo.observation_id, mo.ticker, mo.sector, mo.metric, mo.value,
                   mo.period, mo.source_id, mo.quality_status, sr.source_tier
            FROM metric_observations AS mo
            LEFT JOIN source_records AS sr ON sr.source_id = mo.source_id
            WHERE mo.ticker IN ({tickers})
              AND mo.period IN ({periods})
              AND mo.metric IN ({metrics})
            ORDER BY mo.ticker, mo.period, mo.metric, mo.observation_id
            """.format(
                tickers=",".join("?" for _ in tickers),
                periods=",".join("?" for _ in periods),
                metrics=",".join("?" for _ in metrics),
            ),
            (*tickers, *periods, *metrics),
        ).fetchall()
    finally:
        connection.close()

    grouped: dict[tuple[str, str, str], list[tuple[Any, ...]]] = {}
    for row in rows:
        grouped.setdefault((row[1], row[5], row[3]), []).append(row)
    missing = sorted(expected - set(grouped))
    extra = sorted(set(grouped) - expected)
    if missing or extra:
        raise ValueError(f"target scope mismatch: missing={missing} extra={extra}")

    output: list[dict[str, str]] = []
    for ticker, period, metric in sorted(expected):
        candidates = grouped[(ticker, period, metric)]
        target_id = f"{ticker}:{period}:{metric}"
        statuses = [str(row[7]) for row in candidates]
        review_status = (
            "base_gold_carry_forward"
            if ticker in carry_forward_tickers and all(status in {"valid", "missing"} for status in statuses)
            else "pending_human_review"
        )
        output.append({
            "target_id": target_id,
            "ticker": ticker,
            "sector": str(candidates[0][2]),
            "metric": metric,
            "period": period,
            "review_status": review_status,
            "candidate_observation_ids": json.dumps([row[0] for row in candidates], ensure_ascii=False),
            "candidate_values": json.dumps([row[4] for row in candidates], ensure_ascii=False),
            "candidate_source_ids": json.dumps([row[6] for row in candidates], ensure_ascii=False),
            "candidate_source_tiers": json.dumps([row[8] for row in candidates], ensure_ascii=False),
            "candidate_quality_statuses": json.dumps(statuses, ensure_ascii=False),
        })
    return output


def build(
    candidate_db: Path,
    register_output: Path,
    ledger_output: Path,
    *,
    tickers: Sequence[str] = ("ACB", "TCB", "VPB", "MBB", "VCB"),
    periods: Sequence[str] = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
    metrics: Sequence[str] = ("bank.roa", "bank.roe", "bank.npl_g35", "bank.llr_coverage"),
) -> dict[str, Any]:
    rows = build_register(candidate_db, tickers=tickers, periods=periods, metrics=metrics)
    _write_csv(register_output, REGISTER_FIELDS, rows)
    # build_review_ledger intentionally exposes only the target contract and
    # blank reviewer slots; candidate alternatives stay in the internal register.
    ledger_rows = build_review_ledger(register_output)
    write_review_ledger(ledger_rows, ledger_output)
    return {
        "candidate_db": str(candidate_db),
        "register": str(register_output),
        "ledger_template": str(ledger_output),
        "target_cell_count": len(rows),
        "candidate_observation_count": sum(
            len(json.loads(row["candidate_observation_ids"])) for row in rows
        ),
        "base_gold_carry_forward_cells": sum(
            row["review_status"] == "base_gold_carry_forward" for row in rows
        ),
        "pending_human_review_cells": sum(
            row["review_status"] == "pending_human_review" for row in rows
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_db", type=Path)
    parser.add_argument("register_output", type=Path)
    parser.add_argument("ledger_output", type=Path)
    args = parser.parse_args()
    try:
        result = build(args.candidate_db, args.register_output, args.ledger_output)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
