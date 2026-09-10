import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.snapshot import audit_snapshot


class SnapshotAuditTests(unittest.TestCase):
    def create_fixture(self, root: Path) -> Path:
        db_path = root / "fixture.sqlite"
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            CREATE TABLE dataset_run (
                run_id TEXT,
                snapshot_status TEXT,
                benchmark_periods TEXT,
                universe TEXT
            );
            INSERT INTO dataset_run VALUES
                ('fixture-v1', 'raw_and_normalized_pending_validation',
                 '2024_Q1,2024_Q2', 'VCB,ACB');
            CREATE TABLE benchmark_periods (
                period TEXT,
                period_start TEXT,
                period_end TEXT,
                status TEXT
            );
            INSERT INTO benchmark_periods VALUES
                ('2024_Q1', '2024-01-01', '2024-03-31', 'provisional'),
                ('2024_Q2', '2024-04-01', '2024-06-31', 'provisional');
            CREATE TABLE source_records (
                source_id TEXT,
                quality_status TEXT
            );
            INSERT INTO source_records VALUES ('source-1', 'pending_validation');
            CREATE TABLE financial_observations (
                ticker TEXT,
                statement_type TEXT,
                period TEXT,
                field_code TEXT,
                source_id TEXT
            );
            INSERT INTO financial_observations VALUES
                ('VCB', 'income', '2024_Q1', 'profit', 'source-1');
            """
        )
        connection.close()
        return db_path

    def create_metric_snapshot_fixture(self, root: Path) -> Path:
        db_path = root / "metric-fixture.sqlite"
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            CREATE TABLE snapshot_metadata (
                snapshot_id TEXT,
                created_at_utc TEXT,
                status TEXT,
                config_json TEXT
            );
            INSERT INTO snapshot_metadata VALUES
                ('metric-fixture-v1', '2026-09-05T00:00:00Z',
                 'normalized_candidate_pending_validation', '{}');
            CREATE TABLE source_records (
                source_id TEXT,
                quality_status TEXT
            );
            INSERT INTO source_records VALUES ('source-1', 'pending_validation');
            CREATE TABLE metric_observations (
                observation_id TEXT PRIMARY KEY,
                ticker TEXT,
                period TEXT,
                quality_status TEXT
            );
            INSERT INTO metric_observations VALUES
                ('obs-1', 'ACB', '2024_Q1', 'pending_validation');
            """
        )
        connection.close()
        return db_path

    def test_reports_missing_ticker_and_period(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = audit_snapshot(
                self.create_fixture(Path(directory)),
                expected_tickers=("VCB", "ACB"),
                expected_periods=("2024_Q1", "2024_Q2"),
            )

        codes = {finding["code"] for finding in audit.findings}
        self.assertIn("missing_ticker", codes)
        self.assertIn("missing_period", codes)

    def test_reports_invalid_date_and_pending_source(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = audit_snapshot(
                self.create_fixture(Path(directory)),
                expected_tickers=("VCB",),
                expected_periods=("2024_Q1", "2024_Q2"),
            )

        codes = {finding["code"] for finding in audit.findings}
        self.assertIn("invalid_period_boundary", codes)
        self.assertIn("sources_not_accepted", codes)

    def test_reports_missing_gold_tables_and_clean_duplicate_check(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = audit_snapshot(
                self.create_fixture(Path(directory)),
                expected_tickers=("VCB",),
                expected_periods=("2024_Q1",),
            )

        codes = {finding["code"] for finding in audit.findings}
        self.assertIn("missing_gold_table", codes)
        missing_tables = set(audit.summary["missing_tables"])
        self.assertIn("coverage_summary", missing_tables)
        self.assertEqual(audit.summary["duplicate_groups"], 0)

    def test_metric_snapshot_does_not_require_legacy_staging_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = audit_snapshot(
                self.create_metric_snapshot_fixture(Path(directory)),
                expected_tickers=("ACB",),
                expected_periods=("2024_Q1",),
            )

        legacy_tables = {
            finding.get("table")
            for finding in audit.findings
            if finding["code"] == "missing_required_table"
        }
        self.assertNotIn("benchmark_periods", legacy_tables)
        self.assertNotIn("financial_observations", legacy_tables)
        self.assertEqual(audit.summary["snapshot_kind"], "metric_snapshot")
