"""Build an independent, blind review packet for MBB official candidates.

The candidate JSONL contains four ROA rows and two ROE variants per quarter.
The review target is one cell per metric and quarter; candidate alternatives are
kept in the internal register so a later accepted review can map to exactly one
observation without exposing the alternatives in the blind checker copies.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.build_review_ledger import (  # noqa: E402
    REVIEW_LEDGER_FIELDS,
    build_reviewer_copy_from_rows,
    write_reviewer_copy,
)


REGISTER_FIELDS = (
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
    "reviewer_decision",
    "checker_id",
    "review_notes",
)

NAVIGATION_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "navigation_status",
    "source_id",
    "source_type",
    "source_tier",
    "publisher",
    "source_url",
    "local_path",
    "source_quality_status",
    "source_locator",
    "source_document",
    "page_numbers",
    "review_instruction",
)

_PDF_PAGE_RE = re.compile(r"pdf_pages:([^;]+)")


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
            rows.append(row)
    if not rows:
        raise ValueError("candidate JSONL is empty")
    return rows


def _load_source_manifest(path: Path) -> dict[str, dict[str, Any]]:
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


def _target_id(row: dict[str, Any]) -> str:
    return f"{row['ticker']}:{row['period']}:{row['metric']}"


def _page_numbers(locator: str) -> str:
    match = _PDF_PAGE_RE.search(locator)
    if not match:
        return ""
    return match.group(1).strip()


def build_register(candidate_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in candidate_rows:
        required = ("observation_id", "ticker", "sector", "metric", "period", "value", "unit", "period_basis", "source_id", "source_locator", "quality_status")
        missing = [field for field in required if field not in row]
        if missing:
            raise ValueError(f"candidate row is missing fields: {missing}")
        grouped.setdefault(_target_id(row), []).append(row)

    output: list[dict[str, str]] = []
    for target_id in sorted(grouped):
        alternatives = sorted(grouped[target_id], key=lambda row: row["observation_id"])
        first = alternatives[0]
        if any(row["ticker"] != first["ticker"] or row["sector"] != first["sector"] or row["metric"] != first["metric"] or row["period"] != first["period"] for row in alternatives):
            raise ValueError(f"mixed target identity for {target_id}")
        if len({row["unit"] for row in alternatives}) != 1 or len({row["period_basis"] for row in alternatives}) != 1:
            raise ValueError(f"candidate alternatives disagree on unit or period basis: {target_id}")
        if any(row["quality_status"] != "pending_validation" for row in alternatives):
            raise ValueError(f"candidate target is not fully pending_validation: {target_id}")
        output.append({
            "target_id": target_id,
            "ticker": str(first["ticker"]),
            "sector": str(first["sector"]),
            "metric": str(first["metric"]),
            "period": str(first["period"]),
            "candidate_observation_ids": json.dumps([row["observation_id"] for row in alternatives], ensure_ascii=False),
            "candidate_values": json.dumps([row["value"] for row in alternatives], ensure_ascii=False),
            "candidate_variants": json.dumps([row.get("variant") for row in alternatives], ensure_ascii=False),
            "candidate_source_ids": json.dumps(sorted({row["source_id"] for row in alternatives}), ensure_ascii=False),
            "candidate_unit": str(first["unit"]),
            "candidate_period_basis": str(first["period_basis"]),
            "candidate_source_locator": str(first["source_locator"]),
            "candidate_status": "pending_validation",
            "reviewer_decision": "",
            "checker_id": "",
            "review_notes": "",
        })
    return output


def build_navigation(register_rows: list[dict[str, str]], sources: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for target in register_rows:
        source_ids = json.loads(target["candidate_source_ids"])
        for source_id in source_ids:
            if source_id not in sources:
                raise ValueError(f"candidate source is absent from manifest: {source_id}")
            source = sources[source_id]
            local_path = PROJECT_ROOT / Path(str(source["local_path"]))
            if not local_path.exists():
                raise FileNotFoundError(local_path)
            rows.append({
                "target_id": target["target_id"],
                "ticker": target["ticker"],
                "sector": target["sector"],
                "metric": target["metric"],
                "period": target["period"],
                "navigation_status": "source_route_available",
                "source_id": source_id,
                "source_type": str(source.get("source_type", "")),
                "source_tier": str(source.get("source_tier", "")),
                "publisher": str(source.get("publisher", "")),
                "source_url": str(source.get("url", "")),
                "local_path": str(source["local_path"]),
                "source_quality_status": str(source.get("quality_status", "")),
                "source_locator": target["candidate_source_locator"],
                "source_document": str(source.get("filename", "")),
                "page_numbers": _page_numbers(target["candidate_source_locator"]),
                "review_instruction": "Independently transcribe inputs, recompute the metric, and record accepted/missing/conflicting/invalid with provenance.",
            })
    return rows


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_packet(
    candidate_path: Path,
    source_manifest_path: Path,
    output_dir: Path,
    *,
    packet_version: str = "v1",
) -> dict[str, Any]:
    candidates = _load_jsonl(candidate_path)
    sources = _load_source_manifest(source_manifest_path)
    register_rows = build_register(candidates)
    navigation_rows = build_navigation(register_rows, sources)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not packet_version.strip():
        raise ValueError("packet_version must be non-empty")
    register_path = output_dir / f"MBB_official_review-register-{packet_version}.csv"
    ledger_path = output_dir / f"MBB_official_review-ledger-template-{packet_version}.csv"
    checker_a_path = output_dir / f"MBB_official_checker-a-blind-{packet_version}.csv"
    checker_b_path = output_dir / f"MBB_official_checker-b-blind-{packet_version}.csv"
    navigation_path = output_dir / f"MBB_official_source-navigation-{packet_version}.csv"
    manifest_path = output_dir / f"MBB_official_review-manifest-{packet_version}.json"
    if any(path.exists() for path in (register_path, ledger_path, checker_a_path, checker_b_path, navigation_path, manifest_path)):
        raise FileExistsError(f"refusing to overwrite review packet under {output_dir}")

    _write_csv(register_path, REGISTER_FIELDS, register_rows)
    ledger_rows = []
    for row in register_rows:
        ledger_rows.append({field: row.get(field, "") if field in row else "" for field in REVIEW_LEDGER_FIELDS})
    _write_csv(ledger_path, REVIEW_LEDGER_FIELDS, ledger_rows)
    blind_rows = build_reviewer_copy_from_rows(register_rows)
    write_reviewer_copy(blind_rows, checker_a_path)
    write_reviewer_copy(blind_rows, checker_b_path)
    _write_csv(navigation_path, NAVIGATION_FIELDS, navigation_rows)

    manifest = {
        "schema_version": 1,
        "packet_id": f"MBB-official-review-{packet_version}",
        "status": "human_review_required",
        "candidate_input": str(candidate_path),
        "source_manifest": str(source_manifest_path),
        "target_cell_count": len(register_rows),
        "candidate_observation_count": len(candidates),
        "candidate_values_in_blind_copies": False,
        "checker_count": 2,
        "reviewer_files": {
            "register": str(register_path),
            "ledger_template": str(ledger_path),
            "checker_a": str(checker_a_path),
            "checker_b": str(checker_b_path),
            "source_navigation": str(navigation_path),
        },
        "promotion_policy": "two independent completed reviews plus explicit adjudication for disagreement; no automatic Gold promotion",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_jsonl", type=Path)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--packet-version", default="v1")
    args = parser.parse_args()
    try:
        result = build_packet(
            args.candidate_jsonl,
            args.source_manifest,
            args.output_dir,
            packet_version=args.packet_version,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
