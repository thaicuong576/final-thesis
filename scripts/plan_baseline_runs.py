"""Create a non-executing baseline job plan from a typed question set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_plan import build_baseline_plan_from_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_set", type=Path)
    parser.add_argument("snapshot_id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        plan = build_baseline_plan_from_file(args.question_set, args.snapshot_id)
        rendered = json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(
                json.dumps(
                    {
                        "comparative_result": plan.comparative_result,
                        "job_count": len(plan.jobs),
                        "question_set_id": plan.question_set_id,
                        "question_set_sha256": plan.question_set_sha256,
                        "snapshot_id": plan.snapshot_id,
                        "status": plan.status.value,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            if args.output.exists():
                raise FileExistsError(f"refusing to overwrite baseline plan: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "job_count": len(plan.jobs),
                        "output": str(args.output),
                        "status": plan.status.value,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    except (FileExistsError, ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
