"""Render and validate analysis-report-v2 for every provider manifest in a run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.analysis_report import build_analysis_report  # noqa: E402
from thesis_data.analysis_report_validation import validate_analysis_report  # noqa: E402
from thesis_data.report_view import load_report_view  # noqa: E402

from render_analysis_report_v2 import render_html, render_markdown  # noqa: E402


def _manifest_paths(run_dir: Path) -> list[Path]:
    return sorted(
        path for path in run_dir.glob("*.json") if path.name != "failures.json"
    )


def render_batch(
    run_dir: Path, db_path: Path, output_dir: Path, questions_path: Path | None = None
) -> dict:
    if not run_dir.exists():
        raise FileNotFoundError(run_dir)
    manifests = _manifest_paths(run_dir)
    if not manifests:
        raise RuntimeError(f"no_provider_manifests:{run_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    question_map = {}
    if questions_path is not None:
        questions = json.loads(questions_path.read_text(encoding="utf-8"))
        question_map = {item["id"]: item for item in questions.get("questions", [])}
    rows: list[dict] = []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("failure_status") and not manifest.get("final_payload"):
            question = question_map.get(manifest.get("question_id"), {})
            workload = question.get("workload") or {}
            rows.append(
                {
                    "manifest": str(manifest_path),
                    "report_dir": None,
                    "arm": manifest.get("arm"),
                    "question_id": manifest.get("question_id"),
                    "workload_tier": manifest.get("workload_tier") or workload.get("tier"),
                    "issuer_count": len(workload.get("issuers", [])),
                    "contract_version": None,
                    "claim_count": 0,
                    "valid_cells": None,
                    "cells_with_stored_evidence": None,
                    "status": "failed",
                    "failure_status": manifest.get("failure_status"),
                    "failure_blockers": manifest.get("failure_blockers", []),
                    "claim_origin": None,
                    "quality_review_eligible": False,
                    "cost_estimate_usd": manifest.get("total_cost_estimate"),
                    "wall_clock_latency_ms": manifest.get("wall_clock_latency_ms"),
                    "input_tokens": manifest.get("total_input_tokens"),
                    "output_tokens": manifest.get("total_output_tokens"),
                }
            )
            continue
        report = build_analysis_report(load_report_view(manifest_path, db_path))
        validate_analysis_report(report)
        item_dir = output_dir / manifest_path.stem
        item_dir.mkdir(parents=True, exist_ok=True)
        existing_json = item_dir / "analysis-report.json"
        if existing_json.exists():
            existing_report = json.loads(existing_json.read_text(encoding="utf-8"))
            validate_analysis_report(existing_report)
            if existing_report.get("run", {}).get("job_id") != report.get("run", {}).get("job_id"):
                raise RuntimeError(f"existing_report_identity_mismatch:{existing_json}")
        else:
            existing_json.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (item_dir / "analysis-report.md").write_text(
                render_markdown(report), encoding="utf-8"
            )
            (item_dir / "analysis-report.html").write_text(
                render_html(report), encoding="utf-8"
            )
        rows.append(
            {
                "manifest": str(manifest_path),
                "report_dir": str(item_dir),
                "arm": report["run"].get("arm"),
                "question_id": report["run"].get("question_id"),
                "workload_tier": manifest.get("workload_tier"),
                "issuer_count": len(manifest.get("issuers") or manifest.get("final_payload", {}).get("issuers", [])),
                "contract_version": report["contract_version"],
                "claim_count": len(report["claims"]),
                "valid_cells": report["data_quality"]["valid_cells"],
                "cells_with_stored_evidence": report["data_quality"]["cells_with_stored_evidence"],
                "status": report["run"].get("status"),
                "failure_status": manifest.get("failure_status"),
                "failure_blockers": manifest.get("failure_blockers", []),
                "claim_origin": report["data_quality"].get("claim_origin"),
                "quality_review_eligible": (
                    manifest.get("failure_status") is None
                    and report["data_quality"].get("claim_origin") == "model"
                ),
                "cost_estimate_usd": report["run"].get("telemetry", {}).get("cost_estimate_usd"),
                "wall_clock_latency_ms": report["run"].get("telemetry", {}).get("wall_clock_latency_ms"),
                "input_tokens": report["run"].get("telemetry", {}).get("input_tokens"),
                "output_tokens": report["run"].get("telemetry", {}).get("output_tokens"),
            }
        )
    summary = {
        "run_dir": str(run_dir),
        "db": str(db_path),
        "report_contract_version": "analysis-report-v2",
        "manifest_count": len(rows),
        "rendered_report_count": sum(item["report_dir"] is not None for item in rows),
        "quality_review_eligible_count": sum(item["quality_review_eligible"] for item in rows),
        "failed_manifest_count": sum(item["failure_status"] is not None for item in rows),
        "reports": rows,
    }
    (output_dir / "batch-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Analysis Report v2 batch",
        "",
        f"- Provider manifests: **{len(rows)}**",
        f"- Rendered reports: **{summary['rendered_report_count']}**",
        f"- Quality-review eligible model reports: **{summary['quality_review_eligible_count']}**",
        f"- Failed provider manifests: **{summary['failed_manifest_count']}**",
        f"- Contract: `analysis-report-v2`",
        "",
        "Every completed manifest has a JSON, Markdown and HTML report.",
        "Failed manifests remain explicit failure records and are excluded from semantic quality review.",
        "The report renderer reads the selected Gold snapshot and does not mutate the run manifest.",
        "",
    ]
    (output_dir / "batch-summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=None)
    args = parser.parse_args()
    summary = render_batch(args.run_dir, args.db, args.output_dir, args.questions)
    print(json.dumps({k: summary[k] for k in ("manifest_count", "rendered_report_count", "quality_review_eligible_count", "failed_manifest_count", "report_contract_version")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
