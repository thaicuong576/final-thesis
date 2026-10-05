"""Unit tests for Task PROMPT-1: writer prompts, verifier rules, audit citations, count rule, and token limits."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from thesis_api.analysis_writer import (
    COMPOSE_REPORT_PROMPT_TEMPLATE,
    FINDINGS_PROMPT_TEMPLATE,
    REWRITE_SENTENCE_PROMPT_TEMPLATE,
    OpenAIAnalysisWriter,
)
from thesis_api.schemas import SentenceDroppedDTO
from thesis_api.settings import Settings
from thesis_data.narrative_verification import (
    NarrativeSentence,
    VerificationContext,
    verify_sentence,
)
from thesis_data.report_facts import Fact


def _make_ctx(facts: dict[str, Fact], **overrides) -> VerificationContext:
    defaults = {
        "facts": facts,
        "plan_entities": frozenset({"ACB", "TCB", "VPB", "MBB", "VCB", "HDB", "CTG", "BID"}),
        "catalog_entities": frozenset({"ACB", "TCB", "VPB", "MBB", "VCB", "HDB", "CTG", "BID", "SHB", "STB"}),
        "metric_terms": {
            "bank.roe": ("roe", "sinh lời trên vốn", "return on equity"),
            "bank.roa": ("roa", "sinh lời trên tài sản", "return on assets"),
            "bank.npl_g35": ("nợ xấu", "tỷ lệ nợ xấu", "npl"),
            "bank.llr_coverage": ("bao phủ", "bao phủ nợ xấu", "đệm dự phòng", "llr"),
            "derived.roe_over_roa": ("roe/roa", "đòn bẩy vốn", "roe trên roa"),
        },
        "hi_words": {
            "bank.roe": ("cao",),
            "bank.roa": ("cao",),
            "bank.npl_g35": ("cao",),
            "bank.llr_coverage": ("dày", "cao"),
        },
        "lo_words": {
            "bank.roe": ("thấp",),
            "bank.roa": ("thấp",),
            "bank.npl_g35": ("thấp",),
            "bank.llr_coverage": ("mỏng", "thấp"),
        },
        "directions": {
            "bank.roe": "higher_is_better",
            "bank.roa": "higher_is_better",
            "bank.npl_g35": "lower_is_better",
            "bank.llr_coverage": "higher_is_better",
            "derived.roe_over_roa": "neutral",
        },
        "flat_pp": {
            "bank.roe": 0.5,
            "bank.roa": 0.05,
            "bank.npl_g35": 0.05,
            "bank.llr_coverage": 1.0,
        },
        "anchor_year": 2026,
    }
    defaults.update(overrides)
    return VerificationContext(**defaults)


def _make_sent(
    sentence_id: str,
    text: str,
    fact_ids: tuple[str, ...],
    author: str = "company_specialist",
    source: str = "model",
) -> NarrativeSentence:
    return NarrativeSentence(
        sentence_id=sentence_id,
        text=text,
        fact_ids=tuple(fact_ids),
        author=author,
        source=source,
    )


class Prompt1VerifierRulesTestCase(unittest.TestCase):
    """Test suite covering the 5 items required by Task PROMPT-1."""

    # -------------------------------------------------------------------------
    # Item 1: Audit carries citations (SentenceDroppedDTO & backward compatibility)
    # -------------------------------------------------------------------------
    def test_item_1_sentence_dropped_dto_carries_fact_ids(self) -> None:
        """SentenceDroppedDTO carries cited fact_ids and serializes properly."""
        dto = SentenceDroppedDTO(
            sentence_id="sent-1",
            author="company_specialist",
            text="Tỷ lệ nợ xấu giảm.",
            fact_ids=["fact:delta:ACB:2026_Q2:2026_Q1:bank.npl_g35"],
            reason_code="trend_direction_mismatch",
            reason="Nhận định không khớp",
        )
        self.assertEqual(dto.fact_ids, ["fact:delta:ACB:2026_Q2:2026_Q1:bank.npl_g35"])
        dumped = dto.model_dump(mode="json")
        self.assertIn("fact_ids", dumped)
        self.assertEqual(dumped["fact_ids"], ["fact:delta:ACB:2026_Q2:2026_Q1:bank.npl_g35"])

    def test_item_1_sentence_dropped_dto_backward_compatible(self) -> None:
        """Existing stored runs without fact_ids in dropped sentences load with default []."""
        payload = {
            "sentence_id": "sent-old",
            "author": "orchestrator",
            "text": "Câu cũ không có fact_ids.",
            "reason_code": "unknown_fact",
            "reason": "không kiểm chứng được",
        }
        dto = SentenceDroppedDTO.model_validate(payload)
        self.assertEqual(dto.fact_ids, [])

    # -------------------------------------------------------------------------
    # Item 2: Offline unit reproductions for Cases A, B, C, D
    # -------------------------------------------------------------------------
    def test_item_2_case_a_reproduction(self) -> None:
        """Case A: Two metrics moving in different directions in a single sentence.

        Verifier limit found: Verifier binds direction words against the first delta fact
        (primary delta), so opposing direction words ('đi ngang' vs -8.64 pp) fail.
        """
        f_llr_delta = Fact(
            fact_id="fact:delta:ACB:2026_Q2:2026_Q1:bank.llr_coverage",
            fact_type="delta",
            entity_id="ACB",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            from_period="2026_Q1",
            value=-8.64,
            unit="pp",
        )
        f_npl_delta = Fact(
            fact_id="fact:delta:ACB:2026_Q2:2026_Q1:bank.npl_g35",
            fact_type="delta",
            entity_id="ACB",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            from_period="2026_Q1",
            value=0.03,
            unit="pp",
        )
        facts = {f_llr_delta.fact_id: f_llr_delta, f_npl_delta.fact_id: f_npl_delta}
        ctx = _make_ctx(facts)

        sent_text = (
            "So với quý 1/2026, tỷ lệ bao phủ nợ xấu giảm -8,6 điểm %, "
            "còn tỷ lệ nợ xấu đi ngang (+0,03 điểm %)."
        )

        # (a) Fully cited with both delta facts: rejected with trend_direction_mismatch
        s_full = _make_sent(
            sentence_id="s_case_a_full",
            text=sent_text,
            fact_ids=(f_llr_delta.fact_id, f_npl_delta.fact_id),
            author="company_specialist",
        )
        v_full = verify_sentence(s_full, ctx)
        self.assertFalse(v_full.ok)
        self.assertEqual(v_full.reason_code, "trend_direction_mismatch")

        # (b) Partially cited (only LLR delta): rejected with number_mismatch for 0.03
        s_part = _make_sent(
            sentence_id="s_case_a_part",
            text=sent_text,
            fact_ids=(f_llr_delta.fact_id,),
            author="company_specialist",
        )
        v_part = verify_sentence(s_part, ctx)
        self.assertFalse(v_part.ok)
        self.assertEqual(v_part.reason_code, "number_mismatch")

        # Split into two sentences: both pass
        s1 = _make_sent(
            sentence_id="s1",
            text="So với quý 1/2026, tỷ lệ bao phủ nợ xấu giảm -8,6 điểm %.",
            fact_ids=(f_llr_delta.fact_id,),
            author="company_specialist",
        )
        s2 = _make_sent(
            sentence_id="s2",
            text="So với quý 1/2026, tỷ lệ nợ xấu đi ngang (+0,03 điểm %).",
            fact_ids=(f_npl_delta.fact_id,),
            author="company_specialist",
        )
        self.assertTrue(verify_sentence(s1, ctx).ok)
        self.assertTrue(verify_sentence(s2, ctx).ok)

    def test_item_2_case_b_reproduction(self) -> None:
        """Case B: Multi-quarter trend sentence naming quarters not all cited / conflicting trends.

        Verifier limit found: Named quarters require matching period or from_period in facts;
        conflicting direction words across quarters also fail against primary delta.
        """
        f_roa_q1 = Fact(
            fact_id="fact:value:ACB:2024_Q1:bank.roa",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.roa",
            period="2024_Q1",
            value=2.19,
            unit="%",
        )
        f_roa_q3 = Fact(
            fact_id="fact:value:ACB:2024_Q3:bank.roa",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.roa",
            period="2024_Q3",
            value=1.99,
            unit="%",
        )
        f_roa_q4 = Fact(
            fact_id="fact:value:ACB:2024_Q4:bank.roa",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.roa",
            period="2024_Q4",
            value=2.00,
            unit="%",
        )
        f_roa_delta_fy = Fact(
            fact_id="fact:delta:ACB:2024_Q4:2024_Q1:bank.roa",
            fact_type="delta",
            entity_id="ACB",
            metric_id="bank.roa",
            period="2024_Q4",
            from_period="2024_Q1",
            value=-0.19,
            unit="pp",
        )
        facts = {
            f_roa_q1.fact_id: f_roa_q1,
            f_roa_q3.fact_id: f_roa_q3,
            f_roa_q4.fact_id: f_roa_q4,
            f_roa_delta_fy.fact_id: f_roa_delta_fy,
        }
        ctx = _make_ctx(facts, anchor_year=2024)

        sent_text = (
            "ROA giảm từ 2,19% quý 1/2024 xuống 1,99% quý 3/2024, "
            "sau đó đi ngang ở 2,00% quý 4/2024; tính cả năm, ROA giảm -0,19 điểm %."
        )

        # (a) Fully cited with all quarters and full-year delta: rejected with trend_direction_mismatch
        # because 'đi ngang' is tested against full-year delta -0.19 pp
        s_full = _make_sent(
            sentence_id="s_case_b_full",
            text=sent_text,
            fact_ids=(f_roa_q1.fact_id, f_roa_q3.fact_id, f_roa_q4.fact_id, f_roa_delta_fy.fact_id),
            author="company_specialist",
        )
        v_full = verify_sentence(s_full, ctx)
        self.assertFalse(v_full.ok)
        self.assertEqual(v_full.reason_code, "trend_direction_mismatch")

        # (b) Partially cited (omit Q3 fact): rejected with period_not_cited on quý 3
        s_part = _make_sent(
            sentence_id="s_case_b_part",
            text=sent_text,
            fact_ids=(f_roa_q1.fact_id, f_roa_q4.fact_id, f_roa_delta_fy.fact_id),
            author="company_specialist",
        )
        v_part = verify_sentence(s_part, ctx)
        self.assertFalse(v_part.ok)
        self.assertEqual(v_part.reason_code, "period_not_cited")

    def test_item_2_case_c_reproduction(self) -> None:
        """Case C: Multiple metrics and ranks in one sentence causing rank_mismatch.

        Verifier limit found: Metric matching in rank clause without explicit metric term
        scans the sentence sorted by descending length, causing collisions between
        'bao phủ nợ xấu' (len 14) and 'tỷ lệ nợ xấu' (len 12).
        """
        f_npl_val = Fact(
            fact_id="fact:value:ACB:2026_Q2:bank.npl_g35",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            value=1.03,
            unit="%",
        )
        f_npl_gap = Fact(
            fact_id="fact:gap_to_median:ACB:sector:bank:2026_Q2:bank.npl_g35",
            fact_type="gap_to_median",
            entity_id="ACB",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            value=-0.61,
            unit="pp",
            denominator=10,
        )
        f_npl_rank = Fact(
            fact_id="fact:peer_rank:ACB:sector:bank:2026_Q2:bank.npl_g35",
            fact_type="peer_rank",
            entity_id="ACB",
            metric_id="bank.npl_g35",
            period="2026_Q2",
            value=2.0,
            unit="rank",
            rank_better=2,
            rank_desc=2,
            denominator=10,
        )
        f_llr_val = Fact(
            fact_id="fact:value:ACB:2026_Q2:bank.llr_coverage",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            value=105.3,
            unit="%",
        )
        f_llr_rank = Fact(
            fact_id="fact:peer_rank:ACB:sector:bank:2026_Q2:bank.llr_coverage",
            fact_type="peer_rank",
            entity_id="ACB",
            metric_id="bank.llr_coverage",
            period="2026_Q2",
            value=4.0,
            unit="rank",
            rank_better=4,
            rank_desc=4,
            denominator=10,
        )
        facts = {
            f.fact_id: f
            for f in (f_npl_val, f_npl_gap, f_npl_rank, f_llr_val, f_llr_rank)
        }
        ctx = _make_ctx(facts)

        sent_text = (
            "Chất lượng tài sản tích cực: tỷ lệ nợ xấu 1,03%, thấp hơn trung vị nhóm -0,61 điểm %, "
            "hạng 2/10; bao phủ nợ xấu 105,3%, hạng 4/10."
        )

        # (a) Fully cited: rejected with rank_mismatch
        s_full = _make_sent(
            sentence_id="s_case_c_full",
            text=sent_text,
            fact_ids=tuple(facts.keys()),
            author="company_specialist",
        )
        v_full = verify_sentence(s_full, ctx)
        self.assertFalse(v_full.ok)
        self.assertEqual(v_full.reason_code, "rank_mismatch")

        # (b) Split into two sentences: both pass!
        s1 = _make_sent(
            sentence_id="s_c_split1",
            text="Tỷ lệ nợ xấu 1,03%, thấp hơn trung vị nhóm -0,61 điểm %, hạng 2/10.",
            fact_ids=(f_npl_val.fact_id, f_npl_gap.fact_id, f_npl_rank.fact_id),
            author="company_specialist",
        )
        s2 = _make_sent(
            sentence_id="s_c_split2",
            text="Bao phủ nợ xấu 105,3%, hạng 4/10.",
            fact_ids=(f_llr_val.fact_id, f_llr_rank.fact_id),
            author="company_specialist",
        )
        self.assertTrue(verify_sentence(s1, ctx).ok)
        self.assertTrue(verify_sentence(s2, ctx).ok)

    def test_item_2_case_d_reproduction(self) -> None:
        """Case D: Listing multiple entity values and ranks in one sentence.

        Verifier limit found: Entity-number proximity window (3 words lookback) fails
        when rank intervenes between entity and number, e.g. 'HDB hạng 1/10 (25,4%)'.
        Placing value adjacent to entity passes.
        """
        f_hdb_val = Fact(
            fact_id="fact:value:HDB:2025_Q4:bank.roe",
            fact_type="value",
            entity_id="HDB",
            metric_id="bank.roe",
            period="2025_Q4",
            value=25.4,
            unit="%",
        )
        f_hdb_rank = Fact(
            fact_id="fact:peer_rank:HDB:sector:bank:2025_Q4:bank.roe",
            fact_type="peer_rank",
            entity_id="HDB",
            metric_id="bank.roe",
            period="2025_Q4",
            value=1.0,
            unit="rank",
            rank_better=1,
            rank_desc=1,
            denominator=10,
        )
        f_mbb_val = Fact(
            fact_id="fact:value:MBB:2025_Q4:bank.roe",
            fact_type="value",
            entity_id="MBB",
            metric_id="bank.roe",
            period="2025_Q4",
            value=21.6,
            unit="%",
        )
        f_mbb_rank = Fact(
            fact_id="fact:peer_rank:MBB:sector:bank:2025_Q4:bank.roe",
            fact_type="peer_rank",
            entity_id="MBB",
            metric_id="bank.roe",
            period="2025_Q4",
            value=2.0,
            unit="rank",
            rank_better=2,
            rank_desc=2,
            denominator=10,
        )
        f_ctg_val = Fact(
            fact_id="fact:value:CTG:2025_Q4:bank.roe",
            fact_type="value",
            entity_id="CTG",
            metric_id="bank.roe",
            period="2025_Q4",
            value=21.2,
            unit="%",
        )
        f_ctg_rank = Fact(
            fact_id="fact:peer_rank:CTG:sector:bank:2025_Q4:bank.roe",
            fact_type="peer_rank",
            entity_id="CTG",
            metric_id="bank.roe",
            period="2025_Q4",
            value=3.0,
            unit="rank",
            rank_better=3,
            rank_desc=3,
            denominator=10,
        )
        facts = {
            f.fact_id: f
            for f in (f_hdb_val, f_hdb_rank, f_mbb_val, f_mbb_rank, f_ctg_val, f_ctg_rank)
        }
        ctx = _make_ctx(facts, anchor_year=2025)

        sent_text = (
            "ROE quý 4/2025 xếp hạng: HDB hạng 1/10 (25,4%), "
            "MBB hạng 2/10 (21,6%), CTG hạng 3/10 (21,2%)."
        )

        # (a) Fully cited: rejected with number_mismatch due to lookahead cross-pairing
        s_full = _make_sent(
            sentence_id="s_case_d_full",
            text=sent_text,
            fact_ids=tuple(facts.keys()),
            author="company_specialist",
        )
        v_full = verify_sentence(s_full, ctx)
        self.assertFalse(v_full.ok)
        self.assertEqual(v_full.reason_code, "number_mismatch")

        # (b) Partially cited (only ranks, no values): rejected with number_mismatch
        s_part = _make_sent(
            sentence_id="s_case_d_part",
            text=sent_text,
            fact_ids=(f_hdb_rank.fact_id, f_mbb_rank.fact_id, f_ctg_rank.fact_id),
            author="company_specialist",
        )
        v_part = verify_sentence(s_part, ctx)
        self.assertFalse(v_part.ok)
        self.assertEqual(v_part.reason_code, "number_mismatch")

        # Rewritten placing value directly adjacent to entity: passes!
        rewritten_text = (
            "ROE quý 4/2025: HDB đạt 25,4% (hạng 1/10), "
            "MBB đạt 21,6% (hạng 2/10), CTG đạt 21,2% (hạng 3/10)."
        )
        s_fixed = _make_sent(
            sentence_id="s_case_d_fixed",
            text=rewritten_text,
            fact_ids=tuple(facts.keys()),
            author="company_specialist",
        )
        self.assertTrue(verify_sentence(s_fixed, ctx).ok)

    # -------------------------------------------------------------------------
    # Item 3: All 3 prompt templates contain the 4 verifier rules
    # -------------------------------------------------------------------------
    def test_item_3_prompt_templates_contain_all_four_rules(self) -> None:
        """Each of the 3 prompt templates states the 4 verifier rules in Vietnamese."""
        templates = {
            "FINDINGS_PROMPT_TEMPLATE": FINDINGS_PROMPT_TEMPLATE,
            "COMPOSE_REPORT_PROMPT_TEMPLATE": COMPOSE_REPORT_PROMPT_TEMPLATE,
            "REWRITE_SENTENCE_PROMPT_TEMPLATE": REWRITE_SENTENCE_PROMPT_TEMPLATE,
        }

        for name, tmpl in templates.items():
            # Rule 1: fact_ids must cover every number, rank, and period (quarter only if cited)
            self.assertTrue(
                "MỌI số liệu, mọi thứ hạng và mọi kỳ xuất hiện trong câu" in tmpl
                and "chỉ được nêu tên quý nếu fact" in tmpl,
                f"{name} must contain rule 1 on fact_ids covering every number, rank, and period",
            )
            # Rule 2: Write periods in full 'quý N/YYYY'
            self.assertTrue(
                'quý N/YYYY' in tmpl,
                f"{name} must contain rule 2 on full period format 'quý N/YYYY'",
            )
            # Rule 3: One sentence describes one metric and one direction word; split two metrics
            self.assertTrue(
                "Một câu chỉ mô tả một chỉ tiêu và dùng một từ định hướng" in tmpl
                and "Hai chỉ tiêu biến động khác nhau phải tách thành hai câu" in tmpl,
                f"{name} must contain rule 3 on single metric/direction and splitting two metrics",
            )
            # Rule 4: Copy fact_id exactly without inventing
            self.assertTrue(
                "Chép chính xác chuỗi fact_id" in tmpl
                and "tuyệt đối không tự tạo hoặc sửa fact_id" in tmpl,
                f"{name} must contain rule 4 on copying fact_id strings exactly",
            )

    # -------------------------------------------------------------------------
    # Item 4: Count rule (E) accepts distinct cited entities count
    # -------------------------------------------------------------------------
    def test_item_4_count_rule_accepts_distinct_entities_in_head_to_head(self) -> None:
        """Count 'hai ngân hàng' passes when cited facts cover exactly 2 distinct entities with denominator=None."""
        f_acb = Fact(
            fact_id="fact:value:ACB:2026_Q2:bank.roe",
            fact_type="value",
            entity_id="ACB",
            metric_id="bank.roe",
            period="2026_Q2",
            value=21.5,
            unit="%",
            denominator=None,
        )
        f_tcb = Fact(
            fact_id="fact:value:TCB:2026_Q2:bank.roe",
            fact_type="value",
            entity_id="TCB",
            metric_id="bank.roe",
            period="2026_Q2",
            value=18.2,
            unit="%",
            denominator=None,
        )
        ctx = _make_ctx({f_acb.fact_id: f_acb, f_tcb.fact_id: f_tcb})

        # Sentence with 'hai ngân hàng' citing 2 distinct entities -> PASSES
        s_two = _make_sent(
            sentence_id="s_h2h_2",
            text="Lợi thế được phân bổ cân bằng giữa hai ngân hàng.",
            fact_ids=(f_acb.fact_id, f_tcb.fact_id),
            author="company_specialist",
        )
        self.assertTrue(verify_sentence(s_two, ctx).ok)

        # Sentence with 'ba ngân hàng' citing only 2 distinct entities -> REJECTED with number_mismatch
        s_three = _make_sent(
            sentence_id="s_h2h_3",
            text="Lợi thế được phân bổ cân bằng giữa ba ngân hàng.",
            fact_ids=(f_acb.fact_id, f_tcb.fact_id),
            author="company_specialist",
        )
        v_three = verify_sentence(s_three, ctx)
        self.assertFalse(v_three.ok)
        self.assertEqual(v_three.reason_code, "number_mismatch")

    def test_item_4_count_rule_still_accepts_denominator(self) -> None:
        """Count matching fact denominator continues to pass."""
        f_rank = Fact(
            fact_id="fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
            fact_type="peer_rank",
            entity_id="ACB",
            metric_id="bank.roe",
            period="2024_Q4",
            value=2.0,
            unit="rank",
            denominator=5,
        )
        ctx = _make_ctx({f_rank.fact_id: f_rank}, anchor_year=2024)
        s = _make_sent(
            sentence_id="s_cnt_denom",
            text="ACB đứng thứ hai trong nhóm năm ngân hàng.",
            fact_ids=(f_rank.fact_id,),
            author="company_specialist",
        )
        self.assertTrue(verify_sentence(s, ctx).ok)

    # -------------------------------------------------------------------------
    # Item 5: Output limits (G) in Settings, Critic, and Writer
    # -------------------------------------------------------------------------
    def test_item_5_settings_output_limits_defaults(self) -> None:
        """Settings defaults: writer 6000, critic 8192."""
        s = Settings()
        self.assertEqual(s.analysis_writer_max_output_tokens, 6000)
        self.assertEqual(s.semantic_critic_max_output_tokens, 8192)

    def test_item_5_settings_output_limits_env_override(self) -> None:
        """Settings overrides via environment variables."""
        s = Settings(
            ANALYSIS_WRITER_MAX_OUTPUT_TOKENS=7500,
            SEMANTIC_CRITIC_MAX_OUTPUT_TOKENS=9000,
        )
        self.assertEqual(s.analysis_writer_max_output_tokens, 7500)
        self.assertEqual(s.semantic_critic_max_output_tokens, 9000)

    def test_item_5_openai_analysis_writer_max_output_tokens(self) -> None:
        """OpenAIAnalysisWriter accepts max_output_tokens or defaults to Settings."""
        mock_client = MagicMock()
        writer_default = OpenAIAnalysisWriter(client=mock_client, model="gpt-4o-mini")
        self.assertEqual(writer_default.max_output_tokens, 6000)

        writer_custom = OpenAIAnalysisWriter(client=mock_client, model="gpt-4o-mini", max_output_tokens=7000)
        self.assertEqual(writer_custom.max_output_tokens, 7000)

    def test_item_5_builders_pass_max_output_tokens(self) -> None:
        """build_openai_semantic_critic and build_openai_analysis_writer wire output limits."""
        from thesis_api.adaptive_runtime import (
            build_openai_analysis_writer,
            build_openai_semantic_critic,
        )
        s = Settings(
            OPENAI_API_KEY="test-key",
            ANALYSIS_WRITER_MAX_OUTPUT_TOKENS=7200,
            SEMANTIC_CRITIC_MAX_OUTPUT_TOKENS=9500,
        )
        critic = build_openai_semantic_critic(s)
        self.assertEqual(critic._config.max_output_tokens, 9500)

        writer = build_openai_analysis_writer(s)
        self.assertEqual(writer.max_output_tokens, 7200)


if __name__ == "__main__":
    unittest.main()

