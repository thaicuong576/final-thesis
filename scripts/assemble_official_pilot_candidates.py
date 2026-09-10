"""Assemble official pilot candidates into one non-gold SQLite snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.pilot_assembly import assemble_official_pilot_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--source-manifest", type=Path, action="append", required=True)
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--period", action="append", required=True)
    parser.add_argument("--metric", action="append", required=True)
    args = parser.parse_args()
    result = assemble_official_pilot_candidates(
        args.candidate,
        args.source_manifest,
        args.evidence,
        args.output,
        tickers=args.ticker,
        periods=args.period,
        required_metrics=args.metric,
    )
    print(
        f"candidate_rows={result.candidate_count} "
        f"missing_placeholders={result.placeholder_count} "
        f"observations={result.candidate_count + result.placeholder_count} "
        f"unique_cells={result.unique_candidate_cells} "
        f"sources={result.source_count} evidence={result.evidence_count} "
        f"output={result.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
