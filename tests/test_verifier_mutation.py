"""Tests for narrative verifier mutation operators and evaluation logic."""

import random
from typing import Sequence
import pytest

from scripts.verifier_mutation import (
    ALL_OPERATORS,
    apply_mutation_operator,
    find_metric_numbers,
    mutate_causal_claim,
    mutate_denominator,
    mutate_digit_swap,
    mutate_direction_flip,
    mutate_entity_swap,
    mutate_metric_swap,
    mutate_number_large,
    mutate_number_small,
    mutate_period,
    mutate_rank,
    mutate_recommendation,
    mutate_unsupported_number,
    wilson_ci,
)


def test_wilson_ci_boundaries():
    """Verify Wilson score confidence interval boundary calculations."""
    low, high = wilson_ci(100, 100)
    assert low > 0.95
    assert high == 1.0

    low_zero, high_zero = wilson_ci(0, 100)
    assert low_zero == 0.0
    assert high_zero < 0.05

    low_empty, high_empty = wilson_ci(0, 0)
    assert low_empty == 0.0
    assert high_empty == 0.0


def test_find_metric_numbers():
    """Verify that period years, ranks, and quarters are masked out from metric numbers."""
    # Sentence with rank, period, and financial metric percentage
    s1 = "BID đạt ROA 0,97% (hạng 9/10), thấp hơn trung vị nhóm trong quý 2/2026."
    nums = find_metric_numbers(s1)
    assert len(nums) == 1
    raw, suffix, start, end = nums[0]
    assert raw == "0,97"
    assert suffix == "%"

    # Sentence with no metric numbers, only qualitative comparison and period
    s2 = "BID: đệm dự phòng dưới nhóm, chất lượng nợ dưới nhóm trong quý 2/2026."
    assert find_metric_numbers(s2) == []

    # Sentence with delta pp
    s3 = "Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 2/2026."
    nums3 = find_metric_numbers(s3)
    assert len(nums3) == 1
    assert nums3[0][0] == "11,0"


def test_sentence_without_number_yields_no_number_mutants():
    """Requirement 5: A sentence without a number yields no number mutants."""
    text_without_number = "BID: đệm dự phòng dưới nhóm, chất lượng nợ dưới nhóm trong quý 2/2026."
    rng = random.Random(42)

    assert mutate_number_small(text_without_number, rng) is None
    assert mutate_number_large(text_without_number, rng) is None
    assert mutate_digit_swap(text_without_number, rng) is None

    # Via unified apply_mutation_operator
    assert apply_mutation_operator("number_small", text_without_number, [], [], [], rng) is None
    assert apply_mutation_operator("number_large", text_without_number, [], [], [], rng) is None
    assert apply_mutation_operator("digit_swap", text_without_number, [], [], [], rng) is None


def test_operator_number_small():
    """Verify number_small modifies number by 1-5% in Vietnamese format."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_number_small(text, rng)
    assert mut is not None
    assert mut != text
    assert "," in mut  # Vietnamese comma decimal separator
    assert "%" in mut


def test_operator_number_large():
    """Verify number_large multiplies or divides by 2 in Vietnamese format."""
    text = "Tỷ lệ bao phủ nợ xấu của BID đạt 75,9% trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_number_large(text, rng)
    assert mut is not None
    assert mut != text
    assert "," in mut
    # Either ~151,8% or ~38,0%
    assert ("151,8%" in mut) or ("38,0%" in mut)


def test_operator_digit_swap():
    """Verify digit_swap swaps two distinct digits."""
    text = "ROE của BID đạt 17,9% trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_digit_swap(text, rng)
    assert mut is not None
    assert mut != text
    assert "%" in mut


def test_operator_rank():
    """Verify rank changes rank x/y to another valid rank."""
    text = "BID đạt ROA 0,97% (hạng 9/10) trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_rank(text, rng)
    assert mut is not None
    assert mut != text
    assert "/10" in mut
    assert "hạng 9/10" not in mut  # Rank changed


def test_operator_denominator():
    """Verify denominator changes x/10 to x/9."""
    text = "BID đạt ROA 0,97% (hạng 9/10) trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_denominator(text, rng)
    assert mut is not None
    assert mut != text
    assert "hạng 9/9" in mut


def test_operator_period():
    """Verify period changes quarter to another quarter."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    available_quarters = ["2025_Q4", "2026_Q1"]
    rng = random.Random(42)
    mut = mutate_period(text, available_quarters, rng)
    assert mut is not None
    assert mut != text
    assert "quý 2/2026" not in mut
    assert ("quý 4/2025" in mut) or ("quý 1/2026" in mut)


def test_operator_entity_swap():
    """Verify entity_swap swaps bank ticker with another bank."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    run_banks = ["VCB", "CTG", "TCB"]
    rng = random.Random(42)
    mut = mutate_entity_swap(text, run_banks, rng)
    assert mut is not None
    assert mut != text
    assert not mut.startswith("BID ")
    assert any(mut.startswith(f"{b} ") for b in run_banks)


def test_operator_direction_flip():
    """Verify direction_flip swaps directional terms."""
    # tăng -> giảm
    t1 = "Tỷ lệ nợ xấu của STB tăng 3,66 điểm % từ quý 3/2025 đến quý 4/2025."
    mut1 = mutate_direction_flip(t1, random.Random(42))
    assert mut1 is not None
    assert "giảm 3,66 điểm %" in mut1

    # cao hơn -> thấp hơn
    t2 = "BID có tỷ lệ nợ xấu cao hơn trung vị nhóm 0,19 điểm % trong quý 2/2026."
    mut2 = mutate_direction_flip(t2, random.Random(42))
    assert mut2 is not None
    assert "thấp hơn trung vị nhóm" in mut2

    # dẫn đầu -> đứng cuối
    t3 = "HDB dẫn đầu ROE quý 4/2025 với 25,4%."
    mut3 = mutate_direction_flip(t3, random.Random(42))
    assert mut3 is not None
    assert "đứng cuối" in mut3


def test_operator_metric_swap():
    """Verify metric_swap swaps metrics while keeping numbers intact."""
    # ROA -> ROE
    t1 = "BID đạt ROA 0,97% trong quý 2/2026."
    mut1 = mutate_metric_swap(t1, random.Random(42))
    assert mut1 is not None
    assert "ROE 0,97%" in mut1

    # bao phủ nợ xấu -> nợ xấu
    t2 = "Tỷ lệ bao phủ nợ xấu của BID đạt 75,9% trong quý 2/2026."
    mut2 = mutate_metric_swap(t2, random.Random(42))
    assert mut2 is not None
    assert "Tỷ lệ nợ xấu của BID đạt 75,9%" in mut2


def test_operator_unsupported_number():
    """Verify unsupported_number appends ungrounded number clause."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    run_facts = [0.97, 17.9]
    rng = random.Random(42)
    mut = mutate_unsupported_number(text, run_facts, rng)
    assert mut is not None
    assert mut != text
    assert "biên lãi thuần đạt" in mut
    assert "%" in mut


def test_operator_causal_claim():
    """Verify causal_claim inserts causal language."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_causal_claim(text, rng)
    assert mut is not None
    assert mut != text
    assert ("do " in mut) or ("vì " in mut)


def test_operator_recommendation():
    """Verify recommendation appends investment advice."""
    text = "BID đạt ROA 0,97% trong quý 2/2026."
    rng = random.Random(42)
    mut = mutate_recommendation(text, rng)
    assert mut is not None
    assert mut != text
    assert ("nên mua" in mut) or ("nên bán" in mut)
