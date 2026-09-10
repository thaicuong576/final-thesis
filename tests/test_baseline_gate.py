import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_gate import audit_baseline_inputs
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class BaselineGateTests(unittest.TestCase):
    def config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB",),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
            min_manual_labels=2,
            min_metric_coverage=1.0,
        )

    def create_promoted_db(self, path: Path, config: GoldConfig | None = None) -> None:
        config = config or self.config()
        create_gold_snapshot_schema(path)
        connection = sqlite3.connect(path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-v1", "2026-09-04T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"), sort_keys=True)),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://example.test", "2026-09-04T00:00:00Z", "data/filing.pdf", "hash", "issuer", "public", "valid", None),
        )
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("obs-1", "VCB", "bank", "bank.npl_g35", 0.02, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("label-1", "obs-1", "value_check", 0.02, None, "checker-1", "2026-09-04T00:00:00", "page:10", "matched"),
                ("label-2", "obs-1", "value_check", 0.02, None, "checker-2", "2026-09-04T00:00:00", "page:10", "matched"),
            ),
        )
        connection.commit()
        connection.close()

    def test_pending_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.sqlite"
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("candidate", "2026-09-04T00:00:00Z", "normalized_candidate_pending_validation", "{}"),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("source-1", "api", "accelerator", "https://example.test", "2026-09-04T00:00:00Z", "data/api.json", "hash", "vendor", "pending", "pending_validation", None),
            )
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("obs-1", "VCB", "bank", "bank.npl_g35", 0.02, "decimal", "2024_Q1", "2024-03-31", "ttm", "source-1", "data[0]", "pending_validation", "not reconciled"),
            )
            connection.commit()
            connection.close()

            audit = audit_baseline_inputs(path, self.config())

        self.assertFalse(audit.eligible)
        self.assertIn("snapshot_not_gold", audit.blockers)
        self.assertIn("non_valid_source_records", audit.blockers)
        self.assertIn("non_publishable_metric_status", audit.blockers)

    def test_promoted_gold_snapshot_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            create_gold_snapshot_schema(path)
            config = self.config()
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                (
                    "gold-v1",
                    "2026-09-04T00:00:00Z",
                    "gold",
                    json.dumps(config.model_dump(mode="json"), sort_keys=True),
                ),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("source-1", "filing", "primary", "https://example.test", "2026-09-04T00:00:00Z", "data/filing.pdf", "hash", "issuer", "public", "valid", None),
            )
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("obs-1", "VCB", "bank", "bank.npl_g35", 0.02, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
            )
            connection.executemany(
                "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ("label-1", "obs-1", "value_check", 0.02, None, "checker-1", "2026-09-04T00:00:00", "page:10", "matched"),
                    ("label-2", "obs-1", "value_check", 0.02, None, "checker-2", "2026-09-04T00:00:00", "page:10", "matched"),
                ),
            )
            connection.commit()
            connection.close()

            audit = audit_baseline_inputs(path, config)

        self.assertTrue(audit.eligible)
        self.assertEqual(audit.snapshot_id, "gold-v1")
        self.assertEqual(audit.valid_cells, 1)
        self.assertEqual(audit.covered_cells, 1)

    def test_gold_snapshot_without_manual_labels_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            create_gold_snapshot_schema(path)
            config = self.config()
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-v1", "2026-09-04T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"), sort_keys=True)),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("source-1", "filing", "primary", "https://example.test", "2026-09-04T00:00:00Z", "data/filing.pdf", "hash", "issuer", "public", "valid", None),
            )
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("obs-1", "VCB", "bank", "bank.npl_g35", 0.02, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
            )
            connection.commit()
            connection.close()

            audit = audit_baseline_inputs(path, config)

        self.assertFalse(audit.eligible)
        self.assertIn("insufficient_manual_labels", audit.blockers)

    def test_snapshot_metric_coverage_policy_must_match_requested_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_promoted_db(path)
            connection = sqlite3.connect(path)
            snapshot_config = self.config().model_dump(mode="json")
            snapshot_config["min_metric_coverage"] = 0.9
            connection.execute(
                "UPDATE snapshot_metadata SET config_json = ?",
                (json.dumps(snapshot_config, sort_keys=True),),
            )
            connection.commit()
            connection.close()

            audit = audit_baseline_inputs(path, self.config())

        self.assertFalse(audit.eligible)
        self.assertIn("snapshot_config_mismatch:min_metric_coverage", audit.blockers)

    def test_gold_snapshot_requires_a_value_check_for_every_target_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            config = GoldConfig(
                tickers=("VCB",),
                periods=("2024_Q1", "2024_Q2", "2024_Q3"),
                required_metrics=("bank.npl_g35",),
                min_manual_labels=4,
                min_metric_coverage=1.0,
            )
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-v1", "2026-09-04T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"), sort_keys=True)),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("source-1", "filing", "primary", "https://example.test", "2026-09-04T00:00:00Z", "data/filing.pdf", "hash", "issuer", "public", "valid", None),
            )
            connection.executemany(
                """INSERT INTO metric_observations VALUES
                (?, 'VCB', 'bank', 'bank.npl_g35', ?, '%', ?,
                 '2024-03-31', 'point_in_time', 'source-1', ?, 'valid', NULL)""",
                (
                    ("obs-q1", 0.02, "2024_Q1", "page:10"),
                    ("obs-q2", 0.021, "2024_Q2", "page:11"),
                    ("obs-q3", 0.022, "2024_Q3", "page:12"),
                ),
            )
            connection.executemany(
                "INSERT INTO gold_labels VALUES (?, ?, 'value_check', ?, NULL, ?, ?, ?, 'matched')",
                (
                    ("label-q1-a", "obs-q1", 0.02, "checker-1", "2026-09-04T00:00:00", "page:10"),
                    ("label-q1-b", "obs-q1", 0.02, "checker-2", "2026-09-04T00:00:00", "page:10"),
                    ("label-q2-a", "obs-q2", 0.021, "checker-1", "2026-09-04T00:00:00", "page:11"),
                    ("label-q2-b", "obs-q2", 0.021, "checker-2", "2026-09-04T00:00:00", "page:11"),
                ),
            )
            connection.commit()
            connection.close()

            audit = audit_baseline_inputs(path, config)

        self.assertFalse(audit.eligible)
        self.assertIn(
            "missing_value_check_for_target_cell:VCB:2024_Q3:bank.npl_g35",
            audit.blockers,
        )


if __name__ == "__main__":
    unittest.main()
