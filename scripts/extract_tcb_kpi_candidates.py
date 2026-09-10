"""Extract pending TCB KPI candidates from the official FY24 presentation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.kpi import extract_tcb_fy24_kpis  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("source_id")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite output: {args.output}")
    observations = extract_tcb_fy24_kpis(args.pdf, args.source_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for observation in observations:
            handle.write(json.dumps(observation.model_dump(mode="json"), ensure_ascii=False) + "\n")
    print(f"candidate_observations={len(observations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
