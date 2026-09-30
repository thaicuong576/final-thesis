"""Tests for sentence-level narrative verification (PR-4 §2.1).

Validates atomic sentences against deterministic facts:
- Number tolerance and display rounding.
- Metric and entity proximity binding.
- Prohibited causal language and investment recommendations with exclusions.
- Period coverage and date masking.
- Competition ranking matching.
- Multi-period trend and continuous progression.
- Pairwise and benchmark comparisons.
"""

from __future__ import annotations

import unittest

from thesis_data.narrative_verification import (
    NarrativeSentence,
    VerificationContext,
    verify_sentence,
    verify_all,
)
from thesis_data.report_facts import Fact


class NarrativeVerificationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # Table C Gold facts for Q4/2024
        # ACB: NPL 1.5122 (#3), LLR 76.5591 (#4), ROA 2.1215 (#3), ROE 21.7459 (#2)
        # MBB: NPL 1.6205 (#4), LLR 92.2484 (#3), ROA 2.2135 (#2), ROE 22.0939 (#1)
        # TCB: NPL 1.17 (#2), LLR 113.8 (#2), ROA 2.4 (#1), ROE 15.5 (#4)
        # VCB: NPL 0.9636 (#1), LLR 223.311 (#1), ROA 1.7249 (#5), ROE 18.5965 (#3)
        # VPB: NPL 4.1956 (#5), LLR 56.1749 (#5), ROA 1.8361 (#4), ROE 11.4117 (#5)
        # Median: NPL 1.5122, LLR 92.2484, ROA 2.1215, ROE 18.5965

        self.facts: dict[str, Fact] = {
            # ACB ROE
            "f_acb_roe_q4": Fact(
                fact_id="f_acb_roe_q4",
                fact_type="value",
                entity_id="ACB",
                metric_id="bank.roe",
                period="2024_Q4",
                value=21.75,
                unit="%",
            ),
            "f_acb_roe_rank_q4": Fact(
                fact_id="f_acb_roe_rank_q4",
                fact_type="peer_rank",
                entity_id="ACB",
                metric_id="bank.roe",
                period="2024_Q4",
                value=2.0,
                unit="rank",
                rank_better=2,
                rank_desc=2,
                denominator=5,
            ),
            "f_acb_roe_gap_q4": Fact(
                fact_id="f_acb_roe_gap_q4",
                fact_type="gap_to_median",
                entity_id="ACB",
                metric_id="bank.roe",
                period="2024_Q4",
                value=3.1494,  # +3.15 pp
                unit="pp",
                denominator=5,
            ),
            # ACB NPL
            "f_acb_npl_q4": Fact(
                fact_id="f_acb_npl_q4",
                fact_type="value",
                entity_id="ACB",
                metric_id="bank.npl_g35",
                period="2024_Q4",
                value=1.5122,
                unit="%",
            ),
            # ACB LLR
            "f_acb_llr_q4": Fact(
                fact_id="f_acb_llr_q4",
                fact_type="value",
                entity_id="ACB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                value=76.5591,
                unit="%",
            ),
            "f_acb_llr_prec_q4": Fact(
                fact_id="f_acb_llr_prec_q4",
                fact_type="value",
                entity_id="ACB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                value=76.6379,
                unit="%",
            ),
            "f_acb_llr_delta_q3_q4": Fact(
                fact_id="f_acb_llr_delta_q3_q4",
                fact_type="delta",
                entity_id="ACB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                from_period="2024_Q3",
                value=-2.51,
                unit="pp",
            ),
            "f_llr_med_delta_q3_q4": Fact(
                fact_id="f_llr_med_delta_q3_q4",
                fact_type="median_delta",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                from_period="2024_Q3",
                value=13.18,
                unit="pp",
            ),
            # VCB LLR
            "f_vcb_llr_q4": Fact(
                fact_id="f_vcb_llr_q4",
                fact_type="value",
                entity_id="VCB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                value=223.311,
                unit="%",
            ),
            "f_vcb_llr_rank_q4": Fact(
                fact_id="f_vcb_llr_rank_q4",
                fact_type="peer_rank",
                entity_id="VCB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                value=1.0,
                unit="rank",
                rank_better=1,
                rank_desc=1,
                denominator=5,
            ),
            "f_vcb_llr_ratio_q4": Fact(
                fact_id="f_vcb_llr_ratio_q4",
                fact_type="ratio_to_median",
                entity_id="VCB",
                metric_id="bank.llr_coverage",
                period="2024_Q4",
                value=2.42,
                unit="x",
            ),
            # VPB ROE across 4 quarters
            "f_vpb_roe_q1": Fact(fact_id="f_vpb_roe_q1", fact_type="value", entity_id="VPB", metric_id="bank.roe", period="2024_Q1", value=8.0671, unit="%"),
            "f_vpb_roe_q2": Fact(fact_id="f_vpb_roe_q2", fact_type="value", entity_id="VPB", metric_id="bank.roe", period="2024_Q2", value=8.5867, unit="%"),
            "f_vpb_roe_q3": Fact(fact_id="f_vpb_roe_q3", fact_type="value", entity_id="VPB", metric_id="bank.roe", period="2024_Q3", value=9.6445, unit="%"),
            "f_vpb_roe_q4": Fact(fact_id="f_vpb_roe_q4", fact_type="value", entity_id="VPB", metric_id="bank.roe", period="2024_Q4", value=11.4117, unit="%"),
            "f_vpb_roe_d_q1_q2": Fact(fact_id="f_vpb_roe_d_q1_q2", fact_type="delta", entity_id="VPB", metric_id="bank.roe", period="2024_Q2", from_period="2024_Q1", value=0.52, unit="pp"),
            "f_vpb_roe_d_q2_q3": Fact(fact_id="f_vpb_roe_d_q2_q3", fact_type="delta", entity_id="VPB", metric_id="bank.roe", period="2024_Q3", from_period="2024_Q2", value=1.06, unit="pp"),
            "f_vpb_roe_d_q3_q4": Fact(fact_id="f_vpb_roe_d_q3_q4", fact_type="delta", entity_id="VPB", metric_id="bank.roe", period="2024_Q4", from_period="2024_Q3", value=1.77, unit="pp"),
            "f_vpb_roe_gap_q1": Fact(fact_id="f_vpb_roe_gap_q1", fact_type="gap_to_median", entity_id="VPB", metric_id="bank.roe", period="2024_Q1", value=-9.39, unit="pp"),
            "f_vpb_roe_gap_q4": Fact(fact_id="f_vpb_roe_gap_q4", fact_type="gap_to_median", entity_id="VPB", metric_id="bank.roe", period="2024_Q4", value=-7.18, unit="pp"),
            # Lead count TCB vs ACB
            "f_tcb_acb_leads": Fact(
                fact_id="f_tcb_acb_leads",
                fact_type="lead_count",
                entity_id="TCB",
                other_entity_id="ACB",
                metric_id="comparison.overall",
                period="2024_Q4",
                value=3.0,
                denominator=4,
                unit="count",
            ),
            # Derived ratio ROE/ROA
            "f_acb_roe_roa": Fact(
                fact_id="f_acb_roe_roa",
                fact_type="derived_ratio",
                entity_id="ACB",
                metric_id="derived.roe_over_roa",
                period="2024_Q4",
                value=10.2502,
                unit="x",
            ),
            "f_tcb_roe_roa": Fact(
                fact_id="f_tcb_roe_roa",
                fact_type="derived_ratio",
                entity_id="TCB",
                metric_id="derived.roe_over_roa",
                period="2024_Q4",
                value=6.4583,
                unit="x",
            ),
            # Multi-period NPL for ACB
            "f_acb_npl_q2": Fact(fact_id="f_acb_npl_q2", fact_type="value", entity_id="ACB", metric_id="bank.npl_g35", period="2024_Q2", value=1.50, unit="%"),
            "f_acb_npl_d_q2_q3": Fact(fact_id="f_acb_npl_d_q2_q3", fact_type="delta", entity_id="ACB", metric_id="bank.npl_g35", period="2024_Q3", from_period="2024_Q2", value=0.01, unit="pp"),
            "f_acb_npl_d_q3_q4": Fact(fact_id="f_acb_npl_d_q3_q4", fact_type="delta", entity_id="ACB", metric_id="bank.npl_g35", period="2024_Q4", from_period="2024_Q3", value=0.002, unit="pp"),
            "f_acb_npl_d_q3_q4_bad": Fact(fact_id="f_acb_npl_d_q3_q4_bad", fact_type="delta", entity_id="ACB", metric_id="bank.npl_g35", period="2024_Q4", from_period="2024_Q3", value=0.0001, unit="pp"),
            # Additional facts for real-model reproduction tests (ER-4b)
            "f_acb_npl_med_q4": Fact(fact_id="f_acb_npl_med_q4", fact_type="peer_median", metric_id="bank.npl_g35", period="2024_Q4", value=1.5122, unit="%", denominator=5),
            "f_acb_npl_rank_q4": Fact(fact_id="f_acb_npl_rank_q4", fact_type="peer_rank", entity_id="ACB", metric_id="bank.npl_g35", period="2024_Q4", value=3.0, unit="rank", rank_better=3, rank_desc=3, denominator=5),
            "f_acb_roa_q4": Fact(fact_id="f_acb_roa_q4", fact_type="value", entity_id="ACB", metric_id="bank.roa", period="2024_Q4", value=2.1215, unit="%"),
            "f_acb_roa_med_q4": Fact(fact_id="f_acb_roa_med_q4", fact_type="peer_median", metric_id="bank.roa", period="2024_Q4", value=2.1215, unit="%", denominator=5),
            "f_acb_roa_rank_q4": Fact(fact_id="f_acb_roa_rank_q4", fact_type="peer_rank", entity_id="ACB", metric_id="bank.roa", period="2024_Q4", value=3.0, unit="rank", rank_better=3, rank_desc=3, denominator=5),
            "f_vcb_npl_q4": Fact(fact_id="f_vcb_npl_q4", fact_type="value", entity_id="VCB", metric_id="bank.npl_g35", period="2024_Q4", value=0.9636, unit="%"),
            "f_vcb_llr_med_q4": Fact(fact_id="f_vcb_llr_med_q4", fact_type="peer_median", metric_id="bank.llr_coverage", period="2024_Q4", value=92.2484, unit="%", denominator=5),
            "f_llr_spread_q4": Fact(fact_id="f_llr_spread_q4", fact_type="spread", metric_id="bank.llr_coverage", period="2024_Q4", value=167.1, unit="pp", denominator=5),
            "f_vpb_roe_med_d_q3_q4": Fact(fact_id="f_vpb_roe_med_d_q3_q4", fact_type="median_delta", metric_id="bank.roe", period="2024_Q4", from_period="2024_Q3", value=-0.94, unit="pp"),
            "f_acb_roe_med_q4": Fact(fact_id="f_acb_roe_med_q4", fact_type="peer_median", metric_id="bank.roe", period="2024_Q4", value=18.5965, unit="%", denominator=5),
            "f_acb_roe_raw_q4": Fact(fact_id="f_acb_roe_raw_q4", fact_type="value", entity_id="ACB", metric_id="bank.roe", period="2024_Q4", value=21.7459, unit="%"),
        }

        self.ctx = VerificationContext(
            facts=self.facts,
            plan_entities=frozenset({"ACB", "TCB", "VPB", "MBB", "VCB", "E1"}),
            catalog_entities=frozenset({"ACB", "TCB", "VPB", "MBB", "VCB", "HDB", "BID", "CTG", "E1"}),
            metric_terms={
                "bank.roe": ("roe", "sinh lời trên vốn", "return on equity"),
                "bank.roa": ("roa", "sinh lời trên tài sản", "return on assets"),
                "bank.npl_g35": ("nợ xấu", "tỷ lệ nợ xấu", "npl"),
                "bank.llr_coverage": ("bao phủ", "bao phủ nợ xấu", "đệm dự phòng", "llr"),
                "derived.roe_over_roa": ("roe/roa", "đòn bẩy vốn", "roe trên roa"),
            },
            hi_words={
                "bank.roe": ("cao",),
                "bank.roa": ("cao",),
                "bank.npl_g35": ("cao",),
                "bank.llr_coverage": ("dày", "cao"),
            },
            lo_words={
                "bank.roe": ("thấp",),
                "bank.roa": ("thấp",),
                "bank.npl_g35": ("thấp",),
                "bank.llr_coverage": ("mỏng", "thấp"),
            },
            directions={
                "bank.roe": "higher_is_better",
                "bank.roa": "higher_is_better",
                "bank.npl_g35": "lower_is_better",
                "bank.llr_coverage": "higher_is_better",
                "derived.roe_over_roa": "neutral",
            },
            flat_pp={
                "bank.roe": 0.5,
                "bank.roa": 0.05,
                "bank.npl_g35": 0.05,
                "bank.llr_coverage": 1.0,
            },
            anchor_year=2024,
        )

    def test_2_1_case_1_ok(self) -> None:
        """ROE 21,7%, cao thứ hai trong 5 ngân hàng, hơn trung vị nhóm 3,1 điểm %."""
        s = NarrativeSentence(
            sentence_id="s1",
            author="company",
            text="ROE 21,7%, cao thứ hai trong 5 ngân hàng, hơn trung vị nhóm 3,1 điểm %.",
            fact_ids=("f_acb_roe_q4", "f_acb_roe_rank_q4", "f_acb_roe_gap_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_2_tolerance_rounding_ok(self) -> None:
        """ROE 21,8% -> ok (within +-0.05 of 21.7459)."""
        s = NarrativeSentence(
            sentence_id="s2",
            author="company",
            text="ROE của ACB đạt 21,8% trong quý 4.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_3_tolerance_two_decimals_mismatch(self) -> None:
        """ROE 21,80% -> number_mismatch."""
        s = NarrativeSentence(
            sentence_id="s3",
            author="company",
            text="ROE của ACB đạt 21,80% trong quý 4.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "number_mismatch")

    def test_review_r1_tolerance_precision_76_6379(self) -> None:
        """Review R1 test: fact 76.6379 -> '76,6%' ok, '76,64%' ok, '76,60%' number_mismatch."""
        # 1. '76,6%' (d=1, tolerance=0.05, |76.6 - 76.6379| = 0.0379 <= 0.05) -> OK
        s1 = NarrativeSentence(
            sentence_id="s_prec_1",
            author="company",
            text="Tỷ lệ bao phủ nợ xấu của ACB đạt 76,6% trong quý 4.",
            fact_ids=("f_acb_llr_prec_q4",),
            source="model",
        )
        v1 = verify_sentence(s1, self.ctx)
        self.assertTrue(v1.ok, f"Expected ok for 76,6%, got: {v1.reason_code}: {v1.reason}")

        # 2. '76,64%' (d=2, tolerance=0.005, |76.64 - 76.6379| = 0.0021 <= 0.005) -> OK
        s2 = NarrativeSentence(
            sentence_id="s_prec_2",
            author="company",
            text="Tỷ lệ bao phủ nợ xấu của ACB đạt 76,64% trong quý 4.",
            fact_ids=("f_acb_llr_prec_q4",),
            source="model",
        )
        v2 = verify_sentence(s2, self.ctx)
        self.assertTrue(v2.ok, f"Expected ok for 76,64%, got: {v2.reason_code}: {v2.reason}")

        # 3. '76,60%' (d=2, tolerance=0.005, |76.60 - 76.6379| = 0.0379 > 0.005) -> number_mismatch
        s3 = NarrativeSentence(
            sentence_id="s_prec_3",
            author="company",
            text="Tỷ lệ bao phủ nợ xấu của ACB đạt 76,60% trong quý 4.",
            fact_ids=("f_acb_llr_prec_q4",),
            source="model",
        )
        v3 = verify_sentence(s3, self.ctx)
        self.assertFalse(v3.ok, "Expected mismatch for 76,60% against 76.6379")
        self.assertEqual(v3.reason_code, "number_mismatch")

    def test_2_1_case_4_wrong_metric_cited_mismatch(self) -> None:
        """ROE 1,51% (trích cả fact NPL) -> number_mismatch."""
        s = NarrativeSentence(
            sentence_id="s4",
            author="company",
            text="ROE của ACB là 1,51% trong quý 4.",
            fact_ids=("f_acb_roe_q4", "f_acb_npl_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "number_mismatch")

    def test_2_1_case_5_trend_direction_mismatch_npl(self) -> None:
        """Nợ xấu cải thiện so với quý 3 với delta = +0.0001 -> trend_direction_mismatch."""
        s = NarrativeSentence(
            sentence_id="s5",
            author="company",
            text="Nợ xấu cải thiện so với quý 3.",
            fact_ids=("f_acb_npl_d_q3_q4_bad",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason_code, "trend_direction_mismatch")

    def test_2_1_case_6_period_coverage(self) -> None:
        """Nợ xấu đi ngang từ quý 2 (1,50%) trích [value Q2, delta Q2->Q3, delta Q3->Q4] -> ok; chỉ trích [value Q4] -> period_not_cited."""
        # Case 6a: OK with all periods covered
        s_ok = NarrativeSentence(
            sentence_id="s6a",
            author="company",
            text="Nợ xấu đi ngang từ quý 2 (1,50%).",
            fact_ids=("f_acb_npl_q2", "f_acb_npl_d_q2_q3", "f_acb_npl_d_q3_q4"),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

        # Case 6b: Missing Q2 in cited facts
        s_fail = NarrativeSentence(
            sentence_id="s6b",
            author="company",
            text="Nợ xấu đi ngang từ quý 2 (1,50%).",
            fact_ids=("f_acb_npl_q4",),
            source="model",
        )
        verdict_fail = verify_sentence(s_fail, self.ctx)
        self.assertFalse(verdict_fail.ok)
        self.assertEqual(verdict_fail.reason_code, "period_not_cited")

    def test_2_1_case_7_counter_trend_ok(self) -> None:
        """Bao phủ giảm 2,5 điểm % so với quý 3, ngược xu hướng nhóm -> ok."""
        s = NarrativeSentence(
            sentence_id="s7",
            author="company",
            text="Bao phủ giảm 2,5 điểm % so với quý 3, ngược xu hướng nhóm.",
            fact_ids=("f_acb_llr_delta_q3_q4", "f_llr_med_delta_q3_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_8_superlative_and_ratio(self) -> None:
        """VCB có đệm dự phòng dày nhất, gấp 2,4 lần trung vị nhóm -> ok; gấp 2,5 lần -> number_mismatch."""
        s_ok = NarrativeSentence(
            sentence_id="s8a",
            author="sector",
            text="VCB có đệm dự phòng dày nhất, gấp 2,4 lần trung vị nhóm.",
            fact_ids=("f_vcb_llr_rank_q4", "f_vcb_llr_ratio_q4"),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

        s_bad = NarrativeSentence(
            sentence_id="s8b",
            author="sector",
            text="VCB có đệm dự phòng dày nhất, gấp 2,5 lần trung vị nhóm.",
            fact_ids=("f_vcb_llr_rank_q4", "f_vcb_llr_ratio_q4"),
            source="model",
        )
        verdict_bad = verify_sentence(s_bad, self.ctx)
        self.assertFalse(verdict_bad.ok)
        self.assertEqual(verdict_bad.reason_code, "number_mismatch")

    def test_2_1_case_9_continuous_trend(self) -> None:
        """ROE của VPB tăng liên tục qua 4 quý -> ok with 3 positive deltas; fail if one is negative."""
        s_ok = NarrativeSentence(
            sentence_id="s9a",
            author="company",
            text="ROE của VPB tăng liên tục qua 4 quý.",
            fact_ids=("f_vpb_roe_d_q1_q2", "f_vpb_roe_d_q2_q3", "f_vpb_roe_d_q3_q4"),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

        # Introduce a negative delta
        bad_delta = Fact(
            fact_id="f_bad_delta",
            fact_type="delta",
            entity_id="VPB",
            metric_id="bank.roe",
            period="2024_Q3",
            from_period="2024_Q2",
            value=-0.5,
            unit="pp",
        )
        ctx_bad = VerificationContext(
            facts={**self.facts, "f_bad_delta": bad_delta},
            plan_entities=self.ctx.plan_entities,
            catalog_entities=self.ctx.catalog_entities,
            metric_terms=self.ctx.metric_terms,
            hi_words=self.ctx.hi_words,
            lo_words=self.ctx.lo_words,
            directions=self.ctx.directions,
            flat_pp=self.ctx.flat_pp,
            anchor_year=2024,
        )
        s_fail = NarrativeSentence(
            sentence_id="s9b",
            author="company",
            text="ROE của VPB tăng liên tục qua 4 quý.",
            fact_ids=("f_vpb_roe_d_q1_q2", "f_bad_delta", "f_vpb_roe_d_q3_q4"),
            source="model",
        )
        verdict_fail = verify_sentence(s_fail, ctx_bad)
        self.assertFalse(verdict_fail.ok)
        self.assertEqual(verdict_fail.reason_code, "trend_direction_mismatch")

    def test_2_1_case_10_gap_narrowing(self) -> None:
        """Khoảng cách với trung vị thu hẹp từ 9,4 xuống 7,2 điểm % -> ok."""
        s = NarrativeSentence(
            sentence_id="s10",
            author="company",
            text="Khoảng cách với trung vị thu hẹp từ 9,4 xuống 7,2 điểm %.",
            fact_ids=("f_vpb_roe_gap_q1", "f_vpb_roe_gap_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_11_lead_count(self) -> None:
        """TCB nhỉnh hơn ở 3/4 chỉ tiêu -> ok; 4/4 chỉ tiêu -> count_mismatch."""
        s_ok = NarrativeSentence(
            sentence_id="s11a",
            author="company",
            text="TCB nhỉnh hơn ở 3/4 chỉ tiêu.",
            fact_ids=("f_tcb_acb_leads",),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

        s_bad = NarrativeSentence(
            sentence_id="s11b",
            author="company",
            text="TCB nhỉnh hơn ở 4/4 chỉ tiêu.",
            fact_ids=("f_tcb_acb_leads",),
            source="model",
        )
        verdict_bad = verify_sentence(s_bad, self.ctx)
        self.assertFalse(verdict_bad.ok)
        self.assertEqual(verdict_bad.reason_code, "count_mismatch")

    def test_2_1_case_12_implication_not_causal(self) -> None:
        """ROE/ROA của ACB khoảng 10,3 lần, hàm ý đòn bẩy vốn cao hơn -> ok (not causal)."""
        s = NarrativeSentence(
            sentence_id="s12",
            author="company",
            text="ROE/ROA của ACB khoảng 10,3 lần, hàm ý đòn bẩy vốn cao hơn.",
            fact_ids=("f_acb_roe_roa",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_13_causal_language_and_exclusion(self) -> None:
        """ROE cao nhờ chi phí thấp -> causal_language; lý do chính... -> không bị."""
        s_bad = NarrativeSentence(
            sentence_id="s13a",
            author="company",
            text="ROE cao nhờ chi phí thấp.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict_bad = verify_sentence(s_bad, self.ctx)
        self.assertFalse(verdict_bad.ok)
        self.assertEqual(verdict_bad.reason_code, "causal_language")

        s_ok = NarrativeSentence(
            sentence_id="s13b",
            author="company",
            text="Lý do chính giúp ROE đạt 21,7% là sự ổn định của bảng cân đối.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

    def test_2_1_case_14_investment_advice_and_exclusion(self) -> None:
        """Nên mua ACB -> investment_advice; mảng bán lẻ -> không bị."""
        s_bad = NarrativeSentence(
            sentence_id="s14a",
            author="company",
            text="Nên mua ACB trong giai đoạn này.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict_bad = verify_sentence(s_bad, self.ctx)
        self.assertFalse(verdict_bad.ok)
        self.assertEqual(verdict_bad.reason_code, "investment_advice")

        s_ok = NarrativeSentence(
            sentence_id="s14b",
            author="company",
            text="Mảng bán lẻ ghi nhận ROE đạt 21,7%.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict_ok = verify_sentence(s_ok, self.ctx)
        self.assertTrue(verdict_ok.ok, f"Expected ok, got: {verdict_ok.reason_code}: {verdict_ok.reason}")

    def test_2_1_case_15_entity_and_year(self) -> None:
        """Tỷ lệ nợ xấu của E1 là một điểm đáng chú ý trong năm 2024 -> ok."""
        fact_e1_npl = Fact(
            fact_id="f_e1_npl_2024",
            fact_type="value",
            entity_id="E1",
            metric_id="bank.npl_g35",
            period="2024_Q4",
            value=1.5122,
            unit="%",
        )
        ctx = VerificationContext(
            facts={**self.facts, "f_e1_npl_2024": fact_e1_npl},
            plan_entities=self.ctx.plan_entities,
            catalog_entities=self.ctx.catalog_entities,
            metric_terms=self.ctx.metric_terms,
            hi_words=self.ctx.hi_words,
            lo_words=self.ctx.lo_words,
            directions=self.ctx.directions,
            flat_pp=self.ctx.flat_pp,
            anchor_year=2024,
        )
        s = NarrativeSentence(
            sentence_id="s15",
            author="company",
            text="Tỷ lệ nợ xấu của E1 là một điểm đáng chú ý trong năm 2024.",
            fact_ids=("f_e1_npl_2024",),
            source="model",
        )
        verdict = verify_sentence(s, ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_2_1_case_16_quarter_not_confused_with_rank(self) -> None:
        """quý 4/2024 không bị hiểu là hạng 4/2024."""
        s = NarrativeSentence(
            sentence_id="s16",
            author="company",
            text="Trong quý 4/2024, ROE của ACB đạt 21,7%.",
            fact_ids=("f_acb_roe_q4",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_reviewer_note_4a_comparison_two_facts_derived_ratio(self) -> None:
        """Mandatory reviewer note 4a:

        'ROE/ROA của ACB 10,25 lần, cao hơn mức 6,46 lần của TCB' -> ok.
        """
        s = NarrativeSentence(
            sentence_id="s_rev_4a",
            author="company",
            text="ROE/ROA của ACB 10,25 lần, cao hơn mức 6,46 lần của TCB.",
            fact_ids=("f_acb_roe_roa", "f_tcb_roe_roa"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")
        self.assertEqual(verdict.numbers_matched, 2)

    def test_fallback_sentences_pass_verifier(self) -> None:
        """Every deterministic fallback sentence generated for any fact must pass verify_sentence."""
        from thesis_api.narrative_templates import make_fallback_sentence

        for fid, f in self.facts.items():
            if f.value is None and f.fact_type != "peer_rank":
                continue
            fb_dto = make_fallback_sentence(f, seq=1)
            ns = NarrativeSentence(
                sentence_id=fb_dto.sentence_id,
                author=fb_dto.author,
                text=fb_dto.text,
                fact_ids=tuple(fb_dto.fact_ids),
                source=fb_dto.source,
            )
            verdict = verify_sentence(ns, self.ctx)
            self.assertTrue(verdict.ok, f"Fallback sentence failed for {fid} ({ns.text}): {verdict.reason_code}: {verdict.reason}")


    def test_er4b_case_aa_equal_to_median(self) -> None:
        """A.a: ACB NPL 1.51% equals peer median and rank 3/5 -> ok."""
        s = NarrativeSentence(
            sentence_id="s_aa",
            author="sector",
            text="Tỷ lệ nợ xấu của ACB ở mức 1,51%, đúng bằng trung vị nhóm và xếp hạng 3/5.",
            fact_ids=("f_acb_npl_q4", "f_acb_npl_med_q4", "f_acb_npl_rank_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

        s_roa = NarrativeSentence(
            sentence_id="s_aa_roa",
            author="sector",
            text="ROA của ACB ở mức 2,12%, bằng trung vị nhóm.",
            fact_ids=("f_acb_roa_q4", "f_acb_roa_med_q4"),
            source="model",
        )
        verdict_roa = verify_sentence(s_roa, self.ctx)
        self.assertTrue(verdict_roa.ok, f"Expected ok, got: {verdict_roa.reason_code}: {verdict_roa.reason}")

    def test_er4b_case_ab_pp_difference(self) -> None:
        """A.b: ACB ROE 21,7% higher than peer median by 3.1 percentage points -> ok."""
        s = NarrativeSentence(
            sentence_id="s_ab",
            author="sector",
            text="ROE của ACB đạt 21,7%, cao hơn trung vị nhóm 3,1 điểm phần trăm và xếp hạng 2/5.",
            fact_ids=("f_acb_roe_raw_q4", "f_acb_roe_med_q4", "f_acb_roe_rank_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_er4b_case_ac_ratio_exceeds_median(self) -> None:
        """A.c: VCB surpasses peer median, 2.4x median 92.2% -> ok."""
        s = NarrativeSentence(
            sentence_id="s_ac",
            author="sector",
            text="VCB vượt trội so với trung vị ngành, gấp 2,4 lần trung vị 92,2%.",
            fact_ids=("f_vcb_llr_q4", "f_vcb_llr_med_q4", "f_vcb_llr_ratio_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_er4b_case_ad_spread_range_not_rank_mismatch(self) -> None:
        """A.d: 'cao nhất và thấp nhất' in spread context describes bounds, not rank."""
        s = NarrativeSentence(
            sentence_id="s_ad",
            author="sector",
            text="Chênh lệch giữa ngân hàng cao nhất và thấp nhất là 167,1 điểm phần trăm, phản ánh phân hóa mạnh về đệm dự phòng trong nhóm.",
            fact_ids=("f_llr_spread_q4",),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_er4b_case_ae_median_trend_decrease(self) -> None:
        """A.e: 'trung vị nhóm ngân hàng giảm -0,9 điểm %' matches median_delta -0.94 and counter-trend."""
        s = NarrativeSentence(
            sentence_id="s_ae",
            author="sector",
            text="Trong khi đó, trung vị nhóm ngân hàng giảm -0,9 điểm % ở quý 4, cho thấy xu hướng ngược chiều.",
            fact_ids=("f_vpb_roe_d_q3_q4", "f_vpb_roe_med_d_q3_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")

    def test_er4b_case_af_lookup_peer_comparison(self) -> None:
        """A.f: 'Mức 0,96% thấp hơn trung vị tỷ lệ nợ xấu của nhóm 5 ngân hàng là 1,51%' -> ok."""
        s = NarrativeSentence(
            sentence_id="s_af",
            author="company",
            text="Mức 0,96% thấp hơn trung vị tỷ lệ nợ xấu của nhóm 5 ngân hàng là 1,51%.",
            fact_ids=("f_vcb_npl_q4", "f_acb_npl_med_q4"),
            source="model",
        )
        verdict = verify_sentence(s, self.ctx)
        self.assertTrue(verdict.ok, f"Expected ok, got: {verdict.reason_code}: {verdict.reason}")


if __name__ == "__main__":
    unittest.main()

