"""Tests for narrative_templates.py — Fix C: ratio_to_median wording.

Verifies that:
- When ratio >= 1: sentence uses "gấp X lần trung vị"
- When ratio < 1: sentence uses "bằng X lần trung vị" (not "gấp")
- The narrative verifier also accepts both forms.
"""

from __future__ import annotations

import unittest

from thesis_api.narrative_templates import make_fallback_sentence, describe_fact
from thesis_data.report_facts import Fact


def _ratio_fact(value: float, entity: str = "VCB", metric: str = "bank.npl_g35") -> Fact:
    return Fact(
        fact_id=f"f_{entity.lower()}_ratio",
        fact_type="ratio_to_median",
        entity_id=entity,
        metric_id=metric,
        period="2024_Q4",
        value=value,
        unit="x",
        denominator=5,
    )


class TestRatioToMedianWording(unittest.TestCase):
    """Fix C: 'gấp' only when ratio >= 1, 'bằng' when ratio < 1."""

    def test_ratio_above_one_uses_gap(self) -> None:
        """ratio=1.5 → 'gấp 1,5 lần trung vị'."""
        fact = _ratio_fact(1.5)
        sent = make_fallback_sentence(fact, seq=1)
        self.assertIn("gấp", sent.text)
        self.assertIn("1,5", sent.text)
        self.assertNotIn("bằng", sent.text)

    def test_ratio_exactly_one_uses_gap(self) -> None:
        """ratio=1.0 → 'gấp 1,0 lần trung vị' (boundary: 1.0 is still >= 1)."""
        fact = _ratio_fact(1.0)
        sent = make_fallback_sentence(fact, seq=1)
        self.assertIn("gấp", sent.text)
        self.assertNotIn("bằng", sent.text)

    def test_ratio_below_one_uses_bang(self) -> None:
        """ratio=0.6 → 'bằng 0,6 lần trung vị', NOT 'gấp'."""
        fact = _ratio_fact(0.6)
        sent = make_fallback_sentence(fact, seq=1)
        self.assertIn("bằng", sent.text)
        self.assertIn("0,6", sent.text)
        self.assertNotIn("gấp", sent.text)

    def test_vcb_npl_ratio_below_one(self) -> None:
        """VCB nợ xấu 0,96% / trung vị 1,51% ≈ 0,64 → 'bằng 0,6 lần trung vị'."""
        # ratio = 0.9636 / 1.5122 ≈ 0.637
        fact = _ratio_fact(0.637, entity="VCB")
        sent = make_fallback_sentence(fact, seq=1)
        self.assertIn("bằng", sent.text)
        self.assertNotIn("gấp", sent.text)

    def test_describe_fact_ratio_below_one(self) -> None:
        """describe_fact with ratio < 1 should also use 'bằng'."""
        fact = _ratio_fact(0.6)
        desc = describe_fact(fact)
        self.assertIn("bằng", desc)
        self.assertNotIn("gấp", desc)

    def test_describe_fact_ratio_above_one(self) -> None:
        """describe_fact with ratio >= 1 should use 'gấp'."""
        fact = _ratio_fact(2.4, entity="VCB", metric="bank.llr_coverage")
        desc = describe_fact(fact)
        self.assertIn("gấp", desc)
        self.assertNotIn("bằng", desc)

    def test_sentence_fact_ids_preserved(self) -> None:
        """Sentence must cite the original fact_id."""
        fact = _ratio_fact(0.6)
        sent = make_fallback_sentence(fact, seq=3)
        self.assertIn(fact.fact_id, sent.fact_ids)
        self.assertEqual(sent.sentence_id, "sent-fb-3")


class TestNonMemberBankRankTemplates(unittest.TestCase):
    """VIBFIX-1 / Bug 1: Non-member rank wording and denominator in fallback templates."""

    def test_fallback_sentence_non_member_rank_11_of_11(self) -> None:
        fact = Fact(
            fact_id="fact:peer_rank:VIB:sector:bank:2025_Q4:bank.llr_coverage",
            fact_type="peer_rank",
            entity_id="VIB",
            metric_id="bank.llr_coverage",
            period="2025_Q4",
            value=11.0,
            rank_better=11,
            rank_desc=11,
            denominator=11,
            unit="rank",
        )
        sent = make_fallback_sentence(fact, seq=1)
        self.assertIn("11/11", sent.text)
        self.assertNotIn("11/10", sent.text)

    def test_fallback_answer_card_non_member_wording(self) -> None:
        from thesis_api.narrative_templates import default_report_spec

        val_fact = Fact(
            fact_id="f_val_vib",
            fact_type="value",
            entity_id="VIB",
            metric_id="bank.llr_coverage",
            period="2025_Q4",
            value=42.87,
            unit="%",
        )
        rank_fact = Fact(
            fact_id="f_rank_vib",
            fact_type="peer_rank",
            entity_id="VIB",
            metric_id="bank.llr_coverage",
            period="2025_Q4",
            value=11.0,
            rank_better=11,
            rank_desc=11,
            denominator=11,
            unit="rank",
        )
        med_fact = Fact(
            fact_id="f_med_bank",
            fact_type="peer_median",
            universe_id="sector:bank",
            metric_id="bank.llr_coverage",
            period="2025_Q4",
            value=96.83,
            unit="%",
            denominator=10,
        )
        from thesis_api.analysis_tools import ToolResult

        all_facts = [val_fact, rank_fact, med_fact]
        tool_results = [ToolResult(tool="lookup", agent="company", label="Tra cứu", facts=all_facts, datasets=[], missing=[])]
        spec = default_report_spec("lookup", tool_results, [], [])
        self.assertEqual(spec.kind, "answer_card")
        ans_block = spec.blocks[0]
        ans_sent = ans_block.sentences[0]
        # Must say 'xếp hạng 11/11'
        self.assertIn("11/11", ans_sent.text)
        # Must say 'khi đặt cạnh 10 ngân hàng trong nhóm' without claiming VIB is in the group
        self.assertIn("khi đặt cạnh 10 ngân hàng trong nhóm", ans_sent.text)
        # Must cite med_fact to satisfy entity count check for '10 ngân hàng'
        self.assertIn(med_fact.fact_id, ans_sent.fact_ids)


if __name__ == "__main__":
    unittest.main()
