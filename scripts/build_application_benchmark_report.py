"""Create a concise application benchmark report from the reviewed comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ARMS = ("single_agent", "hierarchical_no_critique", "hierarchical_bounded_critique")


def build_report(comparison: dict[str, Any]) -> dict[str, Any]:
    operational = comparison.get("operational_by_tier", {})
    human = comparison.get("human_scores_by_tier_and_arm", {})
    tiers: dict[str, Any] = {}
    for tier in sorted(operational):
        tiers[tier] = {"operational": {}, "human_quality": {}}
        for arm in ARMS:
            tiers[tier]["operational"][arm] = operational[tier].get(arm, {})
            tiers[tier]["human_quality"][arm] = human.get(tier, {}).get(arm, {})
    return {
        "report_version": "application-benchmark-v1",
        "source_report": comparison.get("primary_quality_source"),
        "manifest_count": comparison.get("manifest_count"),
        "human_review": comparison.get("human_review"),
        "tiers": tiers,
        "crossover": {
            "confirmed": False,
            "current_conclusion": "no_confirmed_multi_agent_break_even",
            "reason": "Current Gold-covered sweep shows higher multi-agent cost/latency; Tier 2 bounded critique is quality-candidate-only, not an operational break-even.",
            "next_candidate": "data/processed/normalized_candidate_bank-2025-v1.sqlite",
        },
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Application benchmark v1",
        "",
        "Báo cáo này tóm tắt benchmark đã chạy trên Gold snapshot. Nó không dùng scaling candidate đang pending.",
        "",
        f"- Manifests: `{report['manifest_count']}`",
        f"- Human review: `{report.get('human_review', {}).get('valid_score_count', 0)}` rows",
        "",
        "## Operational comparison",
        "",
        "| Tier | Arm | Cost/workload | Throughput/min | Failed jobs |",
        "|---|---|---:|---:|---:|",
    ]
    for tier, tier_data in report["tiers"].items():
        for arm in ARMS:
            item = tier_data["operational"].get(arm, {})
            if not item:
                continue
            lines.append(f"| {tier} | {arm} | ${item.get('cost_per_completed_job_usd', '—')} | {item.get('throughput_completed_jobs_per_minute', '—')} | {item.get('failed_jobs', '—')} |")
    lines.extend([
        "",
        "## Kết luận",
        "",
        "- Chưa có crossover point được xác nhận.",
        "- Tier 2 bounded critique là quality candidate ở một số chiều, nhưng chưa đáng về vận hành.",
        "- Candidate 200 cells là workload tiếp theo sau khi hoàn tất evidence và human review.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    report = build_report(comparison)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "benchmark.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "benchmark.md").write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({"manifest_count": report["manifest_count"], "confirmed_crossover": report["crossover"]["confirmed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
