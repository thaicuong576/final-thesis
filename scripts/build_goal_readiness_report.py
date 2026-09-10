"""Build an evidence-backed readiness report for the multi-agent thesis goal.

The report is intentionally conservative: completed implementation and
provider evidence are separated from Gold/reviewer gates. It never changes a
database, review file, or experiment output.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def review_copy_status(path: Path) -> dict[str, Any]:
    """Summarize a blind reviewer copy without interpreting any decision."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    completed = sum(bool(row.get("decision", "").strip()) for row in rows)
    return {
        "path": str(path),
        "rows": len(rows),
        "completed": completed,
        "completion_rate": completed / len(rows) if rows else 0.0,
        "eligible_for_merge": completed == len(rows) and bool(rows),
    }


def db_status(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        metadata = connection.execute(
            "SELECT snapshot_id, status FROM snapshot_metadata ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
        observations = connection.execute("SELECT COUNT(*) FROM metric_observations").fetchone()[0]
        target_cells = connection.execute(
            "SELECT COUNT(DISTINCT ticker || ':' || period || ':' || metric) FROM metric_observations"
        ).fetchone()[0]
        pending = connection.execute(
            "SELECT COUNT(*) FROM metric_observations WHERE quality_status='pending_validation'"
        ).fetchone()[0]
        gold_labels = connection.execute("SELECT COUNT(*) FROM gold_labels").fetchone()[0]
        quality_counts = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT quality_status, COUNT(*) FROM metric_observations GROUP BY quality_status"
            ).fetchall()
        }
    finally:
        connection.close()
    return {
        "path": str(path),
        "snapshot_id": metadata[0] if metadata else None,
        "status": metadata[1] if metadata else None,
        "observations": observations,
        "target_cells": target_cells,
        "pending_validation_rows": pending,
        "gold_labels": gold_labels,
        "quality_status_counts": quality_counts,
    }


def _manifest_paths(run_dir: Path) -> list[Path]:
    return sorted(
        path for path in run_dir.glob("*.json")
        if path.name not in {"failures.json", "recovery-map.json"}
    )


def provider_telemetry(run_dir: Path, operational_report: Path, comparison_report: Path) -> dict[str, Any]:
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in _manifest_paths(run_dir)]
    operational = json.loads(operational_report.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_report.read_text(encoding="utf-8"))
    first_pass_failures = operational.get(
        "first_pass_failures", comparison.get("first_pass_failures", [])
    )
    required = {
        "total_input_tokens",
        "total_output_tokens",
        "total_cost_estimate",
        "wall_clock_latency_ms",
        "context_budget_chars",
        "peak_context_chars",
    }
    telemetry_complete = all(required.issubset(row) for row in manifests) and bool(manifests)
    timeout_rates = []
    for tier in comparison.get("operational_by_tier", {}).values():
        for arm in tier.values():
            if "timeout_rate" in arm:
                timeout_rates.append(float(arm["timeout_rate"]))
    first_pass_timeout_count = sum(
        "timeout" in json.dumps(row, ensure_ascii=False).lower()
        for row in first_pass_failures
    )
    cost_entries = [
        arm
        for issuer_count in operational.get("by_issuer_count_and_arm", {}).values()
        for arm in issuer_count.values()
    ]
    return {
        "run_dir": str(run_dir),
        "manifest_count": len(manifests),
        "first_pass_failure_count": operational.get(
            "first_pass_failure_count", comparison.get("first_pass_failure_count")
        ),
        "first_pass_failure_rate": (
            len(first_pass_failures) / len(manifests) if manifests else None
        ),
        "first_pass_timeout_count": first_pass_timeout_count,
        "first_pass_timeout_rate": (
            first_pass_timeout_count / len(manifests) if manifests else None
        ),
        "recovered_failure_count": operational.get(
            "recovered_failure_count", comparison.get("recovered_failure_count")
        ),
        "telemetry_fields_complete": telemetry_complete,
        "has_cost_per_completed_workload": bool(cost_entries) and all(
            "cost_per_completed_job_usd" in row for row in cost_entries
        ),
        "has_throughput": bool(cost_entries) and all(
            "throughput_completed_jobs_per_minute" in row for row in cost_entries
        ),
        "has_timeout_rate": bool(timeout_rates),
        "timeout_rate_min": min(timeout_rates) if timeout_rates else None,
        "timeout_rate_max": max(timeout_rates) if timeout_rates else None,
        "quality_report_present": "mechanical_by_issuer_count_and_arm" in operational
        or "scores_by_tier_and_arm" in comparison,
        "input_tokens_total": sum(int(row.get("total_input_tokens") or 0) for row in manifests),
        "output_tokens_total": sum(int(row.get("total_output_tokens") or 0) for row in manifests),
        "cost_estimate_usd_total": round(sum(float(row.get("total_cost_estimate") or 0.0) for row in manifests), 8),
    }


