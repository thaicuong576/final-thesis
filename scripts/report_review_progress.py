"""Report blind-review completion, disagreements, and measured throughput."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.review_progress import summarize_review_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "review_files",
        nargs="+",
        type=Path,
        help="blind reviewer copy or merged ledger CSV path(s)",
    )
    args = parser.parse_args()
    try:
        reports = [summarize_review_file(path).as_dict() for path in args.review_files]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"reports": reports}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
