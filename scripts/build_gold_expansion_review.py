"""Build the guarded 80-cell expansion candidate and human review packet."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.expansion_review import build_expansion_review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-gold", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build_expansion_review(args.base_gold, args.candidate, args.output_db, args.review_dir)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
