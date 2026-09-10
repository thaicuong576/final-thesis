#!/usr/bin/env python3
"""Build an arm-blind human review queue for the scaling sweep."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_rows(score_dir: Path) -> list[dict[str, Any]]:
    identity_map = json.loads((score_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in _jsonl(score_dir / "mechanical-score.jsonl"):
        identity = identity_map.get(str(item["blind_id"]))
        if identity is None:
            continue
        rows.append(
            {
                "blind_id": item["blind_id"],
                "question_id": identity["question_id"],
                "dimension": item["dimension"],
                "machine_score": item["score"],
                "final_score": "",
                "decision_basis": "",
            }
        )
    return sorted(rows, key=lambda row: (row["question_id"], row["blind_id"], row["dimension"]))


def write_outputs(score_dir: Path, rows: list[dict[str, Any]]) -> None:
    csv_path = score_dir / "human-review-queue.csv"
    md_path = score_dir / "human-review-queue.md"
    fields = ["row_number", "blind_id", "question_id", "dimension", "machine_score", "final_score", "decision_basis"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            writer.writerow({"row_number": index, **row})

    packet_count = len({row["blind_id"] for row in rows})
    lines = [
        "# Human review queue — scaling sweep",
        "",
        f"This queue covers {packet_count} arm-blind packets and {len(rows)} mechanical rubric rows.",
        "The queue omits arm, run, manifest filename, and model identity.",
        "The machine score is shown only as a comparison point; the reviewer must independently inspect the blind packet and Gold reference.",
        "",
        "Fill `final_score` and `decision_basis` in `human-review-queue.csv`. Do not average or accept the machine score without checking the rubric.",
        "",
        "Review source: `blind-packets.jsonl` in this directory.",
        "Review rubric: `experiments/scoring-rubric-v1.md`.",
        "",
        "The composed run preserves first-pass and retry provenance, including explicit failed provider jobs. This queue is for quality adjudication and reliability analysis, not a claim that execution was failure-free.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    args = parser.parse_args()
    rows = build_rows(args.score_dir)
    write_outputs(args.score_dir, rows)
    print(json.dumps({"packet_count": len({row['blind_id'] for row in rows}), "mechanical_row_count": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
