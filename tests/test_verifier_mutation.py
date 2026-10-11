"""Tests for narrative verifier mutation operators and evaluation logic."""

import random
import unittest

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


class TestVerifierMutation(unittest.TestCase):
    def test_wilson_ci_boundaries(self):
        """Verify Wilson score confidence interval boundary calculations."""
        low, high = wilson_ci(100, 100)
        self.assertGreater(low, 0.95)
        self.assertEqual(high, 1.0)

        low_zero, high_zero = wilson_ci(0, 100)
        self.assertEqual(low_zero, 0.0)
        self.assertLess(high_zero, 0.05)

        low_empty, high_empty = wilson_ci(0, 0)
        self.assertEqual(low_empty, 0.0)
        self.assertEqual(high_empty, 0.0)

    def test_find_metric_numbers(self):
        """Verify that period years, ranks, and quarters are masked out from metric numbers."""
        s1 = "BID đạt ROA 0,97% (hạng 9/10), thấp hơn trung vị nhóm trong quý 2/2026."
        nums = find_metric_numbers(s1)
        self.assertEqual(len(nums), 1)
        raw, suffix, start, end = nums[0]
        self.assertEqual(raw, "0,97")
        self.assertEqual(suffix, "%")

        s2 = "BID: đệm dự phòng dưới nhóm, chất lượng nợ dưới nhóm trong quý 2/2026."
        self.assertEqual(find_metric_numbers(s2), [])

        s3 = "Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 2/2026."
        nums3 = find_metric_numbers(s3)
        self.assertEqual(len(nums3), 1)
        self.assertEqual(nums3[0][0], "11,0")

    def test_sentence_without_number_yields_no_number_mutants(self):
        """Requirement 5: A sentence without a number yields no number mutants."""
        text_without_number = "BID: đệm dự phòng dưới nhóm, chất lượng nợ dưới nhóm trong quý 2/2026."
        rng = random.Random(42)

        self.assertIsNone(mutate_number_small(text_without_number, rng))
        self.assertIsNone(mutate_number_large(text_without_number, rng))
        self.assertIsNone(mutate_digit_swap(text_without_number, rng))

        # Via unified apply_mutation_operator
        self.assertIsNone(apply_mutation_operator("number_small", text_without_number, [], [], [], rng))
        self.assertIsNone(apply_mutation_operator("number_large", text_without_number, [], [], [], rng))
        self.assertIsNone(apply_mutation_operator("digit_swap", text_without_number, [], [], [], rng))

    def test_operator_number_small(self):
        """Verify number_small modifies number by 1-5% in Vietnamese format."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_number_small(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn(",", mut)
        self.assertIn("%", mut)

    def test_operator_number_large(self):
        """Verify number_large multiplies or divides by 2 in Vietnamese format."""
        text = "Tỷ lệ bao phủ nợ xấu của BID đạt 75,9% trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_number_large(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn(",", mut)
        self.assertTrue(("151,8%" in mut) or ("38,0%" in mut))

    def test_operator_digit_swap(self):
        """Verify digit_swap swaps two distinct digits."""
        text = "ROE của BID đạt 17,9% trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_digit_swap(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn("%", mut)

    def test_operator_rank(self):
        """Verify rank changes rank x/y to another valid rank."""
        text = "BID đạt ROA 0,97% (hạng 9/10) trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_rank(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn("/10", mut)
        self.assertNotIn("hạng 9/10", mut)

    def test_operator_denominator(self):
        """Verify denominator changes x/10 to x/9."""
        text = "BID đạt ROA 0,97% (hạng 9/10) trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_denominator(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn("hạng 9/9", mut)

    def test_operator_period(self):
        """Verify period changes quarter to another quarter."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        available_quarters = ["2025_Q4", "2026_Q1"]
        rng = random.Random(42)
        mut = mutate_period(text, available_quarters, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertNotIn("quý 2/2026", mut)
        self.assertTrue(("quý 4/2025" in mut) or ("quý 1/2026" in mut))

    def test_operator_entity_swap(self):
        """Verify entity_swap swaps bank ticker with another bank."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        run_banks = ["VCB", "CTG", "TCB"]
        rng = random.Random(42)
        mut = mutate_entity_swap(text, run_banks, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertFalse(mut.startswith("BID "))
        self.assertTrue(any(mut.startswith(f"{b} ") for b in run_banks))

    def test_operator_direction_flip(self):
        """Verify direction_flip swaps directional terms."""
        t1 = "Tỷ lệ nợ xấu của STB tăng 3,66 điểm % từ quý 3/2025 đến quý 4/2025."
        mut1 = mutate_direction_flip(t1, random.Random(42))
        self.assertIsNotNone(mut1)
        self.assertIn("giảm 3,66 điểm %", mut1)

        t2 = "BID có tỷ lệ nợ xấu cao hơn trung vị nhóm 0,19 điểm % trong quý 2/2026."
        mut2 = mutate_direction_flip(t2, random.Random(42))
        self.assertIsNotNone(mut2)
        self.assertIn("thấp hơn trung vị nhóm", mut2)

        t3 = "HDB dẫn đầu ROE quý 4/2025 với 25,4%."
        mut3 = mutate_direction_flip(t3, random.Random(42))
        self.assertIsNotNone(mut3)
        self.assertIn("đứng cuối", mut3)

    def test_operator_metric_swap(self):
        """Verify metric_swap swaps metrics while keeping numbers intact."""
        t1 = "BID đạt ROA 0,97% trong quý 2/2026."
        mut1 = mutate_metric_swap(t1, random.Random(42))
        self.assertIsNotNone(mut1)
        self.assertIn("ROE 0,97%", mut1)

        t2 = "Tỷ lệ bao phủ nợ xấu của BID đạt 75,9% trong quý 2/2026."
        mut2 = mutate_metric_swap(t2, random.Random(42))
        self.assertIsNotNone(mut2)
        self.assertIn("Tỷ lệ nợ xấu của BID đạt 75,9%", mut2)

    def test_operator_unsupported_number(self):
        """Verify unsupported_number appends ungrounded number clause."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        run_facts = [0.97, 17.9]
        rng = random.Random(42)
        mut = mutate_unsupported_number(text, run_facts, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertIn("biên lãi thuần đạt", mut)
        self.assertIn("%", mut)

    def test_operator_causal_claim(self):
        """Verify causal_claim inserts causal language."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_causal_claim(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertTrue(("do " in mut) or ("vì " in mut))

    def test_operator_recommendation(self):
        """Verify recommendation appends investment advice."""
        text = "BID đạt ROA 0,97% trong quý 2/2026."
        rng = random.Random(42)
        mut = mutate_recommendation(text, rng)
        self.assertIsNotNone(mut)
        self.assertNotEqual(mut, text)
        self.assertTrue(("nên mua" in mut) or ("nên bán" in mut))


if __name__ == "__main__":
    unittest.main()
