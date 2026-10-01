"""Direction labels for the writer and verified stand-ins for failed opening sentences."""

from __future__ import annotations

import unittest

from thesis_api.analysis_tools import ToolResult
from thesis_api.analysis_writer import _normalize_facts
from thesis_api.narrative_templates import default_report_spec, direction_label
from thesis_data.report_facts import Fact


def _gap(fid: str, metric: str, value: float, other: str = "STB") -> Fact:
    return Fact(fact_id=fid, fact_type="pairwise_gap", entity_id="HDB", other_entity_id=other,
                metric_id=metric, period="2026_Q1", value=value)


class DirectionLabelTest(unittest.TestCase):
    def test_moves_inside_the_flat_band_are_flat(self) -> None:
        small = Fact(fact_id="d1", fact_type="delta", entity_id="MBB", metric_id="bank.roa",
                     period="2024_Q3", from_period="2024_Q2", value=-0.0432)
        self.assertEqual(direction_label(small), "đi ngang")
        drop = Fact(fact_id="d2", fact_type="delta", entity_id="MBB", metric_id="bank.roa",
                    period="2024_Q3", from_period="2024_Q2", value=-0.2)
        self.assertEqual(direction_label(drop), "giảm")

    def test_gap_to_median_beyond_threshold_is_not_in_line(self) -> None:
        gap = Fact(fact_id="g1", fact_type="gap_to_median", entity_id="MBB", metric_id="bank.npl_g35",
                   period="2024_Q3", value=0.5983)
        self.assertEqual(direction_label(gap), "cao hơn trung vị nhóm")

    def test_pairwise_gap_names_the_other_bank_and_values_carry_no_label(self) -> None:
        self.assertEqual(direction_label(_gap("p1", "bank.npl_g35", -4.02)), "thấp hơn STB")
        value = Fact(fact_id="v1", fact_type="value", entity_id="HDB", metric_id="bank.roa",
                     period="2026_Q1", value=1.84)
        self.assertIsNone(direction_label(value))

    def test_writer_payload_keeps_the_label(self) -> None:
        out = _normalize_facts([{"fact_id": "p1", "mo_ta": "x", "hien_thi": "-4,02 điểm %", "huong": "thấp hơn STB"},
                                {"fact_id": "v1", "mo_ta": "y", "hien_thi": "1,84%"}])
        self.assertEqual(out[0]["huong"], "thấp hơn STB")
        self.assertNotIn("huong", out[1])


class HeadToHeadDefaultTest(unittest.TestCase):
    def test_headline_uses_the_widest_named_gap_not_a_metric_count(self) -> None:
        facts = [
            _gap("p-npl", "bank.npl_g35", -4.02),
            _gap("p-roa", "bank.roa", 1.32),
            Fact(fact_id="lead", fact_type="lead_count", entity_id="HDB", other_entity_id="STB",
                 period="2026_Q1", value=1.0, denominator=2),
        ]
        spec = default_report_spec(
            question_type="head_to_head",
            tool_results=[ToolResult(tool="t", agent="a", label="l", facts=facts, datasets=[], missing=[])],
            signals=[],
            findings=[],
        )
        headline = next(b for b in spec.blocks if b.type == "headline").sentence
        self.assertEqual(headline.fact_ids, ["p-npl"])
        self.assertIn("thấp hơn STB", headline.text)
        self.assertNotIn("nhỉnh hơn", headline.text)


class CriticEvaluatorIdentityTest(unittest.TestCase):
    def test_model_echoed_evaluator_version_is_replaced_by_the_configured_one(self) -> None:
        from thesis_data.openai_semantic_critic import _normalize_critic_output

        out = _normalize_critic_output({"evaluator_version": "gpt-6-luna"}, "openai-semantic-critic-v1:gpt-6-luna")
        self.assertEqual(out["evaluator_version"], "openai-semantic-critic-v1:gpt-6-luna")


if __name__ == "__main__":
    unittest.main()
