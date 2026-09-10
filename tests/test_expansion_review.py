import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.expansion_review import audit_expansion_candidate, build_expansion_review
from thesis_data.storage import create_gold_snapshot_schema


class ExpansionReviewTests(unittest.TestCase):
    def _make_db(self, path: Path, *, ticker: str, status: str, source_tier: str):
        create_gold_snapshot_schema(path)
        con = sqlite3.connect(path)
        con.execute("INSERT INTO snapshot_metadata VALUES (?,?,?,?)", ("snap", "now", "gold", "{}"))
        con.execute(
            "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("source-1", "filing", source_tier, "https://example.test", "now", "local", "hash", "issuer", "test", "valid" if source_tier == "primary" else "pending_validation", None),
        )
        con.execute(
            "INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"obs-{ticker}", ticker, "bank", "bank.roa", 1.2, "%", "2024_Q1", "2024-03-31", "ttm", "source-1", "page:1", status, None if status == "valid" else "pending"),
        )
        con.commit(); con.close()

    def test_expansion_is_non_gold_and_registers_pending_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.sqlite"
            candidate = root / "candidate.sqlite"
            output = root / "expansion.sqlite"
            review = root / "review"
            self._make_db(base, ticker="ACB", status="valid", source_tier="primary")
            self._make_db(candidate, ticker="MBB", status="pending_validation", source_tier="primary")
            summary = build_expansion_review(base, candidate, output, review, added_tickers=("MBB",), periods=("2024_Q1",), metrics=("bank.roa",))
            self.assertFalse(summary["new_rows_are_gold"])
            self.assertEqual(summary["candidate_source_policy"], "primary_pending_validation")
            con = sqlite3.connect(output)
            self.assertEqual(con.execute("select snapshot_id from snapshot_metadata").fetchone()[0], "expansion")
            self.assertEqual(con.execute("select snapshot_id from coverage_summary limit 1").fetchone()[0], "expansion")
            self.assertEqual(con.execute("select status from snapshot_metadata").fetchone()[0], "candidate_pending_human_review")
            self.assertEqual(con.execute("select quality_status from metric_observations where ticker='MBB'").fetchone()[0], "pending_validation")
            con.close()
            self.assertTrue((review / "review-register.csv").exists())
            with (review / "review-register.csv").open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
                self.assertEqual(row["candidate_source_tier"], "primary")
                self.assertEqual(row["candidate_source_quality_status"], "valid")

    def test_audit_blocks_negative_reserve_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.sqlite"
            self._make_db(candidate, ticker="MBB", status="pending_validation", source_tier="accelerator")
            con = sqlite3.connect(candidate)
            con.execute(
                "INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("obs-llr", "MBB", "bank", "bank.llr_coverage", -0.8, "%", "2024_Q1", "2024-03-31", "ttm", "source-1", "vendor:llr", "pending_validation", "sign unresolved"),
            )
            con.commit(); con.close()
            report = audit_expansion_candidate(
                candidate,
                added_tickers=("MBB",),
                periods=("2024_Q1",),
                metrics=("bank.roa", "bank.llr_coverage"),
            )
            self.assertFalse(report["ready_for_gold"])
            self.assertIn("negative_llr_coverage_values", report["blockers"])
            self.assertEqual(len(report["negative_llr_coverage_values"]), 1)


if __name__ == "__main__":
    unittest.main()
