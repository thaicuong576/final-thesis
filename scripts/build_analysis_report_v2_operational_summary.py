"""Summarize provider telemetry and explicit failures for the v2 ladder."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _questions(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data.get("questions", [])}


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def summarize(run_dir: Path, questions_path: Path) -> dict[str, Any]:
    question_map = _questions(questions_path)
    manifests = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name == "failures.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        question = question_map.get(data.get("question_id"), {})
        workload = question.get("workload") or {}
        manifests.append(
            {
                "manifest": str(path),
                "question_id": data.get("question_id"),
                "arm": data.get("arm"),
                "workload_tier": data.get("workload_tier") or workload.get("tier"),
                "issuer_count": len(data.get("issuers") or (data.get("final_payload") or {}).get("issuers", []) or workload.get("issuers", [])),
                "failure_status": data.get("failure_status"),
                "failure_blockers": data.get("failure_blockers", []),
                "call_count": data.get("call_count", 0),
                "input_tokens": data.get("total_input_tokens", 0),
                "output_tokens": data.get("total_output_tokens", 0),
                "cost_estimate_usd": data.get("total_cost_estimate"),
                "wall_clock_latency_ms": data.get("wall_clock_latency_ms"),
            }
        )
    if len(manifests) != 75:
        raise RuntimeError(f"expected_75_manifests:{len(manifests)}")
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for item in manifests:
        groups[(item["workload_tier"], item["issuer_count"], item["arm"])].append(item)
    grouped = []
    for (tier, issuer_count, arm), items in sorted(groups.items()):
        completed = [item for item in items if item["failure_status"] is None]
        cost = [_number(item["cost_estimate_usd"]) for item in items]
        latency = [_number(item["wall_clock_latency_ms"]) for item in completed]
        grouped.append(
            {
                "workload_tier": tier,
                "issuer_count": issuer_count,
                "arm": arm,
                "planned": len(items),
                "completed": len(completed),
                "failed": len(items) - len(completed),
                "failure_rate": round((len(items) - len(completed)) / len(items), 6),
                "calls_total": sum(item["call_count"] or 0 for item in items),
                "input_tokens_total": sum(item["input_tokens"] or 0 for item in items),
                "output_tokens_total": sum(item["output_tokens"] or 0 for item in items),
                "cost_total_usd": round(sum(value or 0 for value in cost), 6),
                "cost_mean_usd_all": round(mean([value for value in cost if value is not None]), 6) if any(value is not None for value in cost) else None,
                "latency_mean_ms_completed": round(mean(latency), 3) if latency else None,
                "input_tokens_mean_completed": round(mean([item["input_tokens"] for item in completed]), 3) if completed else None,
                "output_tokens_mean_completed": round(mean([item["output_tokens"] for item in completed]), 3) if completed else None,
            }
        )
    failures = [item for item in manifests if item["failure_status"] is not None]
    blocker_counts = Counter(
        blocker
        for item in failures
        for blocker in item["failure_blockers"]
    )
    return {
        "protocol": "analysis-report-v2-operational-summary-v1",
        "manifest_count": len(manifests),
        "completed_manifest_count": len(manifests) - len(failures),
        "failed_manifest_count": len(failures),
        "overall_failure_rate": round(len(failures) / len(manifests), 6),
        "groups": grouped,
        "failure_blockers": dict(blocker_counts),
        "failures": failures,
        "quality_scoring_status": "semantic_blind_human_review_pending",
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Analysis Report v2 — operational summary",
        "",
        f"- Provider manifests: **{result['manifest_count']}**",
        f"- Completed manifests: **{result['completed_manifest_count']}**",
        f"- Failed manifests: **{result['failed_manifest_count']}**",
        f"- Overall failure rate: **{result['overall_failure_rate']:.1%}**",
        "",
        "| Tier | Issuers | Arm | Completed | Failed | Failure rate | Calls | Input tokens | Output tokens | Cost USD | Mean latency ms (completed) |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["groups"]:
        lines.append(
            f"| {item['workload_tier']} | {item['issuer_count']} | {item['arm']} | {item['completed']}/{item['planned']} | {item['failed']} | {item['failure_rate']:.1%} | {item['calls_total']} | {item['input_tokens_total']} | {item['output_tokens_total']} | {item['cost_total_usd']:.6f} | {item['latency_mean_ms_completed']} |"
        )
    lines.extend(
        [
            "",
            "## Failure blockers",
            "",
        ]
    )
    for blocker, count in sorted(result["failure_blockers"].items()):
        lines.append(f"- `{blocker}`: {count}")
    lines.extend(
        [
            "",
            "Failures remain explicit operational outcomes. They are not replaced by deterministic reference reports in the semantic quality score.",
            "Semantic blind human review is still pending; this file must not be read as a quality ranking.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("questions", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError(f"refusing_to_overwrite_nonempty:{args.output_dir}")
    result = summarize(args.run_dir, args.questions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "operational-summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "operational-summary.md").write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"manifest_count": result["manifest_count"], "completed": result["completed_manifest_count"], "failed": result["failed_manifest_count"], "overall_failure_rate": result["overall_failure_rate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
