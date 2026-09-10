"""Validate a versioned question set and print a deterministic summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.question_set import load_question_set, question_set_sha256  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_set", type=Path)
    args = parser.parse_args()
    try:
        question_set = load_question_set(args.question_set)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "question_count": len(question_set.questions),
                "question_set_id": question_set.question_set_id,
                "question_set_sha256": question_set_sha256(args.question_set),
                "question_types": sorted({question.type.value for question in question_set.questions}),
                "status": question_set.status,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
