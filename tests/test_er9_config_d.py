"""Tests for ER-9D: Configuration D (template-only arm) and per-question comparison."""

import unittest
from scripts.er8_run import ALLOWED_ARMS, ARMS, TemplateOnlyCritic, TemplateOnlyWriter
from scripts.er9_perquestion import calculate_win_tie_loss, fmt_vi_dec


class TestEr9ConfigD(unittest.TestCase):
    def test_arms_definition(self):
        """ARMS remains 3 default arms; ALLOWED_ARMS includes template_only."""
        self.assertEqual(len(ARMS), 3)
        self.assertIn("single_agent", ARMS)
        self.assertIn("hierarchical_no_critique", ARMS)
        self.assertIn("hierarchical_with_critique", ARMS)
        self.assertNotIn("template_only", ARMS)

        self.assertEqual(len(ALLOWED_ARMS), 4)
        self.assertIn("template_only", ALLOWED_ARMS)

    def test_template_only_writer_zero_model_calls(self):
        """TemplateOnlyWriter has client=None, 0 model calls, and 0 tokens."""
        writer = TemplateOnlyWriter()
        self.assertIsNone(writer.client)

        facts = [
            {
                "fact_id": "f-1",
                "mo_ta": "Tỷ lệ nợ xấu",
                "hien_thi": "1,22%",
                "value": 0.0122,
                "unit": "ratio",
            }
        ]

        findings = writer.write_findings(
            role="asset_quality",
            question="Đánh giá chất lượng tài sản",
            question_type="diagnostic",
            facts=facts,
            datasets_summary=[],
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("Tỷ lệ nợ xấu đạt 1,22%.", findings[0]["text"])
        self.assertEqual(findings[0]["fact_ids"], ["f-1"])

        verified_sentences = [
            {
                "sentence_id": "s-1",
                "text": findings[0]["text"],
                "fact_ids": findings[0]["fact_ids"],
            }
        ]

        report = writer.compose_report(
            question="Đánh giá chất lượng tài sản",
            question_type="diagnostic",
            sentences=verified_sentences,
            datasets_summary=[],
            facts=facts,
        )
        self.assertIn("blocks", report)

    def test_template_only_critic_zero_calls(self):
        """TemplateOnlyCritic initializes with calls=0 and does not use real model."""
        critic = TemplateOnlyCritic()
        self.assertEqual(critic.calls, 0)
        self.assertIsNone(critic.tracker)

    def test_calculate_win_tie_loss_synthetic(self):
        """Test win/tie/loss logic on synthetic scores."""
        scores_map = {
            ("T01", "single_agent"): {"coverage_score": 0.50},
            ("T01", "hierarchical_no_critique"): {"coverage_score": 0.75},
            ("T01", "hierarchical_with_critique"): {"coverage_score": 0.50},
            ("T01", "template_only"): {"coverage_score": 0.25},
            ("T02", "single_agent"): {"coverage_score": 0.80},
            ("T02", "hierarchical_no_critique"): {"coverage_score": 0.80},
            ("T02", "hierarchical_with_critique"): {"coverage_score": 0.90},
            ("T02", "template_only"): {"coverage_score": 0.80},
        }
        res = calculate_win_tie_loss(
            scores_map,
            tasks=["T01", "T02"],
            pairs=[
                ("hierarchical_no_critique", "single_agent", "B", "A"),
                ("hierarchical_with_critique", "hierarchical_no_critique", "C", "B"),
            ],
        )
        # B vs A: T01 (0.75 vs 0.50 -> win), T02 (0.80 vs 0.80 -> tie) -> 1 win, 1 tie, 0 loss
        self.assertEqual(res[0]["win"], 1)
        self.assertEqual(res[0]["tie"], 1)
        self.assertEqual(res[0]["loss"], 0)

        # C vs B: T01 (0.50 vs 0.75 -> loss), T02 (0.90 vs 0.80 -> win) -> 1 win, 0 tie, 1 loss
        self.assertEqual(res[1]["win"], 1)
        self.assertEqual(res[1]["tie"], 0)
        self.assertEqual(res[1]["loss"], 1)

    def test_fmt_vi_dec(self):
        """Format numbers with comma for decimals."""
        self.assertEqual(fmt_vi_dec(0.75, decimals=2), "0,75")
        self.assertEqual(fmt_vi_dec(1234.5, decimals=1), "1234,5")


if __name__ == "__main__":
    unittest.main()
