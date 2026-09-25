import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_tools import GoldToolRuntime, ToolExecutionError
from thesis_data.storage import create_gold_snapshot_schema
from tests.agent_sqlite_fixtures import create_synthetic_agent_database


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


class ThesisApiAgentToolsTests(unittest.TestCase):
    """Test suite for thesis_api OpenAI tool definitions and SQLite execution dispatcher."""

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.db_path = create_synthetic_agent_database(
            Path(self._temp_dir.name) / "synthetic-agent-fixture.sqlite"
        )
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA query_only = ON")
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row

    def test_tool_definitions_schema(self) -> None:
        """Verify tool schemas strictly adhere to OpenAI function calling specifications."""
        from thesis_api.agent_tools import (
            ALL_AGENT_TOOLS,
            COMPANY_TOOLS,
            MACRO_TOOLS,
            SECTOR_TOOLS,
            TOOL_GET_COMPANY_METRICS,
            TOOL_GET_MACRO_CONTEXT,
            TOOL_GET_SECTOR_BENCHMARKS,
        )

        for tool in ALL_AGENT_TOOLS:
            self.assertEqual(tool["type"], "function")
            self.assertIn("function", tool)
            fn = tool["function"]
            self.assertIn("name", fn)
            self.assertIn("description", fn)
            self.assertIn("parameters", fn)
            self.assertEqual(fn["parameters"]["type"], "object")
            self.assertIn("properties", fn["parameters"])
            self.assertIn("required", fn["parameters"])

        self.assertIn(TOOL_GET_COMPANY_METRICS, COMPANY_TOOLS)
        self.assertIn(TOOL_GET_SECTOR_BENCHMARKS, SECTOR_TOOLS)
        self.assertIn(TOOL_GET_MACRO_CONTEXT, MACRO_TOOLS)

    def test_get_company_metrics_execution(self) -> None:
        """Test retrieving verified CAMEL ratios for target bank from SQLite."""
        from thesis_api.agent_tools import execute_agent_tool

        result = execute_agent_tool(
            "get_company_metrics",
            {"ticker": "ACB", "period": "2024_Q4"},
            self.conn,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["ticker"], "ACB")
        self.assertEqual(result["period"], "2024_Q4")
        metrics = result["metrics"]
        self.assertIn("roe", metrics)
        self.assertIn("nim", metrics)
        self.assertIn("npl", metrics)
        self.assertIn("cir", metrics)
        self.assertIn("casa", metrics)
        self.assertIsInstance(metrics["roe"], (int, float))
        self.assertGreater(metrics["roe"], 0)

    def test_get_company_metrics_filtered_kpis(self) -> None:
        """Test retrieving filtered KPIs for target bank."""
        from thesis_api.agent_tools import execute_agent_tool

        result = execute_agent_tool(
            "get_company_metrics",
            {"ticker": "ACB", "period": "2024_Q4", "kpis": ["roe", "npl"]},
            self.conn,
        )
        self.assertEqual(result["status"], "success")
        metrics = result["metrics"]
        self.assertIn("roe", metrics)
        self.assertIn("npl", metrics)
        self.assertNotIn("cir", metrics)
        self.assertNotIn("casa", metrics)

    def test_get_sector_benchmarks_execution(self) -> None:
        """Test calculating sector peer medians from SQLite."""
        from thesis_api.agent_tools import execute_agent_tool

        result = execute_agent_tool(
            "get_sector_benchmarks",
            {"sector": "Banking", "period": "2024_Q4", "tickers": ["ACB", "TCB", "MBB"]},
            self.conn,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sector"], "Banking")
        self.assertEqual(result["period"], "2024_Q4")
        benchmarks = result["benchmarks"]
        self.assertIn("peer_median_roe", benchmarks)
        self.assertIn("peer_median_nim", benchmarks)
        self.assertIn("peer_median_npl", benchmarks)
        self.assertIn("peer_median_cir", benchmarks)
        self.assertIn("peer_median_casa", benchmarks)
        self.assertIsInstance(benchmarks["peer_median_roe"], (int, float))

    def test_get_sector_benchmarks_filtered_kpis(self) -> None:
        """Test filtering benchmark KPIs."""
        from thesis_api.agent_tools import execute_agent_tool

        result = execute_agent_tool(
            "get_sector_benchmarks",
            {"sector": "Banking", "period": "2024_Q4", "kpis": ["roe", "npl"]},
            self.conn,
        )
        self.assertEqual(result["status"], "success")
        benchmarks = result["benchmarks"]
        self.assertIn("peer_median_roe", benchmarks)
        self.assertIn("peer_median_npl", benchmarks)
        self.assertNotIn("peer_median_cir", benchmarks)

    def test_get_macro_context_does_not_fabricate_policy_indicators(self) -> None:
        """Missing accepted macro data remains explicitly unavailable."""
        from thesis_api.agent_tools import execute_agent_tool

        result = execute_agent_tool(
            "get_macro_context",
            {"period": "2024"},
            self.conn,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["period"], "2024")
        self.assertIsNone(result["sbv_policy_rate"])
        self.assertIsNone(result["system_credit_growth"])
        self.assertIsNone(result["interest_rate_trend"])
        self.assertIsNone(result["source"])

    def test_unknown_tool_raises_error(self) -> None:
        """Test unknown tool name raises ValueError."""
        from thesis_api.agent_tools import execute_agent_tool

        with self.assertRaises(ValueError) as ctx:
            execute_agent_tool("non_existent_tool", {}, self.conn)
        self.assertIn("Unknown agent tool", str(ctx.exception))

    def test_missing_ticker_raises_error(self) -> None:
        """Test get_company_metrics without ticker raises ValueError."""
        from thesis_api.agent_tools import execute_agent_tool

        with self.assertRaises(ValueError) as ctx:
            execute_agent_tool("get_company_metrics", {"period": "2024"}, self.conn)
        self.assertIn("ticker", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
