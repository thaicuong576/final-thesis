"""Aggregation helpers for blind reviewer artifacts."""

from __future__ import annotations

from typing import Any


def latest_successful_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the latest valid record for each blind answer after resumable retries."""

    result: dict[str, dict[str, Any]] = {}
    for record in records:
        blind_id = record.get("blind_id")
        if not isinstance(blind_id, str) or record.get("error"):
            continue
        result[blind_id] = record
    return result


def agreement_for_records(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
) -> dict[str, int]:
    """Compare two reviewers only where both emitted the same dimension."""

    first_map = latest_successful_records(first)
    second_map = latest_successful_records(second)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for blind_id in sorted(set(first_map) & set(second_map)):
        a = {
            row["dimension"]: row
            for row in first_map[blind_id].get("decisions", [])
            if isinstance(row, dict) and row.get("dimension")
        }
        b = {
            row["dimension"]: row
            for row in second_map[blind_id].get("decisions", [])
            if isinstance(row, dict) and row.get("dimension")
        }
        for dimension in sorted(set(a) & set(b)):
            pairs.append((a[dimension], b[dimension]))
    agreements = sum(
        1
        for first_row, second_row in pairs
        if first_row.get("review_status") == second_row.get("review_status")
        and first_row.get("score") == second_row.get("score")
    )
    return {
        "compared": len(pairs),
        "agreements": agreements,
        "disagreements": len(pairs) - agreements,
    }


def preliminary_verdict(
    scores_by_arm: dict[str, dict[str, dict[str, Any]]],
    operational_by_arm: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Apply the protocol's conservative pilot interpretation guardrail."""

    baseline = scores_by_arm.get("single_agent", {})
    primary_dimensions = (
        "factual_correctness",
        "calculation_correctness",
        "evidence_completeness",
        "coverage_discipline",
        "cross_level_consistency",
        "anomaly_classification",
    )
    assessments: dict[str, Any] = {}
    for arm, scores in scores_by_arm.items():
        if arm == "single_agent":
            continue
        wins: list[str] = []
        losses: list[str] = []
        ties: list[str] = []
        for dimension in primary_dimensions:
            baseline_rate = baseline.get(dimension, {}).get("mean_reviewer_score_rate")
            arm_rate = scores.get(dimension, {}).get("mean_reviewer_score_rate")
            if baseline_rate is None or arm_rate is None:
                continue
            delta = arm_rate - baseline_rate
            if delta > 0.02:
                wins.append(dimension)
            elif delta < -0.02:
                losses.append(dimension)
            else:
                ties.append(dimension)
        baseline_cost = operational_by_arm.get("single_agent", {}).get("cost_estimate_usd")
        baseline_latency = operational_by_arm.get("single_agent", {}).get("latency_ms_total")
        arm_cost = operational_by_arm.get(arm, {}).get("cost_estimate_usd")
        arm_latency = operational_by_arm.get(arm, {}).get("latency_ms_total")
        assessments[arm] = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "cost_ratio_to_single": round(arm_cost / baseline_cost, 3)
            if baseline_cost and arm_cost is not None
            else None,
            "latency_ratio_to_single": round(arm_latency / baseline_latency, 3)
            if baseline_latency and arm_latency is not None
            else None,
        }

    clear_support = any(
        assessment["wins"] and not assessment["losses"]
        for assessment in assessments.values()
    )
    preferred = "multi_agent_candidate" if clear_support else "single_agent"
    return {
        "verdict": "multi_agent_candidate" if clear_support else "multi_agent_not_yet_justified",
        "preferred_under_current_pilot": preferred,
        "assessments": assessments,
        "guardrail": "A multi-agent arm must improve at least one primary dimension without losing another before overhead can be justified; this preliminary verdict still requires independent human review.",
    }


def aggregate_by_tier_and_arm(
    reviews: list[dict[str, Any]],
    manifests: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """Aggregate reviewer rows without mixing Tier 1 and composite tiers."""

    identity_by_blind = {
        item.get("blind_id"): item
        for item in manifests
        if isinstance(item.get("blind_id"), str)
    }
    buckets: dict[tuple[str, str, str], list[float]] = {}
    for review in reviews:
        identity = identity_by_blind.get(review.get("blind_id"), review)
        tier = identity.get("workload_tier")
        arm = identity.get("arm")
        dimension = review.get("dimension")
        score = review.get("score")
        if not all(isinstance(value, str) and value for value in (tier, arm, dimension)):
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        buckets.setdefault((tier, arm, dimension), []).append(float(score))
    result: dict[str, dict[str, dict[str, dict[str, float | int]]]] = {}
    for (tier, arm, dimension), values in sorted(buckets.items()):
        result.setdefault(tier, {}).setdefault(arm, {})[dimension] = {
            "score_rate": round(sum(values) / len(values), 6),
            "count": len(values),
        }
    return result


def compute_scaling_deltas(
    scores_by_tier: dict[str, dict[str, dict[str, dict[str, float | int]]]],
    baseline_arm: str = "single_agent",
) -> dict[str, dict[str, dict[str, float]]]:
    """Compute per-tier quality deltas against the same-tier baseline arm."""

    result: dict[str, dict[str, dict[str, float]]] = {}
    for tier, arms in scores_by_tier.items():
        baseline = arms.get(baseline_arm, {})
        if not baseline:
            continue
        for arm, dimensions in arms.items():
            if arm == baseline_arm:
                continue
            for dimension, values in dimensions.items():
                base_rate = float(baseline.get(dimension, {}).get("score_rate", 0.0))
                arm_rate = float(values.get("score_rate", 0.0))
                result.setdefault(tier, {}).setdefault(arm, {})[dimension] = round(
                    arm_rate - base_rate, 6
                )
    return result


def classify_break_even_region(
    deltas: dict[str, dict[str, dict[str, float]]],
    operational_by_tier: dict[str, dict[str, dict[str, Any]]],
    *,
    material_quality_delta: float = 0.02,
) -> dict[str, dict[str, Any]]:
    """Identify bounded candidate tiers; never extrapolate an asymptotic law."""

    result: dict[str, dict[str, Any]] = {}
    for tier, arms in deltas.items():
        candidates: list[str] = []
        for arm, dimensions in arms.items():
            wins = [value for value in dimensions.values() if value > material_quality_delta]
            losses = [value for value in dimensions.values() if value < -material_quality_delta]
            if wins and not losses:
                candidates.append(arm)
        candidates.sort()
        operational = operational_by_tier.get(tier, {})
        result[tier] = {
            "candidate_arms": candidates,
            "bounded_conclusion": "candidate_only" if candidates else "no_break_even_observed",
            "operational": operational,
            "warning": "This is evidence only for the tested workload tier; it is not a universal scaling law.",
        }
    return result
