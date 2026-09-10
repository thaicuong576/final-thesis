"""Validate one user-facing ``analysis-report-v2`` JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.analysis_report_validation import validate_analysis_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    validate_analysis_report(report)
    print(
        json.dumps(
            {
                "valid": True,
                "contract_version": report["contract_version"],
                "claim_count": len(report["claims"]),
                "claim_origin": report["data_quality"].get("claim_origin"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
