import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_runtime import (
    AgentCallRequest,
    ExperimentInputError,
    run_agent_arm,
)
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.schema import AgentPayload, AgentStatus, EvidenceSnippet, GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class RecordingAdapter:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            findings=[f"fixture:{request.role}"],
        )


class InventedProvenanceAdapter:
    def complete(self, request):
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            source_ids=["invented-source"],
            findings=["invented provenance should be rejected"],
        )


class TamperedEvidenceAdapter:
    def complete(self, request):
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            evidence=[
                EvidenceSnippet(
                    evidence_id="fixture-evidence",
                    source_id="source-1",
                    source_document="data/filing.pdf",
                    page_number=10,
                    section_name="Credit quality",
                    period="2024_Q1",
                    ticker="VCB",
                    quote="tampered evidence",
                    retrieval_score=1.0,
                    parser_status="text_layer",
                    is_paginated=True,
                )
            ],
        )


_REQUEST_SCOPE_DEFAULT = object()


class MismatchedScopeAdapter:
    def __init__(
        self,
        *,
        agent_id=_REQUEST_SCOPE_DEFAULT,
        ticker=_REQUEST_SCOPE_DEFAULT,
        period=_REQUEST_SCOPE_DEFAULT,
    ):
        self.agent_id = agent_id
        self.ticker = ticker
        self.period = period

    def complete(self, request):
        return AgentPayload(
            agent_id=(
                request.role
                if self.agent_id is _REQUEST_SCOPE_DEFAULT
                else self.agent_id
            ),
            status=AgentStatus.SUCCESS,
            ticker=(
                request.ticker
                if self.ticker is _REQUEST_SCOPE_DEFAULT
                else self.ticker
            ),
            period=(
                request.period
                if self.period is _REQUEST_SCOPE_DEFAULT
                else self.period
            ),
        )


class MetricContractAdapter:
    def __init__(
        self,
        *,
        metrics,
        metric_units=None,
        metric_periods=None,
        observation_ids=None,
        source_ids=None,
    ):
        self.metrics = metrics
        self.metric_units = metric_units or {}
        self.metric_periods = metric_periods or {}
        self.observation_ids = observation_ids or []
        self.source_ids = source_ids or []

    def complete(self, request):
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            metrics=self.metrics,
            metric_units=self.metric_units,
            metric_periods=self.metric_periods,
            observation_ids=self.observation_ids,
            source_ids=self.source_ids,
        )


class MutatingContextAdapter:
    def complete(self, request):
        request.context["company"]["source_ids"].append("invented-source")
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            source_ids=["invented-source"],
        )


class CrossCallMutationAdapter:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        if request.role == "macro":
            request.context["shared_facts"]["company"]["findings"].append(
                "mutation-from-macro"
            )
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
        )


