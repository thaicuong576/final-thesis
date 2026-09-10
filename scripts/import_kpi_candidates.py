"""Import extracted official KPI candidates into a non-gold SQLite snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.kpi_storage import import_kpi_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    count = import_kpi_candidates(
        args.candidates, args.source_manifest, args.output, args.evidence
    )
    print(f"imported_candidate_rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
