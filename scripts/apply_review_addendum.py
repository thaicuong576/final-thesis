"""Apply a fresh Checker-B reviewer addendum to a versioned review ledger."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    apply_reviewer_addendum,
    write_review_ledger,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="prior versioned review ledger")
    parser.add_argument("addendum", type=Path, help="completed vendor-free reviewer addendum")
    parser.add_argument("output", type=Path, help="new ledger path")
    parser.add_argument("--adjudicator-id", required=True)
    parser.add_argument("--adjudicated-at", required=True)
    parser.add_argument("--adjudication-reason", required=True)
    args = parser.parse_args()

    rows = apply_reviewer_addendum(
        _read_csv(args.ledger),
        _read_csv(args.addendum),
        adjudicator_id=args.adjudicator_id,
        adjudicated_at=args.adjudicated_at,
        adjudication_reason=args.adjudication_reason,
    )
    write_review_ledger(rows, args.output)
    print(f"addendum_rows={len(_read_csv(args.addendum))} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
