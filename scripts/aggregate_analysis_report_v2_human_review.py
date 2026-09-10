"""Aggregate completed blind scores and estimate a pre-registered crossover."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

try:
    from validate_analysis_report_v2_human_queue import validate
except ModuleNotFoundError:  # Importable from the repository test runner.
    from scripts.validate_analysis_report_v2_human_queue import validate


DIMENSIONS = ("correctness", "usefulness", "evidence", "limitation")
MIN_QUALITY_GAIN = 0.05
MIN_POSITIVE_REPETITIONS = 3


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 6) if values else None


def _median(values: list[float]) -> float | None:
    return round(median(values), 6) if values else None


def aggregate(queue_dir: Path) -> dict[str, Any]:
    validation = validate(queue_dir, require_complete=True)
    if not validation["valid"]:
        raise RuntimeError("human review queue is invalid: " + ";".join(validation["errors"]))
    identities = json.loads((queue_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    with (queue_dir / "human-review-queue.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    # The blind queue intentionally contains only completed, model-origin
    # reports. Keep the full operational denominator alongside the semantic
    # scores so a selective-completion effect cannot make a fragile arm look
    # like a complete comparison.
    operational_path = queue_dir / "operational-manifest-summary.json"
    operational_items = (
        json.loads(operational_path.read_text(encoding="utf-8"))
        if operational_path.exists()
        else []
    )
    operational_groups: dict[tuple[str, int, str], dict[str, int]] = defaultdict(
        lambda: {"planned": 0, "completed": 0, "failed": 0}
    )
    for item in operational_items:
        workload_tier = item.get("workload_tier")
        issuer_count = item.get("issuer_count")
        arm = item.get("arm")
        if workload_tier is None or issuer_count is None or arm is None:
            continue
        key = (str(workload_tier), int(issuer_count), str(arm))
        operational_groups[key]["planned"] += 1
        if item.get("quality_review_eligible") and not item.get("failure_status"):
            operational_groups[key]["completed"] += 1
        else:
            operational_groups[key]["failed"] += 1

    by_blind: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        by_blind[row["blind_id"]][row["dimension"]] = int(row["score"]) / 4.0
    packet_scores: list[dict[str, Any]] = []
    for blind_id, dimensions in sorted(by_blind.items()):
        if set(dimensions) != set(DIMENSIONS):
            raise RuntimeError(f"incomplete_dimensions:{blind_id}")
        identity = identities[blind_id]
        packet_scores.append(
            {
                "blind_id": blind_id,
                **{dimension: round(dimensions[dimension], 6) for dimension in DIMENSIONS},
                "quality_score": round(mean(dimensions.values()), 6),
                "arm": identity["arm"],
                "workload_tier": identity["workload_tier"],
                "issuer_count": identity["issuer_count"],
                "question_id": identity["question_id"],
                "cost_estimate_usd": identity["cost_estimate_usd"],
                "wall_clock_latency_ms": identity["wall_clock_latency_ms"],
                "input_tokens": identity["input_tokens"],
                "output_tokens": identity["output_tokens"],
                "status": identity["status"],
            }
        )

    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for item in packet_scores:
        grouped[(item["workload_tier"], item["issuer_count"], item["arm"])].append(item)
    summaries: list[dict[str, Any]] = []
    for (tier, issuer_count, arm), items in sorted(grouped.items()):
        operational = operational_groups.get(
            (tier, issuer_count, arm),
            {"planned": len(items), "completed": len(items), "failed": 0},
        )
        quality_mean = _mean([item["quality_score"] for item in items])
        completion_rate = (
            operational["completed"] / operational["planned"]
            if operational["planned"]
            else None
        )
        summaries.append(
            {
                "workload_tier": tier,
                "issuer_count": issuer_count,
                "arm": arm,
                "repetitions": len(items),
                "quality_mean": quality_mean,
                "quality_median": _median([item["quality_score"] for item in items]),
                **{
                    f"{dimension}_mean": _mean([item[dimension] for item in items])
                    for dimension in DIMENSIONS
                },
                "cost_mean_usd": _mean([item["cost_estimate_usd"] for item in items if item["cost_estimate_usd"] is not None]),
                "latency_mean_ms": _mean([item["wall_clock_latency_ms"] for item in items if item["wall_clock_latency_ms"] is not None]),
                "input_tokens_mean": _mean([item["input_tokens"] for item in items if item["input_tokens"] is not None]),
                "output_tokens_mean": _mean([item["output_tokens"] for item in items if item["output_tokens"] is not None]),
                "semantic_scored_repetitions": len(items),
                "planned_repetitions": operational["planned"],
                "completed_repetitions": operational["completed"],
                "failed_repetitions": operational["failed"],
                "failure_rate": round(operational["failed"] / operational["planned"], 6)
                if operational["planned"]
                else None,
                "completion_adjusted_quality_mean": round(quality_mean * completion_rate, 6)
                if quality_mean is not None and completion_rate is not None
                else None,
            }
        )

    by_key_arm = {
        (item["workload_tier"], item["issuer_count"], item["question_id"], item["arm"]): item
        for item in packet_scores
    }
    deltas: list[dict[str, Any]] = []
    for item in packet_scores:
        if item["arm"] == "single_agent":
            continue
        baseline = by_key_arm.get(
            (item["workload_tier"], item["issuer_count"], item["question_id"], "single_agent")
        )
        if baseline is None:
            continue
        deltas.append(
            {
                "workload_tier": item["workload_tier"],
                "issuer_count": item["issuer_count"],
                "question_id": item["question_id"],
                "arm": item["arm"],
                "quality_gain": round(item["quality_score"] - baseline["quality_score"], 6),
                **{
                    f"{dimension}_gain": round(item[dimension] - baseline[dimension], 6)
                    for dimension in DIMENSIONS
                },
                "cost_ratio": round(item["cost_estimate_usd"] / baseline["cost_estimate_usd"], 6)
                if item["cost_estimate_usd"] and baseline["cost_estimate_usd"]
                else None,
                "latency_ratio": round(item["wall_clock_latency_ms"] / baseline["wall_clock_latency_ms"], 6)
                if item["wall_clock_latency_ms"] and baseline["wall_clock_latency_ms"]
                else None,
            }
        )

    delta_groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for item in deltas:
        delta_groups[(item["workload_tier"], item["issuer_count"], item["arm"])].append(item)
    crossover: list[dict[str, Any]] = []
    for (tier, issuer_count, arm), items in sorted(delta_groups.items()):
        operational = operational_groups.get(
            (tier, issuer_count, arm),
            {"planned": len(items), "completed": len(items), "failed": 0},
        )
        baseline_operational = operational_groups.get(
            (tier, issuer_count, "single_agent"),
            {"planned": len(items), "completed": len(items), "failed": 0},
        )
        positive_reps = sum(item["quality_gain"] >= MIN_QUALITY_GAIN for item in items)
        evidence_not_lower = all(item["evidence_gain"] >= 0 for item in items)
        limitation_not_lower = all(item["limitation_gain"] >= 0 for item in items)
        semantic_rule_passes = (
            len(items) >= MIN_POSITIVE_REPETITIONS
            and positive_reps >= MIN_POSITIVE_REPETITIONS
            and _mean([item["quality_gain"] for item in items]) >= MIN_QUALITY_GAIN
            and evidence_not_lower
            and limitation_not_lower
        )
        operationally_complete = (
            operational["planned"] > 0
            and baseline_operational["planned"] > 0
            and operational["failed"] == 0
            and baseline_operational["failed"] == 0
        )
        crossover.append(
            {
                "workload_tier": tier,
                "issuer_count": issuer_count,
                "arm": arm,
                "paired_repetitions": len(items),
                "mean_quality_gain": _mean([item["quality_gain"] for item in items]),
                "positive_repetitions_at_threshold": positive_reps,
                "evidence_not_lower": evidence_not_lower,
                "limitation_not_lower": limitation_not_lower,
                "cost_ratio_mean": _mean([item["cost_ratio"] for item in items if item["cost_ratio"] is not None]),
                "latency_ratio_mean": _mean([item["latency_ratio"] for item in items if item["latency_ratio"] is not None]),
                "semantic_rule_passes": semantic_rule_passes,
                "operationally_complete_comparison": operationally_complete,
                "arm_failure_rate": round(operational["failed"] / operational["planned"], 6)
                if operational["planned"]
                else None,
                "baseline_failure_rate": round(
                    baseline_operational["failed"] / baseline_operational["planned"], 6
                )
                if baseline_operational["planned"]
                else None,
                "qualifies_as_crossover": semantic_rule_passes and operationally_complete,
            }
        )

    qualifying = [item for item in crossover if item["qualifies_as_crossover"]]
    first = min(qualifying, key=lambda item: (item["issuer_count"], item["workload_tier"], item["arm"])) if qualifying else None
    return {
        "protocol": "analysis-report-v2-blind-human-review-v1",
        "packet_count": len(packet_scores),
        "dimension_scale": "0-4 normalized to 0-1",
        "arm_summaries": summaries,
        "paired_deltas": deltas,
        "crossover_rule": {
            "minimum_quality_gain": MIN_QUALITY_GAIN,
            "minimum_positive_repetitions": MIN_POSITIVE_REPETITIONS,
            "evidence_gain_must_be_non_negative": True,
            "limitation_gain_must_be_non_negative": True,
        },
        "crossover_candidates": crossover,
        "first_observed_crossover": first,
        "interpretation": "observed_crossover_only; requires complete operational comparison and is not a universal asymptotic claim",
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Analysis Report v2 — blind human review aggregate",
        "",
        f"- Packets scored: **{result['packet_count']}**",
        f"- Protocol: `{result['protocol']}`",
        "",
        "## Quality and operations by tier",
        "",
        "| Tier | Issuers | Arm | Scored/planned | Failed | Quality mean | Completion-adjusted quality | Correctness | Usefulness | Evidence | Limitation | Cost USD | Latency ms |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["arm_summaries"]:
        lines.append(
            f"| {item['workload_tier']} | {item['issuer_count']} | {item['arm']} | {item['semantic_scored_repetitions']}/{item['planned_repetitions']} | {item['failed_repetitions']} | {item['quality_mean']} | {item['completion_adjusted_quality_mean']} | {item['correctness_mean']} | {item['usefulness_mean']} | {item['evidence_mean']} | {item['limitation_mean']} | {item['cost_mean_usd']} | {item['latency_mean_ms']} |"
        )
    lines.extend(["", "## Crossover", ""])
    if result["first_observed_crossover"]:
        item = result["first_observed_crossover"]
        lines.append(
            f"First observed crossover candidate: **{item['arm']} at {item['issuer_count']} issuer(s), {item['workload_tier']}**; mean quality gain `{item['mean_quality_gain']}`, cost ratio `{item['cost_ratio_mean']}`, latency ratio `{item['latency_ratio_mean']}`."
        )
    else:
        lines.append("No observed crossover satisfies the preregistered quality/evidence/limitation rule with a complete operational comparison.")
    lines.extend(
        [
            "",
            "A crossover requires both the semantic rule and zero provider failures in the compared arm and single-agent baseline. Completion-adjusted quality is a secondary deployment metric, not a substitute for human quality.",
            "The result is an observed crossover in this frozen workload, not a proof of universal multi-agent superiority or an asymptotic law.",
            "",
            "| Tier | Issuers | Arm | Mean quality gain | Positive reps ≥ threshold | Evidence not lower | Limitation not lower | Operationally complete | Semantic rule | Qualifies |",
            "|---|---:|---|---:|---:|---|---|---|---|---|",
        ]
    )
    for item in result["crossover_candidates"]:
        lines.append(
            f"| {item['workload_tier']} | {item['issuer_count']} | {item['arm']} | {item['mean_quality_gain']} | {item['positive_repetitions_at_threshold']}/{item['paired_repetitions']} | {item['evidence_not_lower']} | {item['limitation_not_lower']} | {item['operationally_complete_comparison']} | {item['semantic_rule_passes']} | {item['qualifies_as_crossover']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError(f"refusing_to_overwrite_nonempty:{args.output_dir}")
    result = aggregate(args.queue_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "aggregate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "aggregate.md").write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"packet_count": result["packet_count"], "first_observed_crossover": result["first_observed_crossover"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
