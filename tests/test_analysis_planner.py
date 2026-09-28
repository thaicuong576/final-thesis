"""Tests for analysis planning, rules fallback, model proposals, and AnalysisPlan builder."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()

from thesis_api.analysis_planner import (
    PlanSpec,
    ToolCallSpec,
    build_analysis_plan,
    model_plan,
    plan_question,
    rules_plan,
    validate_plan,
)
from thesis_api.messages_vi import suggestions_for
from thesis_api.query_understanding import resolve_query
from thesis_api.service import AnalysisBlocked
from thesis_data.analysis_plan import AnalysisAgent, RequirementType
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    PeerUniverse,
    SupportedOperation,
)


def _make_test_catalog() -> DatasetCapabilityCatalog:
    ref = DatasetRef(dataset_id="plan-test", dataset_snapshot_id="plan-test-v1")
    entities = tuple(
        DatasetEntity(
            entity_id=f"BANK_{c}",
            entity_type=DatasetEntityType.COMPANY,
            display_name=f"Bank {c}",
            attributes={"ticker": f"BANK_{c}"},
        )
        for c in ("A", "B", "C", "D", "E")
    )
    periods = tuple(
        DatasetPeriod(period_id=f"2024_Q{q}", label=f"2024 Q{q}")
        for q in range(1, 5)
    )
    metrics = (
        DatasetMetric(
            metric_id="bank.npl_g35",
            display_name="Tỷ lệ nợ xấu (nhóm 3–5)",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.llr_coverage",
            display_name="Tỷ lệ bao phủ nợ xấu",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.roa",
            display_name="ROA",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.roe",
            display_name="ROE",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
    )
    peer_universes = (
        PeerUniverse(
            peer_universe_id="universe-banks",
            display_name="Bank universe",
            entity_ids=tuple(e.entity_id for e in entities),
        ),
    )
    return DatasetCapabilityCatalog(
        dataset_ref=ref,
        entities=entities,
        periods=periods,
        metrics=metrics,
        peer_universes=peer_universes,
        supported_operations=(
            SupportedOperation.GET_METRIC,
            SupportedOperation.RESOLVE_OBSERVATION,
            SupportedOperation.GET_SOURCE,
            SupportedOperation.GET_PEER_BENCHMARK,
        ),
    )


class TestAnalysisPlanner(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = _make_test_catalog()

    def test_acceptance_section_a_queries_via_rules(self) -> None:
        # A1: Sức khỏe tài chính của BANK_A so với các ngân hàng cùng nhóm, quý 4/2024
        res1 = resolve_query("Sức khỏe tài chính của BANK_A so với các ngân hàng cùng nhóm, quý 4/2024", self.catalog)
        p1 = rules_plan(res1, self.catalog)
        self.assertEqual(p1.question_type, "company_profile")
        self.assertEqual(p1.focus_entity, "BANK_A")
        self.assertEqual(p1.anchor_period, "2024_Q4")
        self.assertEqual(set(p1.metrics), {"bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"})
        tools1 = [t.tool for t in p1.tools]
        self.assertEqual(tools1, ["peer_position", "trend", "decomposition"])

        # A2: Chất lượng tín dụng của BANK_A quý 4/2024 thế nào?
        res2 = resolve_query("Chất lượng tín dụng của BANK_A quý 4/2024 thế nào?", self.catalog)
        p2 = rules_plan(res2, self.catalog)
        self.assertEqual(p2.question_type, "company_profile")
        self.assertEqual(p2.focus_entity, "BANK_A")
        self.assertEqual(set(p2.metrics), {"bank.npl_g35", "bank.llr_coverage"})
        self.assertEqual([t.tool for t in p2.tools], ["peer_position", "trend"])
        self.assertFalse(any("vĩ mô" in lim.lower() for lim in p2.limitations))

        # A3: Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?
        res3 = resolve_query("Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?", self.catalog)
        p3 = rules_plan(res3, self.catalog)
        self.assertEqual(p3.question_type, "ranking")
        self.assertIsNone(p3.focus_entity)
        self.assertEqual(p3.metrics, ("bank.llr_coverage",))
        self.assertEqual(len(p3.tools), 1)
        self.assertEqual(p3.tools[0].tool, "ranking")
        ctx = p3.tools[0].params.get("context_metrics", [])
        self.assertTrue(len(ctx) > 0)
        self.assertNotIn("bank.llr_coverage", ctx)

        # A4: BANK_A đứng thứ mấy về ROE trong nhóm quý 4/2024?
        res4 = resolve_query("BANK_A đứng thứ mấy về ROE trong nhóm quý 4/2024?", self.catalog)
        p4 = rules_plan(res4, self.catalog)
        self.assertEqual(p4.question_type, "ranking")
        self.assertEqual(p4.focus_entity, "BANK_A")
        self.assertEqual(p4.metrics, ("bank.roe",))
        self.assertEqual(p4.tools[0].params.get("highlight_entity"), "BANK_A")

        # A5: ROE của BANK_B thay đổi thế nào trong năm 2024?
        res5 = resolve_query("ROE của BANK_B thay đổi thế nào trong năm 2024?", self.catalog)
        p5 = rules_plan(res5, self.catalog)
        self.assertEqual(p5.question_type, "trend")
        self.assertEqual(p5.focus_entity, "BANK_B")
        self.assertEqual(p5.periods, ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"))
        self.assertEqual(p5.metrics, ("bank.roe",))
        self.assertEqual([t.tool for t in p5.tools], ["trend", "peer_position"])

        # A6: Diễn biến ROA của BANK_B từ 2024_Q1 đến 2024_Q4
        res6 = resolve_query("Diễn biến ROA của BANK_B từ 2024_Q1 đến 2024_Q4", self.catalog)
        p6 = rules_plan(res6, self.catalog)
        self.assertEqual(p6.question_type, "trend")
        self.assertEqual(p6.focus_entity, "BANK_B")
        self.assertEqual(p6.periods, ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"))
        self.assertEqual(p6.metrics, ("bank.roa",))
        self.assertEqual([t.tool for t in p6.tools], ["trend", "peer_position"])

        # A7: So sánh BANK_A và BANK_C quý 4/2024
        res7 = resolve_query("So sánh BANK_A và BANK_C quý 4/2024", self.catalog)
        p7 = rules_plan(res7, self.catalog)
        self.assertEqual(p7.question_type, "head_to_head")
        self.assertEqual(p7.entities, ("BANK_A", "BANK_C"))
        self.assertEqual([t.tool for t in p7.tools], ["head_to_head", "decomposition"])

        # A8: So sánh BANK_A, BANK_C và BANK_B về ROE quý 3/2024
        res8 = resolve_query("So sánh BANK_A, BANK_C và BANK_B về ROE quý 3/2024", self.catalog)
        p8 = rules_plan(res8, self.catalog)
        self.assertEqual(p8.question_type, "head_to_head")
        self.assertEqual(p8.entities, ("BANK_A", "BANK_C", "BANK_B"))
        self.assertEqual(p8.anchor_period, "2024_Q3")
        self.assertEqual(p8.metrics, ("bank.roe",))
        self.assertEqual([t.tool for t in p8.tools], ["head_to_head"])

        # A9: Tỷ lệ nợ xấu của BANK_D quý 4/2024 là bao nhiêu?
        res9 = resolve_query("Tỷ lệ nợ xấu của BANK_D quý 4/2024 là bao nhiêu?", self.catalog)
        p9 = rules_plan(res9, self.catalog)
        self.assertEqual(p9.question_type, "lookup")
        self.assertEqual(p9.focus_entity, "BANK_D")
        self.assertEqual(p9.metrics, ("bank.npl_g35",))
        self.assertEqual([t.tool for t in p9.tools], ["lookup"])

        # A10: Sức khỏe tài chính của BANK_B (mặc định anchor mới nhất)
        res10 = resolve_query("Sức khỏe tài chính của BANK_B", self.catalog)
        p10 = rules_plan(res10, self.catalog)
        self.assertEqual(p10.question_type, "company_profile")
        self.assertEqual(p10.focus_entity, "BANK_B")
        self.assertEqual(p10.anchor_period, "2024_Q4")
        self.assertIn("period_defaulted_to_latest", res10.defaults_applied)

        # A11: phan tich no xau cua BANK_B quy 4 2024 (không dấu)
        res11 = resolve_query("phan tich no xau cua BANK_B quy 4 2024", self.catalog)
        p11 = rules_plan(res11, self.catalog)
        self.assertEqual(p11.question_type, "company_profile")
        self.assertEqual(p11.focus_entity, "BANK_B")
        self.assertEqual(p11.metrics, ("bank.npl_g35",))

        # A12: Lãi suất điều hành ảnh hưởng thế nào đến nợ xấu của BANK_B quý 4/2024?
        res12 = resolve_query("Lãi suất điều hành ảnh hưởng thế nào đến nợ xấu của BANK_B quý 4/2024?", self.catalog)
        p12 = rules_plan(res12, self.catalog)
        self.assertEqual(p12.question_type, "company_profile")
        self.assertEqual(p12.metrics, ("bank.npl_g35",))
        self.assertTrue(any("vĩ mô" in lim.lower() for lim in p12.limitations))

        # A13: Vì sao ROE của BANK_A cao?
        res13 = resolve_query("Vì sao ROE của BANK_A cao?", self.catalog)
        p13 = rules_plan(res13, self.catalog)
        self.assertEqual(p13.question_type, "company_profile")
        self.assertEqual(p13.metrics, ("bank.roe",))
        self.assertTrue(any("nguyên nhân" in lim.lower() for lim in p13.limitations))
        tools13 = [t.tool for t in p13.tools]
        self.assertIn("decomposition", tools13)

    def test_acceptance_section_a_blocked_queries(self) -> None:
        # X1: unsupported_period
        with self.assertRaises(AnalysisBlocked) as cm1:
            resolve_query("Tỷ lệ nợ xấu của BANK_A quý 4/2023", self.catalog)
        self.assertEqual(cm1.exception.code, "unsupported_period")

        # X2: unsupported_macro_scope
        res_x2 = resolve_query("Tăng trưởng tín dụng toàn ngành 2024 thế nào?", self.catalog)
        with self.assertRaises(AnalysisBlocked) as cm2:
            rules_plan(res_x2, self.catalog)
        self.assertEqual(cm2.exception.code, "unsupported_macro_scope")

        # X3: unsupported_metric
        with self.assertRaises(AnalysisBlocked) as cm3:
            resolve_query("NIM của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(cm3.exception.code, "unsupported_metric")

        # X4: unsupported_entity
        res_x4 = resolve_query("Phân tích HDB quý 4/2024", self.catalog)
        with self.assertRaises(AnalysisBlocked) as cm4:
            rules_plan(res_x4, self.catalog)
        self.assertEqual(cm4.exception.code, "unsupported_entity")

        # X5: metric_required (lookup with no metric)
        res_x5 = resolve_query("BANK_A quý 4/2024 là bao nhiêu?", self.catalog)
        with self.assertRaises(AnalysisBlocked) as cm5:
            rules_plan(res_x5, self.catalog)
        self.assertEqual(cm5.exception.code, "metric_required")

    def test_model_plan_validation_and_fallback(self) -> None:
        resolved = resolve_query("Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?", self.catalog)

        # 1. Valid model plan accepted
        fake_client = MagicMock()
        fake_client.responses.create.return_value = SimpleNamespace(
            output_text='{"question_type":"lookup","focus_entity":"BANK_A","entities":["BANK_A"],"metrics":["bank.npl_g35"],"anchor_period":"2024_Q4","periods":["2024_Q4"],"tools":[{"tool":"lookup","params":{"entities":["BANK_A"],"metrics":["bank.npl_g35"],"period":"2024_Q4"}}],"rationale":"Tra cứu nợ xấu"}'
        )

        plan_spec, source, fallbacks, _ = plan_question(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?",
            self.catalog,
            settings=SimpleNamespace(planner_mode="model_with_fallback"),
            client=fake_client,
        )
        self.assertEqual(source, "model")
        self.assertEqual(plan_spec.question_type, "lookup")
        self.assertEqual(fallbacks, [])

        # 2. Model alters explicit entity -> rejected, falls back to rules
        fake_client.responses.create.return_value = SimpleNamespace(
            output_text='{"question_type":"lookup","focus_entity":"BANK_B","entities":["BANK_B"],"metrics":["bank.npl_g35"],"anchor_period":"2024_Q4","periods":["2024_Q4"],"tools":[{"tool":"lookup","params":{"entities":["BANK_B"],"metrics":["bank.npl_g35"],"period":"2024_Q4"}}],"rationale":"Tra cứu"}'
        )

        plan_spec_fb, source_fb, fallbacks_fb, _ = plan_question(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?",
            self.catalog,
            settings=SimpleNamespace(planner_mode="model_with_fallback"),
            client=fake_client,
        )
        self.assertEqual(source_fb, "rules")
        self.assertEqual(plan_spec_fb.focus_entity, "BANK_A")
        self.assertTrue(len(fallbacks_fb) > 0)

        # 3. Model chooses disabled question type -> fallback
        fake_client.responses.create.return_value = SimpleNamespace(
            output_text='{"question_type":"sector_theme","focus_entity":null,"entities":[],"metrics":["bank.npl_g35"],"anchor_period":"2024_Q4","periods":["2024_Q4"],"tools":[],"rationale":"Theme"}'
        )

        plan_spec_dis, source_dis, fallbacks_dis, _ = plan_question(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?",
            self.catalog,
            settings=SimpleNamespace(planner_mode="model_with_fallback"),
            client=fake_client,
        )
        self.assertEqual(source_dis, "rules")

        # 4. Model exception -> fallback
        fake_client.responses.create.side_effect = RuntimeError("OpenAI error")
        plan_spec_err, source_err, fallbacks_err, _ = plan_question(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?",
            self.catalog,
            settings=SimpleNamespace(planner_mode="model_with_fallback"),
            client=fake_client,
        )
        self.assertEqual(source_err, "rules")
        self.assertIn("model_error", fallbacks_err)

        # 5. Missing API key (client is None) -> fallback with model_unconfigured
        plan_spec_none, source_none, fallbacks_none, _ = plan_question(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?",
            self.catalog,
            settings=SimpleNamespace(planner_mode="model_with_fallback"),
            client=None,
        )
        self.assertEqual(source_none, "rules")
        self.assertIn("model_unconfigured", fallbacks_none)

    def test_runtime_plan_request_sources_and_fallbacks(self) -> None:
        from thesis_api.adaptive_runtime import _plan_request
        from thesis_api.schemas import AnalysisRequest

        # 1. Model client returns valid plan -> plannerSource = "model"
        fake_client = MagicMock()
        fake_client.responses.create.return_value = SimpleNamespace(
            output_text='{"question_type":"lookup","focus_entity":"BANK_A","entities":["BANK_A"],"metrics":["bank.npl_g35"],"anchor_period":"2024_Q4","periods":["2024_Q4"],"tools":[{"tool":"lookup","params":{"entities":["BANK_A"],"metrics":["bank.npl_g35"],"period":"2024_Q4"}}],"rationale":"Tra cứu"}'
        )
        plan_res = _plan_request(
            request=AnalysisRequest(query="Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?"),
            catalog=self.catalog,
            dataset_ref=self.catalog.dataset_ref,
            settings=SimpleNamespace(planner_mode="model_with_fallback", openai_api_key="sk-test", openai_model="gpt-4o-mini"),
            client=fake_client,
        )
        self.assertEqual(plan_res.planner_source, "model")
        self.assertEqual(plan_res.fallback_reasons, [])

        # 2. Client raises -> plannerSource = "rules" and reason = "model_error"
        fake_client_err = MagicMock()
        fake_client_err.responses.create.side_effect = RuntimeError("Service unavailable")
        plan_res_err = _plan_request(
            request=AnalysisRequest(query="Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?"),
            catalog=self.catalog,
            dataset_ref=self.catalog.dataset_ref,
            settings=SimpleNamespace(planner_mode="model_with_fallback", openai_api_key="sk-test", openai_model="gpt-4o-mini"),
            client=fake_client_err,
        )
        self.assertEqual(plan_res_err.planner_source, "rules")
        self.assertIn("model_error", plan_res_err.fallback_reasons)

        # 3. Missing API key (no client, no key) -> plannerSource = "rules" and reason = "model_unconfigured"
        plan_res_unconf = _plan_request(
            request=AnalysisRequest(query="Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?"),
            catalog=self.catalog,
            dataset_ref=self.catalog.dataset_ref,
            settings=SimpleNamespace(planner_mode="model_with_fallback", openai_api_key=None, openai_model="gpt-4o-mini"),
            client=None,
        )
        self.assertEqual(plan_res_unconf.planner_source, "rules")
        self.assertIn("model_unconfigured", plan_res_unconf.fallback_reasons)

    def test_build_analysis_plan_ranking_requirements_and_context_periods(self) -> None:
        # Ranking has requirement for all 5 entities
        res = resolve_query("Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?", self.catalog)
        spec = rules_plan(res, self.catalog)
        plan, target, periods, metrics, peers, macro = build_analysis_plan(
            spec, self.catalog, self.catalog.dataset_ref
        )
        self.assertEqual(periods, ("2024_Q4",))
        # Context periods are not in plan.scope.periods
        self.assertEqual(plan.scope.periods, ("2024_Q4",))
        # Requirements cover all 5 entities
        factual_reqs = [
            r for r in plan.requirements if r.requirement_type is RequirementType.FACTUAL_OBSERVATION
        ]
        factual_entities = {r.entities[0] for r in factual_reqs}
        self.assertEqual(factual_entities, {"BANK_A", "BANK_B", "BANK_C", "BANK_D", "BANK_E"})

    def test_suggestions_from_catalog_resolve_and_do_not_raise(self) -> None:
        suggestions = suggestions_for(self.catalog)
        self.assertEqual(len(suggestions), 5)
        for s in suggestions:
            res = resolve_query(s, self.catalog)
            plan = rules_plan(res, self.catalog)
            self.assertIn(plan.question_type, ["lookup", "company_profile", "ranking", "trend", "head_to_head"])


if __name__ == "__main__":
    unittest.main()
