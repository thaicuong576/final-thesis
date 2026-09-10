"""Build an independent, blind review packet for VCB official candidates.

The candidate JSONL contains four metrics across four quarters and two ROE
denominator variants per quarter. The packet exposes one row per target cell
to each checker while keeping candidate values and observation IDs private.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.build_mbb_official_review_packet import (  # noqa: E402
    NAVIGATION_FIELDS,
    REGISTER_FIELDS,
    build_navigation,
    build_register,
)
from scripts.build_review_ledger import (  # noqa: E402
    REVIEW_LEDGER_FIELDS,
    build_reviewer_copy_from_rows,
    write_reviewer_copy,
)


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
    """Build a new packet; never overwrite an existing review surface."""
    if not packet_version.strip():
        raise ValueError("packet_version must be non-empty")
    candidates = _load_jsonl(candidate_path)
    sources = _load_source_manifest(source_manifest_path)
    register_rows = build_register(candidates)
    navigation_rows = build_navigation(register_rows, sources)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "register": output_dir / f"VCB_official_review-register-{packet_version}.csv",
        "ledger_template": output_dir / f"VCB_official_review-ledger-template-{packet_version}.csv",
        "checker_a": output_dir / f"VCB_official_checker-a-blind-{packet_version}.csv",
        "checker_b": output_dir / f"VCB_official_checker-b-blind-{packet_version}.csv",
        "source_navigation": output_dir / f"VCB_official_source-navigation-{packet_version}.csv",
        "manifest": output_dir / f"VCB_official_review-manifest-{packet_version}.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError(f"refusing to overwrite review packet under {output_dir}")

    _write_csv(paths["register"], REGISTER_FIELDS, register_rows)
    ledger_rows = [
        {field: row.get(field, "") if field in row else "" for field in REVIEW_LEDGER_FIELDS}
        for row in register_rows
    ]
    _write_csv(paths["ledger_template"], REVIEW_LEDGER_FIELDS, ledger_rows)
    blind_rows = build_reviewer_copy_from_rows(register_rows)
    write_reviewer_copy(blind_rows, paths["checker_a"])
    write_reviewer_copy(blind_rows, paths["checker_b"])
    _write_csv(paths["source_navigation"], NAVIGATION_FIELDS, navigation_rows)

    manifest = {
        "schema_version": 1,
        "packet_id": f"VCB-official-review-{packet_version}",
        "status": "human_review_required",
        "candidate_input": str(candidate_path),
        "source_manifest": str(source_manifest_path),
        "target_cell_count": len(register_rows),
        "candidate_observation_count": len(candidates),
        "candidate_values_in_blind_copies": False,
        "checker_count": 2,
        "reviewer_files": {key: str(value) for key, value in paths.items() if key != "manifest"},
        "promotion_policy": "two independent completed reviews plus explicit adjudication for disagreement; no automatic Gold promotion",
        "restatement_warning": "Q1-Q3 TTM candidates use the Q4 2024 restated comparative as the common beginning basis; reviewers must verify this policy before acceptance.",
    }
    paths["manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
