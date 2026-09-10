#!/usr/bin/env python3
"""Validate the arm-blind scaling human-review queue without scoring it."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "row_number",
    "blind_id",
    "question_id",
    "dimension",
    "machine_score",
    "final_score",
    "decision_basis",
]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_queue(
    queue_path: Path,
    packets_path: Path,
    mechanical_path: Path,
    *,
    require_complete: bool = False,
) -> dict[str, Any]:
    """Return a conservative validation summary; never infer human scores."""

    errors: list[str] = []
    rows = list(csv.DictReader(queue_path.open(encoding="utf-8", newline="")))
    fieldnames = list(rows[0].keys()) if rows else []
    if fieldnames != REQUIRED_FIELDS:
        errors.append(f"queue_columns_invalid:{fieldnames}")

    packets = _jsonl(packets_path)
    question_by_blind = {
        packet.get("blind_id"): packet.get("question", {}).get("id", "")
        for packet in packets
        if isinstance(packet.get("blind_id"), str)
    }

    expected_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for item in _jsonl(mechanical_path):
        blind_id = item.get("blind_id")
        dimension = item.get("dimension")
        if not isinstance(blind_id, str) or not isinstance(dimension, str):
            errors.append(f"mechanical_identity_invalid:{item!r}")
            continue
        key = (blind_id, dimension)
        if key in expected_by_key:
            errors.append(f"mechanical_duplicate:{blind_id}:{dimension}")
            continue
        expected_by_key[key] = {
            "question_id": str(question_by_blind.get(blind_id, "")),
            "machine_score": str(item.get("score", "")),
        }

    seen: set[tuple[str, str]] = set()
    filled = 0
    for row in rows:
        blind_id = row.get("blind_id", "").strip()
        dimension = row.get("dimension", "").strip()
        key = (blind_id, dimension)
        if key in seen:
            errors.append(f"queue_duplicate:{blind_id}:{dimension}")
        seen.add(key)

        expected = expected_by_key.get(key)
        if expected is None:
            errors.append(f"queue_unexpected_identity:{blind_id}:{dimension}")
            continue
        if row.get("question_id", "").strip() != expected["question_id"]:
            errors.append(
                f"question_id_mismatch:{blind_id}:{row.get('question_id', '')}:{expected['question_id']}"
            )
        if row.get("machine_score", "").strip() != expected["machine_score"]:
            errors.append(
                f"machine_score_changed:{blind_id}:{dimension}:{row.get('machine_score', '')}:{expected['machine_score']}"
            )

        final_score = row.get("final_score", "").strip()
        decision_basis = row.get("decision_basis", "").strip()
        if final_score:
            if final_score not in {"0", "1"}:
                errors.append(f"final_score_invalid:{blind_id}:{dimension}:{final_score}")
            else:
                filled += 1
            if not decision_basis:
                errors.append(f"decision_basis_missing:{blind_id}:{dimension}")
        elif decision_basis:
            errors.append(f"decision_basis_without_score:{blind_id}:{dimension}")

    missing_keys = sorted(set(expected_by_key) - seen)
    if missing_keys:
        errors.append(f"queue_missing_rows:{len(missing_keys)}")
    if len(rows) != len(expected_by_key):
        errors.append(f"queue_row_count:{len(rows)}:expected:{len(expected_by_key)}")
    if require_complete and filled != len(expected_by_key):
        errors.append(f"human_review_incomplete:{filled}/{len(expected_by_key)}")

    return {
        "queue": str(queue_path),
        "expected_rows": len(expected_by_key),
        "actual_rows": len(rows),
        "final_score_filled": filled,
        "complete": filled == len(expected_by_key),
        "valid": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail unless every row has a valid final_score and decision_basis",
    )
    args = parser.parse_args()
    summary = validate_queue(
        args.score_dir / "human-review-queue.csv",
        args.score_dir / "blind-packets.jsonl",
        args.score_dir / "mechanical-score.jsonl",
        require_complete=args.require_complete,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
