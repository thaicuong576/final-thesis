"""Build a source-only navigation index for independent pilot review."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.review_navigation import (  # noqa: E402
    build_blind_source_navigation_index,
    write_blind_source_navigation_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows = build_blind_source_navigation_index(args.register, args.snapshot)
    result = write_blind_source_navigation_index(rows, args.output)
    print(
        f"targets={result.target_count} rows={result.row_count} "
        f"source_gaps={result.source_gap_count} output={result.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
