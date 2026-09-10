import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_tools import GoldToolRuntime, ToolExecutionError
from thesis_data.storage import create_gold_snapshot_schema


class AgentToolsTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        db = root / "gold.sqlite"
        create_gold_snapshot_schema(db)
        connection = sqlite3.connect(db)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold", "2026-09-06T00:00:00Z", "gold", "{}"),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://example.test/filing", "2026-09-06T00:00:00Z", "private.pdf", "hash", "issuer", "test", "valid", None),
        )
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("obs-1", "VCB", "bank", "bank.roa", 1.2, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:1", "valid", None),
        )
        connection.execute(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("evidence-1", "source-1", "filing.pdf", 1, "KPI", "2024_Q1", "VCB", "ROA was 1.2 percent.", 1.0, "text_layer", 1),
        )
        connection.commit()
        connection.close()
        return db

    def runtime(self, db: Path) -> GoldToolRuntime:
        return GoldToolRuntime(
            db,
            ticker="VCB",
            periods=("2024_Q1",),
            metric_ids=("bank.roa", "bank.roe"),
            macro_indicator_ids=(),
            peer_tickers=("VCB", "ACB"),
            source_policy_id="primary-only-v1",
        )

    def test_role_registry_is_strict_and_does_not_expose_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            definitions = runtime.definitions("company")

        self.assertEqual(
            {item["name"] for item in definitions},
            {"get_company_metrics", "get_evidence", "get_source_metadata", "check_missing_or_conflict"},
        )
        self.assertTrue(all(item["strict"] for item in definitions))
        self.assertTrue(all(item["parameters"]["additionalProperties"] is False for item in definitions))

    def test_company_and_evidence_tools_return_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            company = runtime.execute(
                "company", "get_company_metrics",
                {"ticker": "VCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]},
            )
            evidence = runtime.execute(
                "company", "get_evidence",
                {"source_ids": ["source-1"], "ticker": "VCB", "period": "2024_Q1"},
            )

        self.assertEqual(company.output["metrics"]["bank.roa"], 1.2)
        self.assertEqual(company.output["observation_ids"], ["obs-1"])
        self.assertEqual(evidence.output[0]["evidence_id"], "evidence-1")
        self.assertEqual(len(company.trace.result_sha256), 64)

    def test_out_of_scope_and_disallowed_tools_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company", "get_company_metrics",
                    {"ticker": "ACB", "period": "2024_Q1", "metric_ids": ["bank.roa"]},
                )
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company", "get_sector_benchmarks",
                    {"sector": "bank", "period": "2024_Q1", "metric_ids": ["bank.roa"], "tickers": ["VCB"]},
                )

    def test_missing_check_is_explicit_and_never_fills(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            result = runtime.execute(
                "verification", "check_missing_or_conflict",
                {"ticker": "VCB", "period": "2024_Q1", "metric_id": "bank.roe"},
            )

        self.assertEqual(result.output["status"], "unaccepted")
        self.assertIsNone(result.output.get("value"))


if __name__ == "__main__":
    unittest.main()
