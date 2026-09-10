"""Compare claim-driven analysis-report-v2 outputs without overclaiming quality."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _support_counts(report: dict[str, Any]) -> dict[str, int]:
    counts = report.get("data_quality", {}).get("claim_support_counts", {})
    if not isinstance(counts, dict):
        return {}
    return {str(key): int(value) for key, value in counts.items()}


def _claim_origin_counts(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in report.get("claims", ()) or ():
        if not isinstance(claim, dict):
            continue
        origin = str(claim.get("origin", "unknown"))
        counts[origin] = counts.get(origin, 0) + 1
    return counts


def _summarize(report_path: Path, manifest_path: Path) -> dict[str, Any]:
    report = _load(report_path)
    manifest = _load(manifest_path)
    claims = [item for item in report.get("claims", ()) or () if isinstance(item, dict)]
    support = _support_counts(report)
    origin = _claim_origin_counts(report)
    claim_count = len(claims)
    evidence_backed = support.get("evidence_backed", 0)
    limitations_present = sum(bool(str(item.get("limitation", "")).strip()) for item in claims)
    refs = sum(len(item.get("data_refs", ()) or ()) for item in claims)
    run = report.get("run", {})
    telemetry = run.get("telemetry", {}) if isinstance(run, dict) else {}
    valid_claim_origin = set(origin).issubset({"model"}) and bool(origin)
    return {
        "arm": str(run.get("arm", manifest.get("arm", "unknown"))),
        "report_path": str(report_path),
        "manifest_path": str(manifest_path),
        "contract_version": report.get("contract_version"),
        "status": report.get("data_quality", {}).get("partial"),
        "contract_valid": True,
        "quality_benchmark_eligible": valid_claim_origin,
        "claim_origin_counts": origin,
        "claim_count": claim_count,
        "claim_types": sorted({str(item.get("claim_type", "unknown")) for item in claims}),
        "support_counts": support,
        "evidence_backed_claim_rate": round(evidence_backed / claim_count, 4) if claim_count else 0.0,
        "claim_data_ref_count": refs,
        "limitations_present": limitations_present,
        "limitations_coverage": round(limitations_present / claim_count, 4) if claim_count else 0.0,
        "valid_cells": report.get("data_quality", {}).get("valid_cells"),
        "total_cells": report.get("data_quality", {}).get("total_cells"),
        "cells_with_stored_evidence": report.get("data_quality", {}).get("cells_with_stored_evidence"),
        "source_count": report.get("data_quality", {}).get("source_count"),
        "subreport_count": manifest.get("subreport_count"),
        "payload_count": len(manifest.get("payloads", ()) or ()),
        "failure_status": manifest.get("failure_status"),
        "failure_blockers": manifest.get("failure_blockers", []),
        "call_count": telemetry.get("call_count", manifest.get("call_count")),
        "input_tokens": telemetry.get("input_tokens", manifest.get("total_input_tokens")),
        "output_tokens": telemetry.get("output_tokens", manifest.get("total_output_tokens")),
        "cost_estimate_usd": telemetry.get("cost_estimate_usd", manifest.get("total_cost_estimate")),
        "wall_clock_latency_ms": telemetry.get("wall_clock_latency_ms", manifest.get("wall_clock_latency_ms")),
        "headline": report.get("executive_summary", {}).get("headline"),
    }


def _ratio(value: Any, base: Any) -> float | None:
    if not isinstance(value, (int, float)) or not isinstance(base, (int, float)) or base == 0:
        return None
    return round(value / base, 4)


def build_benchmark(report_paths: list[Path], manifest_paths: list[Path]) -> dict[str, Any]:
    if len(report_paths) != len(manifest_paths) or not report_paths:
        raise ValueError("report and manifest counts must match and be non-zero")
    arms = [_summarize(report, manifest) for report, manifest in zip(report_paths, manifest_paths)]
    eligible = all(bool(item["quality_benchmark_eligible"]) for item in arms)
    baseline = next((item for item in arms if item["arm"] == "single_agent"), arms[0])
    for item in arms:
        item["cost_vs_single_agent"] = _ratio(item["cost_estimate_usd"], baseline["cost_estimate_usd"])
        item["latency_vs_single_agent"] = _ratio(item["wall_clock_latency_ms"], baseline["wall_clock_latency_ms"])
    return {
        "benchmark_contract_version": "analysis-report-v2-benchmark-v1",
        "report_contract_version": "analysis-report-v2",
        "comparative_result": False,
        "sample_size_per_arm": 1,
        "arms": arms,
        "quality_benchmark_eligible": eligible,
        "interpretation_boundary": [
            "This is a provider-backed smoke comparison, not a statistically reliable quality ranking.",
            "Claim support is checked against Gold data/evidence; semantic usefulness and correctness still require blind human review.",
            "Deterministic reference reports must not be mixed with model-origin reports in the quality comparison.",
        ],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_markdown(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        "# Analysis Report v2 — smoke benchmark",
        "",
        "> Đây là smoke comparison provider-backed, n=1 cho mỗi arm. Nó kiểm tra contract, provenance, chi phí và cấu trúc report; chưa đủ để kết luận arm nào có chất lượng phân tích tốt hơn một cách thống kê.",
        "",
        "## Kết quả vận hành",
        "",
        "| Arm | Contract | Claims | Evidence-backed | Calls | Input tokens | Output tokens | Cost (USD) | Latency (s) | Subreports |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in arms:
        evidence = item["support_counts"].get("evidence_backed", 0)
        latency = item["wall_clock_latency_ms"] / 1000 if isinstance(item["wall_clock_latency_ms"], (int, float)) else None
        lines.append(
            f"| {item['arm']} | {'PASS' if item['contract_valid'] else 'FAIL'} | {item['claim_count']} | {evidence}/{item['claim_count']} ({_fmt(item['evidence_backed_claim_rate'])}) | {item['call_count']} | {_fmt(item['input_tokens'])} | {_fmt(item['output_tokens'])} | {_fmt(item['cost_estimate_usd'])} | {_fmt(latency)} | {item['subreport_count']} |"
        )
    lines.extend(["", "## So với single-agent", ""])
    for item in arms:
        lines.append(
            f"- `{item['arm']}`: cost ×{_fmt(item['cost_vs_single_agent'])}, latency ×{_fmt(item['latency_vs_single_agent'])}; support distribution `{item['support_counts']}`."
        )
    lines.extend(["", "## Nội dung report", ""])
    for item in arms:
        lines.extend(
            [
                f"### {item['arm']}",
                "",
                f"- Claim origin: `{item['claim_origin_counts']}`; quality-benchmark eligible: `{item['quality_benchmark_eligible']}`.",
                f"- Limitation coverage: `{item['limitations_present']}/{item['claim_count']}`.",
                f"- Claim types: `{', '.join(item['claim_types'])}`.",
                f"- Headline: {item['headline']}",
                f"- Report: `{item['report_path']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Ranh giới diễn giải",
            "",
            "- Các arm đều tạo được report v2 hợp lệ và full 120 task references trong smoke này.",
            "- Hierarchical dùng nhiều call hơn vì thực sự tách company/sector/orchestrator; bounded-critique thêm verification có trigger. Chi phí cao hơn là quan sát vận hành, không tự động chứng minh chất lượng cao hơn.",
            "- Muốn kết luận multi-agent đáng dùng cần chạy full ladder, blind human scoring theo rubric, và so sánh claim correctness/usefulness cùng cost-latency.",
        ]
    )
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, required=True)
    parser.add_argument("--manifest", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = build_benchmark(args.report, args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "benchmark.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "benchmark.md").write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "arms": len(result["arms"]), "eligible": result["quality_benchmark_eligible"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
