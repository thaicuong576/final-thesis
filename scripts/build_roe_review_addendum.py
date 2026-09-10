"""Build a fresh, convention-bound ROE review packet for MBB and VCB."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    build_reviewer_copy_from_rows,
    write_reviewer_copy,
)


REVIEW_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "decision",
    "value",
    "unit",
    "period_basis",
    "source_id",
    "source_url",
    "source_locator",
    "consolidation_basis",
    "definition_match",
    "checked_at",
    "notes",
    "checker_id",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: tuple[str, ...] | list[str], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def build_packet(
    mbb_register: Path,
    mbb_navigation: Path,
    vcb_register: Path,
    vcb_navigation: Path,
    output_dir: Path,
    *,
    convention: str = "parent_attributable_equity",
) -> dict[str, object]:
    if convention not in {"parent_attributable_equity", "total_consolidated_equity"}:
        raise ValueError("unsupported ROE convention")
    mbb_rows = [row for row in _read_csv(mbb_register) if row.get("metric") == "bank.roe"]
    vcb_rows = [row for row in _read_csv(vcb_register) if row.get("metric") == "bank.roe"]
    register_rows = sorted(mbb_rows + vcb_rows, key=lambda row: row["target_id"])
    if len(register_rows) != 8 or len({row["target_id"] for row in register_rows}) != 8:
        raise ValueError("expected eight unique MBB/VCB ROE targets")

    output_dir.mkdir(parents=True, exist_ok=True)
    register_fields = (
        "target_id",
        "ticker",
        "sector",
        "metric",
        "period",
        "candidate_observation_ids",
        "candidate_values",
        "candidate_variants",
        "candidate_source_ids",
        "candidate_unit",
        "candidate_period_basis",
        "candidate_source_locator",
        "candidate_status",
        "required_convention",
        "review_status",
    )
    internal_rows = []
    for row in register_rows:
        internal_rows.append({
            field: row.get(field, "")
            for field in register_fields
        } | {
            "required_convention": convention,
            "review_status": "fresh_review_required",
        })
    _write_csv(output_dir / "ROE_addendum_register-v1.csv", register_fields, internal_rows)

    navigation = []
    wanted = {row["target_id"] for row in register_rows}
    for path in (mbb_navigation, vcb_navigation):
        navigation.extend(row for row in _read_csv(path) if row.get("target_id") in wanted)
    navigation.sort(key=lambda row: row["target_id"])
    if len(navigation) != 8:
        raise ValueError("source navigation does not cover all eight ROE targets")
    nav_fields = list(dict.fromkeys(list(navigation[0]) + ["required_convention", "review_instruction"]))
    for row in navigation:
        row["required_convention"] = convention
        row["review_instruction"] = (
            "Recompute TTM ROE from official consolidated statements using parent-attributable profit "
            f"and average {convention.replace('_', ' ')}; record accepted/missing/conflicting/invalid."
        )
    _write_csv(output_dir / "ROE_addendum_source-navigation-v1.csv", nav_fields, navigation)

    blind_rows = build_reviewer_copy_from_rows(register_rows)
    for filename in ("ROE_addendum_checker-a-blind-v1.csv", "ROE_addendum_checker-b-blind-v1.csv"):
        _write_csv(output_dir / filename, REVIEW_FIELDS, blind_rows)

    readme = (
        "# Fresh ROE review addendum\n\n"
        "Status: `proposed_convention_not_yet_promoted`\n\n"
        f"This packet covers eight ROE cells (MBB and VCB, 2024 Q1-Q4) under the proposed frozen "
        f"convention `{convention}`. It does not change the existing conflicting/missing ledger and "
        "does not create Gold.\n\n"
        "Two independent checkers must review the official PDFs again after the convention is formally "
        "confirmed. For Q1-Q3 use `prior_fy - prior_ytd + current_ytd`; for Q4 use FY2024. Use the "
        "parent-attributable profit numerator and the beginning/end average equity denominator specified "
        "by the convention.\n\n"
        "Candidate alternatives remain in the internal register only; do not copy them into a blind "
        "review without checking the official source.\n"
    )
    readme_path = output_dir / "README.md"
    if readme_path.exists():
        raise FileExistsError(f"refusing to overwrite {readme_path}")
    readme_path.write_text(readme, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "packet_id": "ROE-addendum-parent-equity-v1",
        "status": "proposed_convention_not_yet_promoted",
        "convention": convention,
        "target_cell_count": 8,
        "candidate_values_in_blind_copies": False,
        "reviewer_count": 2,
        "reviewer_files": {
            "checker_a": str(output_dir / "ROE_addendum_checker-a-blind-v1.csv"),
            "checker_b": str(output_dir / "ROE_addendum_checker-b-blind-v1.csv"),
        },
    }
    manifest_path = output_dir / "ROE_addendum_manifest-v1.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mbb-register", type=Path, required=True)
    parser.add_argument("--mbb-navigation", type=Path, required=True)
    parser.add_argument("--vcb-register", type=Path, required=True)
    parser.add_argument("--vcb-navigation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--convention", default="parent_attributable_equity")
    args = parser.parse_args()
    result = build_packet(
        args.mbb_register,
        args.mbb_navigation,
        args.vcb_register,
        args.vcb_navigation,
        args.output_dir,
        convention=args.convention,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
