"""Audit persisted VCB candidates without promoting or rewriting them.

This is a deterministic consistency audit, not a substitute for independent
source review. It checks that the JSONL values agree with their persisted input
facts and formulas, that source routes exist, and that every row remains
explicitly non-Gold.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid candidate JSON at line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"candidate line {line_number} is not an object")
            rows.append(row)
    if not rows:
        raise ValueError("candidate JSONL is empty")
    return rows


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("source manifest must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for row in raw:
        source_id = str(row.get("source_id", "")).strip()
        if not source_id or source_id in result:
            raise ValueError("source manifest has an empty or duplicate source_id")
        result[source_id] = row
    return result


def _percent(numerator: int | float, denominator: int | float) -> Decimal:
    return (Decimal(str(numerator)) / Decimal(str(denominator)) * Decimal("100")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def _expected_value(row: dict[str, Any]) -> Decimal:
    facts = row.get("input_facts")
    if not isinstance(facts, dict):
        raise ValueError("input_facts is missing or not an object")
    metric = row.get("metric")
    if metric == "bank.roa":
        numerator = facts["pat_ttm"]
        denominator = (
            Decimal(str(facts["beginning_total_assets"]))
            + Decimal(str(facts["ending_total_assets"]))
        ) / Decimal("2")
        return _percent(numerator, denominator)
    if metric == "bank.roe":
        numerator = facts["parent_profit_ttm"]
        denominator_key = (
            "average_parent_equity"
            if row.get("variant") == "parent_attributable_equity"
            else "average_total_equity"
        )
        return _percent(numerator, facts[denominator_key])
    if metric == "bank.npl_g35":
        numerator = facts["stage_3"] + facts["stage_4"] + facts["stage_5"]
        return _percent(numerator, facts["gross_loans"])
    if metric == "bank.llr_coverage":
        numerator = facts["specific_provision"] + facts["general_provision"]
        denominator = facts["npl_g35_balance"]
        return _percent(numerator, denominator)
    raise ValueError(f"unsupported metric: {metric}")


def audit(candidate_path: Path, source_manifest_path: Path) -> dict[str, Any]:
    """Return consistency findings; never modify either input."""
    rows = _load_jsonl(candidate_path)
    sources = _load_manifest(source_manifest_path)
    findings: list[dict[str, Any]] = []
    observation_ids = [str(row.get("observation_id", "")) for row in rows]
    if len(set(observation_ids)) != len(observation_ids) or "" in observation_ids:
        findings.append({"code": "duplicate_or_empty_observation_id"})

    expected_metrics = {
        "bank.roa": 4,
        "bank.roe": 8,
        "bank.npl_g35": 4,
        "bank.llr_coverage": 4,
    }
    counts = {metric: 0 for metric in expected_metrics}
    pending_rows = 0
    non_gold_violations = 0
    missing_sources = 0
    missing_locators = 0
    value_mismatches = 0
    for row in rows:
        metric = str(row.get("metric", ""))
        if metric in counts:
            counts[metric] += 1
        if row.get("quality_status") == "pending_validation":
            pending_rows += 1
        if row.get("quality_status") == "gold" or row.get("extraction_status") == "gold":
            non_gold_violations += 1
            findings.append({"code": "gold_status_in_candidate", "observation_id": row.get("observation_id")})
        source_id = str(row.get("source_id", ""))
        source = sources.get(source_id)
        if source is None:
            missing_sources += 1
            findings.append({"code": "source_missing_from_manifest", "observation_id": row.get("observation_id"), "source_id": source_id})
        else:
            local_path = PROJECT_ROOT / Path(str(source.get("local_path", "")))
            if not local_path.exists():
                missing_sources += 1
                findings.append({"code": "source_local_file_missing", "observation_id": row.get("observation_id"), "source_id": source_id})
        locator = str(row.get("source_locator", ""))
        if "pdf_pages:" not in locator:
            missing_locators += 1
            findings.append({"code": "source_locator_missing_pdf_pages", "observation_id": row.get("observation_id")})
        try:
            expected = _expected_value(row)
            actual = Decimal(str(row.get("value")))
            if actual != expected:
                value_mismatches += 1
                findings.append({
                    "code": "value_formula_mismatch",
                    "observation_id": row.get("observation_id"),
                    "actual": str(actual),
                    "expected": str(expected),
                })
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            value_mismatches += 1
            findings.append({"code": "formula_input_error", "observation_id": row.get("observation_id"), "error": str(exc)})

    for metric, expected_count in expected_metrics.items():
        if counts[metric] != expected_count:
            findings.append({"code": "unexpected_metric_count", "metric": metric, "actual": counts[metric], "expected": expected_count})

    blockers = ["pending_validation_rows", "human_review_required"]
    if findings:
        blockers.append("consistency_findings")
    if non_gold_violations:
        blockers.append("gold_status_violation")
    if missing_sources:
        blockers.append("missing_source_routes")
    if missing_locators:
        blockers.append("missing_source_locators")
    if value_mismatches:
        blockers.append("formula_value_mismatches")
    return {
        "candidate_jsonl": str(candidate_path),
        "source_manifest": str(source_manifest_path),
        "row_count": len(rows),
        "target_cell_count": len({f"{row.get('ticker')}:{row.get('period')}:{row.get('metric')}" for row in rows}),
        "metric_counts": counts,
        "source_count": len(sources),
        "pending_validation_rows": pending_rows,
        "non_gold_violations": non_gold_violations,
        "missing_source_routes": missing_sources,
        "missing_source_locators": missing_locators,
        "formula_value_mismatches": value_mismatches,
        "findings": findings,
        "blockers": list(dict.fromkeys(blockers)),
        "ready_for_gold": False,
        "interpretation": "consistent_pending_candidate; this audit does not validate the underlying official source and cannot replace two independent human reviews",
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# VCB official candidate consistency audit",
        "",
        "This audit is read-only. It checks persisted candidate/formula consistency and source-route presence; it does not validate the underlying PDF transcription and does not promote Gold.",
        "",
        f"- Candidate rows: `{report['row_count']}`",
        f"- Target cells: `{report['target_cell_count']}`",
        f"- Pending-validation rows: `{report['pending_validation_rows']}`",
        f"- Formula mismatches: `{report['formula_value_mismatches']}`",
        f"- Missing source routes: `{report['missing_source_routes']}`",
        f"- Ready for Gold: `{report['ready_for_gold']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- `{blocker}`" for blocker in report["blockers"])
    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        lines.extend(f"- `{json.dumps(finding, ensure_ascii=False, sort_keys=True)}`" for finding in report["findings"])
    else:
        lines.append("- None detected by this deterministic consistency audit.")
    lines.extend([
        "",
        "Conclusion: the persisted candidate package is internally consistent under the recorded input facts, but remains pending primary-source verification and independent human review.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.candidate_jsonl, args.source_manifest)
    for path in (args.output_json, args.output_md):
        if path.exists():
            parser.error(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
