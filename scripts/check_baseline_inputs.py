"""Check that a snapshot is safe to use as a comparative-agent input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_gate import audit_baseline_inputs  # noqa: E402
from thesis_data.schema import GoldConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--period", action="append", required=True)
    parser.add_argument("--metric", action="append", required=True)
    args = parser.parse_args()
    audit = audit_baseline_inputs(
        args.snapshot,
        GoldConfig(
            tickers=tuple(args.ticker),
            periods=tuple(args.period),
            required_metrics=tuple(args.metric),
        ),
    )
    print(json.dumps(audit.__dict__, ensure_ascii=False, sort_keys=True))
    return 0 if audit.eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
