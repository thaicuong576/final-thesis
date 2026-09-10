"""Promote a completed two-checker review into a new gold snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.review_promotion import promote_reviewed_snapshot  # noqa: E402
from thesis_data.schema import GoldConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_db", type=Path)
    parser.add_argument("review_ledger", type=Path)
    parser.add_argument("gold_labels", type=Path)
    parser.add_argument("register", type=Path)
    parser.add_argument("output_db", type=Path)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--period", action="append", required=True)
    parser.add_argument("--metric", action="append", required=True)
    parser.add_argument("--min-manual-labels", type=int, default=40)
    parser.add_argument("--min-independent-checkers", type=int, default=2)
    parser.add_argument("--min-metric-coverage", type=float, default=0.9)
    args = parser.parse_args()

    result = promote_reviewed_snapshot(
        args.candidate_db,
        args.review_ledger,
        args.gold_labels,
        args.register,
        args.output_db,
        GoldConfig(
            tickers=tuple(args.ticker),
            periods=tuple(args.period),
            required_metrics=tuple(args.metric),
            min_manual_labels=args.min_manual_labels,
            min_independent_checkers=args.min_independent_checkers,
            min_metric_coverage=args.min_metric_coverage,
        ),
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    return 0 if result.eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
