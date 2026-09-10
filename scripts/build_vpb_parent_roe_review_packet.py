"""Build a fresh blind review packet for VPB parent-attributable-equity ROE."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import build_reviewer_copy_from_rows, write_reviewer_copy  # noqa: E402


REGISTER_FIELDS = (
    "target_id", "ticker", "sector", "metric", "period",
    "candidate_observation_ids", "candidate_values", "candidate_variants",
    "candidate_source_ids", "candidate_unit", "candidate_period_basis",
    "candidate_source_locator", "candidate_status", "required_convention",
    "review_status",
)

NAVIGATION_FIELDS = (
    "target_id", "ticker", "sector", "metric", "period", "navigation_status",
    "source_id", "source_type", "source_tier", "publisher", "source_url",
    "local_path", "source_quality_status", "source_locator", "source_document",
    "page_numbers", "review_instruction", "required_convention",
)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != 4:
        raise ValueError("expected four VPB parent-equity ROE candidates")
    return rows


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_packet(candidate_jsonl: Path, candidate_db: Path, output_dir: Path) -> dict[str, object]:
    candidates = _read_jsonl(candidate_jsonl)
    source_ids = {str(row["source_id"]) for row in candidates}
    connection = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    try:
        source_rows = {
            row[0]: row
            for row in connection.execute(
                "SELECT source_id,source_type,source_tier,source_url,local_path,publisher,quality_status FROM source_records"
            )
        }
    finally:
        connection.close()
    if not source_ids.issubset(source_rows):
        raise ValueError(f"candidate sources missing from DB: {sorted(source_ids - set(source_rows))}")

    output_dir.mkdir(parents=True, exist_ok=True)
    register_rows = []
    navigation_rows = []
    for candidate in sorted(candidates, key=lambda row: str(row["observation_id"])):
        target_id = f"{candidate['ticker']}:{candidate['period']}:{candidate['metric']}"
        register_rows.append({
            "target_id": target_id,
            "ticker": str(candidate["ticker"]),
            "sector": str(candidate["sector"]),
            "metric": str(candidate["metric"]),
            "period": str(candidate["period"]),
            "candidate_observation_ids": json.dumps([candidate["observation_id"]], ensure_ascii=False),
            "candidate_values": json.dumps([candidate["value"]], ensure_ascii=False),
            "candidate_variants": json.dumps([candidate["variant"]], ensure_ascii=False),
            "candidate_source_ids": json.dumps([candidate["source_id"]], ensure_ascii=False),
            "candidate_unit": str(candidate["unit"]),
            "candidate_period_basis": str(candidate["period_basis"]),
            "candidate_source_locator": str(candidate["source_locator"]),
            "candidate_status": str(candidate["quality_status"]),
            "required_convention": "parent_attributable_equity",
            "review_status": "fresh_review_required",
        })
        source = source_rows[str(candidate["source_id"])]
        navigation_rows.append({
            "target_id": target_id,
            "ticker": "VPB",
            "sector": "bank",
            "metric": "bank.roe",
            "period": str(candidate["period"]),
            "navigation_status": "source_route_available",
            "source_id": str(source[0]),
            "source_type": str(source[1]),
            "source_tier": str(source[2]),
            "publisher": str(source[5]),
            "source_url": str(source[3]),
            "local_path": str(source[4]),
            "source_quality_status": str(source[6]),
            "source_locator": str(candidate["source_locator"]),
            "source_document": Path(str(source[4])).name,
            "page_numbers": "6,8",
            "review_instruction": (
                "Recompute TTM ROE from the official consolidated filing using parent-attributable profit "
                "and average parent-attributable equity = total consolidated equity - non-controlling interest. "
                "For Q1-Q3 use prior_fy - prior_ytd + current_ytd; for Q4 use FY2024. "
                "Record accepted/missing/conflicting/invalid with full provenance."
            ),
            "required_convention": "parent_attributable_equity",
        })

    _write_csv(output_dir / "VPB_parent_roe_register-v1.csv", REGISTER_FIELDS, register_rows)
    _write_csv(output_dir / "VPB_parent_roe_source-navigation-v1.csv", NAVIGATION_FIELDS, navigation_rows)
    blind_rows = build_reviewer_copy_from_rows(register_rows)
    write_reviewer_copy(blind_rows, output_dir / "VPB_parent_roe_checker-a-blind-v1.csv")
    write_reviewer_copy(blind_rows, output_dir / "VPB_parent_roe_checker-b-blind-v1.csv")
    readme = (
        "# Fresh VPB ROE review packet\n\n"
        "Status: `candidate_pending_fresh_review`\n\n"
        "This packet covers four VPB 2024 ROE cells under the parent-attributable-equity convention. "
        "The blind checker files contain only target identity; candidate values are kept in the internal "
        "register and must not be copied into a review result. Two independent reviewers must inspect "
        "the official PDFs and recompute the values. This packet does not create or modify Gold.\n"
    )
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "packet_id": "VPB-parent-roe-review-v1",
        "status": "candidate_pending_fresh_review",
        "convention": "parent_attributable_equity",
        "target_cell_count": 4,
        "candidate_values_in_blind_copies": False,
        "reviewer_count": 2,
    }
    (output_dir / "VPB_parent_roe_manifest-v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("candidate_db", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_packet(args.candidate_jsonl, args.candidate_db, args.output_dir), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
