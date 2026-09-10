"""Build the gated five-issuer scaling question set without executing a run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ISSUERS = ("ACB", "TCB", "VPB", "MBB", "VCB")
PERIODS = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
METRICS = ("bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe")
TASKS = (
    "snapshot",
    "trend",
    "peer_comparison",
    "missing_conflict",
    "anomaly_review",
    "evidence_summary",
)
REPETITIONS = 5


def _prompt(selected: tuple[str, ...]) -> str:
    names = ", ".join(selected)
    return (
        f"Analyze {names} together across all four 2024 quarters and the four core metrics. "
        "Produce comparable issuer snapshots, cross-period trends, peer comparisons, "
        "missing/conflict checks, anomaly review, and evidence summaries. Keep every "
        "claim bound to issuer, period, task, and provenance; do not infer causality."
    )


def build_question_set() -> dict:
    questions: list[dict] = []
    for size in range(1, len(ISSUERS) + 1):
        selected = ISSUERS[:size]
        tier = "tier_2" if size == 1 else "tier_3"
        for repetition in range(1, REPETITIONS + 1):
            question_id = f"scale_{size}issuer_rep{repetition}_5issuer_v1"
            questions.append(
                {
                    "id": question_id,
                    "type": "composite_workload",
                    "prompt": _prompt(selected),
                    "workload": {
                        "question_id": question_id,
                        "tier": tier,
                        "issuers": list(selected),
                        "periods": list(PERIODS),
                        "metric_ids": list(METRICS),
                        "analysis_tasks": list(TASKS),
                        "peer_tickers": list(ISSUERS),
                        "macro_indicator_ids": [],
                        "complexity_vector": {
                            "issuer_count": size,
                            "period_count": len(PERIODS),
                            "metric_count": len(METRICS),
                            "analysis_task_count": len(TASKS),
                            "cross_issuer_comparisons": 1,
                            "missing_conflict_checks": size * len(PERIODS) * len(METRICS),
                            "evidence_groups": size * len(PERIODS),
                        },
                    },
                }
            )
    return {
        "schema_version": 1,
        "question_set_id": "pilot-2024-bank-scaling-5issuer-v1",
        "status": "frozen_gated_on_gold_5issuer_promotion",
        "scope": {
            "issuers": list(ISSUERS),
            "periods": list(PERIODS),
            "core_metrics": list(METRICS),
            "conditional_metrics": ["bank.cir", "bank.nim"],
        },
        "questions": questions,
    }


def build_design() -> dict:
    """Return non-schema design metadata in a separate companion artifact."""

    return {
        "schema_version": 1,
        "question_set_id": "pilot-2024-bank-scaling-5issuer-v1",
        "issuer_sizes": list(range(1, len(ISSUERS) + 1)),
        "repetitions_per_size": REPETITIONS,
        "arms": ["single_agent", "hierarchical_no_critique", "hierarchical_bounded_critique"],
        "question_count": len(ISSUERS) * REPETITIONS,
        "planned_jobs": len(ISSUERS) * REPETITIONS * 3,
        "snapshot_gate": "PENDING_GOLD_5_ISSUER",
        "execution_status": "not_executed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite {args.output}")
    payload = build_question_set()
    design = build_design()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    design_path = args.output.with_name(args.output.stem + ".design.json")
    if design_path.exists():
        parser.error(f"refusing to overwrite {design_path}")
    design_path.write_text(json.dumps(design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "design": str(design_path), "questions": len(payload["questions"]), "planned_jobs": design["planned_jobs"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
