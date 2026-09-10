#!/usr/bin/env python3
"""Run read-only company, sector, macro, and evidence queries on a snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.query import (  # noqa: E402
    EvidenceQuery,
    get_company_metrics,
    get_evidence,
    get_macro_context,
    get_sector_benchmarks,
)


def _add_metric_ids(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--metric",
        action="append",
        dest="metric_ids",
        required=True,
        help="metric identifier; repeat for multiple metrics",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    company = commands.add_parser("company", help="query one company's metrics")
    company.add_argument("snapshot", type=Path)
    company.add_argument("ticker")
    company.add_argument("period")
    _add_metric_ids(company)

    sector = commands.add_parser("sector", help="calculate sector medians")
    sector.add_argument("snapshot", type=Path)
    sector.add_argument("sector")
    sector.add_argument("period")
    _add_metric_ids(sector)

    macro = commands.add_parser("macro", help="query period-aligned macro context")
    macro.add_argument("snapshot", type=Path)
    macro.add_argument("period")
    macro.add_argument(
        "--indicator",
        action="append",
        dest="indicator_ids",
        required=True,
        help="macro indicator identifier; repeat for multiple indicators",
    )

    evidence = commands.add_parser("evidence", help="query page-aware evidence")
    evidence.add_argument("snapshot", type=Path)
    evidence.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        required=True,
        help="source identifier; repeat for multiple sources",
    )
    evidence.add_argument("--ticker")
    evidence.add_argument("--period")
    evidence.add_argument("--text")

    return parser


def _query(args: argparse.Namespace) -> dict | list[dict]:
    if args.command == "company":
        return get_company_metrics(
            args.snapshot,
            args.ticker,
            args.period,
            tuple(args.metric_ids),
        ).model_dump(mode="json")
    if args.command == "sector":
        return get_sector_benchmarks(
            args.snapshot,
            args.sector,
            args.period,
            tuple(args.metric_ids),
        ).model_dump(mode="json")
    if args.command == "macro":
        return get_macro_context(
            args.snapshot,
            args.period,
            tuple(args.indicator_ids),
        ).model_dump(mode="json")
    if args.command == "evidence":
        snippets = get_evidence(
            args.snapshot,
            tuple(args.source_ids),
            EvidenceQuery(
                ticker=args.ticker,
                period=args.period,
                text=args.text,
            ),
        )
        return [snippet.model_dump(mode="json") for snippet in snippets]
    raise ValueError(f"unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = _query(args)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
