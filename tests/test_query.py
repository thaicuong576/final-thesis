import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.query import (
    EvidenceQuery,
    get_company_metrics,
    get_evidence,
    get_macro_context,
    get_sector_benchmarks,
)
from thesis_data.storage import create_gold_snapshot_schema


class QueryBoundaryTests(unittest.TestCase):
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
            INSERT INTO source_records VALUES
                ('source-2', 'filing', 'primary', 'https://example.test/pending',
                 '2026-09-04T00:00:00', 'data/pending.pdf', 'hash-2',
                 'Issuer', 'public', 'pending_validation', NULL);
            INSERT INTO source_records VALUES
                ('source-3', 'api', 'accelerator', 'https://example.test/api',
                 '2026-09-04T00:00:00', 'data/api.json', 'hash-3',
                 'Vendor', 'public', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-vcb', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-acb', 'ACB', 'bank', 'bank.npl_g35', 1.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:11', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-pending', 'VCB', 'bank', 'bank.roa', 99.0, '%',
                 '2024_Q1', '2024-03-31', 'quarter_only', 'source-2',
                 'page:12', 'pending_validation', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-valid-pending-source', 'VCB', 'bank', 'bank.roe', 88.0, '%',
                 '2024_Q1', '2024-03-31', 'quarter_only', 'source-2',
                 'page:13', 'valid', NULL);
            INSERT INTO metric_observations VALUES
                ('obs-accelerator', 'VCB', 'bank', 'bank.nim', 7.7, '%',
                 '2024_Q1', '2024-03-31', 'quarter_only', 'source-3',
                 'data[0].nim', 'valid', NULL);
            INSERT INTO evidence_snippets VALUES
                ('evidence-1', 'source-1', 'annual-report.pdf', 10,
                 'Credit quality', '2024_Q1', 'VCB', 'NPL group 3-5 was 2.5 percent.',
                 0.95, 'text_layer', 1);
            INSERT INTO evidence_snippets VALUES
                ('evidence-pending', 'source-2', 'pending.pdf', 12,
                 'Credit quality', '2024_Q1', 'VCB', 'ROA was 99 percent.',
                 0.95, 'text_layer', 1);
            INSERT INTO macro_observations VALUES
                ('macro-1', 'macro.policy_rate', 4.5, '%', '2024_Q1',
                 'source-1', 'valid', NULL);
            INSERT INTO macro_observations VALUES
                ('macro-accelerator', 'macro.credit_growth', 9.9, '%', '2024_Q1',
                 'source-3', 'valid', NULL);
            INSERT INTO evidence_snippets VALUES
                ('evidence-accelerator', 'source-3', 'vendor.json', NULL,
                 'Macro context', '2024_Q1', NULL,
                 'System credit growth was 9.9 percent.', 0.8, 'json', 0);
            """
        )
        connection.commit()
        connection.close()
        return db_path

    def test_company_query_returns_valid_metric_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_company_metrics(
                self.create_gold_fixture(Path(directory)),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
            )

        self.assertEqual(payload.status.value, "success")
        self.assertEqual(payload.metrics["bank.npl_g35"], 2.5)
        self.assertEqual(payload.metric_units["bank.npl_g35"], "%")
        self.assertIn("source-1", payload.source_ids)
        self.assertIn("obs-vcb", payload.observation_ids)

    def test_sector_query_calculates_median_from_valid_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_sector_benchmarks(
                self.create_gold_fixture(Path(directory)),
                "bank",
                "2024_Q1",
                ("bank.npl_g35",),
            )

        self.assertEqual(payload.sector_benchmarks["bank.npl_g35"], 2.0)
        self.assertEqual(payload.status.value, "success")
        self.assertEqual(set(payload.observation_ids), {"obs-vcb", "obs-acb"})

    def test_sector_query_respects_frozen_peer_tickers(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_sector_benchmarks(
                self.create_gold_fixture(Path(directory)),
                "bank",
                "2024_Q1",
                ("bank.npl_g35",),
                tickers=("VCB",),
            )

        self.assertEqual(payload.sector_benchmarks["bank.npl_g35"], 2.5)
        self.assertEqual(payload.observation_ids, ["obs-vcb"])

    def test_sector_query_excludes_valid_metric_with_pending_source(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_sector_benchmarks(
                self.create_gold_fixture(Path(directory)),
                "bank",
                "2024_Q1",
                ("bank.roe",),
                tickers=("VCB",),
            )

        self.assertEqual(payload.status.value, "partial")
        self.assertIsNone(payload.sector_benchmarks["bank.roe"])
        self.assertIn("missing_or_unaccepted:bank.roe", payload.findings)
        self.assertNotIn("source-2", payload.source_ids)

    def test_company_query_does_not_publish_pending_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_company_metrics(
                self.create_gold_fixture(Path(directory)),
                "VCB",
                "2024_Q1",
                ("bank.roa",),
            )

        self.assertEqual(payload.status.value, "partial")
        self.assertIsNone(payload.metrics["bank.roa"])
        self.assertIn("missing_or_unaccepted:bank.roa", payload.findings)
        self.assertNotIn("source-2", payload.source_ids)

    def test_company_query_excludes_valid_metric_with_pending_source(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_company_metrics(
                self.create_gold_fixture(Path(directory)),
                "VCB",
                "2024_Q1",
                ("bank.roe",),
            )

        self.assertEqual(payload.status.value, "partial")
        self.assertIsNone(payload.metrics["bank.roe"])
        self.assertIn("missing_or_unaccepted:bank.roe", payload.findings)
        self.assertNotIn("source-2", payload.source_ids)

    def test_company_query_respects_source_tier_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_company_metrics(
                self.create_gold_fixture(Path(directory)),
                "VCB",
                "2024_Q1",
                ("bank.nim",),
                source_tiers=("primary",),
            )

        self.assertEqual(payload.status.value, "partial")
        self.assertIsNone(payload.metrics["bank.nim"])
        self.assertIn("missing_or_unaccepted:bank.nim", payload.findings)
        self.assertNotIn("source-3", payload.source_ids)

    def test_macro_query_returns_period_aligned_context(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_macro_context(
                self.create_gold_fixture(Path(directory)),
                "2024_Q1",
                ("macro.policy_rate",),
            )

        self.assertEqual(payload.metrics["macro.policy_rate"], 4.5)
        self.assertEqual(payload.metric_periods["macro.policy_rate"], "2024_Q1")
        self.assertEqual(payload.observation_ids, ["macro-1"])

    def test_macro_query_respects_source_tier_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = get_macro_context(
                self.create_gold_fixture(Path(directory)),
                "2024_Q1",
                ("macro.credit_growth",),
                source_tiers=("primary",),
            )

        self.assertEqual(payload.status.value, "partial")
        self.assertIsNone(payload.metrics["macro.credit_growth"])
        self.assertNotIn("source-3", payload.source_ids)

    def test_evidence_query_returns_page_aware_snippet(self):
        with tempfile.TemporaryDirectory() as directory:
            snippets = get_evidence(
                self.create_gold_fixture(Path(directory)),
                ("source-1",),
                EvidenceQuery(ticker="VCB", period="2024_Q1", text="NPL"),
            )

        self.assertEqual(len(snippets), 1)
        self.assertEqual(snippets[0].page_number, 10)
        self.assertEqual(snippets[0].source_id, "source-1")

    def test_evidence_query_excludes_pending_source(self):
        with tempfile.TemporaryDirectory() as directory:
            snippets = get_evidence(
                self.create_gold_fixture(Path(directory)),
                ("source-2",),
                EvidenceQuery(ticker="VCB", period="2024_Q1"),
            )

        self.assertEqual(snippets, [])

    def test_evidence_query_respects_source_tier_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            snippets = get_evidence(
                self.create_gold_fixture(Path(directory)),
                ("source-3",),
                EvidenceQuery(period="2024_Q1"),
                source_tiers=("primary",),
            )

        self.assertEqual(snippets, [])
