import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_tools import (
    CompanyMetricArguments,
    GoldToolRuntime,
    ToolExecutionError,
    validate_composite_tool_scope,
)
from thesis_data.storage import create_gold_snapshot_schema
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)


class CompositeToolScopeTests(unittest.TestCase):
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
            (
                "source-1", "filing", "primary", "https://example.test/filing",
                "2026-09-06T00:00:00Z", "private.pdf", "hash", "issuer", "test",
                "valid", None,
            ),
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("obs-vcb", "VCB", "bank", "bank.roa", 1.2, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:1", "valid", None),
                ("obs-acb", "ACB", "bank", "bank.roa", 1.4, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:2", "valid", None),
            ],
        )
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("evidence-vcb", "source-1", "filing.pdf", 1, "KPI", "2024_Q1", "VCB", "ROA was 1.2 percent.", 1.0, "text_layer", 1),
                ("evidence-acb", "source-1", "filing.pdf", 2, "KPI", "2024_Q1", "ACB", "ROA was 1.4 percent.", 1.0, "text_layer", 1),
            ],
        )
        connection.commit()
        connection.close()
        return db

    def runtime(self, db: Path) -> GoldToolRuntime:
        return GoldToolRuntime(
            db,
            tickers=("VCB", "ACB"),
            periods=("2024_Q1", "2024_Q2"),
            metric_ids=("bank.roa",),
            macro_indicator_ids=(),
            peer_tickers=("VCB", "ACB"),
            source_policy_id="primary-only-v1",
        )

    def composite_runtime(self, db: Path) -> GoldToolRuntime:
        return GoldToolRuntime(
            db,
            tickers=("VCB", "ACB"),
            periods=("2024_Q1", "2024_Q2"),
            metric_ids=("bank.roa",),
            macro_indicator_ids=(),
            peer_tickers=("VCB", "ACB"),
            source_policy_id="primary-only-v1",
            composite_tools=True,
        )

    def test_composite_runtime_reads_each_declared_issuer(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            vcb = runtime.execute(
                "company", "get_company_metrics",
                {"ticker": "VCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]},
            )
            acb = runtime.execute(
                "company", "get_company_metrics",
                {"ticker": "ACB", "period": "2024_Q1", "metric_ids": ["bank.roa"]},
            )

        self.assertEqual(vcb.output["metrics"]["bank.roa"], 1.2)
        self.assertEqual(acb.output["metrics"]["bank.roa"], 1.4)

    def test_allowed_tickers_are_immutable_and_standalone_validator_is_strict(self):
        spec = CompositeWorkloadSpec(
            question_id="q-composite-tier-3",
            tier=WorkloadTier.TIER_3,
            issuers=("VCB", "ACB"),
            periods=("2024_Q1",),
            metric_ids=("bank.roa",),
            analysis_tasks=(AnalysisTask.SNAPSHOT,),
            peer_tickers=("VCB", "ACB"),
            complexity_vector=ComplexityVector(
                issuer_count=2,
                period_count=1,
                metric_count=1,
                analysis_task_count=1,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=0,
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            self.assertEqual(runtime.allowed_tickers, frozenset({"VCB", "ACB"}))
            with self.assertRaises(ToolExecutionError):
                validate_composite_tool_scope(
                    CompanyMetricArguments(
                        ticker="TCB", period="2024_Q1", metric_ids=["bank.roa"]
                    ),
                    spec,
                    "company",
                )
            validate_composite_tool_scope(
                CompanyMetricArguments(
                    ticker="ACB", period="2024_Q1", metric_ids=["bank.roa"]
                ),
                spec,
                "company",
            )

    def test_composite_runtime_rejects_undeclared_issuer_and_period(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company", "get_company_metrics",
                    {"ticker": "TCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]},
                )
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company", "get_company_metrics",
                    {"ticker": "ACB", "period": "2025_Q1", "metric_ids": ["bank.roa"]},
                )

    def test_composite_peer_scope_remains_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(self.fixture(Path(directory)))
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "sector", "get_sector_benchmarks",
                    {
                        "sector": "bank",
                        "period": "2024_Q1",
                        "metric_ids": ["bank.roa"],
                        "tickers": ["VCB", "TCB"],
                    },
                )

    def test_composite_batch_reads_are_deterministic_and_role_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.composite_runtime(self.fixture(Path(directory)))
            definitions = {item["name"] for item in runtime.definitions("company")}
            self.assertIn("get_company_metrics_batch", definitions)
            self.assertIn("check_missing_or_conflict_batch", definitions)
            self.assertNotIn("get_sector_benchmarks_batch", definitions)
            result = runtime.execute(
                "company",
                "get_company_metrics_batch",
                {
                    "tickers": ["VCB", "ACB"],
                    "periods": ["2024_Q1", "2024_Q2"],
                    "metric_ids": ["bank.roa"],
                },
            )

        self.assertEqual([item["ticker"] for item in result.output], ["VCB", "VCB", "ACB", "ACB"])
        self.assertEqual([item["period"] for item in result.output], ["2024_Q1", "2024_Q2", "2024_Q1", "2024_Q2"])
        self.assertEqual(result.output[0]["metrics"]["bank.roa"], 1.2)
        self.assertEqual(result.output[2]["metrics"]["bank.roa"], 1.4)

    def test_composite_batch_scope_rejects_any_out_of_scope_member(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.composite_runtime(self.fixture(Path(directory)))
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company",
                    "get_company_metrics_batch",
                    {
                        "tickers": ["VCB", "TCB"],
                        "periods": ["2024_Q1"],
                        "metric_ids": ["bank.roa"],
                    },
                )
            with self.assertRaises(ToolExecutionError):
                runtime.execute(
                    "company",
                    "check_missing_or_conflict_batch",
                    {
                        "tickers": ["VCB"],
                        "periods": ["2025_Q1"],
                        "metric_ids": ["bank.roa"],
                    },
                )


if __name__ == "__main__":
    unittest.main()
