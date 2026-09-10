#!/usr/bin/env python3
"""Aggregate arm-blinded AI review records by workload tier and arm."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.blind_aggregate import agreement_for_records  # noqa: E402
from thesis_data.blind_scoring import load_complexity_manifests  # noqa: E402


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _blind_id(claim_id: str) -> str:
    return claim_id.split(":", 1)[0]


def aggregate(score_dir: Path, run_dir: Path) -> dict[str, Any]:
    manifests = load_complexity_manifests(run_dir)
    identity_map = json.loads((score_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    packets = _jsonl(score_dir / "blind-packets.jsonl")
    by_blind = identity_map

    reviewer_rates: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    reviewer_records: dict[str, list[dict[str, Any]]] = {}
    for reviewer_id in ("ai_checker_a", "ai_checker_b"):
        records = _jsonl(score_dir / f"{reviewer_id}.jsonl")
        reviewer_records[reviewer_id] = records
        for row in _jsonl(score_dir / f"{reviewer_id}-claim-reviews.jsonl"):
            blind_id = _blind_id(str(row["claim_id"]))
            identity = by_blind.get(blind_id)
            score = row.get("score")
            if identity is None or not isinstance(score, (int, float)) or isinstance(score, bool):
                continue
            reviewer_rates[(
                reviewer_id,
                identity["workload_tier"],
                identity["arm"],
                row["dimension"],
            )].append(int(score))

    scores: dict[str, dict[str, dict[str, Any]]] = {}
    for (reviewer, tier, arm, dimension), values in sorted(reviewer_rates.items()):
        item = {
            "numerator": sum(values),
            "denominator": len(values),
            "score_rate": round(sum(values) / len(values), 6),
        }
        scores.setdefault(tier, {}).setdefault(arm, {}).setdefault(dimension, {})[reviewer] = item

    mean_scores: dict[str, dict[str, dict[str, Any]]] = {}
    for tier, arms in scores.items():
        for arm, dimensions in arms.items():
            for dimension, by_reviewer in dimensions.items():
                rates = [item["score_rate"] for item in by_reviewer.values()]
                mean_scores.setdefault(tier, {}).setdefault(arm, {})[dimension] = {
                    "reviewers": by_reviewer,
                    "mean_reviewer_score_rate": round(sum(rates) / len(rates), 6),
                }

    telemetry: dict[str, Any] = {}
    for reviewer_id in reviewer_records:
        rows = _jsonl(score_dir / f"{reviewer_id}-telemetry.jsonl")
        telemetry[reviewer_id] = {
            "attempts": len(rows),
            "successful": sum(1 for row in rows if row.get("status") == "provided"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
            "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
            "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
            "cost_estimate_usd": round(sum(float(row.get("cost_estimate") or 0.0) for row in rows), 8),
        }

    return {
        "packet_count": len(packets),
        "manifest_count": len(manifests),
        "reviewer_ids": ["ai_checker_a", "ai_checker_b"],
        "reviewer_integrity": {
            reviewer: {
                "attempt_records": len(records),
                "successful_packets": sum(1 for record in records if not record.get("error")),
                "failed_attempts": sum(1 for record in records if record.get("error")),
            }
            for reviewer, records in reviewer_records.items()
        },
        "ai_scores_by_tier_and_arm": mean_scores,
        "reviewer_specific_scores": scores,
        "reviewer_agreement": agreement_for_records(
            reviewer_records["ai_checker_a"], reviewer_records["ai_checker_b"]
        ),
        "reviewer_telemetry": telemetry,
        "interpretation": {
            "status": "preliminary_ai_assisted_blind_score",
            "human_validation_required": True,
            "superiority_claim": "withheld_for_thesis_final",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = aggregate(args.score_dir, args.run_dir)
    if args.output.exists():
        raise FileExistsError(f"refusing_to_overwrite:{args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"packet_count": report["packet_count"], "manifest_count": report["manifest_count"], "tiers": sorted(report["ai_scores_by_tier_and_arm"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
