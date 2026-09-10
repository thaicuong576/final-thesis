from csv import DictReader
from pathlib import Path
import sqlite3
import unittest


MATRIX_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "reconciliation"
    / "gold-bank-2025-pilot-v1"
    / "metric-comparability-matrix.csv"
)
SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "official-pilot-candidate-2024-v2.sqlite"
)


class ComparabilityMatrixTests(unittest.TestCase):
    def test_matrix_covers_each_core_issuer_metric_pair_once(self):
        with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
            rows = list(DictReader(handle))

        expected = {
            (ticker, metric)
            for ticker in ("ACB", "TCB", "VPB")
            for metric in (
                "bank.npl_g35",
                "bank.llr_coverage",
                "bank.roa",
                "bank.roe",
            )
        }
        actual = {(row["ticker"], row["metric"]) for row in rows}

        self.assertEqual(len(rows), 12)
        self.assertEqual(actual, expected)
        self.assertTrue(all(row["candidate_coverage"] for row in rows))
        self.assertTrue(all(row["current_status"] for row in rows))

    def test_matrix_is_a_review_input_and_never_claims_acceptance(self):
        with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
            rows = list(DictReader(handle))

        allowed_statuses = {
            "pending_independent_review",
            "source_gap_pending_review",
        }
        self.assertTrue(
            all(row["current_status"] in allowed_statuses for row in rows)
        )
        all_values = " ".join(
            " ".join(row.values()) for row in rows
        ).lower()
        self.assertNotIn("accepted", all_values)
        self.assertTrue(all(row["review_action"] for row in rows))

    def test_matrix_coverage_uses_target_cells_not_candidate_row_variants(self):
        with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
            matrix = {
                (row["ticker"], row["metric"]): row for row in DictReader(handle)
            }

        with sqlite3.connect(SNAPSHOT_PATH) as connection:
            summary_rows = connection.execute(
                """
                SELECT ticker, metric, expected_count, candidate_count, missing_count
                FROM coverage_summary
                WHERE ticker IN ('ACB', 'TCB', 'VPB')
                  AND metric IN (
                    'bank.npl_g35', 'bank.llr_coverage',
                    'bank.roa', 'bank.roe'
                  )
                ORDER BY ticker, metric
                """
            ).fetchall()

        self.assertEqual(len(summary_rows), 12)
        for ticker, metric, expected_count, candidate_count, missing_count in summary_rows:
            # coverage_summary counts both candidate and explicit missing cells
            # as represented target cells; this matrix reports only cells with
            # an official candidate route.
            self.assertEqual(
                matrix[(ticker, metric)]["candidate_coverage"],
                f"{candidate_count - missing_count}/{expected_count}",
            )


if __name__ == "__main__":
    unittest.main()
