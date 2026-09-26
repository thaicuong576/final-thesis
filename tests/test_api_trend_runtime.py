"""Focused contract and planner checks for bounded Company trend requests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError
from fastapi.testclient import TestClient

from thesis_data.acceptance import validate_stage1_claims
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
from thesis_data.schema import (
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
)
from thesis_data.semantic_evaluation import (
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
    expected_dimension_applicability,
)

from thesis_api.adaptive_runtime import _plan_request, _query_declared_periods, run_adaptive_analysis
from thesis_api.database import get_analysis_run
from thesis_api.main import create_app
from thesis_api.schemas import (
    AnalysisPlanDTO,
    AnalysisRequest,
    AnalysisResponse,
    CompanyInsightDTO,
    CompanyMetricPeriodRecordDTO,
)
from thesis_api.service import AnalysisBlocked, AnalysisEngine, ProviderBinding
from thesis_api.settings import Settings
from test_api_analyze import _ExplicitOfflineAcceptingCritic


_QUESTION_BANK = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "p4-questions-v1.jsonl"


def _canonical_question(task_id: str) -> str:
    for line in _QUESTION_BANK.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item["task_id"] == task_id:
            return item["question_text"]
    raise AssertionError(f"Canonical P4 question {task_id} was not found")


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
                    period_basis=(
                        "ttm" if metric_id in {"bank.roa", "bank.roe"}
                        else "quarter_only"
                    ),
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
    def __init__(self, *, target_roe_q2_with_issue: bool = False) -> None:
        self.target_roe_q2_with_issue = target_roe_q2_with_issue
        self.specialist_calls: list[str] = []
        self.claim_calls: list[dict] = []
        self.synthesis_calls: list[dict] = []

    def write_specialist(self, *, role, plan, claims, issues, **_kwargs):
        self.specialist_calls.append(role)
        self.claim_calls.append({
            "role": role,
            "claim_ids": [item["claim_id"] for item in claims],
            "issues": issues,
            "periods": [item["accepted_observation"]["period_id"] for item in claims],
            "plan_periods": plan["scope"]["periods"],
        })
        result = {}
        for item in claims:
            observation = item["accepted_observation"]
            target = (
                self.target_roe_q2_with_issue
                and observation["entity_id"] == "MBB"
                and observation["metric_id"] == "bank.roe"
                and observation["period_id"] == "2024_Q2"
            )
            if target and issues:
                prose = "This accepted reading alone does not establish durable profitability."
            elif target:
                prose = "This accepted reading proves durable profitability."
            else:
                prose = "This fact remains anchored to its accepted provider observation and declared scope."
            result[item["claim_id"]] = {
                "prose": prose,
                "supporting_claim_ids": [item["claim_id"]],
            }
        return result

    def synthesize(self, *, plan, specialist_outputs, issues, **_kwargs):
        claim_ids = [item["claim_id"] for rows in specialist_outputs.values() for item in rows]
        self.synthesis_calls.append({
            "periods": plan["scope"]["periods"],
            "claim_ids": claim_ids,
            "issues": issues,
        })
        return {
            "summary": "The report stays within the accepted provider evidence and frozen request scope.",
            "supporting_claim_ids": claim_ids,
        }


class _TargetedTrendCritic:
    """Offline critic targeting the MBB ROE cell inside a multi-period trend."""

    def __init__(self, *, resolve_after_revision: bool) -> None:
        self.resolve_after_revision = resolve_after_revision
        self.calls: list[dict] = []

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        del stage1_report
        target = next(
            claim
            for claim in claims
            if any(
                assertion.entity == "MBB"
                and assertion.metric_id == "bank.roe"
                and assertion.period == "2024_Q2"
                for assertion in claim.assertions
            )
        )
        factual_requirement = next(
            item
            for item in plan.requirements
            if item.requirement_type is RequirementType.FACTUAL_OBSERVATION
            and item.entities == ("MBB",)
            and item.metric_ids == ("bank.roe",)
            and item.periods == ("2024_Q2",)
        )
        resolved = (
            self.resolve_after_revision
            and round_context.round_number > 0
            and "does not establish durable profitability" in target.claim_text
        )
        issue = CritiqueIssue(
            issue_id="trend-roe-interpretation-review",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MAJOR,
            affected_agent="company",
            affected_claim_ids=(target.claim_id,),
            affected_requirement_ids=(factual_requirement.requirement_id,),
            description=(
                "The company wording overstates what the observed ROE reading establishes about profitability."
            ),
            required_action=CritiqueAction.REVISE_CLAIM,
            resolution_status=(
                CritiqueIssueStatus.RESOLVED if resolved else CritiqueIssueStatus.OPEN
            ),
        )
        claim_ids = tuple(item.claim_id for item in claims)
        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(SemanticDimensionResult(
                dimension=dimension,
                applicability=applicability,
                score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                rationale="Offline trend critic reviewed the complete frozen Company candidate.",
                supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
                affected_requirement_ids=(factual_requirement.requirement_id,)
                if dimension is SemanticDimension.ANSWER_COVERAGE
                else (),
                issue_ids=(issue.issue_id,) if dimension is SemanticDimension.ANSWER_COVERAGE else (),
            ))
        self.calls.append({
            "round": round_context.round_number,
            "claim_ids": claim_ids,
            "target_claim_id": target.claim_id,
            "target_claim_text": target.claim_text,
            "periods": plan.scope.periods,
            "synthesis_summary": round_context.synthesis_summary,
            "synthesis_claim_ids": round_context.synthesis_supporting_claim_ids,
            "issue": issue,
        })
        return StructuredCriticResult(
            evaluator_version="test-only-targeted-trend-critic-v1",
            dimension_scores=tuple(dimensions),
            critique_issues=(issue,),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
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

    def test_t04_t05_company_trends_keep_all_cells_and_only_invoke_company(self) -> None:
        period_ids = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        cases = (
            (
                "TCB",
                (("bank.npl_g35", "NPL"), ("bank.llr_coverage", "LLR coverage")),
                _canonical_question("T04"),
            ),
            (
                "MBB",
                (("bank.roa", "ROA"), ("bank.roe", "ROE")),
                _canonical_question("T05"),
            ),
        )
        for ticker, metrics, query in cases:
            with self.subTest(ticker=ticker), TemporaryDirectory() as directory:
                provider = _TrendProvider(ticker, metrics)
                writer = _TrendWriter()
                settings = Settings(
                    app_env="test",
                    sqlite_db_path=str(Path(directory) / "accepted.sqlite"),
                    analysis_runs_db_path=str(Path(directory) / "runs.sqlite"),
                )
                binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "trend-fixture")
                app = create_app(
                    settings,
                    semantic_critic=_ExplicitOfflineAcceptingCritic(),
                    analysis_writer=writer,
                )
                with TestClient(app) as client, patch(
                    "thesis_api.service._load_provider", return_value=binding,
                ):
                    response = client.post(
                        "/api/analyze",
                        json={
                            "query": query,
                            "target_ticker": ticker,
                            "periods": period_ids,
                        },
                    )

                self.assertEqual(response.status_code, 200, response.text)
                report = AnalysisResponse.model_validate(response.json())

                self.assertEqual(report.status, "completed", report.limitations)
                self.assertEqual(report.analysis_plan.query, query)
                self.assertEqual(report.analysis_plan.period, period_ids[-1])
                self.assertEqual(report.analysis_plan.periods, period_ids)
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
                if ticker == "MBB":
                    self.assertTrue(all(
                        item.period_basis == "ttm"
                        for item in records
                        if item.metric_id in {"bank.roa", "bank.roe"}
                    ))
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
                self.assertEqual(writer.specialist_calls, ["company"])

    def test_multiperiod_trend_claim_gets_targeted_revision_and_full_stage1_rerun(self) -> None:
        periods = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        query = _canonical_question("T05")
        provider = _TrendProvider("MBB", (("bank.roa", "ROA"), ("bank.roe", "ROE")))
        critic = _TargetedTrendCritic(resolve_after_revision=True)
        writer = _TrendWriter(target_roe_q2_with_issue=True)
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "trend-fixture")
        stage1_candidates: list[dict] = []
        original_stage1 = validate_stage1_claims

        def capture_stage1(*args, **kwargs):
            claims = tuple(args[1] if len(args) > 1 else kwargs["claims"])
            plan = kwargs["plan"]
            report = original_stage1(*args, **kwargs)
            stage1_candidates.append({
                "claim_ids": tuple(item.claim_id for item in claims),
                "claims": tuple(item.model_copy(deep=True) for item in claims),
                "periods": plan.scope.periods,
                "passed": all(item.passed for item in report.gate_results.values())
                and not report.integrity_violations,
            })
            return report

        with TemporaryDirectory() as directory:
            settings = Settings(
                app_env="test",
                sqlite_db_path=str(Path(directory) / "accepted.sqlite"),
                analysis_runs_db_path=str(Path(directory) / "runs.sqlite"),
            )
            app = create_app(settings, semantic_critic=critic, analysis_writer=writer)
            with TestClient(app) as client, patch(
                "thesis_api.service._load_provider", return_value=binding,
            ), patch(
                "thesis_api.adaptive_runtime.validate_stage1_claims",
                side_effect=capture_stage1,
            ):
                response = client.post(
                    "/api/analyze",
                    json={"query": query, "target_ticker": "MBB", "periods": periods},
                )

        self.assertEqual(response.status_code, 200, response.text)
        report = AnalysisResponse.model_validate(response.json())
        self.assertEqual(report.status, "completed", report.limitations)
        self.assertEqual(report.revision_summary.status, "revised_and_passed")
        self.assertEqual(report.revision_summary.revised_capabilities, ["company"])
        self.assertEqual(len(critic.calls), 2)
        self.assertEqual([item["round"] for item in critic.calls], [0, 1])
        self.assertTrue(all(item["periods"] == tuple(periods) for item in critic.calls))
        self.assertTrue(all(item["synthesis_summary"] for item in critic.calls))
        self.assertTrue(all(len(item["synthesis_claim_ids"]) == 8 for item in critic.calls))
        self.assertEqual(critic.calls[0]["issue"].resolution_status, CritiqueIssueStatus.OPEN)
        self.assertEqual(critic.calls[1]["issue"].resolution_status, CritiqueIssueStatus.RESOLVED)

        self.assertEqual(len(stage1_candidates), 2)
        self.assertTrue(all(item["passed"] for item in stage1_candidates))
        self.assertTrue(all(item["periods"] == tuple(periods) for item in stage1_candidates))
        self.assertTrue(all(len(item["claims"]) == 8 for item in stage1_candidates))
        first_by_id = {item.claim_id: item for item in stage1_candidates[0]["claims"]}
        final_by_id = {item.claim_id: item for item in stage1_candidates[1]["claims"]}
        self.assertEqual(set(first_by_id), set(final_by_id))
        target_id = critic.calls[0]["target_claim_id"]
        self.assertEqual(
            first_by_id[target_id].claim_text,
            "This accepted reading proves durable profitability.",
        )
        self.assertEqual(
            final_by_id[target_id].claim_text,
            "This accepted reading alone does not establish durable profitability.",
        )
        for claim_id, before in first_by_id.items():
            if claim_id != target_id:
                self.assertEqual(before, final_by_id[claim_id])
            else:
                self.assertEqual(
                    before.model_dump(mode="json", exclude={"claim_text"}),
                    final_by_id[claim_id].model_dump(mode="json", exclude={"claim_text"}),
                )

        self.assertEqual(writer.specialist_calls, ["company", "company"])
        self.assertEqual(writer.claim_calls[0]["plan_periods"], periods)
        self.assertEqual(writer.claim_calls[0]["periods"], [period for period in periods for _ in range(2)])
        self.assertEqual(writer.claim_calls[1]["claim_ids"], [target_id])
        self.assertEqual(writer.claim_calls[1]["periods"], ["2024_Q2"])
        self.assertEqual(writer.claim_calls[1]["plan_periods"], periods)
        self.assertEqual(writer.claim_calls[1]["issues"][0]["required_action"], "REVISE_CLAIM")
        self.assertEqual(len(writer.synthesis_calls), 2)
        self.assertTrue(all(item["periods"] == periods for item in writer.synthesis_calls))
        self.assertTrue(all(len(item["claim_ids"]) == 8 for item in writer.synthesis_calls))
        final_target = next(item for item in report.atomic_claims if item.claim_id == target_id)
        self.assertEqual(final_target.stage2_critique_status, "revised")
        self.assertEqual(final_target.statement, final_by_id[target_id].claim_text)
        trail_by_claim = {item.claim_id: item for item in report.evidence_trail}
        self.assertEqual(len(trail_by_claim), 8)
        for claim_id, claim in final_by_id.items():
            assertion = claim.assertions[0]
            observation = provider.observations[(assertion.metric_id, assertion.period)]
            trail = trail_by_claim[claim_id]
            self.assertEqual(trail.observation_id, observation.observation_id)
            self.assertEqual(trail.source_id, observation.source_ref)
            self.assertEqual(trail.period, assertion.period)
            self.assertEqual(trail.table_locator, observation.source_locator)

    def test_unrepaired_critical_trend_issue_fails_within_bounded_rounds(self) -> None:
        periods = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        query = _canonical_question("T05")
        provider = _TrendProvider("MBB", (("bank.roa", "ROA"), ("bank.roe", "ROE")))
        critic = _TargetedTrendCritic(resolve_after_revision=False)
        writer = _TrendWriter(target_roe_q2_with_issue=True)
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "trend-fixture")
        stage1_count = 0
        original_stage1 = validate_stage1_claims

        def count_stage1(*args, **kwargs):
            nonlocal stage1_count
            stage1_count += 1
            return original_stage1(*args, **kwargs)

        with TemporaryDirectory() as directory:
            settings = Settings(
                app_env="test",
                sqlite_db_path=str(Path(directory) / "accepted.sqlite"),
                analysis_runs_db_path=str(Path(directory) / "runs.sqlite"),
            )
            app = create_app(settings, semantic_critic=critic, analysis_writer=writer)
            with TestClient(app) as client, patch(
                "thesis_api.service._load_provider", return_value=binding,
            ), patch(
                "thesis_api.adaptive_runtime.validate_stage1_claims",
                side_effect=count_stage1,
            ):
                response = client.post(
                    "/api/analyze",
                    json={"query": query, "target_ticker": "MBB", "periods": periods},
                )

        self.assertEqual(response.status_code, 200, response.text)
        report = AnalysisResponse.model_validate(response.json())
        self.assertEqual(report.status, "error")
        self.assertIn("fail_acceptance", report.limitations[0])
        self.assertEqual(report.atomic_claims, [])
        self.assertEqual(len(critic.calls), 2)
        self.assertEqual(critic.calls[-1]["issue"].resolution_status, CritiqueIssueStatus.OPEN)
        self.assertEqual(stage1_count, 2)
        self.assertEqual(writer.claim_calls[1]["claim_ids"], [critic.calls[0]["target_claim_id"]])

    def test_company_trend_sse_and_persisted_run_round_trip_ordered_periods(self) -> None:
        periods = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        metrics = (("bank.roa", "ROA"), ("bank.roe", "ROE"))
        query = _canonical_question("T05")
        provider = _TrendProvider("MBB", metrics)
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "trend-fixture")
        writer = _TrendWriter()
        persisted: list[dict] = []
        original_persist = AnalysisEngine.persist_run

        def persist_then_read(engine, request, report, events):
            original_persist(engine, request, report, events)
            run = get_analysis_run(engine._runs_store_path(), report.report_id)
            self.assertIsNotNone(run)
            persisted.append(run)

        def parse_sse(response_text: str) -> list[tuple[str, dict]]:
            parsed = []
            for block in response_text.strip().split("\n\n"):
                event_type = next(
                    line.removeprefix("event:").strip()
                    for line in block.splitlines()
                    if line.startswith("event:")
                )
                data = json.loads(next(
                    line.removeprefix("data:").strip()
                    for line in block.splitlines()
                    if line.startswith("data:")
                ))
                self.assertEqual(data["type"], event_type)
                parsed.append((event_type, data))
            return parsed

        with TemporaryDirectory() as directory:
            settings = Settings(
                app_env="test",
                sqlite_db_path=str(Path(directory) / "accepted.sqlite"),
                analysis_runs_db_path=str(Path(directory) / "runs.sqlite"),
            )
            app = create_app(
                settings,
                semantic_critic=_ExplicitOfflineAcceptingCritic(),
                analysis_writer=writer,
            )
            with TestClient(app) as client, patch(
                "thesis_api.service._load_provider", return_value=binding,
            ), patch.object(
                AnalysisEngine,
                "persist_run",
                autospec=True,
                side_effect=persist_then_read,
            ):
                response = client.post(
                    "/api/analyze/stream",
                    json={"query": query, "target_ticker": "MBB", "periods": periods},
                )
                events = parse_sse(response.text)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(events[-1][0], "REPORT_READY")
                ready_payload = events[-1][1]["payload"]
                report_id = ready_payload["reportId"]
                history_response = client.get(f"/api/runs/{report_id}")

        self.assertEqual(history_response.status_code, 200, history_response.text)
        history = history_response.json()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["run_id"], report_id)
        self.assertEqual(persisted[0]["status"], "completed")
        self.assertEqual(persisted[0]["events"][-1]["type"], "REPORT_READY")
        self.assertEqual(history["events"][-1]["type"], "REPORT_READY")
        self.assertEqual(history["events"][-1], events[-1][1])
        self.assertEqual(history["query"], query)
        self.assertEqual(history["period"], periods[-1])

        stream_report = ready_payload["report"]
        stored_report = history["report"]
        self.assertEqual(ready_payload["status"], "completed")
        self.assertEqual(stored_report["status"], "completed")
        self.assertEqual(stream_report["analysis_plan"]["periods"], periods)
        self.assertEqual(stored_report["analysis_plan"]["periods"], periods)
        expected_cells = [
            (metric_id, period)
            for period in periods
            for metric_id, _display_name in metrics
        ]
        self.assertEqual(
            [(item["metric_id"], item["period"]) for item in stored_report["company_insights"][0]["metric_period_records"]],
            expected_cells,
        )
        self.assertEqual(
            {item["claim_id"] for item in stream_report["atomic_claims"]},
            {item["claim_id"] for item in stored_report["atomic_claims"]},
        )
        self.assertEqual(
            {item["claim_id"] for item in stream_report["atomic_claims"]},
            {item["claim_id"] for item in stored_report["evidence_trail"]},
        )
        self.assertEqual(
            [item["period"] for item in stored_report["atomic_claims"]],
            [period for period in periods for _metric in metrics],
        )
        self.assertEqual(stored_report["revision_summary"]["status"], "passed")
        for _event_type, event in events:
            scoped_periods = event["payload"].get("periods")
            if scoped_periods is not None:
                self.assertEqual(scoped_periods, periods)

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
