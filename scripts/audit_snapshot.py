#!/usr/bin/env python3
"""Run a read-only readiness audit for a thesis SQLite snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.snapshot import audit_snapshot  # noqa: E402


DEFAULT_TICKERS = ("VCB", "ACB", "MBB", "TCB", "VPB")
DEFAULT_PERIODS = tuple(
    f"{year}_Q{quarter}"
    for year in (2024, 2025)
    for quarter in range(1, 5)
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--period", action="append", dest="periods")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tickers = tuple(args.tickers or DEFAULT_TICKERS)
    periods = tuple(args.periods or DEFAULT_PERIODS)
    result = audit_snapshot(args.db_path, tickers, periods)
    payload = result.to_json()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
