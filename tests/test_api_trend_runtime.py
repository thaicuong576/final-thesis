"""Focused contract and planner checks for bounded Company trend requests."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from thesis_data.dataset_contract import (
    AnalyticalLevel,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.analysis_plan import RequirementType

from thesis_api.adaptive_runtime import _plan_request, _query_declared_periods
from thesis_api.database import get_analysis_run
from thesis_api.schemas import (
    AnalysisPlanDTO,
    AnalysisRequest,
    AnalysisResponse,
    CompanyInsightDTO,
    CompanyMetricPeriodRecordDTO,
)
from thesis_api.service import AnalysisBlocked, AnalysisEngine
from thesis_api.settings import Settings


def _trend_catalog() -> DatasetCapabilityCatalog:
    dataset_ref = DatasetRef(dataset_id="trend-fixture", dataset_snapshot_id="trend-fixture-v1")
    return DatasetCapabilityCatalog(
        dataset_ref=dataset_ref,
        entities=(
            DatasetEntity(entity_id="ACB", entity_type=DatasetEntityType.COMPANY, display_name="ACB"),
            DatasetEntity(entity_id="MBB", entity_type=DatasetEntityType.COMPANY, display_name="MBB"),
        ),
        periods=tuple(
            DatasetPeriod(period_id=f"2024_Q{quarter}", label=f"2024 Q{quarter}")
            for quarter in range(1, 5)
        ),
        metrics=(
            DatasetMetric(metric_id="bank.roe", display_name="Return on equity", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),
            DatasetMetric(metric_id="bank.npl_g35", display_name="Non-performing loan ratio", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),
        ),
        supported_operations=(
            SupportedOperation.GET_METRIC,
            SupportedOperation.RESOLVE_OBSERVATION,
            SupportedOperation.GET_SOURCE,
        ),
    )


class CompanyTrendRequestTests(unittest.TestCase):
    def test_period_and_periods_normalize_to_final_anchor(self) -> None:
        single = AnalysisRequest(query="ROE of ACB at 2024_Q4", period="2024_q4")
        self.assertEqual(single.period, "2024_Q4")
        self.assertEqual(single.periods, ["2024_Q4"])
        self.assertFalse(single._periods_explicit)

        trend = AnalysisRequest(
            query="ROE of ACB at 2024_Q1 and 2024_Q4",
            periods=["2024_Q1", "2024_Q4"],
        )
        self.assertEqual(trend.period, "2024_Q4")
        self.assertEqual(trend.periods, ["2024_Q1", "2024_Q4"])
        self.assertTrue(trend._periods_explicit)

    def test_rejects_duplicate_descending_over_budget_and_anchor_conflict(self) -> None:
        invalid_scopes = (
            ["2024_Q1", "2024_Q1"],
            ["2024_Q2", "2024_Q1"],
            ["2023_Q4", "2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
        )
        for periods in invalid_scopes:
            with self.subTest(periods=periods), self.assertRaises(ValidationError):
                AnalysisRequest(query="Trend analysis", periods=periods)
        with self.assertRaises(ValidationError):
            AnalysisRequest(query="Trend analysis", period="2024_Q3", periods=["2024_Q1", "2024_Q4"])

    def test_expands_supported_quarter_ranges_exactly(self) -> None:
        self.assertEqual(
            _query_declared_periods("Analyze ROE from 2024_Q1 through 2024_Q4"),
            (("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"), True),
        )
        self.assertEqual(
            _query_declared_periods("Analyze ROE for 2024_Q1-Q4"),
            (("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"), True),
        )

    def test_freezes_one_factual_requirement_per_cell_and_one_trend_target_per_metric(self) -> None:
        catalog = _trend_catalog()
        request = AnalysisRequest(
            query="Analyze ROE and NPL of ACB from 2024_Q1 through 2024_Q4",
            target_ticker="ACB",
            periods=["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
        )
        plan, target, periods, metrics, peers, macro_metrics = _plan_request(
            request, catalog.dataset_ref, catalog,
        )
        factual = [item for item in plan.requirements if item.requirement_type is RequirementType.FACTUAL_OBSERVATION]
        trends = [item for item in plan.requirements if item.requirement_type is RequirementType.TREND]
        self.assertEqual(target, "ACB")
        self.assertEqual(periods, ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"))
        self.assertEqual(plan.scope.periods, periods)
        self.assertEqual(metrics, ("bank.roe", "bank.npl_g35"))
        self.assertEqual(peers, ())
        self.assertEqual(macro_metrics, ())
        self.assertEqual(len(factual), 8)
        self.assertEqual(
            {(item.entities[0], item.metric_ids[0], item.periods[0]) for item in factual},
            {("ACB", metric, period) for metric in metrics for period in periods},
        )
        self.assertEqual(len(trends), 2)
        self.assertEqual(
            {(item.entities[0], item.metric_ids[0], item.periods) for item in trends},
            {("ACB", metric, periods) for metric in metrics},
        )
        self.assertTrue(all(item.inference_ceiling.value == "trend_allowed" for item in trends))
        self.assertTrue(all(item.fulfillment_policy.value == "VALID_VALUE_REQUIRED" for item in trends))
        self.assertEqual(plan.scope.periods[-1], request.period)

    def test_period_scope_is_bound_into_candidate_identity(self) -> None:
        catalog = _trend_catalog()
        query = "Review ROE for ACB as a trend"
        first = _plan_request(
            AnalysisRequest(query=query, target_ticker="ACB", periods=["2024_Q1", "2024_Q2"]),
            catalog.dataset_ref,
            catalog,
        )[0]
        second = _plan_request(
            AnalysisRequest(query=query, target_ticker="ACB", periods=["2024_Q3", "2024_Q4"]),
            catalog.dataset_ref,
            catalog,
        )[0]
        self.assertNotEqual(first.query_id, second.query_id)

    def test_query_range_requires_explicit_periods_and_lists_must_match(self) -> None:
        catalog = _trend_catalog()
        with self.assertRaisesRegex(AnalysisBlocked, "explicit ordered periods"):
            _plan_request(
                AnalysisRequest(
                    query="Analyze ROE of ACB from 2024_Q1 through 2024_Q4",
                    target_ticker="ACB",
                    period="2024_Q4",
                ),
                catalog.dataset_ref,
                catalog,
            )
        with self.assertRaisesRegex(AnalysisBlocked, "exactly match"):
            _plan_request(
                AnalysisRequest(
                    query="Analyze ROE of ACB at 2024_Q4",
                    target_ticker="ACB",
                    periods=["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                ),
                catalog.dataset_ref,
                catalog,
            )

    def test_multi_period_peer_scope_fails_during_planning(self) -> None:
        catalog = _trend_catalog()
        with self.assertRaises(AnalysisBlocked) as blocked:
            _plan_request(
                AnalysisRequest(
                    query="Compare ACB with MBB for ROE from 2024_Q1 through 2024_Q4",
                    target_ticker="ACB",
                    peer_tickers=["MBB"],
                    periods=["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                ),
                catalog.dataset_ref,
                catalog,
            )
        self.assertEqual(blocked.exception.code, "multi_period_unsupported")
        with self.assertRaises(AnalysisBlocked) as blocked:
            _plan_request(
                AnalysisRequest(
                    query="Compare ACB with MBB for ROE from 2024_Q1 through 2024_Q4",
                    target_ticker="ACB",
                    peer_tickers=["MBB"],
                ),
                catalog.dataset_ref,
                catalog,
            )
        self.assertEqual(blocked.exception.code, "multi_period_unsupported")

    def test_missing_metric_period_record_keeps_required_nulls_when_excluding_none(self) -> None:
        record = CompanyMetricPeriodRecordDTO(
            metric_id="bank.roe",
            period="2024_Q1",
            validation_status="missing",
            missing_reason="DATA_UNAVAILABLE",
        )
        serialized = record.model_dump(mode="json", exclude_none=True)
        self.assertEqual(serialized["validation_status"], "missing")
        for field in ("value", "unit", "period_basis", "reporting_scope", "scope_status", "observation_id", "source_id", "claim_id"):
            self.assertIsNone(serialized[field])

    def test_unavailable_scope_is_explicit_and_requires_response_limitation(self) -> None:
        record = CompanyMetricPeriodRecordDTO(
            metric_id="bank.roe",
            period="2024_Q1",
            validation_status="valid",
            value=12.5,
            unit="percent",
            period_basis="quarterly",
            reporting_scope=None,
            scope_status="unavailable",
            observation_id="obs-roe-q1",
            source_id="source-roe-q1",
            claim_id="claim-roe-q1",
        )
        insight = CompanyInsightDTO(ticker="ACB", assessment="Accepted value.", metric_period_records=[record])
        with self.assertRaisesRegex(ValidationError, "explicit response limitation"):
            AnalysisResponse(
                report_id="report-1",
                status="completed",
                company_insights=[insight],
            )
        AnalysisResponse(
            report_id="report-2",
            status="accepted_with_limitations",
            company_insights=[insight],
            limitations=["Reporting scope is unavailable for obs-roe-q1; no scope is inferred."],
        )

    def test_run_store_keeps_ordered_periods_in_report_and_events(self) -> None:
        periods = ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"]
        with TemporaryDirectory() as directory:
            base = Path(directory)
            settings = Settings(
                sqlite_db_path=str(base / "accepted.sqlite"),
                analysis_runs_db_path=str(base / "runs.sqlite"),
            )
            engine = AnalysisEngine(base / "accepted.sqlite", settings)
            request = AnalysisRequest(
                query="Review ACB through 2024_Q4",
                target_ticker="ACB",
                periods=periods,
            )
            report = AnalysisResponse(
                report_id="report-periods",
                status="completed",
                analysis_plan=AnalysisPlanDTO(
                    plan_id="plan-periods",
                    query=request.query,
                    target_ticker="ACB",
                    period=periods[-1],
                    periods=periods,
                    required_capabilities=["company"],
                    dataset_snapshot_id="snapshot-periods",
                ),
            )
            events = [{"type": "PLAN_CREATED", "payload": {"periods": periods}}]
            engine.persist_run(request, report, events)

            saved = get_analysis_run(base / "runs.sqlite", report.report_id)
            self.assertEqual(saved["period"], periods[-1])
            self.assertEqual(saved["report"]["analysis_plan"]["periods"], periods)
            self.assertEqual(saved["events"][0]["payload"]["periods"], periods)


if __name__ == "__main__":
    unittest.main()
