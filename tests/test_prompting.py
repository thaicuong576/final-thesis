"""Tests for deterministic, provider-neutral agent prompt rendering."""

from __future__ import annotations

import unittest

from thesis_data.agent_runtime import AgentCallRequest
from thesis_data.prompting import PromptRenderError, render_agent_prompt, render_composite_prompt
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)


class PromptRenderingTests(unittest.TestCase):
    def request(self, *, role: str = "company", context: dict | None = None) -> AgentCallRequest:
        return AgentCallRequest(
            role=role,
            ticker="VCB",
            period="2024_Q1",
            periods=("2024_Q1", "2024_Q2"),
            metric_ids=("bank.npl_g35", "bank.roa"),
            macro_indicator_ids=("macro.policy_rate",),
            question_id="q-company-trend",
            question_type="company_trend",
            question_prompt="Describe the supported quarterly direction.",
            prompt_version="prompt-contract-v1",
            context=context or {"z": [2, 1], "a": {"value": "được chuẩn bị"}},
        )

    def test_rendering_is_deterministic_and_contains_frozen_scope(self):
        first = render_agent_prompt(self.request(context={"b": 2, "a": 1}))
        second = render_agent_prompt(self.request(context={"a": 1, "b": 2}))

        self.assertEqual(first, second)
        self.assertIn("Prompt version: prompt-contract-v1", first)
        self.assertIn("Role: company", first)
        self.assertIn("Ticker: VCB", first)
        self.assertIn("Periods: 2024_Q1, 2024_Q2", first)
        self.assertIn("bank.npl_g35, bank.roa", first)
        self.assertIn("Describe the supported quarterly direction.", first)

    def test_macro_rendering_preserves_indicator_scope(self):
        rendered = render_agent_prompt(self.request(role="macro"))

        self.assertIn("Role instruction: Use only the declared macro indicators", rendered)
        self.assertIn("macro.policy_rate", rendered)

    def test_unknown_role_fails_closed(self):
        with self.assertRaises(PromptRenderError) as raised:
            render_agent_prompt(self.request(role="invented-role"))

        self.assertEqual(raised.exception.blockers, ("prompt_role_unknown",))

    def test_empty_question_prompt_fails_closed(self):
        request = self.request()
        request = AgentCallRequest(**{**request.__dict__, "question_prompt": "  "})

        with self.assertRaises(PromptRenderError) as raised:
            render_agent_prompt(request)

        self.assertEqual(raised.exception.blockers, ("prompt_question_missing",))

    def test_non_json_safe_context_fails_closed(self):
        with self.assertRaises(PromptRenderError) as raised:
            render_agent_prompt(self.request(context={"bad": float("nan")}))

        self.assertEqual(raised.exception.blockers, ("prompt_context_not_json_safe",))

    def test_composite_prompt_renders_sop_and_scope_without_raw_facts(self):
        spec = CompositeWorkloadSpec(
            question_id="q-composite-tier-2",
            tier=WorkloadTier.TIER_2,
            issuers=("VCB",),
            periods=("2024_Q1", "2024_Q2"),
            metric_ids=("bank.roa", "bank.roe"),
            analysis_tasks=(AnalysisTask.SNAPSHOT, AnalysisTask.TREND, AnalysisTask.EVIDENCE_SUMMARY),
            peer_tickers=("VCB", "ACB"),
            complexity_vector=ComplexityVector(
                issuer_count=1,
                period_count=2,
                metric_count=2,
                analysis_task_count=3,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=2,
            ),
        )

        rendered = render_composite_prompt(
            spec,
            role="company",
            prompt_version="composite-prompt-v1",
            question_prompt="Analyze the requested issuer workload.",
        )

        self.assertIn("Composite workload tier: tier_2", rendered)
        self.assertIn("VCB", rendered)
        self.assertIn("2024_Q1, 2024_Q2", rendered)
        self.assertIn("Stage 1: decompose", rendered)
        self.assertIn("CompositeAnalysisPayload", rendered)
        self.assertIn("Missing-data policy", rendered)
        self.assertNotIn("ROA was 1.2 percent", rendered)

    def test_composite_prompt_rejects_unknown_role_and_empty_question(self):
        spec = CompositeWorkloadSpec(
            question_id="q-composite-tier-2",
            tier=WorkloadTier.TIER_2,
            issuers=("VCB",),
            periods=("2024_Q1",),
            metric_ids=("bank.roa",),
            analysis_tasks=(AnalysisTask.SNAPSHOT,),
            complexity_vector=ComplexityVector(
                issuer_count=1,
                period_count=1,
                metric_count=1,
                analysis_task_count=1,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=0,
            ),
        )

        with self.assertRaises(PromptRenderError) as raised:
            render_composite_prompt(spec, "invented-role", "v1", "question")
        self.assertEqual(raised.exception.blockers, ("prompt_role_unknown",))

        with self.assertRaises(PromptRenderError) as raised:
            render_composite_prompt(spec, "company", "v1", "  ")
        self.assertEqual(raised.exception.blockers, ("prompt_question_missing",))


if __name__ == "__main__":
    unittest.main()
