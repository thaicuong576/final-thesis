"""Build the frozen composite complexity plan without executing a provider."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_plan import build_complexity_plan, load_complexity_question_set  # noqa: E402
from thesis_data.experiment_contract import ExperimentArm  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_set", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--model-id", required=True)
    args = parser.parse_args()

    question_set = load_complexity_question_set(args.question_set)
    plan = build_complexity_plan(
        question_set,
        args.question_set,
        tuple(ExperimentArm),
        args.snapshot_id,
        args.model_id,
        total_call_ceilings={"tier_2": 6, "tier_3": 6},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
