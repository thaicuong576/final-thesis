import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thesis_data.storage import create_gold_snapshot_schema


class QuerySnapshotCliTests(unittest.TestCase):
    def create_gold_fixture(self, root: Path) -> Path:
        db_path = root / "gold.sqlite"
        create_gold_snapshot_schema(db_path)
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-vcb', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-acb', 'ACB', 'bank', 'bank.npl_g35', 1.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:11', 'valid', NULL);
            INSERT INTO macro_observations VALUES
                ('macro-1', 'macro.policy_rate', 4.5, '%', '2024_Q1',
                 'source-1', 'valid', NULL);
            INSERT INTO evidence_snippets VALUES
                ('evidence-1', 'source-1', 'annual-report.pdf', 10,
                 'Credit quality', '2024_Q1', 'VCB',
                 'NPL group 3-5 was 2.5 percent.', 0.95, 'text_layer', 1);
            """
        )
        connection.commit()
        connection.close()
        return db_path

    def run_cli(self, db_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        script = Path(__file__).resolve().parents[1] / "scripts" / "query_snapshot.py"
        return subprocess.run(
            [sys.executable, str(script), arguments[0], str(db_path), *arguments[1:]],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_exposes_company_sector_macro_and_evidence_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.create_gold_fixture(Path(directory))

            company = self.run_cli(
                db_path,
                "company",
                "VCB",
                "2024_Q1",
                "--metric",
                "bank.npl_g35",
            )
            sector = self.run_cli(
                db_path,
                "sector",
                "bank",
                "2024_Q1",
                "--metric",
                "bank.npl_g35",
            )
            macro = self.run_cli(
                db_path,
                "macro",
                "2024_Q1",
                "--indicator",
                "macro.policy_rate",
            )
            evidence = self.run_cli(
                db_path,
                "evidence",
                "--source-id",
                "source-1",
                "--ticker",
                "VCB",
                "--period",
                "2024_Q1",
                "--text",
                "NPL",
            )

        for result in (company, sector, macro, evidence):
            self.assertEqual(result.returncode, 0, result.stderr)

        company_payload = json.loads(company.stdout)
        self.assertEqual(company_payload["status"], "success")
        self.assertEqual(company_payload["metrics"]["bank.npl_g35"], 2.5)
        self.assertEqual(company_payload["observation_ids"], ["obs-vcb"])

        sector_payload = json.loads(sector.stdout)
        self.assertEqual(sector_payload["sector_benchmarks"]["bank.npl_g35"], 2.0)

        macro_payload = json.loads(macro.stdout)
        self.assertEqual(macro_payload["metrics"]["macro.policy_rate"], 4.5)
        self.assertEqual(macro_payload["observation_ids"], ["macro-1"])

        evidence_payload = json.loads(evidence.stdout)
        self.assertEqual(len(evidence_payload), 1)
        self.assertEqual(evidence_payload[0]["evidence_id"], "evidence-1")
        self.assertEqual(evidence_payload[0]["page_number"], 10)

    def test_cli_queries_are_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.create_gold_fixture(Path(directory))
            before = db_path.read_bytes()

            result = self.run_cli(
                db_path,
                "company",
                "VCB",
                "2024_Q1",
                "--metric",
                "bank.npl_g35",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(db_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
