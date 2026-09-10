"""Audit the MBB/VCB expansion candidate and write a fail-closed report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.expansion_review import audit_expansion_candidate  # noqa: E402


def _markdown(report: dict[str, object]) -> str:
    negative = report["negative_llr_coverage_values"]
    lines = [
        "# Expansion candidate quality audit",
        "",
        "This audit is read-only. It does not modify the candidate database or promote any row to Gold.",
        "",
        f"- Snapshot status: `{report['snapshot_status']}`",
        f"- Target cells: `{report['represented_target_cells']}/{report['expected_target_cells']}` represented",
        f"- Candidate observation rows (including variants): `{report.get('candidate_observation_rows', report['represented_target_cells'])}`",
        f"- Pending-validation rows: `{report['pending_validation_rows']}`",
        f"- Accelerator-source rows: `{report['accelerator_source_rows']}`",
        f"- Ready for Gold: `{report['ready_for_gold']}`",
        "",
        "## Blocking findings",
        "",
    ]
    for blocker in report["blockers"]:
        lines.append(f"- `{blocker}`")
    lines.extend([
        "",
        "The frozen definition is `coverage = loan_loss_provisions / NPL_balance × 100`.",
        "A negative candidate is not silently converted with `abs`; it requires source, sign, unit, and field-mapping reconciliation.",
        "",
        "## Negative reserve-coverage candidates",
        "",
        "| Ticker | Period | Value | Unit | Basis | Source | Tier | Source quality |",
        "|---|---|---:|---|---|---|---|---|",
    ])
    for row in negative:
        lines.append(
            f"| {row['ticker']} | {row['period']} | {row['value']} | {row['unit']} | "
            f"{row['period_basis']} | `{row['source_id']}` | {row['source_tier']} | {row['source_quality_status']} |"
        )
    lines.extend([
        "",
        "Conclusion: this expansion is useful as a review packet and a data-quality test, but it must remain outside Gold and outside thesis claims until independent primary-source reconciliation is complete.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-db", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    report = audit_expansion_candidate(args.candidate_db)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
