import unittest


class BlindAIReviewTests(unittest.TestCase):
    def test_review_schema_requires_strict_dimension_decisions(self):
        from thesis_data.blind_ai_review import review_response_schema

        schema = review_response_schema()

        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("reviews", schema["required"])

    def test_parse_review_decisions_validates_scored_and_unscorable_rows(self):
        from thesis_data.blind_ai_review import parse_review_decisions

        payload = {
            "reviews": [
                {
                    "dimension": "factual_correctness",
                    "review_status": "scored",
                    "score": 1,
                    "reason_code": "matches_gold",
                    "rationale": "The numeric claim matches the reference.",
                },
                {
                    "dimension": "anomaly_classification",
                    "review_status": "unscorable",
                    "score": None,
                    "reason_code": "review_failure",
                    "rationale": "No anomaly case applies.",
                },
            ]
        }

        rows = parse_review_decisions(payload)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["score"], 1)
        self.assertIsNone(rows[1]["score"])

    def test_reviewer_prompt_contains_no_arm_or_run_identity(self):
        from thesis_data.blind_ai_review import build_reviewer_prompt

        packet = {
            "blind_id": "answer-abc",
            "question": {"id": "q", "prompt": "Report ROE."},
            "answer": {"agent_id": "answer", "metrics": {"bank.roe": 20.0}},
            "gold_reference": {"company_by_period": {"2024_Q4": {"metrics": {"bank.roe": 20.0}}}},
        }

        prompt = build_reviewer_prompt(packet, "ai_checker_a")

        self.assertIn("answer-abc", prompt)
        self.assertNotIn("single_agent", prompt)
        self.assertNotIn("hierarchical", prompt)
        self.assertNotIn("run_id", prompt)

    def test_failed_review_record_is_not_marked_completed_for_resume(self):
        from thesis_data.blind_ai_review import successful_blind_ids

        records = [
            {"blind_id": "answer-ok", "decisions": []},
            {"blind_id": "answer-failed", "decisions": [], "error": "ValueError"},
        ]

        self.assertEqual(successful_blind_ids(records), {"answer-ok"})


if __name__ == "__main__":
    unittest.main()
