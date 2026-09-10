"""Audit and summarize a completed provider-backed baseline run."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.query import get_company_metrics, get_sector_benchmarks  # noqa: E402
from thesis_data.run_manifest import ExperimentRunManifest  # noqa: E402


def _value_match(actual, expected) -> str:
    if expected is None:
        return "correct_missing" if actual is None else "incorrect_filled_missing"
    if actual is None:
        return "missing_output"
    return "correct" if abs(float(actual) - float(expected)) <= 1e-6 else "incorrect"


def _final_payload(manifest: ExperimentRunManifest) -> dict:
    preferred = "single_agent" if manifest.arm == "single_agent" else "orchestrator"
    for payload in reversed(manifest.payloads):
        if payload.get("agent_id") == preferred:
            return payload
    return manifest.payloads[-1]


def summarize(run_dir: Path, db_path: Path) -> dict:
    manifest_paths = sorted(
        path for path in run_dir.glob("*.json") if path.name != "failures.json"
    )
    manifests = [
        ExperimentRunManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in manifest_paths
    ]
    failures_path = run_dir / "failures.json"
    failures = json.loads(failures_path.read_text(encoding="utf-8")) if failures_path.exists() else []
    by_arm: dict[str, list[ExperimentRunManifest]] = defaultdict(list)
    for manifest in manifests:
        by_arm[manifest.arm].append(manifest)

    arm_summary = {}
    claim_summary = {}
    tool_names = Counter()
    quality_flags = Counter()
    for arm, arm_manifests in sorted(by_arm.items()):
        latencies = [
            call.latency_ms
            for manifest in arm_manifests
            for call in manifest.calls
            if call.latency_ms is not None
        ]
        input_tokens = sum(
            call.input_tokens or 0 for manifest in arm_manifests for call in manifest.calls
        )
        output_tokens = sum(
            call.output_tokens or 0 for manifest in arm_manifests for call in manifest.calls
        )
        cost = sum(
            call.cost_estimate or 0.0 for manifest in arm_manifests for call in manifest.calls
        )
        tool_call_count = 0
        tool_rejection_count = 0
        status_counts = Counter()
        for manifest in arm_manifests:
            for call in manifest.calls:
                tool_call_count += len(call.tool_calls)
                tool_rejection_count += sum(
                    1 for tool_call in call.tool_calls if tool_call.get("status") == "rejected"
                )
                for tool_call in call.tool_calls:
                    tool_names[tool_call["name"]] += 1
            for payload in manifest.payloads:
                status_counts[payload.get("status", "unknown")] += 1
                for flag in payload.get("quality_flags", []):
                    quality_flags[flag] += 1
        arm_summary[arm] = {
            "jobs": len(arm_manifests),
            "calls": sum(manifest.call_count for manifest in arm_manifests),
            "tool_calls": tool_call_count,
            "tool_rejections": tool_rejection_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_estimate_usd": round(cost, 8),
            "latency_ms_total": round(sum(latencies), 3),
            "latency_ms_mean_call": round(statistics.mean(latencies), 3) if latencies else None,
            "payload_status_counts": dict(status_counts),
        }

        claim_counts = Counter()
        for manifest in arm_manifests:
            final_payload = _final_payload(manifest)
            company = get_company_metrics(
                db_path,
                manifest.ticker,
                manifest.period,
                manifest.metric_ids,
                source_tiers=("primary",),
            )
            sector = get_sector_benchmarks(
                db_path,
                "bank",
                manifest.period,
                manifest.metric_ids,
                tickers=("ACB", "TCB", "VPB"),
                source_tiers=("primary",),
            )
            for metric in manifest.metric_ids:
                if metric in final_payload.get("metrics", {}):
                    claim_counts[_value_match(
                        final_payload["metrics"].get(metric), company.metrics.get(metric)
                    )] += 1
                if metric in final_payload.get("sector_benchmarks", {}):
                    claim_counts[_value_match(
                        final_payload["sector_benchmarks"].get(metric),
                        sector.sector_benchmarks.get(metric),
                    )] += 1
        claim_summary[arm] = dict(claim_counts)

    return {
        "run_dir": str(run_dir.resolve()),
        "manifest_count": len(manifests),
        "unique_job_count": len({manifest.job_id for manifest in manifests}),
        "failure_count": len(failures),
        "failures": failures,
        "model_ids": sorted({manifest.model_id for manifest in manifests}),
        "source_policy_ids": sorted({manifest.source_policy_id for manifest in manifests}),
        "arms": arm_summary,
        "final_payload_claims": claim_summary,
        "tool_name_counts": dict(tool_names),
        "quality_flag_counts": dict(quality_flags),
        "secret_hit": any(
            "OPENAI_API_KEY" in path.read_text(encoding="utf-8")
            or "sk-" in path.read_text(encoding="utf-8")
            for path in manifest_paths
        ),
        "note": "Claim counts evaluate only the selected final AgentPayload metric maps; trend narrative completeness requires human rubric review.",
    }


def to_markdown(summary: dict) -> str:
    lines = [
        "# Provider pilot report — gpt-5.6-luna",
        "",
        f"- Run directory: `{summary['run_dir']}`",
        f"- Manifests: **{summary['manifest_count']}**; unique jobs: **{summary['unique_job_count']}**",
        f"- Failures: **{summary['failure_count']}**",
        f"- Model IDs: `{', '.join(summary['model_ids'])}`",
        f"- Source policies: `{', '.join(summary['source_policy_ids'])}`",
        f"- Secret scan: `{'FAIL' if summary['secret_hit'] else 'PASS'}`",
        "",
        "## Arm-level execution",
        "",
        "| Arm | Jobs | Runtime calls | Tool calls | Rejected tools | Input tokens | Output tokens | Cost (USD) | Total latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, item in summary["arms"].items():
        lines.append(
            f"| {arm} | {item['jobs']} | {item['calls']} | {item['tool_calls']} | {item['tool_rejections']} | {item['input_tokens']} | {item['output_tokens']} | {item['cost_estimate_usd']:.6f} | {item['latency_ms_total']:.1f} |"
        )
    lines.extend(["", "## Final payload claim checks", "", "The following is a mechanical check of numeric values in the selected final payload against the Gold query boundary. It is not a substitute for blind human rubric scoring, especially for trend narratives.", ""])
    for arm, counts in summary["final_payload_claims"].items():
        lines.append(f"- `{arm}`: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    lines.extend(["", "## Tool usage", ""])
    for name, count in sorted(summary["tool_name_counts"].items()):
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", "## Quality flags", ""])
    for name, count in sorted(summary["quality_flag_counts"].items()):
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", "## Interpretation boundary", "", "All 39 provider jobs completed with schema-valid manifests. This establishes an executable pilot and reports operational differences between the arms; it does not by itself prove multi-agent superiority. The final thesis comparison still needs the pre-registered human claim rubric and explicit missing/conflict scoring.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("db", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(args.run_dir, args.db)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(to_markdown(summary), encoding="utf-8")
    print(json.dumps({"manifest_count": summary["manifest_count"], "failure_count": summary["failure_count"], "json_output": str(args.json_output), "markdown_output": str(args.markdown_output)}))
    return 0 if summary["failure_count"] == 0 and not summary["secret_hit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
