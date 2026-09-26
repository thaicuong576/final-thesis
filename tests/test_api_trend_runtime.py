"""Focused contract and planner checks for bounded Company trend requests."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetSource,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.schema import QualityStatus, SourceTier
from thesis_data.analysis_plan import RequirementType

from thesis_api.adaptive_runtime import _plan_request, _query_declared_periods, run_adaptive_analysis
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
from test_api_analyze import _ExplicitOfflineAcceptingCritic


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


class _TrendProvider:
    def __init__(self, ticker: str, metrics: tuple[tuple[str, str], ...]) -> None:
        self.dataset_ref = DatasetRef(dataset_id="trend-e2e", dataset_snapshot_id=f"{ticker}-trend-v1")
        self.periods = tuple(f"2024_Q{quarter}" for quarter in range(1, 5))
        self.metric_defs = tuple(
            DatasetMetric(
                metric_id=metric_id,
                display_name=display_name,
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
            )
            for metric_id, display_name in metrics
        )
        self.catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=(DatasetEntity(entity_id=ticker, entity_type=DatasetEntityType.COMPANY, display_name=ticker),),
            periods=tuple(DatasetPeriod(period_id=item, label=item) for item in self.periods),
            metrics=self.metric_defs,
            source_refs=tuple(
                f"source-{ticker}-{metric_id.rsplit('.', 1)[-1]}-{period}"
                for metric_id, _display_name in metrics for period in self.periods
            ),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
            ),
        )
        self.observations: dict[tuple[str, str], CanonicalObservation] = {}
        self.sources: dict[str, DatasetSource] = {}
        self.get_metric_calls: list[tuple[str, str, str]] = []
        for metric_index, (metric_id, _display_name) in enumerate(metrics):
            for period_index, period in enumerate(self.periods):
                suffix = metric_id.rsplit(".", 1)[-1]
                observation_id = f"obs-{ticker}-{suffix}-{period}"
                source_id = f"source-{ticker}-{suffix}-{period}"
                observation = CanonicalObservation(
                    observation_id=observation_id,
                    dataset_id=self.dataset_ref.dataset_id,
                    dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                    entity_id=ticker,
                    period_id=period,
                    metric_id=metric_id,
                    value=10.0 + metric_index + period_index,
                    unit="percent",
                    period_basis="quarter_only",
                    reporting_scope="consolidated",
                    source_ref=source_id,
                    source_locator=f"table:{suffix};row:{period}",
                    validation_status=QualityStatus.VALID,
                )
                self.observations[(metric_id, period)] = observation
                self.sources[source_id] = DatasetSource(
                    source_ref=source_id,
                    source_type="filing",
                    source_tier=SourceTier.PRIMARY,
                    source_url=f"https://example.test/{ticker}/{suffix}/{period}",
                    publisher="Accepted trend fixture",
                    retrieved_at="2026-09-26T00:00:00Z",
                    content_hash=f"sha256-{ticker}-{suffix}-{period}",
                    validation_status=QualityStatus.VALID,
                )

    def get_capabilities(self, _dataset_ref):
        return self.catalog

    def get_metric(self, _dataset_ref, entity_id, period_id, metric_id):
        self.get_metric_calls.append((entity_id, period_id, metric_id))
        return self.observations.get((metric_id, period_id))

    def resolve_observation(self, _dataset_ref, observation_id):
        return next((item for item in self.observations.values() if item.observation_id == observation_id), None)

    def get_source(self, _dataset_ref, source_id):
        return self.sources.get(source_id)


class _TrendWriter:
    def __init__(self) -> None:
        self.specialist_calls: list[str] = []

    def write_specialist(self, *, claims, **_kwargs):
        self.specialist_calls.append("company")
        return {
            item["claim_id"]: {
                "prose": "This fact remains anchored to its accepted provider observation and declared scope.",
                "supporting_claim_ids": [item["claim_id"]],
            }
            for item in claims
        }

    def synthesize(self, *, specialist_outputs, **_kwargs):
        claim_ids = [item["claim_id"] for rows in specialist_outputs.values() for item in rows]
        return {
            "summary": "The report stays within the accepted provider evidence and frozen request scope.",
            "supporting_claim_ids": claim_ids,
        }


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

    def test_t04_t05_company_trends_keep_all_cells_and_only_invoke_company(self) -> None:
        period_ids = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        cases = (
            (
                "TCB",
                (("bank.npl_g35", "NPL"), ("bank.llr", "LLR")),
                "Analyze TCB NPL and loan loss reserve coverage from 2024_Q1 through 2024_Q4",
            ),
            (
                "MBB",
                (("bank.roa", "ROA"), ("bank.roe", "ROE")),
                "Analyze MBB return on assets and return on equity from 2024_Q1 through 2024_Q4",
            ),
        )
        for ticker, metrics, query in cases:
            with self.subTest(ticker=ticker):
                provider = _TrendProvider(ticker, metrics)
                request = AnalysisRequest(query=query, target_ticker=ticker, periods=period_ids)
                emitted: list[tuple[str, dict]] = []
                report = run_adaptive_analysis(
                    provider=provider,
                    dataset_ref=provider.dataset_ref,
                    catalog=provider.catalog,
                    request=request,
                    settings=Settings(),
                    semantic_critic=_ExplicitOfflineAcceptingCritic(),
                    analysis_writer=_TrendWriter(),
                    emit=lambda event, payload: emitted.append((event, payload)),
                )

                self.assertEqual(report.status, "completed", report.limitations)
                insight = report.company_insights[0]
                expected_cells = {
                    (metric_id, period)
                    for metric_id, _display_name in metrics for period in period_ids
                }
                records = insight.metric_period_records
                self.assertEqual(len(records), 8)
                self.assertEqual({(item.metric_id, item.period) for item in records}, expected_cells)
                self.assertEqual(
                    [item.period for item in records],
                    [period for period in period_ids for _metric in metrics],
                )
                self.assertTrue(all(item.validation_status == "valid" for item in records))
                self.assertEqual(len(report.atomic_claims), 8)
                self.assertEqual(
                    {(item.period, item.observation_id) for item in report.atomic_claims},
                    {
                        (period, provider.observations[(metric_id, period)].observation_id)
                        for metric_id, _display_name in metrics for period in period_ids
                    },
                )
                trail_by_claim = {item.claim_id: item for item in report.evidence_trail}
                self.assertEqual(len(trail_by_claim), 8)
                self.assertTrue(all(item.source_id == trail_by_claim[item.claim_id].source_id for item in records))
                self.assertEqual(
                    set(provider.get_metric_calls),
                    {(ticker, period, metric_id) for metric_id, _display_name in metrics for period in period_ids},
                )
                role_events = [payload for event, payload in emitted if event == "SPECIALIST_INVOKED"]
                self.assertEqual([item["specialist"] for item in role_events], ["company"])
                self.assertEqual(role_events[0]["periods"], period_ids)
                for event_name in ("PLAN_CREATED", "SYNTHESIS_STARTED", "REVIEW_STARTED", "SYNTHESIS_COMPLETED"):
                    payload = next(payload for event, payload in emitted if event == event_name)
                    self.assertEqual(payload["periods"], period_ids)

    def test_trend_fact_without_period_basis_fails_before_model_calls(self) -> None:
        periods = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        metrics = (("bank.roe", "ROE"),)
        provider = _TrendProvider("MBB", metrics)
        observation = provider.observations[("bank.roe", "2024_Q2")]
        provider.observations[("bank.roe", "2024_Q2")] = observation.model_copy(update={"period_basis": None})
        critic = _ExplicitOfflineAcceptingCritic()
        writer = _TrendWriter()
        report = run_adaptive_analysis(
            provider=provider,
            dataset_ref=provider.dataset_ref,
            catalog=provider.catalog,
            request=AnalysisRequest(
                query="Analyze MBB ROE from 2024_Q1 through 2024_Q4",
                target_ticker="MBB",
                periods=periods,
            ),
            settings=Settings(),
            semantic_critic=critic,
            analysis_writer=writer,
        )

        self.assertEqual(report.status, "error")
        self.assertIn("company_trend_period_basis_missing", report.limitations[0])
        self.assertEqual(writer.specialist_calls, [])
        self.assertEqual(critic.calls, 0)


if __name__ == "__main__":
    unittest.main()
