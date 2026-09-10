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
from thesis_data.review_promotion import promote_reviewed_snapshot
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


TARGET_ID = "TCB:2024_Q1:bank.roa"


def _review_row(decision: str = "accepted") -> dict[str, str]:
    ticker, period, metric = TARGET_ID.split(":", 2)
    row = {field: "" for field in REVIEW_LEDGER_FIELDS}
    row.update(
        {
            "target_id": TARGET_ID,
            "ticker": ticker,
            "sector": "bank",
            "metric": metric,
            "period": period,
            "register_review_status": "pending_official_check",
        }
    )
    for prefix, checker_id in (("checker_a", "checker-a"), ("checker_b", "checker-b")):
        row[f"{prefix}_id"] = checker_id
        row[f"{prefix}_decision"] = decision
        row[f"{prefix}_checked_at"] = "2026-09-05T09:00:00Z"
        row[f"{prefix}_notes"] = "reviewed"
        if decision == "accepted":
            row[f"{prefix}_value"] = "2.5"
            row[f"{prefix}_unit"] = "%"
            row[f"{prefix}_period_basis"] = "TTM"
            row[f"{prefix}_source_id"] = "official-source"
            row[f"{prefix}_source_url"] = "https://issuer.test/results.pdf"
            row[f"{prefix}_source_locator"] = "pdf_page:30;row:ROA"
            row[f"{prefix}_consolidation_basis"] = "consolidated"
            row[f"{prefix}_definition_match"] = "yes"
    return row


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _candidate_db(path: Path) -> None:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        ("candidate-v1", "2026-09-05T00:00:00Z", "normalized_candidate_pending_validation", "{}"),
    )
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
    connection.execute(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
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
        ),
    )
    connection.execute(
        "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "evidence-roa",
            "official-source",
            "data/results.pdf",
            30,
            "KPI",
            "2024_Q1",
            "TCB",
            "ROA (LTM) 2.5%",
            1.0,
            "text_layer",
            1,
        ),
    )
    connection.commit()
    connection.close()


def _config() -> GoldConfig:
    return GoldConfig(
        tickers=("TCB",),
        periods=("2024_Q1",),
        required_metrics=("bank.roa",),
        min_manual_labels=2,
        min_metric_coverage=1.0,
    )


class ReviewPromotionTests(unittest.TestCase):
    def test_cli_help_runs_as_a_direct_script(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "promote_reviewed_snapshot.py"

        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--min-metric-coverage", result.stdout)

    def test_promotes_reviewed_candidate_without_mutating_candidate_db(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            register = root / "register.csv"
            labels = root / "gold-labels-candidate.jsonl"
            output = root / "gold.sqlite"
            _candidate_db(candidate)
            _write_csv(ledger, [_review_row()], list(REVIEW_LEDGER_FIELDS))
            _write_csv(register, [{"target_id": TARGET_ID}], ["target_id"])
            import_review_ledger(ledger, candidate, labels, register)
            before = candidate.read_bytes()

            result = promote_reviewed_snapshot(
                candidate,
                ledger,
                labels,
                register,
                output,
                _config(),
            )

            candidate_after = candidate.read_bytes()
            gold = sqlite3.connect(output)
            metric = gold.execute(
                "SELECT value, quality_status, source_id FROM metric_observations"
            ).fetchone()
            source_status = gold.execute(
                "SELECT quality_status FROM source_records WHERE source_id = 'official-source'"
            ).fetchone()[0]
            label_count = gold.execute("SELECT COUNT(*) FROM gold_labels").fetchone()[0]
            gold.close()

        self.assertTrue(result.eligible)
        self.assertEqual(metric, (2.5, "valid", "official-source"))
        self.assertEqual(source_status, "valid")
        self.assertEqual(label_count, 2)
        self.assertEqual(candidate_after, before)

    def test_marks_all_explicitly_cited_ttm_sources_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            register = root / "register.csv"
            labels = root / "gold-labels-candidate.jsonl"
            output = root / "gold.sqlite"
            _candidate_db(candidate)
            connection = sqlite3.connect(candidate)
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

            row = _review_row()
            for prefix in ("checker_a", "checker_b"):
                row[f"{prefix}_source_id"] = "official-source | official-prior-year"
                row[f"{prefix}_source_url"] = (
                    "https://issuer.test/results.pdf | https://issuer.test/prior-year.pdf"
                )
            _write_csv(ledger, [row], list(REVIEW_LEDGER_FIELDS))
            _write_csv(register, [{"target_id": TARGET_ID}], ["target_id"])
            import_review_ledger(ledger, candidate, labels, register)

            result = promote_reviewed_snapshot(
                candidate,
                ledger,
                labels,
                register,
                output,
                _config(),
            )
            gold = sqlite3.connect(output)
            statuses = dict(
                gold.execute(
                    "SELECT source_id, quality_status FROM source_records"
                ).fetchall()
            )
            gold.close()

        self.assertTrue(result.eligible)
        self.assertEqual(statuses["official-source"], "valid")
        self.assertEqual(statuses["official-prior-year"], "valid")

    def test_promotion_rejects_unresolved_review_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.sqlite"
            ledger = root / "merged-ledger.csv"
            register = root / "register.csv"
            labels = root / "gold-labels-candidate.jsonl"
            output = root / "gold.sqlite"
            _candidate_db(candidate)
            row = _review_row("conflicting")
            _write_csv(ledger, [row], list(REVIEW_LEDGER_FIELDS))
            _write_csv(register, [{"target_id": TARGET_ID}], ["target_id"])

            result = promote_reviewed_snapshot(
                candidate,
                ledger,
                labels,
                register,
                output,
                _config(),
            )

        self.assertFalse(result.eligible)
        self.assertTrue(any("unresolved_review_decision" in blocker for blocker in result.blockers))
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
