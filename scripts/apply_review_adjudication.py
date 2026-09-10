"""Apply a reviewed adjudication overlay to a merged two-checker ledger."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    apply_adjudication_overlay,
    write_review_ledger,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="merged two-checker ledger")
    parser.add_argument("adjudication", type=Path, help="adjudication overlay CSV")
    parser.add_argument("output", type=Path, help="new adjudicated ledger path")
    args = parser.parse_args()

    rows = apply_adjudication_overlay(_read_csv(args.ledger), _read_csv(args.adjudication))
    write_review_ledger(rows, args.output)
    print(f"adjudicated_rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
