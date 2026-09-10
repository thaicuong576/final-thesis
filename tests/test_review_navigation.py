import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.review_navigation import (
    NAVIGATION_FIELDS,
    build_blind_source_navigation_index,
    write_blind_source_navigation_index,
)
from thesis_data.storage import create_gold_snapshot_schema


def _write_register(path: Path) -> None:
    rows = [
        {
            "target_id": "TCB:2024_Q1:bank.roa",
            "ticker": "TCB",
            "sector": "bank",
            "metric": "bank.roa",
            "period": "2024_Q1",
        },
        {
            "target_id": "ACB:2024_Q1:bank.roa",
            "ticker": "ACB",
            "sector": "bank",
            "metric": "bank.roa",
            "period": "2024_Q1",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_snapshot(path: Path) -> None:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "official-tcb-q1",
            "filing",
            "primary",
            "https://issuer.test/tcb-q1.pdf",
            "2026-09-05T00:00:00+00:00",
            "data/raw/tcb-q1.pdf",
            "sha256:source",
            "TCB",
            "public",
            "pending_validation",
            "must not be exported to blind navigation index",
        ),
    )
    connection.execute(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "observation-secret-42-7",
            "TCB",
            "bank",
            "bank.roa",
            42.7,
            "%",
            "2024_Q1",
            "2024-03-31",
            "ttm",
            "official-tcb-q1",
            "page:30;row:ROA;phrase:ROA 42.7%;formula:secret_formula;scope:secret_scope",
            "pending_validation",
            "candidate-only value must not leak",
        ),
    )
    connection.execute(
        "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "evidence-secret-quote",
            "official-tcb-q1",
            "tcb-q1.pdf",
            30,
            "Highlights",
            "2024_Q1",
            "TCB",
            "ROA 42.7% hidden quote",
            1.0,
            "text_layer_table_row",
            1,
        ),
    )
    connection.commit()
    connection.close()


class ReviewNavigationTests(unittest.TestCase):
    def test_navigation_index_covers_gaps_without_leaking_candidate_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            snapshot = root / "candidate.sqlite"
            _write_register(register)
            _write_snapshot(snapshot)

            rows = build_blind_source_navigation_index(register, snapshot)
            output = root / "blind-source-navigation-index.csv"
            write_blind_source_navigation_index(rows, output)

            with output.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                written_rows = list(reader)

            self.assertEqual(reader.fieldnames, list(NAVIGATION_FIELDS))
            self.assertEqual(
                {row["target_id"] for row in written_rows},
                {"TCB:2024_Q1:bank.roa", "ACB:2024_Q1:bank.roa"},
            )
            tcb_row = next(row for row in written_rows if row["ticker"] == "TCB")
            self.assertEqual(tcb_row["navigation_status"], "source_route_available")
            self.assertEqual(tcb_row["source_locator"], "page:30;row:ROA")
            self.assertEqual(tcb_row["page_number"], "30")
            acb_row = next(row for row in written_rows if row["ticker"] == "ACB")
            self.assertEqual(acb_row["navigation_status"], "source_gap")
            self.assertEqual(acb_row["source_id"], "")

            output_text = output.read_text(encoding="utf-8")
            self.assertNotIn("42.7", output_text)
            self.assertNotIn("observation-secret-42-7", output_text)
            self.assertNotIn("hidden quote", output_text)
            self.assertNotIn("vendor", output_text.lower())
            self.assertNotIn("value", {field.lower() for field in reader.fieldnames or []})
            self.assertNotIn("observation_id", {field.lower() for field in reader.fieldnames or []})
            self.assertNotIn("quote", {field.lower() for field in reader.fieldnames or []})

    def test_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.csv"
            output.write_text("existing\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_blind_source_navigation_index([], output)


if __name__ == "__main__":
    unittest.main()
