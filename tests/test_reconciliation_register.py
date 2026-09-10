import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_reconciliation_register import build_register, write_register


class ReconciliationRegisterTests(unittest.TestCase):
    def test_register_has_one_row_per_target_and_preserves_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            selection = root / "selection.json"
            output = root / "register.csv"

            connection = sqlite3.connect(staging)
            connection.executescript(
                """
                CREATE TABLE ratio_observations (
                    id TEXT, ticker TEXT, sector TEXT, period TEXT,
                    ratio_type TEXT, field_code TEXT, value REAL, unit TEXT,
                    source_id TEXT, source_locator TEXT, quality_status TEXT
                );
                CREATE TABLE source_records (
                    source_id TEXT, source_url TEXT, quality_status TEXT
                );
                INSERT INTO source_records VALUES
                    ('vendor-1', 'https://vendor.test/data', 'pending_validation');
                INSERT INTO ratio_observations VALUES
                    ('row-1', 'VCB', 'bank', '2024_Q1', 'RATIO_TTM',
                     'npl', 0.02, 'vendor_ratio_decimal_or_native',
                     'vendor-1', 'data[0].npl', 'pending_validation');
                """
            )
            connection.commit()
            connection.close()
            selection.write_text(
                json.dumps(
                    {
                        "issuers": [{"ticker": "VCB"}],
                        "periods": [{"period": "2024_Q1"}],
                        "primary_metrics": ["bank.npl_g35", "bank.cir"],
                    }
                ),
                encoding="utf-8",
            )

            rows = build_register(staging, selection)
            write_register(rows, output)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["target_id"], "VCB:2024_Q1:bank.npl_g35")
            self.assertEqual(rows[0]["vendor_observation_ids"], "row-1")
            self.assertEqual(rows[0]["review_status"], "pending_official_check")
            self.assertEqual(rows[1]["review_status"], "missing_vendor_candidate")
            self.assertTrue(output.exists())

    def test_register_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "register.csv"
            output.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_register([], output)


if __name__ == "__main__":
    unittest.main()
