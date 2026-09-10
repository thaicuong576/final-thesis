"""Validate the analysis-report-v2 blind queue without assigning scores."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DIMENSIONS = {"correctness", "usefulness", "evidence", "limitation"}
FIELDS = ["row_number", "blind_id", "dimension", "prompt", "score", "decision_basis"]
DIMENSION_PROMPTS = {
    "correctness": "Are the material claims factually correct for the stated scope, periods and Gold data?",
    "usefulness": "Does the report help an analyst decide what matters and what to investigate next?",
    "evidence": "Can the material claims be followed to the correct source, page and evidence record?",
    "limitation": "Does the report state missingness, scope, definition and uncertainty limits precisely enough?",
}


def validate(queue_dir: Path, *, require_complete: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    packets_path = queue_dir / "blind-packets.jsonl"
    identity_path = queue_dir / "private-identity-map.json"
    queue_path = queue_dir / "human-review-queue.csv"
    packets = [
        json.loads(line)
        for line in packets_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    identities = json.loads(identity_path.read_text(encoding="utf-8"))
    with queue_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0]) if rows else []
    if fieldnames != FIELDS:
        errors.append(f"queue_columns_invalid:{fieldnames}")
    packet_ids = {packet.get("blind_id") for packet in packets}
    if packet_ids != set(identities):
        errors.append("packet_identity_map_mismatch")
    forbidden = ("single_agent", "hierarchical_no_critique", "hierarchical_bounded_critique", "gpt-5.6")
    leaked = []
    for packet in packets:
        text = json.dumps(packet, ensure_ascii=False)
        if any(term in text for term in forbidden):
            leaked.append(packet.get("blind_id"))
    if leaked:
        errors.append(f"blind_identity_leak:{','.join(str(item) for item in leaked)}")

    expected = {(blind_id, dimension) for blind_id in packet_ids for dimension in DIMENSIONS}
    seen: set[tuple[str, str]] = set()
    filled = 0
    for index, row in enumerate(rows, start=1):
        key = (row.get("blind_id", "").strip(), row.get("dimension", "").strip())
        if key in seen:
            errors.append(f"duplicate_row:{key[0]}:{key[1]}")
        seen.add(key)
        if key not in expected:
            errors.append(f"unexpected_row:{key[0]}:{key[1]}")
        if row.get("row_number", "").strip() != str(index):
            errors.append(f"row_number_mutated:{key[0]}:{key[1]}:{row.get('row_number')}:expected:{index}")
        if row.get("prompt", "") != DIMENSION_PROMPTS.get(row.get("dimension", "")):
            errors.append(f"prompt_mutated:{key[0]}:{key[1]}")
        score = row.get("score", "").strip()
        basis = row.get("decision_basis", "").strip()
        if score:
            try:
                value = int(score)
            except ValueError:
                errors.append(f"score_not_integer:{key[0]}:{key[1]}")
            else:
                if value < 0 or value > 4:
                    errors.append(f"score_out_of_range:{key[0]}:{key[1]}:{value}")
                else:
                    filled += 1
            if not basis:
                errors.append(f"decision_basis_missing:{key[0]}:{key[1]}")
        elif basis:
            errors.append(f"basis_without_score:{key[0]}:{key[1]}")
    missing = expected - seen
    if missing:
        errors.append(f"missing_rows:{len(missing)}")
    if len(rows) != len(expected):
        errors.append(f"row_count:{len(rows)}:expected:{len(expected)}")
    if require_complete and filled != len(expected):
        errors.append(f"human_review_incomplete:{filled}/{len(expected)}")
    return {
        "packet_count": len(packet_ids),
        "expected_rows": len(expected),
        "actual_rows": len(rows),
        "filled_scores": filled,
        "complete": filled == len(expected),
        "valid": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue_dir", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = validate(args.queue_dir, require_complete=args.require_complete)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