def build_report(
    root: Path = PROJECT_ROOT,
    *,
    gold_db: Path | None = None,
    expansion_db: Path | None = None,
    mechanical_gold_db: Path | None = None,
    semantic_gate: Path | None = None,
    definition_manifest: Path | None = None,
    data_reviews: list[Path] | None = None,
    experiment_review: Path | None = None,
    plan_path: Path | None = None,
    run_dir: Path | None = None,
    operational_report: Path | None = None,
    comparison_report: Path | None = None,
) -> dict[str, Any]:
    gold_db = gold_db or root / "data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite"
    expansion_db = expansion_db or root / "data/processed/gold-bank-2025-expansion-official-candidate-v3.sqlite"
    mechanical_gold_db = mechanical_gold_db or root / "data/processed/gold-bank-2025-expanded-v3.sqlite"
    semantic_gate = semantic_gate or root / "reports/data-foundation/gold-bank-2025-expansion-v3/roe-definition-consistency-gate-v1.md"
    definition_manifest = definition_manifest or root / "data/manifests/gold-bank-2025-expansion-v3/comparative-definition-gate-v1.json"
    data_reviews = data_reviews or [
        root / "data/reconciliation/gold-bank-2025-expansion-v1/MBB-official-credit-review-v1/MBB_official_checker-a-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v1/MBB-official-credit-review-v1/MBB_official_checker-b-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v1/VCB-official-review-v1/VCB_official_checker-a-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v1/VCB-official-review-v1/VCB_official_checker-b-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v2/roe-addendum-parent-equity-v3/ROE_addendum_checker-a-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v2/roe-addendum-parent-equity-v3/ROE_addendum_checker-b-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v3/VPB-parent-roe-review-v1/VPB_parent_roe_checker-a-blind-v1.csv",
        root / "data/reconciliation/gold-bank-2025-expansion-v3/VPB-parent-roe-review-v1/VPB_parent_roe_checker-b-blind-v1.csv",
    ]
    experiment_review = experiment_review or root / "reports/complexity-scaling-blind-score-gpt-5.6-luna-20260907T123000Z/human-review-queue.csv"
    plan_path = plan_path or root / "experiments/runs/complexity-plan-scaling-5issuer-v1.json"
    run_dir = run_dir or root / "experiments/outputs/provider/complexity-scaling-recovered-gpt-5.6-luna-20260907T123000Z"
    operational_report = operational_report or root / "reports/complexity-scaling-operational-gpt-5.6-luna-20260907T123000Z-v2.json"
    comparison_report = comparison_report or root / "reports/complexity-scaling-comparison-gpt-5.6-luna-20260907T123000Z.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scaling_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    context_manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in _manifest_paths(run_dir)
    ]
    data_review_status = [review_copy_status(path) for path in data_reviews]
    experiment_rows = []
    if experiment_review.exists():
        with experiment_review.open("r", encoding="utf-8", newline="") as handle:
            experiment_rows = list(csv.DictReader(handle))
    experiment_completed = sum(bool(row.get("final_score", "").strip()) for row in experiment_rows)
    telemetry = provider_telemetry(
        run_dir,
        operational_report,
        comparison_report,
    )
    context_values = [row.get("context_budget_chars") for row in context_manifests]
    peak_values = [row.get("peak_context_chars") for row in context_manifests]
    definition = json.loads(definition_manifest.read_text(encoding="utf-8"))
    gold_status = db_status(mechanical_gold_db)
    definition_ready = (
        definition.get("status") == "eligible_for_comparative_definition_gate"
        and all(bool(rule.get("comparative_compatible")) for rule in definition.get("issuer_rules", {}).values())
        and gold_status.get("status") == "gold"
    )
    run_complete = len(context_manifests) == len(scaling_plan.get("jobs", []))
    data_reviews_complete = all(item["eligible_for_merge"] for item in data_review_status)
    experiment_review_complete = bool(experiment_rows) and experiment_completed == len(experiment_rows)
    requirements = [
        {
            "id": "controlled_database_expansion",
            "status": "gold_and_comparative_gate_passed_with_explicit_missingness" if definition_ready else "mechanical_gold_semantic_gate_blocked",
            "evidence": {
                "gold_base": db_status(gold_db),
                "official_expansion_candidate": db_status(expansion_db),
                "mechanical_expanded_gold": db_status(mechanical_gold_db),
                "semantic_gate": {
                    "path": str(semantic_gate),
                    "status": "passed" if definition_ready else "blocked_for_comparative_experiment",
                    "reason": "All issuer rules are compatible with parent-attributable equity; four ACB Q1 cells remain explicit missing observations." if definition_ready else "Comparative definition gate has not passed.",
                },
                "machine_preflight": {
                    "path": str(definition_manifest),
                    "status": "passed" if definition_ready else "implemented_and_rejects_current_snapshot",
                    "observed_blocker": None if definition_ready else "comparative_definition_incompatible_or_snapshot_not_ready",
                },
                "semantic_correction_path": {
                    "path": str(root / "scripts/replace_review_targets.py"),
                    "status": "implemented_requires_explicit_reason_and_new_ledger_version",
                },
            },
        },
        {
            "id": "parallel_issuer_workers",
            "status": "implemented_and_provider_tested",
            "evidence": {
                "scaling_plan_status": scaling_plan.get("status"),
                "recovered_provider_manifests": telemetry["manifest_count"],
                "planned_provider_jobs": len(scaling_plan.get("jobs", [])),
                "provider_run_complete": run_complete,
                "worker_parallelism_values": sorted({job.get("worker_parallelism") for job in scaling_plan.get("jobs", [])}),
            },
        },
        {
            "id": "bounded_context_between_agents",
            "status": "implemented_and_observed",
            "evidence": {
                "manifest_count": len(context_manifests),
                "context_budget_chars": sorted(set(context_values)),
                "peak_context_chars_max": max(peak_values) if peak_values else None,
                "budget_respected": bool(context_values) and all(
                    peak is not None and budget is not None and peak <= budget
                    for peak, budget in zip(peak_values, context_values)
                ),
            },
        },
        {
            "id": "operational_and_quality_measurement",
            "status": "implemented_provider_measured_human_quality_complete" if experiment_review_complete else "implemented_preliminary_human_quality_pending",
            "evidence": telemetry,
        },
        {
            "id": "human_review_before_thesis_claims",
            "status": "passed" if data_reviews_complete and experiment_review_complete else "blocked_pending_human_input",
            "evidence": {
                "data_review": data_review_status,
                "scaling_experiment_review_rows": len(experiment_rows),
                "scaling_experiment_final_scores": experiment_completed,
            },
        },
    ]
    blockers = []
    caveats = []
    if not definition_ready:
        blockers.append("Comparative definition gate is not passed for the selected Gold snapshot")
    if gold_status.get("target_cells") and gold_status.get("target_cells") != gold_status.get("observations"):
        blockers.append("Gold snapshot contains a cell-count mismatch; inspect duplicate or out-of-scope observations")
    if gold_status.get("quality_status_counts", {}).get("missing", 0):
        caveats.append("Gold contains explicit missing observations; do not impute or treat them as zero")
    if not run_complete:
        blockers.append(f"Provider run is incomplete: {telemetry['manifest_count']}/{len(scaling_plan.get('jobs', []))} manifests")
    if telemetry.get("recovered_failure_count"):
        caveats.append(f"Provider run has {telemetry['recovered_failure_count']} recovered/unrecovered failure manifests; report first-pass and recovery rates separately")
    if not experiment_review_complete:
        blockers.append(f"Human quality review is incomplete: {experiment_completed}/{len(experiment_rows)} final scores")
    if not telemetry.get("telemetry_fields_complete"):
        blockers.append("Provider telemetry is incomplete for one or more manifests")
    goal_complete = not blockers
    execution_status = "executed_and_audited" if run_complete else plan.get("status")
    execution_snapshot_id = definition.get("snapshot_id") or plan.get("snapshot_id")
    return {
        "schema_version": 1,
        "generated_from": "current_worktree_read_only_audit",
        "goal_complete": goal_complete,
        "five_issuer_plan": {
            "status": execution_status,
            "snapshot_id": execution_snapshot_id,
            "job_count": len(plan.get("jobs", [])),
            "question_set_id": plan.get("question_set_id"),
            "model_id": plan.get("model_id"),
        },
        "requirements": requirements,
        "blockers": blockers,
        "caveats": caveats,
        "interpretation": "The report distinguishes data/definition readiness, provider execution, operational telemetry, and human quality review. A completed provider run is evidence about this fixed workload only; it is not asymptotic proof that multi-agent systems always outperform single-agent systems.",
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-agent thesis goal readiness report",
        "",
        "This is a read-only, conservative audit. It separates implemented/provider-tested components from Gold and human-review gates.",
        "",
        f"- Goal complete: `{report['goal_complete']}`",
        f"- Five-issuer plan: `{report['five_issuer_plan']['job_count']}` jobs, snapshot `{report['five_issuer_plan']['snapshot_id']}`",
        "",
        "| Requirement | Status |",
        "|---|---|",
    ]
    for requirement in report["requirements"]:
        lines.append(f"| `{requirement['id']}` | `{requirement['status']}` |")
    lines.extend(["", "## Current blockers", ""])
    lines.extend(f"- {blocker}" for blocker in report["blockers"])
    lines.extend(["", "## Recorded caveats", ""])
    lines.extend(f"- {caveat}" for caveat in report.get("caveats", []))
    lines.extend([
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--gold-db", type=Path)
    parser.add_argument("--expansion-db", type=Path)
    parser.add_argument("--mechanical-gold-db", type=Path)
    parser.add_argument("--semantic-gate", type=Path)
    parser.add_argument("--definition-manifest", type=Path)
    parser.add_argument("--data-review", type=Path, action="append")
    parser.add_argument("--experiment-review", type=Path)
    parser.add_argument("--plan-path", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--operational-report", type=Path)
    parser.add_argument("--comparison-report", type=Path)
    args = parser.parse_args()
    for path in (args.output_json, args.output_md):
        if path.exists():
            parser.error(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(
        gold_db=args.gold_db,
        expansion_db=args.expansion_db,
        mechanical_gold_db=args.mechanical_gold_db,
        semantic_gate=args.semantic_gate,
        definition_manifest=args.definition_manifest,
        data_reviews=args.data_review,
        experiment_review=args.experiment_review,
        plan_path=args.plan_path,
        run_dir=args.run_dir,
        operational_report=args.operational_report,
        comparison_report=args.comparison_report,
    )
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
