"""Create a pending normalized candidate snapshot from the staged vendor ratios."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.normalize import normalize_vendor_snapshot  # noqa: E402


DEFAULT_TICKERS = ("VCB", "ACB", "MBB", "TCB", "VPB")
DEFAULT_PERIODS = tuple(
    f"{year}_Q{quarter}"
    for year in (2024, 2025)
    for quarter in range(1, 5)
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_db", type=Path)
    parser.add_argument("output_db", type=Path)
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--period", action="append", dest="periods")
    args = parser.parse_args()
    count = normalize_vendor_snapshot(
        args.staging_db,
        args.output_db,
        tickers=tuple(args.tickers or DEFAULT_TICKERS),
        periods=tuple(args.periods or DEFAULT_PERIODS),
    )
    print(f"normalized_candidate_rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
