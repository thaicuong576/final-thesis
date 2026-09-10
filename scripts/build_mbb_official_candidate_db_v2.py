"""Materialize the MBB four-metric official candidate packet as non-Gold SQLite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.build_mbb_official_candidate_db import build_candidate_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("output_db", type=Path)
    parser.add_argument("--snapshot-id", default="MBB-official-candidate-2024-v2")
    parser.add_argument("--min-manual-labels", type=int, default=16)
    args = parser.parse_args()
    try:
        result = build_candidate_db(
            args.candidate_jsonl,
            args.source_manifest,
            args.output_db,
            snapshot_id=args.snapshot_id,
            min_manual_labels=args.min_manual_labels,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
