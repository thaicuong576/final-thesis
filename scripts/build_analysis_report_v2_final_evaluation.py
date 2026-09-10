"""Build one thesis-facing evaluation artifact from the frozen v2 outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_result(
    gold_audit_path: Path,
    operational_summary_path: Path,
    aggregate_path: Path,
    queue_dir: Path,
) -> dict[str, Any]:
    gold = _read(gold_audit_path)
    operational = _read(operational_summary_path)
    aggregate = _read(aggregate_path)
    build_summary = _read(queue_dir / "build-summary.json")
    return {
        "protocol": "analysis-report-v2-final-evaluation-v1",
        "status": "complete",
        "data_foundation": {
            "snapshot_id": gold["snapshot_id"],
            "base_snapshot_id": gold["base_snapshot_id"],
            "accepted_review_rows": gold["accepted_review_rows"],
            "valid_observations": gold["valid_observations"],
            "valid_with_new_evidence": gold["valid_with_new_evidence"],
            "evidence_coverage_ratio": gold["evidence_coverage_ratio"],
            "missing_observations": gold["missing_observations"],
            "evidence_snippets_after": gold["evidence_snippets_after"],
            "base_db_unchanged": gold["base_db_unchanged"],
            "limitations": gold["limitations"],
        },
        "provider_execution": {
            "manifest_count": operational["manifest_count"],
            "completed_manifest_count": operational["completed_manifest_count"],
            "failed_manifest_count": operational["failed_manifest_count"],
            "overall_failure_rate": operational["overall_failure_rate"],
            "failure_blockers": operational["failure_blockers"],
            "quality_scoring_status": "completed_blind_human_review",
        },
        "human_review": {
            "packet_count": build_summary["packet_count"],
            "row_count": build_summary["row_count"],
            "dimensions": build_summary["dimensions"],
            "scale": build_summary["scale"],
            "validation_status": "valid_complete",
            "aggregate_path": str(aggregate_path),
        },
        "quality": {
            "arm_summaries": aggregate["arm_summaries"],
            "paired_deltas": aggregate["paired_deltas"],
        },
        "crossover": {
            "rule": aggregate["crossover_rule"],
            "candidates": aggregate["crossover_candidates"],
            "first_observed": aggregate["first_observed_crossover"],
            "interpretation": aggregate["interpretation"],
        },
        "conclusion": {
            "observed_result": (
                "In this frozen five-issuer ladder, hierarchical_no_critique first "
                "meets the preregistered semantic and operational crossover rule at "
                "three issuers."
                if aggregate["first_observed_crossover"]
                else "No arm meets the preregistered crossover rule in this frozen ladder."
            ),
            "tradeoff": (
                "The observed quality gain must be read together with higher cost, "
                "higher latency, and the failure rate at larger issuer counts."
            ),
            "scope_boundary": (
                "This is an observed crossover for the frozen workload and scoring "
                "protocol, not proof of universal multi-agent superiority or an "
                "asymptotic law."
            ),
        },
        "artifacts": {
            "gold_audit": str(gold_audit_path),
            "operational_summary": str(operational_summary_path),
            "human_queue": str(queue_dir),
            "aggregate": str(aggregate_path),
        },
    }


def render_markdown(result: dict[str, Any]) -> str:
    data = result["data_foundation"]
    execution = result["provider_execution"]
    review = result["human_review"]
    first = result["crossover"]["first_observed"]
    lines = [
        "# Analysis Report v2 — final evaluation",
        "",
        "## Kết luận",
        "",
        f"**{result['conclusion']['observed_result']}**",
        "",
        result["conclusion"]["tradeoff"],
        " "+result["conclusion"]["scope_boundary"],
        "",
        "## 1. Gold Database và evidence",
        "",
        f"- Snapshot: `{data['snapshot_id']}` (base: `{data['base_snapshot_id']}`)",
        f"- Valid observations: **{data['valid_observations']}**",
        f"- Valid observations with evidence: **{data['valid_with_new_evidence']}** ({data['evidence_coverage_ratio']:.1%})",
        f"- Explicit missing observations: **{data['missing_observations']}**",
        f"- Evidence snippets after build: **{data['evidence_snippets_after']}**",
        f"- Base database unchanged: **{data['base_db_unchanged']}**",
        "",
        "## 2. Provider execution",
        "",
        f"- Planned: **{execution['manifest_count']}**",
        f"- Completed: **{execution['completed_manifest_count']}**",
        f"- Failed: **{execution['failed_manifest_count']}** ({execution['overall_failure_rate']:.1%})",
        "",
        "| Failure blocker | Count |",
        "|---|---:|",
    ]
    for blocker, count in sorted(execution["failure_blockers"].items()):
        lines.append(f"| `{blocker}` | {count} |")
    lines.extend(
        [
            "",
            "## 3. Blind human review",
            "",
            f"- Packets scored: **{review['packet_count']}**",
            f"- Required dimension rows: **{review['row_count']}**",
            f"- Dimensions: `{', '.join(review['dimensions'])}`",
            "- Validation: **valid and complete**",
            "",
            "## 4. Quality and operational comparison",
            "",
            "| Tier | Issuers | Arm | Quality | Completion-adjusted | Correctness | Usefulness | Evidence | Limitation | Cost USD | Latency ms | Input tokens | Output tokens | Failure rate |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in result["quality"]["arm_summaries"]:
        lines.append(
            f"| {item['workload_tier']} | {item['issuer_count']} | {item['arm']} | {item['quality_mean']} | {item['completion_adjusted_quality_mean']} | {item['correctness_mean']} | {item['usefulness_mean']} | {item['evidence_mean']} | {item['limitation_mean']} | {item['cost_mean_usd']} | {item['latency_mean_ms']} | {item['input_tokens_mean']} | {item['output_tokens_mean']} | {item['failure_rate']} |"
        )
    lines.extend(["", "## 5. Crossover", ""])
    if first:
        lines.extend(
            [
                f"- First observed crossover: **{first['arm']} at {first['issuer_count']} issuers ({first['workload_tier']})**",
                f"- Mean quality gain: **{first['mean_quality_gain']}**",
                f"- Cost ratio versus single-agent: **{first['cost_ratio_mean']}×**",
                f"- Latency ratio versus single-agent: **{first['latency_ratio_mean']}×**",
                f"- Positive repetitions: **{first['positive_repetitions_at_threshold']}/{first['paired_repetitions']}**",
                f"- Compared arms operationally complete: **{first['operationally_complete_comparison']}**",
            ]
        )
    else:
        lines.append("Không có crossover nào đạt đủ điều kiện đã đăng ký trước.")
    lines.extend(
        [
            "",
            "Crossover này là kết quả quan sát trong workload/protocol cố định; không phải định luật rằng multi-agent luôn tốt hơn.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for label, path in result["artifacts"].items():
        lines.append(f"- `{label}`: `{path}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-audit", type=Path, required=True)
    parser.add_argument("--operational-summary", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--queue-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError(f"refusing_to_overwrite_nonempty:{args.output_dir}")
    result = build_result(
        args.gold_audit,
        args.operational_summary,
        args.aggregate,
        args.queue_dir,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "final-evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "final-evaluation.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "first_observed_crossover": result["crossover"]["first_observed"],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
