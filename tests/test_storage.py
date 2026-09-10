import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.storage import GoldConfig, create_gold_snapshot_schema, create_gold_snapshot


class StorageTests(unittest.TestCase):
    def test_gold_schema_contains_required_entities(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            connection.close()

        self.assertTrue(
            {
                "source_records",
                "coverage_summary",
                "metric_observations",
                "derived_metrics",
                "macro_observations",
                "evidence_snippets",
                "gold_labels",
                "evaluation_questions",
                "snapshot_metadata",
            }.issubset(tables)
        )

    def test_gold_creation_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            output = root / "gold.sqlite"
            sqlite3.connect(staging).close()
            output.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                create_gold_snapshot(
                    staging,
                    output,
                    GoldConfig(
                        tickers=("VCB",),
                        periods=("2024_Q1",),
                        required_metrics=("bank.npl_g35",),
                    ),
                )

    def test_gold_creation_fails_closed_for_unaccepted_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            connection = sqlite3.connect(staging)
            connection.executescript(
                """
                CREATE TABLE source_records (
                    source_id TEXT,
                    quality_status TEXT
                );
                INSERT INTO source_records VALUES ('source-1', 'pending_validation');
                """
            )
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("sources_not_accepted", result.blockers)

    def test_gold_creation_fails_closed_for_coverage_and_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=1,
                    min_metric_coverage=1.0,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("insufficient_metric_coverage", result.blockers)
        self.assertIn("insufficient_manual_labels", result.blockers)

    def test_gold_creation_rejects_incomplete_target_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO metric_observations VALUES
                ('obs-1', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL)"""
            )
            connection.executemany(
                """INSERT INTO gold_labels VALUES
                (?, 'obs-1', 'value_check', 2.5, NULL, ?,
                 '2026-09-04T00:00:00', 'page:10', 'matched')""",
                (("label-1", "checker-1"), ("label-2", "checker-2")),
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1", "2024_Q2"),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=2,
                    min_metric_coverage=0.5,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("incomplete_target_cells", result.blockers)

    def test_gold_creation_rejects_duplicate_publishable_target_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.executemany(
                """INSERT INTO metric_observations VALUES
                (?, 'VCB', 'bank', 'bank.npl_g35', ?, '%', '2024_Q1',
                 '2024-03-31', 'point_in_time', 'source-1', ?, 'valid', NULL)""",
                (
                    ("obs-1", 2.5, "page:10"),
                    ("obs-1-alt", 2.6, "page:11"),
                ),
            )
            connection.executemany(
                """INSERT INTO gold_labels VALUES
                (?, 'obs-1', 'value_check', 2.5, NULL, ?,
                 '2026-09-04T00:00:00', 'page:10', 'matched')""",
                (("label-1", "checker-1"), ("label-2", "checker-2")),
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=2,
                    min_metric_coverage=1.0,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("duplicate_target_cells", result.blockers)

    def test_gold_creation_requires_a_value_check_for_every_target_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.executemany(
                """INSERT INTO metric_observations VALUES
                (?, 'VCB', 'bank', 'bank.npl_g35', ?, '%', ?,
                 '2024-03-31', 'point_in_time', 'source-1', ?, 'valid', NULL)""",
                (
                    ("obs-q1", 2.5, "2024_Q1", "page:10"),
                    ("obs-q2", 2.6, "2024_Q2", "page:11"),
                    ("obs-q3", 2.7, "2024_Q3", "page:12"),
                ),
            )
            connection.executemany(
                """INSERT INTO gold_labels VALUES
                (?, ?, 'value_check', ?, NULL, ?,
                 '2026-09-04T00:00:00', ?, 'matched')""",
                (
                    ("label-q1-a", "obs-q1", 2.5, "checker-1", "page:10"),
                    ("label-q1-b", "obs-q1", 2.5, "checker-2", "page:10"),
                    ("label-q2-a", "obs-q2", 2.6, "checker-1", "page:11"),
                    ("label-q2-b", "obs-q2", 2.6, "checker-2", "page:11"),
                ),
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1", "2024_Q2", "2024_Q3"),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=4,
                    min_metric_coverage=1.0,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn(
            "missing_value_check_for_target_cell:VCB:2024_Q3:bank.npl_g35",
            result.blockers,
        )

    def test_gold_creation_rejects_single_checker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO metric_observations VALUES
                ('obs-1', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO gold_labels VALUES
                ('label-1', 'obs-1', 'value_check', 2.5, NULL,
                 'checker-1', '2026-09-04T00:00:00', 'page:10', 'matched')"""
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=1,
                    min_metric_coverage=1.0,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("insufficient_independent_checkers", result.blockers)

    def test_gold_creation_requires_value_checks_for_each_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.executemany(
                """INSERT INTO metric_observations VALUES
                (?, 'VCB', 'bank', ?, 2.5, '%', '2024_Q1',
                 '2024-03-31', 'point_in_time', 'source-1', ?, 'valid', NULL)""",
                (("obs-npl", "bank.npl_g35", "page:10"), ("obs-roa", "bank.roa", "page:11")),
            )
            connection.executemany(
                """INSERT INTO gold_labels VALUES
                (?, 'obs-npl', 'value_check', 2.5, NULL, ?,
                 '2026-09-04T00:00:00', 'page:10', 'matched')""",
                (("label-1", "checker-1"), ("label-2", "checker-2")),
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                root / "gold.sqlite",
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35", "bank.roa"),
                    min_manual_labels=2,
                    min_metric_coverage=1.0,
                ),
            )

        self.assertFalse(result.eligible)
        self.assertIn("insufficient_metric_label_coverage", result.blockers)

    def test_gold_creation_preserves_evidence_support_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            output = root / "gold.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO metric_observations VALUES
                ('obs-1', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO evidence_snippets VALUES
                ('evidence-1', 'source-1', 'filing.pdf', 10, 'Risk',
                 '2024_Q1', 'VCB', 'NPL 2.5%', 0.9, 'text_layer', 1)"""
            )
            connection.executemany(
                """INSERT INTO gold_labels VALUES
                (?, ?, ?, 2.5, NULL, ?, '2026-09-04T00:00:00',
                 'page:10', 'matched')""",
                (
                    ("label-1", "obs-1", "value_check", "checker-1"),
                    ("label-2", "evidence-1", "evidence_support", "checker-2"),
                ),
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                output,
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=2,
                    min_metric_coverage=1.0,
                ),
            )

            gold = sqlite3.connect(output)
            labels = gold.execute(
                "SELECT label_id, target_id FROM gold_labels ORDER BY label_id"
            ).fetchall()
            gold.close()

        self.assertTrue(result.eligible)
        self.assertEqual(labels, [("label-1", "obs-1"), ("label-2", "evidence-1")])

    def test_gold_creation_copies_only_valid_scoped_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging.sqlite"
            output = root / "gold.sqlite"
            create_gold_snapshot_schema(staging)
            connection = sqlite3.connect(staging)
            connection.execute(
                """INSERT INTO source_records VALUES
                ('source-1', 'filing', 'primary', 'https://example.test/filing',
                 '2026-09-04T00:00:00', 'data/filing.pdf', 'hash-1',
                 'Issuer', 'public', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO metric_observations VALUES
                ('obs-1', 'VCB', 'bank', 'bank.npl_g35', 2.5, '%',
                 '2024_Q1', '2024-03-31', 'point_in_time', 'source-1',
                 'page:10', 'valid', NULL)"""
            )
            connection.execute(
                """INSERT INTO gold_labels VALUES
                ('label-1', 'obs-1', 'value_check', 2.5, NULL,
                'checker-1', '2026-09-04T00:00:00', 'page:10', 'matched')"""
            )
            connection.execute(
                """INSERT INTO gold_labels VALUES
                ('label-2', 'obs-1', 'value_check', 2.5, NULL,
                'checker-2', '2026-09-04T00:00:00', 'page:10', 'matched')"""
            )
            connection.execute(
                """INSERT INTO macro_observations VALUES
                ('macro-1', 'macro.policy_rate', 4.5, '%', '2024_Q1',
                 'source-1', 'valid', NULL)"""
            )
            connection.commit()
            connection.close()

            result = create_gold_snapshot(
                staging,
                output,
                GoldConfig(
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                    required_metrics=("bank.npl_g35",),
                    min_manual_labels=1,
                    min_metric_coverage=1.0,
                ),
            )

            gold = sqlite3.connect(output)
            source_count = gold.execute("SELECT COUNT(*) FROM source_records").fetchone()[0]
            metric_count = gold.execute(
                "SELECT COUNT(*) FROM metric_observations"
            ).fetchone()[0]
            label_count = gold.execute("SELECT COUNT(*) FROM gold_labels").fetchone()[0]
            macro_count = gold.execute(
                "SELECT COUNT(*) FROM macro_observations"
            ).fetchone()[0]
            coverage_count = gold.execute(
                "SELECT COUNT(*) FROM coverage_summary"
            ).fetchone()[0]
            gold.close()

        self.assertTrue(result.eligible)
        self.assertEqual(source_count, 1)
        self.assertEqual(metric_count, 1)
        self.assertEqual(label_count, 2)
        self.assertEqual(macro_count, 1)
        self.assertEqual(coverage_count, 1)
