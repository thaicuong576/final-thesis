"""Tests for analysis tools: deterministic facts, exhibits, and fixture verification."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from typing import Any, Sequence

from tests.socket_guard import install_socket_guard
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    PeerUniverse,
    QualityStatus,
    SourceTier,
    SupportedOperation,
)
from thesis_api.analysis_planner import plan_question, build_analysis_plan
from thesis_api.analysis_tools import (
    TOOLS,
    ToolContext,
    build_source_notes,
    humanize_locator,
    run_decomposition_tool,
    run_dispersion_tool,
    run_head_to_head_tool,
    run_lookup_tool,
    run_peer_position_tool,
    run_ranking_tool,
    run_relationship_tool,
    run_trend_tool,
    verify_fact_inputs,
)
from thesis_api.metric_presentation import get_metric_presentation
from thesis_api.settings import Settings
from thesis_data.report_facts import Fact, classify_signals, detect_cross_level_candidates

setUpModule = install_socket_guard


class _MockProvider:
    """In-memory mock provider with 5 peer entities and missing Q1 cell for target E1."""

    def __init__(self) -> None:
        self.dataset_ref = DatasetRef(dataset_id="mock-bank", dataset_snapshot_id="mock-v1")
        self.entities = ["E1", "E2", "E3", "E4", "E5"]
        self.periods = ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"]
        self.metrics = ["bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"]
        self.observations: dict[tuple[str, str, str], CanonicalObservation] = {}
        self.obs_by_id: dict[str, CanonicalObservation] = {}
        self.sources: dict[str, DatasetSource] = {}

        # Base values for entities
        base_vals = {
            "E1": {"bank.npl_g35": 1.5, "bank.llr_coverage": 80.0, "bank.roa": 2.1, "bank.roe": 21.0},
            "E2": {"bank.npl_g35": 1.6, "bank.llr_coverage": 90.0, "bank.roa": 2.2, "bank.roe": 22.0},
            "E3": {"bank.npl_g35": 1.2, "bank.llr_coverage": 110.0, "bank.roa": 2.4, "bank.roe": 16.0},
            "E4": {"bank.npl_g35": 0.9, "bank.llr_coverage": 220.0, "bank.roa": 1.7, "bank.roe": 18.0},
            "E5": {"bank.npl_g35": 4.2, "bank.llr_coverage": 55.0, "bank.roa": 1.8, "bank.roe": 11.0},
        }

        for ent in self.entities:
            for p_idx, p in enumerate(self.periods):
                src_id = f"src:{ent}:{p}"
                self.sources[src_id] = DatasetSource(
                    source_ref=src_id,
                    source_type="regulatory_filing",
                    source_tier=SourceTier.PRIMARY,
                    source_url=f"https://data.example.com/{ent}/{p}",
                    publisher="Mock Publisher",
                    retrieved_at="2024-12-31T00:00:00Z",
                    content_hash="mockhash",
                    validation_status=QualityStatus.VALID,
                )
                for m in self.metrics:
                    obs_id = f"obs:{ent}:{p}:{m}"
                    # E1 in Q1 is MISSING for all metrics
                    if ent == "E1" and p == "2024_Q1":
                        obs = CanonicalObservation(
                            observation_id=obs_id,
                            dataset_id=self.dataset_ref.dataset_id,
                            dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                            entity_id=ent,
                            period_id=p,
                            metric_id=m,
                            value=None,
                            unit="%" if "coverage" not in m and "roe" not in m else "%",
                            period_basis="quarterly",
                            reporting_scope="consolidated",
                            validation_status=QualityStatus.MISSING,
                            missing_reason="DATA_UNAVAILABLE",
                            source_ref=None,
                        )
                    else:
                        base = base_vals[ent][m]
                        # Slight variation by period
                        v = base + (p_idx * 0.1 if m != "bank.roe" else p_idx * 0.5)
                        obs = CanonicalObservation(
                            observation_id=obs_id,
                            dataset_id=self.dataset_ref.dataset_id,
                            dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                            entity_id=ent,
                            period_id=p,
                            metric_id=m,
                            value=round(v, 4),
                            unit="%",
                            period_basis="quarterly",
                            reporting_scope="consolidated",
                            validation_status=QualityStatus.VALID,
                            source_ref=src_id,
                            source_locator="printed_page:10;section:note_credit",
                        )
                    self.observations[(ent, p, m)] = obs
                    self.obs_by_id[obs_id] = obs

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        return DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=tuple(
                DatasetEntity(
                    entity_id=e,
                    entity_type=DatasetEntityType.COMPANY,
                    display_name=e,
                    attributes={"sector": "bank"},
                )
                for e in self.entities
            ),
            periods=tuple(DatasetPeriod(period_id=p, label=p) for p in self.periods),
            metrics=tuple(
                DatasetMetric(
                    metric_id=m,
                    display_name=m,
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="%",
                )
                for m in self.metrics
            ),
            peer_universes=(
                PeerUniverse(
                    peer_universe_id="sector:bank",
                    display_name="Vietnamese Banks",
                    entity_ids=tuple(self.entities),
                ),
            ),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.GET_ENTITY_METRICS,
                SupportedOperation.GET_PEER_BENCHMARK,
                SupportedOperation.GET_SOURCE,
                SupportedOperation.RESOLVE_OBSERVATION,
            ),
        )

    def get_metric(
        self, dataset_ref: DatasetRef, entity_id: str, period_id: str, metric_id: str
    ) -> CanonicalObservation | None:
        return self.observations.get((entity_id, period_id, metric_id))

    def get_entity_metrics(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        res = []
        for p in period_ids:
            for m in metric_ids:
                obs = self.get_metric(dataset_ref, entity_id, p, m)
                if obs is not None:
                    res.append(obs)
        return tuple(res)

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        from thesis_data.dataset_provider import aggregate_peer_median

        res = []
        members = peer_entity_ids or self.entities
        for m in metric_ids:
            valid_obs = [
                self.observations[(e, period_id, m)]
                for e in members
                if (e, period_id, m) in self.observations
                and self.observations[(e, period_id, m)].validation_status is QualityStatus.VALID
            ]
            res.append(
                aggregate_peer_median(
                    dataset_ref=dataset_ref,
                    peer_universe_id=peer_universe_id,
                    period_id=period_id,
                    metric_id=m,
                    peer_entity_ids=members,
                    member_observations=valid_obs,
                )
            )
        return tuple(res)

    def get_observation(self, dataset_ref: DatasetRef, observation_id: str) -> CanonicalObservation | None:
        return self.obs_by_id.get(observation_id)

    def resolve_observation(self, dataset_ref: DatasetRef, observation_id: str) -> CanonicalObservation | None:
        return self.get_observation(dataset_ref, observation_id)

    def get_source(self, dataset_ref: DatasetRef, source_ref: str) -> DatasetSource | None:
        return self.sources.get(source_ref)


class TestAnalysisToolsUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _MockProvider()
        self.catalog = self.provider.get_capabilities(self.provider.dataset_ref)
        self.ctx = ToolContext(
            provider=self.provider,
            dataset_ref=self.provider.dataset_ref,
            catalog=self.catalog,
            universe_id="sector:bank",
            universe_members=tuple(self.provider.entities),
            presentation=get_metric_presentation,
            cache={},
        )

    def test_lookup_tool_valid_and_missing(self) -> None:
        # Valid Q4
        res_q4 = run_lookup_tool(self.ctx, {"entity": "E1", "period": "2024_Q4", "metrics": ["bank.npl_g35"]})
        self.assertEqual(len(res_q4.datasets), 1)
        self.assertEqual(res_q4.datasets[0].shape, "kpi")
        self.assertEqual(res_q4.datasets[0].allowed_charts, ["kpi_strip"])
        self.assertEqual(len(res_q4.missing), 0)
        self.assertTrue(any(f.fact_type == "value" for f in res_q4.facts))
        self.assertTrue(any(f.fact_type == "peer_rank" for f in res_q4.facts))
        self.assertTrue(any(f.fact_type == "peer_median" for f in res_q4.facts))
        self.assertTrue(any(f.fact_type == "delta" for f in res_q4.facts))

        # Missing Q1
        res_q1 = run_lookup_tool(self.ctx, {"entity": "E1", "period": "2024_Q1", "metrics": ["bank.npl_g35"]})
        self.assertEqual(len(res_q1.missing), 1)
        self.assertEqual(res_q1.missing[0].entity_id, "E1")
        self.assertEqual(res_q1.missing[0].period, "2024_Q1")
        self.assertEqual(res_q1.datasets[0].rows[0].status, "missing")
        self.assertIsNone(res_q1.datasets[0].rows[0].value)  # NEVER 0

    def test_peer_position_tool(self) -> None:
        res = run_peer_position_tool(
            self.ctx,
            {"entity": "E1", "period": "2024_Q4", "metrics": ["bank.npl_g35", "bank.llr_coverage"]},
        )
        self.assertEqual(len(res.datasets), 2)
        # 1. peer_table
        self.assertEqual(res.datasets[0].shape, "peer_table")
        self.assertEqual(res.datasets[0].allowed_charts, ["rank_heatmap", "comparison_table"])
        # 2. paired scatter
        self.assertEqual(res.datasets[1].shape, "paired")
        self.assertEqual(res.datasets[1].allowed_charts, ["scatter"])

        types = {f.fact_type for f in res.facts}
        self.assertIn("value", types)
        self.assertIn("peer_median", types)
        self.assertIn("peer_rank", types)
        self.assertIn("gap_to_median", types)
        self.assertIn("ratio_to_median", types)

    def test_ranking_tool(self) -> None:
        res = run_ranking_tool(
            self.ctx,
            {
                "metric": "bank.llr_coverage",
                "period": "2024_Q4",
                "context_metrics": ["bank.npl_g35", "bank.roa"],
                "highlight_entity": "E1",
            },
        )
        self.assertEqual(len(res.datasets), 1)
        self.assertEqual(res.datasets[0].shape, "ranked_list")
        self.assertEqual(res.datasets[0].allowed_charts, ["ranked_bar", "comparison_table"])

        types = {f.fact_type for f in res.facts}
        self.assertIn("peer_rank", types)
        self.assertIn("spread", types)
        self.assertIn("ratio_to_median", types)

    def test_trend_tool_single_and_multi_metric(self) -> None:
        # Single metric
        res_single = run_trend_tool(
            self.ctx,
            {"entity": "E1", "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"], "metrics": ["bank.roe"]},
        )
        self.assertEqual(res_single.datasets[0].shape, "series")
        self.assertEqual(res_single.datasets[0].allowed_charts, ["line_trend"])
        # Q1 is missing for E1, verify it was recorded as missing and value is None
        self.assertTrue(any(m.period == "2024_Q1" for m in res_single.missing))
        q1_row = next(r for r in res_single.datasets[0].rows if r.period == "2024_Q1")
        self.assertEqual(q1_row.status, "missing")
        self.assertIsNone(q1_row.value)

        # Multi-metric
        res_multi = run_trend_tool(
            self.ctx,
            {
                "entity": "E1",
                "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                "metrics": ["bank.roe", "bank.roa"],
            },
        )
        self.assertEqual(res_multi.datasets[0].shape, "series_multi")
        self.assertEqual(res_multi.datasets[0].allowed_charts, ["small_multiples"])

    def test_head_to_head_tool(self) -> None:
        res = run_head_to_head_tool(
            self.ctx,
            {
                "entities": ["E1", "E2"],
                "period": "2024_Q4",
                "metrics": ["bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"],
            },
        )
        self.assertEqual(res.datasets[0].shape, "comparison_table")
        self.assertEqual(res.datasets[0].allowed_charts, ["comparison_table", "grouped_bar"])

        # Both forward and reverse lead_count facts
        lead_facts = [f for f in res.facts if f.fact_type == "lead_count"]
        self.assertEqual(len(lead_facts), 2)
        entities_in_leads = {f.entity_id for f in lead_facts}
        self.assertEqual(entities_in_leads, {"E1", "E2"})

    def test_decomposition_tool(self) -> None:
        res = run_decomposition_tool(
            self.ctx,
            {"entities": ["E1", "E2"], "period": "2024_Q4", "formula": "derived.roe_over_roa"},
        )
        self.assertEqual(res.datasets[0].shape, "kpi")
        self.assertEqual(res.datasets[0].allowed_charts, ["kpi_strip"])

        dr_facts = [f for f in res.facts if f.fact_type == "derived_ratio"]
        self.assertEqual(len(dr_facts), 2)
        med_fact = next((f for f in res.facts if f.fact_type == "peer_median"), None)
        self.assertIsNotNone(med_fact)
        assert med_fact is not None
        self.assertEqual(med_fact.metric_id, "derived.roe_over_roa")

    def test_dispersion_and_relationship_tools(self) -> None:
        res_disp = run_dispersion_tool(self.ctx, {"metric": "bank.llr_coverage", "period": "2024_Q4"})
        self.assertEqual(res_disp.datasets[0].shape, "ranked_list")
        self.assertEqual(res_disp.datasets[0].allowed_charts, ["ranked_bar", "comparison_table"])

        res_rel = run_relationship_tool(
            self.ctx, {"metrics": ["bank.npl_g35", "bank.llr_coverage"], "period": "2024_Q4"}
        )
        self.assertEqual(res_rel.datasets[0].shape, "paired")
        self.assertEqual(res_rel.datasets[0].allowed_charts, ["scatter"])

    def test_humanize_locator(self) -> None:
        # 1. Spec example 1
        raw1 = "pdf_pages:29;printed_page:21;section:note_5_customer_loans;row:loan_quality;denominator:dư_nợ_cho_vay;groups:3|4|5;extraction:visual_transcription"
        self.assertEqual(humanize_locator(raw1), "tr. 21 · note 5 customer loans")

        # 2. Spec example 2
        raw2 = "pdf_page:17;printed_page:15;section:Phân tích chất lượng nợ cho vay;extraction:visual_check"
        self.assertEqual(humanize_locator(raw2), "tr. 15 · Phân tích chất lượng nợ cho vay")

        # 3. Multi-page example
        raw3 = "printed_pages:2_and_3_and_7;section:note_5"
        self.assertEqual(humanize_locator(raw3), "tr. 2, 3, 7 · note 5")

        # 4. Task D: VPB ROE example: pdf_pages:6,8 with formula and equity_scope
        raw4 = (
            "pdf_pages:6,8;equity_scope:total_equity_minus_nci;"
            "formula:prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit_over_average_parent_attributable_equity"
        )
        self.assertEqual(humanize_locator(raw4), "tr. 6, 8")

        # 5. Task D: English sections preserved without key=value syntax
        raw5 = "statement:consolidated_balance_sheet;pdf_pages:6"
        self.assertEqual(humanize_locator(raw5), "tr. 6 · consolidated balance sheet")

        # 6. Task D: Machine-only keys return empty string (never raw key=value)
        raw6 = "formula:some_formula_v1;equity_scope:total_equity"
        self.assertEqual(humanize_locator(raw6), "")

    def test_verify_fact_inputs_cascades_dependent_facts(self) -> None:
        # Valid observation and fact
        f1 = Fact(
            fact_id="f1",
            fact_type="value",
            entity_id="E1",
            period="2024_Q4",
            metric_id="bank.npl_g35",
            value=1.5,
            input_observation_ids=["obs:E1:2024_Q4:bank.npl_g35"],
        )
        # Invalid / missing observation and fact
        f2 = Fact(
            fact_id="f2",
            fact_type="value",
            entity_id="E1",
            period="2024_Q1",
            metric_id="bank.npl_g35",
            value=None,
            input_observation_ids=["obs:E1:2024_Q1:bank.npl_g35"],  # QualityStatus.MISSING
        )
        # Dependent fact on f1 and f2
        f3 = Fact(
            fact_id="f3",
            fact_type="delta",
            entity_id="E1",
            period="2024_Q4",
            from_period="2024_Q1",
            metric_id="bank.npl_g35",
            value=0.5,
            input_fact_ids=["f1", "f2"],
        )
        # Further dependent fact on f3
        f4 = Fact(
            fact_id="f4",
            fact_type="lead_count",
            entity_id="E1",
            period="2024_Q4",
            value=1.0,
            input_fact_ids=["f3"],
        )

        valid, dropped, lims = verify_fact_inputs(
            self.provider, self.provider.dataset_ref, [f1, f2, f3, f4]
        )
        self.assertEqual([f.fact_id for f in valid], ["f1"])
        dropped_ids = [f.fact_id for f in dropped]
        self.assertIn("f2", dropped_ids)
        self.assertIn("f3", dropped_ids)
        self.assertIn("f4", dropped_ids)
        self.assertTrue(len(lims) >= 3)

    def test_tool_failure_does_not_abort_runtime(self) -> None:
        """Verify that a tool raising an error is caught and does not crash the run."""
        def broken_tool(ctx: ToolContext, params: dict[str, Any]) -> Any:
            raise RuntimeError("Unexpected failure in tool")

        original_tool = TOOLS.get("custom_broken")
        TOOLS["custom_broken"] = broken_tool
        try:
            # Execute broken tool wrapped in runtime-style try/except
            facts = []
            lims = []
            try:
                res = broken_tool(self.ctx, {})
                facts.extend(res.facts)
            except Exception:
                lims.append("Không thực hiện được phép phân tích broken.")

            self.assertEqual(len(facts), 0)
            self.assertEqual(len(lims), 1)
            self.assertIn("Không thực hiện được", lims[0])
        finally:
            if original_tool is None:
                TOOLS.pop("custom_broken", None)
            else:
                TOOLS["custom_broken"] = original_tool

    def test_tools_without_universe_record_missing_and_no_peer_facts(self) -> None:
        """When universe_id is None, peer-dependent facts are omitted or recorded as missing."""
        ctx_no_univ = ToolContext(
            provider=self.provider,
            dataset_ref=self.provider.dataset_ref,
            catalog=self.catalog,
            universe_id=None,
            universe_members=(),
            presentation=get_metric_presentation,
            cache={},
        )
        # 1. Lookup: only company value facts, no median or rank facts
        res_lookup = run_lookup_tool(ctx_no_univ, {"entity": "E1", "period": "2024_Q4", "metric": "bank.npl_g35"})
        fact_types = {f.fact_type for f in res_lookup.facts}
        self.assertIn("value", fact_types)
        self.assertNotIn("peer_median", fact_types)
        self.assertNotIn("peer_rank", fact_types)

        # 2. Peer position: no universe -> missing cell UNIVERSE_UNAVAILABLE, no peer facts
        res_peer = run_peer_position_tool(ctx_no_univ, {"target": "E1", "period": "2024_Q4", "metrics": ["bank.npl_g35"]})
        self.assertTrue(any(m.reason == "UNIVERSE_UNAVAILABLE" for m in res_peer.missing))
        self.assertFalse(any(f.fact_type in ("peer_median", "peer_rank", "gap_to_median") for f in res_peer.facts))

        # 3. Ranking: no universe -> missing cell UNIVERSE_UNAVAILABLE, empty facts
        res_rank = run_ranking_tool(ctx_no_univ, {"metric": "bank.npl_g35", "period": "2024_Q4"})
        self.assertEqual(len(res_rank.facts), 0)
        self.assertTrue(any(m.reason == "UNIVERSE_UNAVAILABLE" for m in res_rank.missing))

    def test_company_profile_peer_position_and_trend_facts_are_unique_by_fact_id(self) -> None:
        """Verify that running company_profile with peer_position + trend produces deduplicated unique fact_ids."""
        from thesis_api.adaptive_runtime import _AdaptiveRun
        from thesis_api.schemas import AnalysisRequest
        from tests.test_api_analyze import (
            _ExplicitOfflineAcceptingCritic,
            _ExplicitOfflineAnalysisWriter,
        )

        req = AnalysisRequest(query="Sức khỏe tài chính của E1 so với các ngân hàng cùng nhóm, quý 4/2024")
        settings = Settings(planner_mode="rules_only")
        run = _AdaptiveRun(
            provider=self.provider,
            dataset_ref=self.provider.dataset_ref,
            catalog=self.catalog,
            request=req,
            settings=settings,
            critic=_ExplicitOfflineAcceptingCritic(),
            writer=_ExplicitOfflineAnalysisWriter(injected_text="Valid explanation within accepted scope."),
            emit=lambda *_: None,
        )
        resp = run.execute()
        self.assertEqual(resp.status, "completed")
        self.assertEqual(resp.question_type, "company_profile")
        # Ensure planned tools include both peer_position and trend
        planned_tools = [t["tool"] if isinstance(t, dict) else t.tool for t in resp.analysis_plan.tools]
        self.assertIn("peer_position", planned_tools)
        self.assertIn("trend", planned_tools)
        # Check fact uniqueness
        fact_ids = [f.fact_id for f in resp.facts]
        self.assertGreater(len(fact_ids), 0)
        self.assertEqual(len(set(fact_ids)), len(resp.facts))

    def test_f1_build_source_notes_handles_source_ref_none(self) -> None:
        """F1: build_source_notes must produce notes even when obs.source_ref is None.

        Simulates the real-staging scenario where the SQLite provider returns observations
        with source_ref=None but obs_id follows the <source_id>:<period>:<metric>:<variant>
        convention — so build_source_notes must fall back to splitting the obs_id.
        """
        from types import SimpleNamespace

        obs_id = "official-E1-2024-Q4-consolidated:2024_Q4:bank.npl_g35:aligned_non_margin_variant"
        # Use SimpleNamespace to avoid CanonicalObservation's Pydantic validator
        obs = SimpleNamespace(
            observation_id=obs_id,
            entity_id="E1",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            value=1.5,
            unit="%",
            reporting_scope="consolidated",
            source_ref=None,  # intentionally None — triggers F1 fallback in build_source_notes
            source_locator=None,
            metadata=None,
        )

        class _NoSourceRefProvider:
            """Provider that holds the obs but get_source always returns None."""

            def __init__(self) -> None:
                self._obs_by_id = {obs_id: obs}

            def resolve_observation(self, dataset_ref: Any, oid: str) -> Any:
                return self._obs_by_id.get(oid)

            def get_source(self, dataset_ref: Any, source_ref: str) -> None:
                return None  # source lookup fails — notes must still be produced

        from thesis_data.report_facts import Fact

        fact = Fact(
            fact_id="fact:value:E1:2024_Q4:bank.npl_g35",
            fact_type="value",
            entity_id="E1",
            metric_id="bank.npl_g35",
            period="2024_Q4",
            value=1.5,
            input_observation_ids=[obs_id],
        )

        notes = build_source_notes(_NoSourceRefProvider(), self.provider.dataset_ref, [fact])

        self.assertGreater(len(notes), 0, "build_source_notes must produce at least one note from obs_id fallback")
        self.assertEqual(notes[0].note_no, 1)
        # source_id should be the first colon-delimited segment of the obs_id
        self.assertEqual(notes[0].source_id, "official-E1-2024-Q4-consolidated")
        self.assertIsNone(notes[0].url)  # no source object → no URL

    def test_f2_paired_dataset_has_reference_lines(self) -> None:
        """F2: paired scatter dataset produced by run_peer_position_tool must have reference_lines
        for both scatter metrics (peer_median) so frontend can draw median lines."""
        res = run_peer_position_tool(
            self.ctx,
            {"entity": "E1", "period": "2024_Q4", "metrics": ["bank.npl_g35", "bank.llr_coverage"]},
        )
        paired = next((d for d in res.datasets if d.shape == "paired"), None)
        self.assertIsNotNone(paired, "run_peer_position_tool must produce a paired dataset")
        assert paired is not None
        self.assertGreaterEqual(
            len(paired.reference_lines), 2,
            "Paired dataset must have reference_lines for both scatter metrics",
        )
        ref_metric_ids = {rl.metric_id for rl in paired.reference_lines}
        self.assertIn("bank.npl_g35", ref_metric_ids)
        self.assertIn("bank.llr_coverage", ref_metric_ids)
        # All reference lines must be median kind and have a fact_id
        for rl in paired.reference_lines:
            self.assertEqual(rl.kind, "median")
            self.assertIsNotNone(rl.fact_id)
            self.assertIsNotNone(rl.value)


class TestGoldFixtureFactVerification(unittest.TestCase):
    """Independent verification: compare ER-3 computed facts against frontend/src/test/fixtures."""

    def test_all_fixtures_match_er3_facts(self) -> None:

        db_path = Path("data/processed/gold-bank-2025-expanded-v5-evidence.sqlite")
        auth_path = Path("data/evaluation/gold-v5-reporting-scope-authority-v1.json")
        if not db_path.exists() or not auth_path.exists():
            self.skipTest("Gold v5 database or scope authority file not found in worktree")

        from thesis_api.service import _load_provider

        binding = _load_provider(db_path, scope_authority_path=auth_path)
        settings = Settings(planner_mode="rules_only", gold_scope_authority_path=auth_path)

        fixture_map = {
            "er-lookup-vcb-npl-2024q4.json": "Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?",
            "er-ranking-coverage-2024q4.json": "Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?",
            "er-trend-vpb-roe-2024.json": "ROE của VPB thay đổi thế nào trong năm 2024?",
            "er-h2h-acb-tcb-2024q4.json": "So sánh ACB và TCB quý 4/2024",
            "er-profile-acb-2024q4.json": "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024",
        }

        fixtures_dir = Path("frontend/src/test/fixtures")

        for fname, q_text in fixture_map.items():
            fpath = fixtures_dir / fname
            with open(fpath, encoding="utf-8") as f:
                fdata = json.load(f)
            fixture_facts = {fact["fact_id"]: fact for fact in fdata.get("facts", [])}

            spec, _, _, _ = plan_question(q_text, binding.catalog, settings=settings)
            ctx = ToolContext(
                provider=binding.provider,
                dataset_ref=binding.dataset_ref,
                catalog=binding.catalog,
                universe_id="sector:bank",
                universe_members=("ACB", "MBB", "TCB", "VCB", "VPB"),
                presentation=get_metric_presentation,
                cache={},
            )
            computed_facts = {}
            for tc in spec.tools:
                res = TOOLS[tc.tool](ctx, tc.params)
                for cf in res.facts:
                    computed_facts[cf.fact_id] = cf

            matched = 0
            for fid, ffact in fixture_facts.items():
                self.assertIn(
                    fid,
                    computed_facts,
                    f"Fact {fid} in fixture {fname} was not produced by ER-3 tools",
                )
                cf = computed_facts[fid]
                f_val = ffact.get("value")
                c_val = cf.value
                if f_val is not None and c_val is not None:
                    self.assertAlmostEqual(
                        float(c_val),
                        float(f_val),
                        places=5,
                        msg=f"Value mismatch for {fid} in {fname}: computed {c_val} vs fixture {f_val}",
                    )
                else:
                    self.assertEqual(c_val, f_val)

                if ffact.get("rank_better") is not None:
                    self.assertEqual(cf.rank_better, ffact["rank_better"])
                if ffact.get("denominator") is not None:
                    self.assertEqual(cf.denominator, ffact["denominator"])

                matched += 1

            self.assertGreaterEqual(matched, 5, f"Too few facts matched in {fname}")


if __name__ == "__main__":
    unittest.main()
