#!/usr/bin/env python3
"""Aggregate mechanical and blind AI-assisted scores for the provider pilot."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.blind_aggregate import (  # noqa: E402
    agreement_for_records,
    latest_successful_records,
    preliminary_verdict,
)
from thesis_data.evaluation import ClaimReview, summarize_claim_reviews  # noqa: E402
from thesis_data.blind_scoring import load_provider_manifests  # noqa: E402


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def aggregate(output_dir: Path, run_dir: Path) -> dict[str, Any]:
    manifests = load_provider_manifests(run_dir)
    identity_map = json.loads((output_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    by_blind_id = identity_map
    packets = _jsonl(output_dir / "blind-packets.jsonl")
    mechanical = _jsonl(output_dir / "mechanical-score.jsonl")
    operational = json.loads((output_dir / "operational-summary.json").read_text(encoding="utf-8"))

    reviewer_records: dict[str, list[dict[str, Any]]] = {}
    claim_reviews: list[ClaimReview] = []
    reviewer_integrity: dict[str, Any] = {}
    for reviewer_id in ("ai_checker_a", "ai_checker_b"):
        records = _jsonl(output_dir / f"{reviewer_id}.jsonl")
        reviewer_records[reviewer_id] = records
        latest = latest_successful_records(records)
        errors = [record for record in records if record.get("error")]
        reviewer_integrity[reviewer_id] = {
            "attempt_records": len(records),
            "final_successful_packets": len(latest),
            "historical_failed_attempts": len(errors),
            "all_packets_have_final_review": len(latest) == len(packets),
        }
        for line in (output_dir / f"{reviewer_id}-claim-reviews.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                claim_reviews.append(ClaimReview.model_validate(json.loads(line)))

    score_summaries = [item.model_dump(mode="json") for item in summarize_claim_reviews(claim_reviews)]
    by_reviewer_arm_dimension: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in score_summaries:
        by_reviewer_arm_dimension[(item["reviewer_id"], item["arm"], item["dimension"])] = item

    dimensions = sorted({item["dimension"] for item in score_summaries})
    arms = sorted({manifest["arm"] for manifest in manifests})
    ai_arm_scores: dict[str, dict[str, Any]] = {}
    for arm in arms:
        ai_arm_scores[arm] = {}
        for dimension in dimensions:
            reviewers: dict[str, dict[str, Any]] = {}
            rates: list[float] = []
            for reviewer_id in reviewer_records:
                item = by_reviewer_arm_dimension.get((reviewer_id, arm, dimension))
                if item is not None:
                    reviewers[reviewer_id] = {
                        "numerator": item["numerator"],
                        "denominator": item["denominator"],
                        "unscorable_count": item["unscorable_count"],
                        "score_rate": item["score_rate"],
                    }
                    if item["score_rate"] is not None:
                        rates.append(item["score_rate"])
            ai_arm_scores[arm][dimension] = {
                "reviewers": reviewers,
                "mean_reviewer_score_rate": _mean(rates),
            }

    mechanical_by_arm: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    counts: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in mechanical:
        arm = by_blind_id[row["blind_id"]]["arm"]
        counts[(arm, row["dimension"])].append(int(row["score"]))
    for (arm, dimension), values in sorted(counts.items()):
        mechanical_by_arm[arm][dimension] = {
            "numerator": sum(values),
            "denominator": len(values),
            "score_rate": round(sum(values) / len(values), 6) if values else None,
        }

    agreement = agreement_for_records(
        reviewer_records["ai_checker_a"], reviewer_records["ai_checker_b"]
    )
    telemetry: dict[str, Any] = {}
    for reviewer_id in reviewer_records:
        rows = _jsonl(output_dir / f"{reviewer_id}-telemetry.jsonl")
        telemetry[reviewer_id] = {
            "attempts": len(rows),
            "successful": sum(1 for row in rows if row.get("status") == "provided"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
            "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
            "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
            "cost_estimate_usd": round(sum(float(row.get("cost_estimate") or 0.0) for row in rows), 8),
        }

    score_files_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output_dir.glob("*.jsonl")
    )
    secret_hit = "OPENAI_API_KEY" in score_files_text or "sk-" in score_files_text
    all_final = all(item["all_packets_have_final_review"] for item in reviewer_integrity.values())
    verdict = preliminary_verdict(ai_arm_scores, operational)
    return {
        "run_dir": str(run_dir.resolve()),
        "score_dir": str(output_dir.resolve()),
        "packet_count": len(packets),
        "manifest_count": len(manifests),
        "reviewer_integrity": reviewer_integrity,
        "score_binding": {
            "snapshot_id": manifests[0]["snapshot_id"],
            "question_set_sha256": manifests[0]["question_set_sha256"],
            "rubric_version": manifests[0]["rubric_version"],
            "prompt_version": manifests[0]["prompt_version"],
            "model_id": manifests[0]["model_id"],
        },
        "blind_integrity": {
            "arm_identity_stored_separately": True,
            "all_reviewers_complete": all_final,
            "secret_hit": secret_hit,
        },
        "operational_by_arm": operational,
        "mechanical_by_arm": dict(mechanical_by_arm),
        "ai_score_summaries": score_summaries,
        "ai_scores_by_arm": ai_arm_scores,
        "reviewer_agreement": agreement,
        "reviewer_telemetry": telemetry,
        "interpretation": {
            "status": "preliminary_ai_assisted_blind_score",
            **verdict,
            "superiority_claim": "withheld_for_thesis_final",
            "reason": "The two blind reviewers are AI-assisted and must not substitute for the protocol's final independent human review. Operational cost and quality scores are reported separately.",
        },
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Blind score report — provider pilot",
        "",
        f"- Packets: **{report['packet_count']}**; manifests: **{report['manifest_count']}**",
        f"- Model: `{report['score_binding']['model_id']}`",
        f"- Rubric: `{report['score_binding']['rubric_version']}`",
        f"- Blind integrity: `{'PASS' if report['blind_integrity']['all_reviewers_complete'] and not report['blind_integrity']['secret_hit'] else 'FAIL'}`",
        "- Published answer rule: single-agent payload for Arm A; last orchestrator payload for both hierarchical arms; verification payloads are not scored as final answers.",
        "",
        "## AI-assisted rubric scores",
        "",
        "Rates are the mean of the two reviewer-specific rates. Numerator/denominator and unscorable counts remain in the JSON artifact.",
        "",
        "| Arm | Dimension | Reviewer A | Reviewer B | Mean rate |",
        "|---|---|---:|---:|---:|",
    ]
    for arm, dimensions in report["ai_scores_by_arm"].items():
        for dimension, item in dimensions.items():
            reviewer_values = []
            for reviewer_id in ("ai_checker_a", "ai_checker_b"):
                value = item["reviewers"].get(reviewer_id, {}).get("score_rate")
                reviewer_values.append("n/a" if value is None else f"{value:.3f}")
            mean = item["mean_reviewer_score_rate"]
            lines.append(
                f"| {arm} | {dimension} | {reviewer_values[0]} | {reviewer_values[1]} | {'n/a' if mean is None else f'{mean:.3f}'} |"
            )
    lines.extend(["", "## Mechanical structured checks", "", "| Arm | Dimension | Score |", "|---|---|---:|"])
    for arm, dimensions in report["mechanical_by_arm"].items():
        for dimension, item in dimensions.items():
            lines.append(f"| {arm} | {dimension} | {item['numerator']}/{item['denominator']} ({item['score_rate']:.3f}) |")
    lines.extend(["", "## Reviewer agreement", "", f"- Compared decisions: **{report['reviewer_agreement']['compared']}**", f"- Agreements: **{report['reviewer_agreement']['agreements']}**", f"- Disagreements: **{report['reviewer_agreement']['disagreements']}**", ""])
    lines.extend(["## Operational cost and latency", "", "| Arm | Jobs | Calls | Input tokens | Output tokens | Cost estimate | Total latency (ms) |", "|---|---:|---:|---:|---:|---:|---:|"])
    for arm, item in report["operational_by_arm"].items():
        lines.append(f"| {arm} | {item['jobs']} | {item['runtime_calls']} | {item['input_tokens']} | {item['output_tokens']} | ${item['cost_estimate_usd']:.6f} | {item['latency_ms_total']:.1f} |")
    lines.extend(["", "## Review overhead", ""])
    for reviewer_id, item in report["reviewer_telemetry"].items():
        lines.append(f"- `{reviewer_id}`: {item['input_tokens']} input + {item['output_tokens']} output tokens; cost estimate `${item['cost_estimate_usd']:.6f}`; failed attempts `{item['failed']}`.")
    interpretation = report["interpretation"]
    lines.extend(["", "## Preliminary interpretation", "", f"- Verdict: **{interpretation['verdict']}**", f"- Preferred under this pilot: **{interpretation['preferred_under_current_pilot']}**", ""])
    for arm, assessment in interpretation["assessments"].items():
        lines.append(f"- `{arm}` vs single-agent: wins `{', '.join(assessment['wins']) or 'none'}`; losses `{', '.join(assessment['losses']) or 'none'}`; cost ratio `{assessment['cost_ratio_to_single']}x`; latency ratio `{assessment['latency_ratio_to_single']}x`.")
    lines.extend(["", "## Interpretation boundary", "", "This is a preliminary AI-assisted blind score, not final human thesis validation. It is valid for exposing quality/overhead signals and reviewer disagreement, but the superiority claim remains withheld for the thesis until the protocol's independent human review is completed. A larger score is not sufficient if evidence, missing/conflict handling, or consistency degrades, and tool-call count is not a quality score.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    report = aggregate(args.output_dir, args.run_dir)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({"packet_count": report["packet_count"], "manifest_count": report["manifest_count"], "all_reviewers_complete": report["blind_integrity"]["all_reviewers_complete"], "secret_hit": report["blind_integrity"]["secret_hit"]}, ensure_ascii=False, sort_keys=True))
    return 0 if report["blind_integrity"]["all_reviewers_complete"] and not report["blind_integrity"]["secret_hit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
