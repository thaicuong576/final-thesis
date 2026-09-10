"""Validate a frozen composite complexity plan before provider execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_plan import audit_complexity_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("question_set", type=Path)
    args = parser.parse_args()
    audit = audit_complexity_plan(args.plan, args.question_set)
    print(
        json.dumps(
            {
                "eligible": audit.eligible,
                "blockers": list(audit.blockers),
                "question_count": audit.question_count,
                "job_count": audit.job_count,
                "snapshot_id": audit.snapshot_id,
                "question_set_id": audit.question_set_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if audit.eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
