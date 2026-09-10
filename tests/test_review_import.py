import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_review_ledger import REVIEW_LEDGER_FIELDS
from thesis_data.review_import import import_review_ledger
from thesis_data.storage import create_gold_snapshot_schema


def _ledger_row(target_id: str = "TCB:2024_Q1:bank.roa") -> dict[str, str]:
    ticker, period, metric = target_id.split(":", 2)
    row = {field: "" for field in REVIEW_LEDGER_FIELDS}
    row.update(
        {
            "target_id": target_id,
            "ticker": ticker,
            "sector": "bank",
            "metric": metric,
            "period": period,
            "register_review_status": "pending_official_check",
        }
    )
    for prefix, checker_id in (("checker_a", "checker-a"), ("checker_b", "checker-b")):
        row[f"{prefix}_id"] = checker_id
        row[f"{prefix}_decision"] = "accepted"
        row[f"{prefix}_value"] = "2.5"
        row[f"{prefix}_unit"] = "%"
        row[f"{prefix}_period_basis"] = "TTM"
        row[f"{prefix}_source_id"] = "official-source"
        row[f"{prefix}_source_url"] = "https://issuer.test/results.pdf"
        row[f"{prefix}_source_locator"] = "pdf_page:30;row:ROA"
        row[f"{prefix}_consolidation_basis"] = "consolidated"
        row[f"{prefix}_definition_match"] = "yes"
        row[f"{prefix}_checked_at"] = "2026-09-05T00:00:00Z"
        row[f"{prefix}_notes"] = "verified independently"
    return row


def _write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_register(path: Path, target_ids: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target_id"])
        writer.writeheader()
        writer.writerows({"target_id": target_id} for target_id in target_ids)


def _candidate_db(
    path: Path,
    *,
    duplicate: bool = False,
    duplicate_value: float = 2.6,
    include_missing: bool = False,
) -> None:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "official-source",
            "issuer_ir",
            "primary",
            "https://issuer.test/results.pdf",
            "2026-09-05T00:00:00Z",
            "data/results.pdf",
            "sha256:source",
            "TCB",
            "public",
            "pending_validation",
            "candidate",
        ),
    )
    observation = (
        "obs-tcb-roa-q1",
        "TCB",
        "bank",
        "bank.roa",
        2.5,
        "%",
        "2024_Q1",
        "2024-03-31",
        "ttm",
        "official-source",
        "pdf_page:30;row:ROA",
        "pending_validation",
        "pending independent review",
    )
    connection.execute(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        observation,
    )
    if duplicate:
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "obs-tcb-roa-q1-alt",
                *observation[1:4],
                duplicate_value,
                observation[5],
                *observation[6:9],
                observation[9],
                "pdf_page:31;row:ROA",
                *observation[11:],
            ),
        )
    if include_missing:
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "missing:TCB:2024_Q2:bank.roa",
                "TCB",
                "bank",
                "bank.roa",
                None,
                None,
                "2024_Q2",
                None,
                None,
                None,
                None,
                "missing",
                "no official candidate route",
            ),
        )
    connection.commit()
    connection.close()


