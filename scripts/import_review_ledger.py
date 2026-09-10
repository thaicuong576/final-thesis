"""Export a completed review ledger as a non-mutating gold-label artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.review_import import import_review_ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_ledger", type=Path)
    parser.add_argument("candidate_db", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--register",
        type=Path,
        required=True,
        help="complete one-row-per-target register used to enforce review completeness",
    )
    args = parser.parse_args()
    count = import_review_ledger(
        args.review_ledger, args.candidate_db, args.output, args.register
    )
    print(f"gold_label_rows={count} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
