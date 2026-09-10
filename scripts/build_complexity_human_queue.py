#!/usr/bin/env python3
"""Build an arm-blind human adjudication queue for a complexity run.

The input reviewer files contain private arm/run/model fields.  This script
intentionally writes only blind IDs, question IDs, dimensions, and the two
reviewer scores so a human can adjudicate disagreements without being told
which system produced the answer.
"""

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


def _blind_id(claim_id: str) -> str:
    return claim_id.split(":", 1)[0]


def build_queue(score_dir: Path) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for reviewer_id in ("ai_checker_a", "ai_checker_b"):
        for row in _jsonl(score_dir / f"{reviewer_id}-claim-reviews.jsonl"):
            claim_id = str(row["claim_id"])
            item = records.setdefault(
                claim_id,
                {
                    "claim_id": claim_id,
                    "blind_id": _blind_id(claim_id),
                    "question_id": row.get("question_id", ""),
                    "dimension": row.get("dimension", ""),
                    "scores": {},
                },
            )
            item["scores"][reviewer_id] = row.get("score")

    queue = []
    for item in records.values():
        scores = item["scores"]
        if set(scores) == {"ai_checker_a", "ai_checker_b"} and scores["ai_checker_a"] != scores["ai_checker_b"]:
            queue.append(
                {
                    "blind_id": item["blind_id"],
                    "question_id": item["question_id"],
                    "dimension": item["dimension"],
                    "reviewer_a_score": scores["ai_checker_a"],
                    "reviewer_b_score": scores["ai_checker_b"],
                    "final_score": "",
                    "decision_basis": "",
                }
            )
    return sorted(queue, key=lambda row: (row["question_id"], row["blind_id"], row["dimension"]))


def write_outputs(score_dir: Path, queue: list[dict[str, Any]]) -> tuple[Path, Path]:
    csv_path = score_dir / "human-adjudication-queue.csv"
    md_path = score_dir / "human-adjudication-queue.md"
    fields = [
        "row_number",
        "blind_id",
        "question_id",
        "dimension",
        "reviewer_a_score",
        "reviewer_b_score",
        "final_score",
        "decision_basis",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(queue, start=1):
            writer.writerow({"row_number": index, **row})

    lines = [
        "# Human adjudication queue — parallel complexity pilot",
        "",
        f"This queue contains {len(queue)} disagreements between two arm-blinded AI reviewers.",
        "It intentionally omits arm, run, manifest filename, and model identity.",
        "Inspect the matching blind packet and Gold reference before filling the final score.",
        "",
        "Do not average reviewer A and reviewer B. Preserve both scores and record an explicit decision basis.",
        "",
        "| # | Blind ID | Question | Dimension | Reviewer A | Reviewer B | Final score | Decision basis / notes |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for index, row in enumerate(queue, start=1):
        lines.append(
            f"| {index} | `{row['blind_id']}` | {row['question_id']} | {row['dimension']} | "
            f"{row['reviewer_a_score']} | {row['reviewer_b_score']} |  |  |"
        )
    lines.extend(
        [
            "",
            "## Review rules",
            "",
            "1. Open the matching row in `blind-packets.jsonl`; use the anonymized answer, question, and Gold reference only.",
            "2. Apply `experiments/scoring-rubric-v1.md`. Score `1` only when the claim is supported; otherwise score `0`.",
            "3. For calculation, do not credit a derived comparison whose input benchmark is unavailable or unsupported.",
            "4. For evidence and citation, require a locator that actually supports the claim, not only an opaque source ID.",
            "5. For coverage, do not penalize an explicitly disclosed missing or unavailable value.",
            "6. If the row cannot be decided from the Gold reference and rubric, mark it `unresolved` rather than forcing a score.",
            "",
            "This queue is a gate for the preliminary AI-assisted result; it is not itself a human score.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    args = parser.parse_args()
    queue = build_queue(args.score_dir)
    csv_path, md_path = write_outputs(args.score_dir, queue)
    print(json.dumps({"disagreement_count": len(queue), "csv": str(csv_path), "markdown": str(md_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
