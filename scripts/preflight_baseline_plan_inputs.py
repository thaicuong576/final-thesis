"""Audit a complete baseline plan against one Gold snapshot without dispatch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_batch_runner import preflight_baseline_plan_inputs  # noqa: E402
from thesis_data.schema import GoldConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("question_set", type=Path)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--period", action="append", required=True)
    parser.add_argument("--metric", action="append", required=True)
    parser.add_argument("--run-id-prefix", required=True)
    parser.add_argument("--rubric-version", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--source-policy-id", required=True)
    parser.add_argument("--max-critique-attempts", type=int, default=2)
    parser.add_argument("--min-manual-labels", type=int, default=40)
    parser.add_argument("--min-independent-checkers", type=int, default=2)
    parser.add_argument("--min-metric-coverage", type=float, default=0.9)
    args = parser.parse_args()

    audit = preflight_baseline_plan_inputs(
        args.snapshot,
        args.plan,
        args.question_set,
        GoldConfig(
            tickers=tuple(args.ticker),
            periods=tuple(args.period),
            required_metrics=tuple(args.metric),
            min_manual_labels=args.min_manual_labels,
            min_independent_checkers=args.min_independent_checkers,
            min_metric_coverage=args.min_metric_coverage,
        ),
        run_id_prefix=args.run_id_prefix,
        rubric_version=args.rubric_version,
        model_id=args.model_id,
        source_policy_id=args.source_policy_id,
        max_critique_attempts=args.max_critique_attempts,
    )
    print(json.dumps(audit.__dict__, ensure_ascii=False, sort_keys=True))
    return 0 if audit.eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
