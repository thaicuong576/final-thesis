import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_expansion_target_register import REGISTER_FIELDS, build
from thesis_data.storage import create_gold_snapshot_schema


class ExpansionTargetRegisterTests(unittest.TestCase):
    def _db(self, path: Path) -> None:
        create_gold_snapshot_schema(path)
        con = sqlite3.connect(path)
        con.execute("INSERT INTO snapshot_metadata VALUES (?,?,?,?)", ("candidate", "now", "candidate_pending_human_review", "{}"))
        con.executemany(
            "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("source-acb", "filing", "primary", "https://a", "now", "local", "hash-a", "ACB", "", "valid", ""),
                ("source-mbb", "filing", "primary", "https://m", "now", "local", "hash-m", "MBB", "", "pending_validation", ""),
            ],
        )
        rows = [
            ("acb-roa", "ACB", "bank", "bank.roa", 1.0, "%", "2024_Q1", "2024-03-31", "ttm", "source-acb", "page:1", "valid", ""),
            ("acb-roe", "ACB", "bank", "bank.roe", 2.0, "%", "2024_Q1", "2024-03-31", "ttm", "source-acb", "page:2", "missing", ""),
            ("mbb-roa", "MBB", "bank", "bank.roa", 3.0, "%", "2024_Q1", "2024-03-31", "ttm", "source-mbb", "page:3", "pending_validation", ""),
            ("mbb-roe-a", "MBB", "bank", "bank.roe", 4.0, "%", "2024_Q1", "2024-03-31", "ttm", "source-mbb", "page:4", "pending_validation", ""),
            ("mbb-roe-b", "MBB", "bank", "bank.roe", 4.1, "%", "2024_Q1", "2024-03-31", "ttm", "source-mbb", "page:4", "pending_validation", ""),
        ]
        con.executemany("INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.commit()
        con.close()

    def test_groups_variants_and_creates_ledger_template(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "candidate.sqlite"
            self._db(db)
            register = root / "register.csv"
            ledger = root / "ledger.csv"
            result = build(db, register, ledger, tickers=("ACB", "MBB"), periods=("2024_Q1",), metrics=("bank.roa", "bank.roe"))

            self.assertEqual(result["target_cell_count"], 4)
            self.assertEqual(result["candidate_observation_count"], 5)
            self.assertEqual(result["base_gold_carry_forward_cells"], 2)
            with register.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(set(rows[0]), set(REGISTER_FIELDS))
            mbb_roe = next(row for row in rows if row["target_id"] == "MBB:2024_Q1:bank.roe")
            self.assertEqual(len(json.loads(mbb_roe["candidate_observation_ids"])), 2)
            with ledger.open(encoding="utf-8", newline="") as handle:
                ledger_rows = list(csv.DictReader(handle))
            self.assertEqual(len(ledger_rows), 4)
            self.assertTrue(all(row["checker_a_decision"] == "" for row in ledger_rows))

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "candidate.sqlite"
            self._db(db)
            register = root / "register.csv"
            ledger = root / "ledger.csv"
            build(db, register, ledger, tickers=("ACB", "MBB"), periods=("2024_Q1",), metrics=("bank.roa", "bank.roe"))
            with self.assertRaises(FileExistsError):
                build(db, root / "other.csv", ledger, tickers=("ACB", "MBB"), periods=("2024_Q1",), metrics=("bank.roa", "bank.roe"))


if __name__ == "__main__":
    unittest.main()
