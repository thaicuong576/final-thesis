"""Unit tests for verifier label rules: metric label mismatch and self-comparison rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tests"))

from thesis_data.narrative_verification import (
    NarrativeSentence,
    VerificationContext,
    verify_sentence,
)
from thesis_data.report_facts import Fact


def _make_context(**kwargs) -> VerificationContext:
    facts = {
        "f_vcb_npl": Fact(
            fact_id="f_vcb_npl",
            fact_type="value",
            entity_id="VCB",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            value=0.96,
            unit="%",
        ),
        "f_vcb_llr": Fact(
            fact_id="f_vcb_llr",
            fact_type="value",
            entity_id="VCB",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            value=158.8,
            unit="%",
        ),
        "f_tcb_roa": Fact(
            fact_id="f_tcb_roa",
            fact_type="value",
            entity_id="TCB",
            metric_id="bank.roa",
            period="2026_Q2",
            value=2.45,
            unit="%",
        ),
        "f_tcb_roe": Fact(
            fact_id="f_tcb_roe",
            fact_type="value",
            entity_id="TCB",
            metric_id="bank.roe",
            period="2026_Q2",
            value=17.5,
            unit="%",
        ),
        "f_tcb_vs_mbb_roa": Fact(
            fact_id="f_tcb_vs_mbb_roa",
            fact_type="pairwise_gap",
            entity_id="TCB",
            other_entity_id="MBB",
            metric_id="bank.roa",
            period="2026_Q2",
            value=0.85,
            unit="pp",
        ),
        "f_tcb_vs_mbb_llr": Fact(
            fact_id="f_tcb_vs_mbb_llr",
            fact_type="pairwise_gap",
            entity_id="TCB",
            other_entity_id="MBB",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            value=32.0,
            unit="pp",
        ),
        "f_bid_llr_d": Fact(
            fact_id="f_bid_llr_d",
            fact_type="delta",
            entity_id="BID",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            from_period="2026_Q1",
            value=-11.0,
            unit="pp",
        ),
        "f_lead_3_4": Fact(
            fact_id="f_lead_3_4",
            fact_type="lead_count",
            entity_id="TCB",
            other_entity_id="MBB",
            period="2026_Q2",
            value=3.0,
            denominator=4,
        ),
        "f_npl_spread": Fact(
            fact_id="f_npl_spread",
            fact_type="spread",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            value=6.93,
            unit="pp",
            denominator=10,
        ),
    }
    defaults = {
        "facts": facts,
        "plan_entities": frozenset({"VCB", "TCB", "MBB", "BID", "CTG", "ACB", "STB", "VPB", "HDB"}),
        "catalog_entities": frozenset({
            "VCB", "CTG", "BID", "TCB", "MBB", "VPB", "HDB", "ACB",
            "STB", "TPB", "VIB", "LPB", "SHB", "MSB", "SSB", "OCB", "EIB",
        }),
        "metric_terms": {
            "bank.npl_g35": ("nợ xấu", "tỷ lệ nợ xấu", "npl"),
            "bank.llr_coverage": ("bao phủ nợ xấu", "tỷ lệ bao phủ nợ xấu", "đệm dự phòng", "llr"),
            "bank.roa": ("roa", "sinh lời trên tài sản"),
            "bank.roe": ("roe", "sinh lời trên vốn"),
        },
        "hi_words": {
            "bank.npl_g35": ("cao",),
            "bank.llr_coverage": ("dày", "cao"),
            "bank.roa": ("cao",),
            "bank.roe": ("cao",),
        },
        "lo_words": {
            "bank.npl_g35": ("thấp",),
            "bank.llr_coverage": ("mỏng", "thấp"),
            "bank.roa": ("thấp",),
            "bank.roe": ("thấp",),
        },
        "directions": {
            "bank.npl_g35": "lower_is_better",
            "bank.llr_coverage": "higher_is_better",
            "bank.roa": "higher_is_better",
            "bank.roe": "higher_is_better",
        },
        "flat_pp": {
            "bank.npl_g35": 0.05,
            "bank.llr_coverage": 1.0,
            "bank.roa": 0.05,
            "bank.roe": 0.5,
        },
        "anchor_year": 2026,
    }
    defaults.update(kwargs)
    return VerificationContext(**defaults)


def _sent(sentence_id: str, text: str, fact_ids: tuple[str, ...]) -> NarrativeSentence:
    return NarrativeSentence(
        sentence_id=sentence_id,
        text=text,
        fact_ids=fact_ids,
        author="orchestrator",
        source="model",
    )


class NarrativeLabelRulesTestCase(unittest.TestCase):
    """Test suite for metric label matching and self-comparison verifier rules."""

    def setUp(self) -> None:
        self.ctx = _make_context()

    # -------------------------------------------------------------------------
    # Part 1: Metric Label Rule (Rule 1)
    # -------------------------------------------------------------------------

    def test_rule1_case1_llr_vs_npl_mismatch(self) -> None:
        """Sentence mentions 'tỷ lệ nợ xấu' but cites an LLR fact -> metric_label_mismatch."""
        s = _sent("s1", "Tỷ lệ nợ xấu của VCB đạt 158,8% trong quý 2/2026.", ("f_vcb_llr",))
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "metric_label_mismatch")

    def test_rule1_case2_bao_phu_no_xau_not_confused_with_no_xau(self) -> None:
        """Longest phrase 'bao phủ nợ xấu' must not match shorter 'nợ xấu'."""
        s = _sent("s2", "Tỷ lệ bao phủ nợ xấu của VCB đạt 158,8% trong quý 2/2026.", ("f_vcb_llr",))
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok but got {verdict.reason_code}: {verdict.reason}")

    def test_rule1_case3_casing_insensitivity(self) -> None:
        """Casing variations like 'roa', 'ROA', 'RoA' match the metric term properly."""
        s_upper = _sent("s3a", "ROA của TCB đạt 2,45% trong quý 2/2026.", ("f_tcb_roa",))
        v_upper = verify_sentence(s_upper, self.ctx)
        self.assertTrue(v_upper.ok)

        s_lower = _sent("s3b", "roa của TCB đạt 2,45% trong quý 2/2026.", ("f_tcb_roa",))
        v_lower = verify_sentence(s_lower, self.ctx)
        self.assertTrue(v_lower.ok)

    def test_rule1_case4_roa_vs_roe_mismatch(self) -> None:
        """Sentence mentions 'ROA' but cites an ROE fact -> metric_label_mismatch."""
        s = _sent("s4", "ROA của TCB đạt 17,5% trong quý 2/2026.", ("f_tcb_roe",))
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "metric_label_mismatch")

    def test_rule1_case5_valid_sentence_without_named_metric(self) -> None:
        """Sentences not naming any specific metric must not be rejected by Rule 1."""
        s = _sent("s5", "TCB dẫn trước MBB ở 3/4 chỉ tiêu chính trong quý 2/2026.", ("f_lead_3_4",))
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok but got: {verdict.reason_code}: {verdict.reason}")

    def test_rule1_case6_npl_vs_llr_abbreviations(self) -> None:
        """Sentence mentions 'NPL' but cites LLR fact -> rejected."""
        s = _sent("s6", "NPL của VCB đạt 158,8% trong quý 2/2026.", ("f_vcb_llr",))
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "metric_label_mismatch")

    def test_rule1_case7_multi_metric_partially_mismatched(self) -> None:
        """Sentence mentions both ROA and nợ xấu, but only cites ROA and LLR -> metric_label_mismatch."""
        s = _sent(
            "s7",
            "TCB vượt trội MBB ở ROA và tỷ lệ nợ xấu trong quý 2/2026.",
            ("f_tcb_vs_mbb_roa", "f_tcb_vs_mbb_llr"),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "metric_label_mismatch")

    # -------------------------------------------------------------------------
    # Part 2: Self-Comparison Rule (Rule 2)
    # -------------------------------------------------------------------------

    def test_rule2_case1_same_bank_comparison_rejected(self) -> None:
        """Comparing bank against itself ('TCB vượt trội TCB') -> rejected with self_comparison."""
        s = _sent(
            "sc1",
            "TCB vượt trội TCB ở ROA và tỷ lệ bao phủ nợ xấu trong quý 2/2026.",
            ("f_tcb_vs_mbb_roa", "f_tcb_vs_mbb_llr"),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "self_comparison")

    def test_rule2_case2_same_period_trend_rejected(self) -> None:
        """Range starting and ending at same period ('từ quý 2/2026 đến quý 2/2026') -> self_comparison."""
        s = _sent(
            "sc2",
            "Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 2/2026 đến quý 2/2026.",
            ("f_bid_llr_d",),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "self_comparison")

    def test_rule2_case3_valid_different_bank_comparison_passes(self) -> None:
        """Valid comparison across distinct banks ('TCB vượt trội MBB') -> accepted."""
        s = _sent(
            "sc3",
            "TCB vượt trội MBB ở ROA và tỷ lệ bao phủ nợ xấu trong quý 2/2026.",
            ("f_tcb_vs_mbb_roa", "f_tcb_vs_mbb_llr"),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok but got: {verdict.reason_code}: {verdict.reason}")

    def test_rule2_case4_valid_different_period_trend_passes(self) -> None:
        """Valid trend across distinct periods ('từ quý 1/2026 đến quý 2/2026') -> accepted."""
        s = _sent(
            "sc4",
            "Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 2/2026.",
            ("f_bid_llr_d",),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok but got: {verdict.reason_code}: {verdict.reason}")

    def test_rule2_case5_spread_extremes_self_comparison_rejected(self) -> None:
        """Spread range comparing same extreme ('thấp nhất – thấp nhất') -> self_comparison."""
        s = _sent(
            "sc5",
            "Chênh lệch thấp nhất – thấp nhất về tỷ lệ nợ xấu của nhóm 10 ngân hàng là 6,93 điểm % trong quý 2/2026.",
            ("f_npl_spread",),
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "self_comparison")

    # -------------------------------------------------------------------------
    # Part 3: Toggle / Flag Behavior
    # -------------------------------------------------------------------------

    def test_toggle_disable_label_rules(self) -> None:
        """When enable_label_rules=False, rules are bypassed (for baseline comparison)."""
        ctx_legacy = _make_context(enable_label_rules=False)
        s_self = _sent(
            "t1",
            "Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 2/2026 đến quý 2/2026.",
            ("f_bid_llr_d",),
        )
        # With enable_label_rules=False, period check sees valid period and numbers match, so it passes
        v_legacy = verify_sentence(s_self, ctx_legacy)
        self.assertTrue(v_legacy.ok)

        # With enable_label_rules=True (default), it is rejected as self_comparison
        v_active = verify_sentence(s_self, self.ctx)
        self.assertFalse(v_active.ok)
        self.assertEqual(v_active.reason_code, "self_comparison")


from thesis_api.adaptive_runtime import run_adaptive_analysis
from thesis_api.schemas import AnalysisRequest
from thesis_api.settings import Settings
from test_api_trend_runtime import _TrendProvider, _TrendWriter
from test_api_analyze import _ExplicitOfflineAcceptingCritic


class _MismatchedLabelAndSelfComparisonWriter(_TrendWriter):
    def write_findings(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]] | None = None,
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]:
        findings = super().write_findings(
            role=role,
            question=question,
            question_type=question_type,
            facts=facts,
            datasets_summary=datasets_summary,
            candidates=candidates,
            max_sentences=max_sentences,
        )
        llr_fact = next(
            (f for f in facts if "llr_coverage" in f.get("fact_id", "")),
            facts[0] if facts else None,
        )
        if llr_fact:
            val_str = llr_fact.get("hien_thi") or "10,0%"
            # 1. Metric label mismatch: mentions "tỷ lệ nợ xấu" (bank.npl_g35) but cites LLR coverage fact
            findings.append({
                "text": f"Tỷ lệ nợ xấu của MBB đạt {val_str}.",
                "fact_ids": [llr_fact["fact_id"]],
            })
            # 2. Self comparison: MBB cao hơn MBB
            findings.append({
                "text": f"MBB cao hơn MBB trong năm 2024 đạt {val_str}.",
                "fact_ids": [llr_fact["fact_id"]],
            })
        return findings


class RuntimeLabelRulesRegressionTests(unittest.TestCase):
    def test_runtime_drops_sentences_with_new_reason_codes_without_validation_error(self) -> None:
        """Offline writer returns metric_label_mismatch and self_comparison sentences.

        Runtime must drop both sentences into narrative_audit.sentences_dropped
        with their respective reason_code without throwing ValidationError.
        """
        periods = [f"2024_Q{quarter}" for quarter in range(1, 5)]
        metrics = (("bank.npl_g35", "Tỷ lệ nợ xấu"), ("bank.llr_coverage", "Tỷ lệ bao phủ nợ xấu"))
        provider = _TrendProvider("MBB", metrics)
        writer = _MismatchedLabelAndSelfComparisonWriter()
        critic = _ExplicitOfflineAcceptingCritic()

        report = run_adaptive_analysis(
            provider=provider,
            dataset_ref=provider.dataset_ref,
            catalog=provider.catalog,
            request=AnalysisRequest(
                query="Analyze MBB NPL and LLR from 2024_Q1 through 2024_Q4",
                target_ticker="MBB",
                periods=periods,
            ),
            settings=Settings(planner_mode="rules_only"),
            semantic_critic=critic,
            analysis_writer=writer,
        )

        self.assertIn(report.status, ("completed", "accepted_with_limitations"))
        dropped = report.narrative_audit.sentences_dropped
        dropped_codes = [d.reason_code for d in dropped]
        self.assertIn("metric_label_mismatch", dropped_codes)
        self.assertIn("self_comparison", dropped_codes)

        spec = report.report_spec
        if spec:
            for blk in spec.blocks:
                if getattr(blk, "sentence", None):
                    self.assertNotIn("MBB cao hơn MBB", blk.sentence.text or "")


if __name__ == "__main__":
    unittest.main()