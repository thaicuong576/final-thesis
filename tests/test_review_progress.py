import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_review_ledger import REVIEWER_COPY_FIELDS
from thesis_data.review_progress import summarize_review_file


def _copy_row(target_id: str, decision: str = "") -> dict[str, str]:
    ticker, period, metric = target_id.split(":", 2)
    row = {field: "" for field in REVIEWER_COPY_FIELDS}
    row.update(
        {
            "target_id": target_id,
            "ticker": ticker,
            "sector": "bank",
            "metric": metric,
            "period": period,
            "checker_id": "checker-a",
            "decision": decision,
        }
    )
    return row


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ReviewProgressTests(unittest.TestCase):
    def test_cli_reports_blank_copy_as_json(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "report_review_progress.py"
        copy_path = Path(__file__).resolve().parents[1] / "data" / "reconciliation" / "gold-bank-2025-pilot-v1" / "review-checker-a-blind-template-v2.csv"

        result = subprocess.run(
            [sys.executable, str(script), str(copy_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["reports"][0]["row_count"], 48)
        self.assertEqual(payload["reports"][0]["checkers"][0]["completed_count"], 0)

    def test_blank_reviewer_copy_is_reported_as_zero_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checker-a.csv"
            _write_csv(
                path,
                [_copy_row("TCB:2024_Q1:bank.roa"), _copy_row("VPB:2024_Q1:bank.roa")],
                list(REVIEWER_COPY_FIELDS),
            )

            report = summarize_review_file(path)

        self.assertEqual(report.row_count, 2)
        self.assertEqual(report.checkers[0].completed_count, 0)
        self.assertEqual(report.checkers[0].completion_rate, 0.0)
        self.assertEqual(report.checkers[0].decision_counts, {})
        self.assertIsNone(report.checkers[0].throughput_rows_per_hour)

    def test_completed_copy_reports_decisions_coverage_and_throughput(self):
        rows = [
            _copy_row("TCB:2024_Q1:bank.roa", "accepted"),
            _copy_row("VPB:2024_Q1:bank.roa", "missing"),
        ]
        rows[0].update(
            {
                "checked_at": "2026-09-05T09:00:00Z",
                "notes": "verified",
            }
        )
        rows[1].update(
            {
                "checked_at": "2026-09-05T10:00:00Z",
                "notes": "not disclosed",
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checker-a.csv"
            _write_csv(path, rows, list(REVIEWER_COPY_FIELDS))
            report = summarize_review_file(path)

        checker = report.checkers[0]
        self.assertEqual(checker.completed_count, 2)
        self.assertEqual(checker.decision_counts, {"accepted": 1, "missing": 1})
        self.assertEqual(checker.completed_by_ticker, {"TCB": 1, "VPB": 1})
        self.assertEqual(checker.completed_by_metric, {"bank.roa": 2})
        self.assertEqual(checker.elapsed_hours, 1.0)
        self.assertEqual(checker.throughput_rows_per_hour, 2.0)


if __name__ == "__main__":
    unittest.main()
