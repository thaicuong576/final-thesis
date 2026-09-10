import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.comparative_gate import audit_comparative_definition_gate
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


def _manifest(config: GoldConfig, snapshot_id: str, compatible: bool) -> dict:
    return {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "working_convention": "parent_attributable_equity",
        "scope": {
            "tickers": list(config.tickers),
            "periods": list(config.periods),
            "required_metrics": list(config.required_metrics),
        },
        "issuer_rules": {
            ticker: {
                "basis": "parent_attributable_equity" if compatible else "total_equity",
                "comparative_compatible": compatible,
                "evidence": "test fixture",
            }
            for ticker in config.tickers
        },
    }


def _make_gold(path: Path, config: GoldConfig, snapshot_id: str) -> None:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        (snapshot_id, "2026-09-07T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"))),
    )
    observation_rows = []
    for ticker in config.tickers:
        for period in config.periods:
            for metric in config.required_metrics:
                observation_rows.append(
                    (
                        f"obs:{ticker}:{period}:{metric}",
                        ticker,
                        "bank",
                        metric,
                        1.0,
                        "%",
                        period,
                        None,
                        "ttm",
                        None,
                        "test",
                        "valid",
                        None,
                    )
                )
    connection.executemany(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        observation_rows,
    )
    connection.commit()
    connection.close()


class ComparativeGateTests(unittest.TestCase):
    def test_accepts_complete_compatible_scope(self):
        config = GoldConfig(tickers=("ACB", "VPB"), periods=("2024_Q1",), required_metrics=("bank.roe",))
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "gold.sqlite"
            manifest = Path(directory) / "definition.json"
            _make_gold(db, config, "gold-v1")
            manifest.write_text(json.dumps(_manifest(config, "gold-v1", True)), encoding="utf-8")

            result = audit_comparative_definition_gate(db, manifest, config)

        self.assertTrue(result.eligible)
        self.assertEqual(result.checked_cells, 2)
        self.assertEqual(result.valid_cells, 2)
        self.assertEqual(result.missing_cells, 0)

    def test_rejects_incompatible_issuer_before_provider_setup(self):
        config = GoldConfig(tickers=("ACB", "VPB"), periods=("2024_Q1",), required_metrics=("bank.roe",))
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "gold.sqlite"
            manifest = Path(directory) / "definition.json"
            _make_gold(db, config, "gold-v1")
            payload = _manifest(config, "gold-v1", True)
            payload["issuer_rules"]["VPB"]["basis"] = "total_consolidated_equity"
            payload["issuer_rules"]["VPB"]["comparative_compatible"] = False
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = audit_comparative_definition_gate(db, manifest, config)

        self.assertFalse(result.eligible)
        self.assertIn(
            "comparative_definition_incompatible:VPB:total_consolidated_equity",
            result.blockers,
        )

    def test_rejects_manifest_scope_mismatch(self):
        config = GoldConfig(tickers=("ACB",), periods=("2024_Q1",), required_metrics=("bank.roe",))
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "gold.sqlite"
            manifest = Path(directory) / "definition.json"
            _make_gold(db, config, "gold-v1")
            payload = _manifest(config, "gold-v1", True)
            payload["scope"]["tickers"] = ["VPB"]
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = audit_comparative_definition_gate(db, manifest, config)

        self.assertFalse(result.eligible)
        self.assertIn("comparative_definition_scope_mismatch", result.blockers)

    def test_rejects_duplicate_observations_in_comparative_scope(self):
        config = GoldConfig(tickers=("ACB",), periods=("2024_Q1",), required_metrics=("bank.roe",))
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "gold.sqlite"
            manifest = Path(directory) / "definition.json"
            _make_gold(db, config, "gold-v1")
            connection = sqlite3.connect(db)
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "duplicate-observation",
                    "ACB",
                    "bank",
                    "bank.roe",
                    2.0,
                    "%",
                    "2024_Q1",
                    None,
                    "ttm",
                    None,
                    "test-duplicate",
                    "valid",
                    None,
                ),
            )
            connection.commit()
            connection.close()
            manifest.write_text(json.dumps(_manifest(config, "gold-v1", True)), encoding="utf-8")

            result = audit_comparative_definition_gate(db, manifest, config)

        self.assertFalse(result.eligible)
        self.assertIn(
            "comparative_definition_duplicate_cell:ACB:2024_Q1:bank.roe",
            result.blockers,
        )


if __name__ == "__main__":
    unittest.main()
