"""Materialize the bounded, adjudicated MacroObservationV2 snapshot locally."""

from __future__ import annotations

import argparse
from pathlib import Path

from thesis_data.macro_gold import (
    MACRO_GOLD_SNAPSHOT_ID,
    materialize_macro_gold_snapshot,
)


DEFAULT_BASE_DB = Path("data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite")
DEFAULT_OUTPUT_DB = Path(
    f"data/processed/{MACRO_GOLD_SNAPSHOT_ID}.sqlite"
)
DEFAULT_CANDIDATE = Path(
    "data/reconciliation/macro-official-2024-q4-v1/candidate-observations.json"
)
DEFAULT_ADJUDICATION = Path(
    "data/reconciliation/macro-official-2024-q4-v1/final-source-adjudication.json"
)
DEFAULT_MANIFEST = Path("data/manifests/macro-official-2024-q4-v1.jsonl")
DEFAULT_EVIDENCE = Path(
    "data/reconciliation/macro-official-2024-q4-v1/evidence-package.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-db", type=Path, default=DEFAULT_BASE_DB)
    parser.add_argument("--output-db", type=Path, default=DEFAULT_OUTPUT_DB)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--adjudication", type=Path, default=DEFAULT_ADJUDICATION)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    result = materialize_macro_gold_snapshot(
        args.base_db,
        args.output_db,
        args.candidate,
        args.adjudication,
        args.manifest,
        args.evidence,
    )
    print(f"eligible={result.eligible}")
    print(f"snapshot_id={result.snapshot_id}")
    print(f"output_path={result.output_path}")
    print(f"macro_rows={len(result.rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

