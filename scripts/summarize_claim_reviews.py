#!/usr/bin/env python3
"""Aggregate reviewer-supplied claim scores into deterministic JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pydantic import ValidationError  # noqa: E402

from thesis_data.evaluation import ClaimReview, summarize_claim_reviews  # noqa: E402


def _load_reviews(path: Path) -> list[ClaimReview]:
    reviews: list[ClaimReview] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            reviews.append(ClaimReview.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid_review_at_line:{line_number}") from exc
    if not reviews:
        raise ValueError("review_file_is_empty")
    return reviews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_file", type=Path, help="JSONL claim-review input")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional new JSON output path; existing files are never overwritten",
    )
    args = parser.parse_args()
    try:
        summaries = summarize_claim_reviews(_load_reviews(args.review_file))
        rendered = json.dumps(
            [summary.model_dump(mode="json") for summary in summaries],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        if args.output:
            if args.output.exists():
                raise FileExistsError(f"refusing to overwrite output: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    except (FileNotFoundError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