class AgentRuntimeTests(unittest.TestCase):
    TREND_PERIODS = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")

    def test_agent_call_request_rejects_empty_prompt_version(self):
        with self.assertRaisesRegex(ValueError, "prompt_version must be non-empty"):
            AgentCallRequest(
                role="single_agent",
                ticker="VCB",
                period="2024_Q1",
                context={},
                prompt_version="",
            )

    def gold_config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB", "ACB"),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
            min_manual_labels=4,
            min_metric_coverage=1.0,
        )

    def run_config(self, arm: ExperimentArm) -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id="run-001",
            snapshot_id="gold-v1",
            question_set_id="questions-v1",
            question_id="q1",
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-v1",
            arm=arm,
            model_id="fixture-model",
            source_policy_id="primary-only-v1",
            max_critique_attempts=2 if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE else 0,
        )

    def question_file(self, directory: str) -> Path:
        path = Path(directory) / "questions.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "test",
                    "question_set_id": "questions-v1",
                    "scope": {
                        "issuers": ["VCB", "ACB"],
                        "periods": ["2024_Q1"],
                        "core_metrics": ["bank.npl_g35"],
                        "conditional_metrics": ["bank.roa"],
                    },
                    "questions": [{
                        "id": "q1",
                        "issuer": "VCB",
                        "type": "company_snapshot",
                        "period": "2024_Q1",
                        "prompt": "test question",
                    }],
                }
            ),
            encoding="utf-8",
        )
        return path

    def trend_question_file(self, directory: str) -> Path:
        path = Path(directory) / "trend-questions.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "test",
                    "question_set_id": "trend-questions-v1",
                    "scope": {
                        "issuers": ["VCB", "ACB"],
                        "periods": list(self.TREND_PERIODS),
                        "core_metrics": ["bank.npl_g35"],
                    },
                    "questions": [{
                        "id": "trend-q1",
                        "issuer": "VCB",
                        "type": "company_trend",
                        "periods": list(self.TREND_PERIODS),
                        "prompt": "test trend question",
                    }],
                }
            ),
            encoding="utf-8",
        )
        return path

    def trend_gold_config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB", "ACB"),
            periods=self.TREND_PERIODS,
            required_metrics=("bank.npl_g35",),
            min_manual_labels=4,
            min_metric_coverage=1.0,
        )

    def gold_db(self, directory: str) -> Path:
        path = Path(directory) / "gold.sqlite"
        config = self.gold_config()
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
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fixture-evidence",
                "source-1",
                "data/filing.pdf",
                10,
                "Credit quality",
                "2024_Q1",
                "VCB",
                "NPL group 3-5 was 2.0 percent.",
                1.0,
                "text_layer",
                1,
            ),
        )
        connection.execute(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fixture-macro-evidence",
                "source-1",
                "data/filing.pdf",
                20,
                "Macro context",
                "2024_Q1",
                None,
                "Policy rate was 4.5 percent.",
                1.0,
                "text_layer",
                1,
            ),
        )
        connection.execute(
            "INSERT INTO macro_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "macro-policy-rate",
                "macro.policy_rate",
                4.5,
                "%",
                "2024_Q1",
                "source-1",
                "valid",
                None,
            ),
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("obs-vcb", "VCB", "bank", "bank.npl_g35", 2.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
                ("obs-acb", "ACB", "bank", "bank.npl_g35", 1.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:11", "valid", None),
                ("obs-mbb", "MBB", "bank", "bank.npl_g35", 99.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:12", "valid", None),
            ],
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("label-vcb-1", "obs-vcb", "value_check", 2.0, None, "checker-1", "2026-09-04T00:00:00", "page:10", "matched"),
                ("label-vcb-2", "obs-vcb", "value_check", 2.0, None, "checker-2", "2026-09-04T00:00:00", "page:10", "matched"),
                ("label-acb-1", "obs-acb", "value_check", 1.0, None, "checker-1", "2026-09-04T00:00:00", "page:11", "matched"),
                ("label-acb-2", "obs-acb", "value_check", 1.0, None, "checker-2", "2026-09-04T00:00:00", "page:11", "matched"),
            ],
        )
        connection.commit()
        connection.close()
        return path

    def trend_gold_db(self, directory: str) -> Path:
        path = self.gold_db(directory)
        connection = sqlite3.connect(path)
        connection.execute(
            "UPDATE snapshot_metadata SET config_json = ?",
            (json.dumps(self.trend_gold_config().model_dump(mode="json"), sort_keys=True),),
        )
        rows = []
        labels = []
        for period_index, period in enumerate(self.TREND_PERIODS[1:], start=2):
            for ticker, value in (("VCB", 2.0 + period_index), ("ACB", 1.0 + period_index)):
                observation_id = f"obs-{ticker.lower()}-{period}"
                rows.append(
                    (
                        observation_id,
                        ticker,
                        "bank",
                        "bank.npl_g35",
                        value,
                        "%",
                        period,
                        f"2024-{period_index * 3:02d}-30",
                        "point_in_time",
                        "source-1",
                        f"page:{20 + period_index}",
                        "valid",
                        None,
                    )
                )
                labels.extend(
                    [
                        (
                            f"label-{ticker.lower()}-{period}-a",
                            observation_id,
                            "value_check",
                            value,
                            None,
                            "checker-1",
                            "2026-09-04T00:00:00",
                            f"page:{20 + period_index}",
                            "matched",
                        ),
                        (
                            f"label-{ticker.lower()}-{period}-b",
                            observation_id,
                            "value_check",
                            value,
                            None,
                            "checker-2",
                            "2026-09-04T00:00:00",
                            f"page:{20 + period_index}",
                            "matched",
                        ),
                    ]
                )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            labels,
        )
        connection.commit()
        connection.close()
        return path

    def test_single_agent_receives_one_prepared_context(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            result = run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.SINGLE_AGENT),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
            )

        self.assertEqual(result.call_count, 1)
        self.assertEqual([call.role for call in adapter.requests], ["single_agent"])
        self.assertEqual(adapter.requests[0].question_id, "q1")
        self.assertEqual(adapter.requests[0].question_type, "company_snapshot")
        self.assertEqual(adapter.requests[0].question_prompt, "test question")
        self.assertEqual(
            set(adapter.requests[0].context),
            {"company", "sector", "macro", "evidence"},
        )

    def test_company_trend_receives_all_requested_periods_in_one_context(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            config = self.run_config(ExperimentArm.SINGLE_AGENT).model_copy(
                update={
                    "snapshot_id": "gold-v1",
                    "question_set_id": "trend-questions-v1",
                    "question_id": "trend-q1",
                }
            )
            run_agent_arm(
                self.trend_gold_db(directory),
                config,
                self.trend_question_file(directory),
                self.trend_gold_config(),
                "VCB",
                "2024_Q4",
                ("bank.npl_g35",),
                adapter,
                question_periods=self.TREND_PERIODS,
            )

        request = adapter.requests[0]
        self.assertEqual(request.periods, self.TREND_PERIODS)
        self.assertEqual(tuple(request.context["period_order"]), self.TREND_PERIODS)
        self.assertEqual(
            tuple(request.context["periods"]),
            self.TREND_PERIODS,
        )
        self.assertEqual(
            request.context["periods"]["2024_Q1"]["company"]["metrics"]["bank.npl_g35"],
            2.0,
        )
        self.assertEqual(
            request.context["periods"]["2024_Q4"]["company"]["metrics"]["bank.npl_g35"],
            6.0,
        )

    def test_company_trend_anomaly_scan_checks_each_period_context(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            config = self.run_config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE).model_copy(
                update={
                    "snapshot_id": "gold-v1",
                    "question_set_id": "trend-questions-v1",
                    "question_id": "trend-q1",
                }
            )
            result = run_agent_arm(
                self.trend_gold_db(directory),
                config,
                self.trend_question_file(directory),
                self.trend_gold_config(),
                "VCB",
                "2024_Q4",
                ("bank.npl_g35",),
                adapter,
                question_periods=self.TREND_PERIODS,
            )

        self.assertEqual(result.anomaly_triggers, ())
        self.assertEqual(result.call_count, 4)

    def test_company_trend_without_complete_period_context_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            config = self.run_config(ExperimentArm.SINGLE_AGENT).model_copy(
                update={
                    "snapshot_id": "gold-v1",
                    "question_set_id": "trend-questions-v1",
                    "question_id": "trend-q1",
                }
            )
            with self.assertRaisesRegex(ValueError, "question_requires_multi_period_runtime"):
                run_agent_arm(
                    self.trend_gold_db(directory),
                    config,
                    self.trend_question_file(directory),
                    self.trend_gold_config(),
                    "VCB",
                    "2024_Q4",
                    ("bank.npl_g35",),
                    adapter,
                )

            self.assertEqual(adapter.requests, [])

    def test_runtime_sector_context_uses_gold_scope_not_all_bank_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.SINGLE_AGENT),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
            )

        sector = adapter.requests[0].context["sector"]
        self.assertEqual(sector["sector_benchmarks"]["bank.npl_g35"], 1.5)
        self.assertNotIn("obs-mbb", sector["observation_ids"])

    def test_adapter_request_carries_configured_prompt_version(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.SINGLE_AGENT),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
            )

        self.assertEqual(
            [request.prompt_version for request in adapter.requests],
            ["prompt-contract-v1"],
        )

    def test_hierarchical_without_critique_dispatches_workers_then_orchestrator(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            result = run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
                verification_requests=("should-not-run",),
            )

        self.assertEqual(result.call_count, 4)
        self.assertEqual(
            [call.role for call in adapter.requests],
            ["macro", "sector", "company", "orchestrator"],
        )

    def test_bounded_critique_never_exceeds_two_verification_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            result = run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
                verification_requests=("one", "two", "three"),
            )

        self.assertEqual(result.call_count, 6)
        self.assertEqual([call.role for call in adapter.requests[-2:]], ["verification", "verification"])
        self.assertEqual([call.attempt for call in adapter.requests[-2:]], [1, 2])

    def test_bounded_critique_uses_generated_triggers_when_requests_are_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            result = run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.roa",),
                adapter,
            )

        self.assertEqual(result.call_count, 6)
        self.assertEqual(
            [trigger.rule_id for trigger in result.anomaly_triggers],
            ["company_metric_missing", "sector_benchmark_missing"],
        )
        self.assertEqual([call.role for call in adapter.requests[-2:]], ["verification", "verification"])
        self.assertIn("company observation", adapter.requests[-2].context["request"])

    def test_candidate_snapshot_is_rejected_before_adapter_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.sqlite"
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("candidate", "2026-09-04T00:00:00Z", "normalized_candidate_pending_validation", "{}"),
            )
            connection.commit()
            connection.close()
            adapter = RecordingAdapter()

            with self.assertRaises(ExperimentInputError) as context:
                run_agent_arm(
                    path,
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    adapter,
                )

        self.assertIn("snapshot_not_gold", context.exception.blockers)
        self.assertEqual(adapter.requests, [])

    def test_unknown_source_policy_is_rejected_before_adapter_call(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            config = self.run_config(ExperimentArm.SINGLE_AGENT).model_copy(
                update={"source_policy_id": "unregistered-policy-v1"}
            )
            with self.assertRaisesRegex(ValueError, "unknown_source_policy"):
                run_agent_arm(
                    self.gold_db(directory),
                    config,
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    adapter,
                )

            self.assertEqual(adapter.requests, [])

    def test_runtime_request_must_match_selected_question_issuer_and_period(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            with self.assertRaisesRegex(ValueError, "question_issuer_mismatch"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "ACB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    adapter,
                )

            self.assertEqual(adapter.requests, [])

    def test_runtime_request_rejects_period_outside_selected_question(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            with self.assertRaisesRegex(ValueError, "question_period_mismatch"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q2",
                    ("bank.npl_g35",),
                    adapter,
                )

            self.assertEqual(adapter.requests, [])

    def test_runtime_request_rejects_metric_outside_question_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            with self.assertRaisesRegex(ValueError, "metric_outside_question_scope"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.cir",),
                    adapter,
                )

            self.assertEqual(adapter.requests, [])

    def test_agent_output_must_match_requested_ticker_and_period(self):
        cases = (
            (MismatchedScopeAdapter(agent_id="company"), "payload_agent_id_mismatch"),
            (MismatchedScopeAdapter(ticker="ACB"), "payload_ticker_mismatch"),
            (MismatchedScopeAdapter(ticker=None), "payload_ticker_mismatch"),
            (MismatchedScopeAdapter(period="2024_Q2"), "payload_period_mismatch"),
        )
        for adapter, blocker in cases:
            with self.subTest(blocker=blocker), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, blocker):
                    run_agent_arm(
                        self.gold_db(directory),
                        self.run_config(ExperimentArm.SINGLE_AGENT),
                        self.question_file(directory),
                        self.gold_config(),
                        "VCB",
                        "2024_Q1",
                        ("bank.npl_g35",),
                        adapter,
                    )

    def test_agent_output_metric_scope_and_metadata_are_bound_to_request(self):
        cases = (
            (
                MetricContractAdapter(
                    metrics={"bank.cir": 1.0},
                    metric_units={"bank.cir": "%"},
                    metric_periods={"bank.cir": "2024_Q1"},
                ),
                "payload_metric_outside_request",
            ),
            (
                MetricContractAdapter(metrics={"bank.npl_g35": 2.0}),
                "payload_metric_unit_missing",
            ),
            (
                MetricContractAdapter(
                    metrics={"bank.npl_g35": 2.0},
                    metric_units={"bank.npl_g35": "%"},
                    metric_periods={"bank.npl_g35": "2024_Q2"},
                ),
                "payload_metric_period_outside_request",
            ),
            (
                MetricContractAdapter(
                    metrics={"bank.npl_g35": 2.0},
                    metric_units={"bank.npl_g35": "%"},
                    metric_periods={"bank.npl_g35": "2024_Q1"},
                ),
                "payload_numeric_metric_without_provenance",
            ),
        )
        for adapter, blocker in cases:
            with self.subTest(blocker=blocker), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, blocker):
                    run_agent_arm(
                        self.gold_db(directory),
                        self.run_config(ExperimentArm.SINGLE_AGENT),
                        self.question_file(directory),
                        self.gold_config(),
                        "VCB",
                        "2024_Q1",
                        ("bank.npl_g35",),
                        adapter,
                    )

    def test_adapter_cannot_invent_provenance_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = InventedProvenanceAdapter()

            with self.assertRaisesRegex(ValueError, "source_id_not_in_context"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    adapter,
                )

    def test_adapter_cannot_modify_context_evidence_before_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "evidence_payload_mismatch"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    TamperedEvidenceAdapter(),
                )

    def test_adapter_cannot_expand_provenance_context_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "source_id_not_in_context"):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    self.question_file(directory),
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    MutatingContextAdapter(),
                )

    def test_worker_context_is_isolated_across_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = CrossCallMutationAdapter()
            run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
            )

        sector_request = adapter.requests[1]
        self.assertNotIn(
            "mutation-from-macro",
            sector_request.context["shared_facts"]["company"]["findings"],
        )

    def test_all_arms_receive_identical_prepared_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.gold_db(directory)
            question_path = self.question_file(directory)
            prepared_by_arm = {}

            for arm in ExperimentArm:
                adapter = RecordingAdapter()
                run_agent_arm(
                    db_path,
                    self.run_config(arm),
                    question_path,
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    adapter,
                )
                context = adapter.requests[0].context
                prepared_by_arm[arm.value] = (
                    context
                    if arm is ExperimentArm.SINGLE_AGENT
                    else context["shared_facts"]
                )

        self.assertEqual(prepared_by_arm["single_agent"], prepared_by_arm["hierarchical_no_critique"])
        self.assertEqual(prepared_by_arm["single_agent"], prepared_by_arm["hierarchical_bounded_critique"])

    def test_prepared_context_includes_period_aligned_macro_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = RecordingAdapter()
            run_agent_arm(
                self.gold_db(directory),
                self.run_config(ExperimentArm.SINGLE_AGENT),
                self.question_file(directory),
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                adapter,
                macro_indicator_ids=("macro.policy_rate",),
            )

        evidence_ids = {
            evidence["evidence_id"] for evidence in adapter.requests[0].context["evidence"]
        }
        self.assertIn("fixture-macro-evidence", evidence_ids)

    def test_macro_question_requires_declared_macro_indicators_at_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            question_path = self.question_file(directory)
            payload = json.loads(question_path.read_text(encoding="utf-8"))
            payload["questions"][0].update(
                {
                    "type": "macro_to_bank",
                    "macro_indicator_ids": ["macro.policy_rate"],
                    "bank_metric_ids": ["bank.npl_g35"],
                    "causal_claim_policy": "association_only",
                }
            )
            question_path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ExperimentInputError,
                "macro_indicator_scope_mismatch",
            ):
                run_agent_arm(
                    self.gold_db(directory),
                    self.run_config(ExperimentArm.SINGLE_AGENT),
                    question_path,
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    RecordingAdapter(),
                )


if __name__ == "__main__":
    unittest.main()
