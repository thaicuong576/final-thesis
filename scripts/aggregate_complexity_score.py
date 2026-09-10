#!/usr/bin/env python3
"""Aggregate composite blind scores and compute bounded scaling deltas."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.blind_aggregate import (  # noqa: E402
    aggregate_by_tier_and_arm,
    classify_break_even_region,
    compute_scaling_deltas,
)
from thesis_data.blind_scoring import load_complexity_manifests  # noqa: E402


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_human_reviews(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Load only complete, binary human scores; never infer missing scores."""

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "blind_id",
        "question_id",
        "dimension",
        "machine_score",
        "final_score",
        "decision_basis",
    }
    errors: list[str] = []
    reviews: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=2):
        if not required.issubset(row):
            errors.append(f"columns_missing:row:{index}")
            break
        final_score = str(row.get("final_score", "")).strip()
        basis = str(row.get("decision_basis", "")).strip()
        if not final_score and not basis:
            continue
        if not final_score and basis:
            errors.append(f"decision_basis_without_score:row:{index}")
            continue
        if final_score not in {"0", "1"}:
            errors.append(f"final_score_invalid:row:{index}")
            continue
        if not basis:
            errors.append(f"decision_basis_missing:row:{index}")
            continue
        reviews.append(
            {
                "blind_id": str(row["blind_id"]).strip(),
                "dimension": str(row["dimension"]).strip(),
                "score": int(final_score),
            }
        )
    complete = not errors and len(reviews) == len(rows) and len(rows) > 0
    summary: dict[str, object] = {
        "path": str(path),
        "row_count": len(rows),
        "valid_score_count": len(reviews),
        "complete": complete,
        "errors": errors,
    }
    return (reviews if complete else []), summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--human-review-queue",
        type=Path,
        help="optional completed human-review queue; incomplete queues are withheld from quality results",
    )
    args = parser.parse_args()
    manifests = load_complexity_manifests(args.run_dir)
    private_map = _read_json(args.score_dir / "private-identity-map.json")
    reviews = _read_jsonl(args.score_dir / "mechanical-score.jsonl")
    manifests_for_aggregate = [
        {**identity, "blind_id": blind_id}
        for blind_id, identity in private_map.items()
    ]
    scores = aggregate_by_tier_and_arm(reviews, manifests_for_aggregate)
    deltas = compute_scaling_deltas(scores)
    operational = _read_json(args.score_dir / "operational-summary-by-tier.json")
    break_even = classify_break_even_region(deltas, operational)
    human_queue_path = args.human_review_queue or (args.score_dir / "human-review-queue.csv")
    human_reviews, human_review_summary = _read_human_reviews(human_queue_path)
    human_scores = aggregate_by_tier_and_arm(human_reviews, manifests_for_aggregate)
    human_deltas = compute_scaling_deltas(human_scores)
    human_break_even = classify_break_even_region(human_deltas, operational)
    human_complete = bool(human_review_summary["complete"])
    payload = {
        "scores_by_tier_and_arm": scores,
        "scaling_deltas": deltas,
        "operational_by_tier": operational,
        "bounded_break_even_region": break_even,
        "human_review": human_review_summary,
        "human_scores_by_tier_and_arm": human_scores,
        "human_scaling_deltas": human_deltas,
        "human_bounded_break_even_region": human_break_even,
        "primary_quality_source": "human_review" if human_complete else "pending_human_review",
        "manifest_count": len(manifests),
        "comparative_result": human_complete,
    }
    if args.output.exists():
        raise FileExistsError(f"refusing_to_overwrite:{args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest_count": len(manifests),
                "tiers": sorted(scores),
                "human_review_complete": human_complete,
                "primary_quality_source": payload["primary_quality_source"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