class ReviewImportTests(unittest.TestCase):
    def test_export_cli_runs_as_a_direct_script(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "import_review_ledger.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--register", result.stdout)

    def test_refuses_partial_ledger_against_register_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            register = root / "register.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db)
            _write_ledger(ledger, [_ledger_row()])
            _write_register(
                register,
                [
                    "TCB:2024_Q1:bank.roa",
                    "TCB:2024_Q2:bank.roa",
                ],
            )

            with self.assertRaisesRegex(ValueError, "target_set_mismatch"):
                import_review_ledger(ledger, candidate_db, output, register)

            self.assertFalse(output.exists())

    def test_exports_two_gold_labels_without_mutating_candidate_db(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db)
            _write_ledger(ledger, [_ledger_row()])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            connection = sqlite3.connect(candidate_db)
            observation = connection.execute(
                "SELECT value, quality_status FROM metric_observations"
            ).fetchone()
            connection.close()

        self.assertEqual(count, 2)
        self.assertEqual(len(labels), 2)
        self.assertEqual({label["target_id"] for label in labels}, {"obs-tcb-roa-q1"})
        self.assertEqual({label["checker_id"] for label in labels}, {"checker-a", "checker-b"})
        self.assertTrue(all(label["label_type"] == "value_check" for label in labels))
        self.assertEqual(observation, (2.5, "pending_validation"))

    def test_refuses_ambiguous_candidate_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, duplicate=True, duplicate_value=2.5)
            row = _ledger_row()
            row["checker_a_source_locator"] = "pdf_page:99;row:ROA"
            row["checker_b_source_locator"] = "pdf_page:99;row:ROA"
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            with self.assertRaisesRegex(ValueError, "ambiguous_candidate_observation"):
                import_review_ledger(ledger, candidate_db, output, register)
            self.assertFalse(output.exists())

    def test_does_not_collapse_nearby_variant_within_old_percentage_tolerance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, duplicate=True, duplicate_value=2.509)
            connection = sqlite3.connect(candidate_db)
            connection.execute(
                "UPDATE metric_observations SET source_locator=? WHERE observation_id=?",
                ("pdf_page:30;row:ROA", "obs-tcb-roa-q1-alt"),
            )
            connection.commit()
            connection.close()
            _write_ledger(ledger, [_ledger_row()])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(count, 2)
        self.assertEqual({label["target_id"] for label in labels}, {"obs-tcb-roa-q1"})

    def test_resolves_variant_by_reviewed_value_and_source_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, duplicate=True)
            _write_ledger(ledger, [_ledger_row()])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(count, 2)
        self.assertEqual({label["target_id"] for label in labels}, {"obs-tcb-roa-q1"})

    def test_accepts_composite_source_references_for_derived_ttm_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db)
            connection = sqlite3.connect(candidate_db)
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "official-prior-year",
                    "issuer_ir",
                    "primary",
                    "https://issuer.test/prior-year.pdf",
                    "2026-09-05T00:00:00Z",
                    "data/prior-year.pdf",
                    "sha256:prior",
                    "TCB",
                    "public",
                    "pending_validation",
                    "prior fiscal-year input",
                ),
            )
            connection.commit()
            connection.close()

            row = _ledger_row()
            for prefix in ("checker_a", "checker_b"):
                row[f"{prefix}_source_id"] = "official-source | official-prior-year"
                row[f"{prefix}_source_url"] = (
                    "https://issuer.test/results.pdf | https://issuer.test/prior-year.pdf"
                )
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            self.assertTrue(output.exists())

        self.assertEqual(count, 2)

    def test_uses_adjudicated_source_slot_for_accepted_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, duplicate=True, duplicate_value=2.6)
            row = _ledger_row()
            row["checker_b_value"] = "2.6"
            row["checker_b_source_locator"] = "pdf_page:31;row:ROA"
            row["adjudication_decision"] = "accepted"
            row["adjudication_source_slot"] = "checker_b"
            row["adjudicator_id"] = "adjudicator-1"
            row["adjudicated_at"] = "2026-09-05T00:00:00Z"
            row["adjudication_reason"] = "Checker B's mapping is the canonical candidate variant."
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(count, 3)
        self.assertEqual(
            {label["target_id"] for label in labels},
            {"obs-tcb-roa-q1-alt"},
        )
        self.assertEqual(
            {label["label_type"] for label in labels},
            {"value_check", "adjudication"},
        )

    def test_missing_review_with_multiple_candidates_emits_unique_label_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, duplicate=True)
            row = _ledger_row()
            for prefix in ("checker_a", "checker_b"):
                row[f"{prefix}_decision"] = "missing"
                row[f"{prefix}_value"] = ""
                row[f"{prefix}_unit"] = ""
                row[f"{prefix}_period_basis"] = ""
                row[f"{prefix}_source_id"] = ""
                row[f"{prefix}_source_url"] = ""
                row[f"{prefix}_source_locator"] = ""
                row[f"{prefix}_consolidation_basis"] = ""
                row[f"{prefix}_definition_match"] = ""
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(count, 4)
        self.assertEqual(len({label["label_id"] for label in labels}), 4)

    def test_exports_missing_labels_to_an_explicit_missing_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db, include_missing=True)
            row = _ledger_row("TCB:2024_Q2:bank.roa")
            for prefix in ("checker_a", "checker_b"):
                row[f"{prefix}_decision"] = "missing"
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q2:bank.roa"])

            count = import_review_ledger(ledger, candidate_db, output, register)
            labels = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(count, 2)
        self.assertEqual(
            {label["target_id"] for label in labels},
            {"missing:TCB:2024_Q2:bank.roa"},
        )
        self.assertEqual({label["expected_judgment"] for label in labels}, {"missing"})
        self.assertTrue(all(label["expected_value"] is None for label in labels))

    def test_refuses_incomplete_or_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_db = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            output = root / "gold-labels-candidate.jsonl"
            _candidate_db(candidate_db)
            row = _ledger_row()
            row["checker_b_decision"] = ""
            _write_ledger(ledger, [row])
            _write_register(register := root / "register.csv", ["TCB:2024_Q1:bank.roa"])

            with self.assertRaisesRegex(ValueError, "review ledger is not eligible"):
                import_review_ledger(ledger, candidate_db, output, register)
            output.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                import_review_ledger(ledger, candidate_db, output, register)


if __name__ == "__main__":
    unittest.main()
