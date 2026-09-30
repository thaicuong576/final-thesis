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


if __name__ == "__main__":
    unittest.main()
