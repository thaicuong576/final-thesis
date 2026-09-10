import unittest


class BlindAggregateTests(unittest.TestCase):
    def test_agreement_counts_scored_and_disagreed_dimensions(self):
        from thesis_data.blind_aggregate import agreement_for_records

        checker_a = [
            {"blind_id": "answer-1", "decisions": [{"dimension": "factual_correctness", "review_status": "scored", "score": 1}]},
        ]
        checker_b = [
            {"blind_id": "answer-1", "decisions": [{"dimension": "factual_correctness", "review_status": "scored", "score": 0}]},
        ]

        result = agreement_for_records(checker_a, checker_b)

        self.assertEqual(result["compared"], 1)
        self.assertEqual(result["agreements"], 0)
        self.assertEqual(result["disagreements"], 1)

    def test_latest_successful_record_wins_over_failed_retry_record(self):
        from thesis_data.blind_aggregate import latest_successful_records

        records = [
            {"blind_id": "answer-1", "error": "ValueError", "decisions": []},
            {"blind_id": "answer-1", "decisions": [{"dimension": "coverage_discipline", "score": 1}]},
        ]

        result = latest_successful_records(records)

        self.assertEqual(result["answer-1"]["decisions"][0]["score"], 1)

    def test_preliminary_verdict_withholds_multi_agent_when_quality_is_mixed(self):
        from thesis_data.blind_aggregate import preliminary_verdict

        scores = {
            "single_agent": {
                "factual_correctness": {"mean_reviewer_score_rate": 1.0},
                "calculation_correctness": {"mean_reviewer_score_rate": 1.0},
                "evidence_completeness": {"mean_reviewer_score_rate": 0.3},
                "coverage_discipline": {"mean_reviewer_score_rate": 0.9},
                "cross_level_consistency": {"mean_reviewer_score_rate": 1.0},
                "anomaly_classification": {"mean_reviewer_score_rate": 1.0},
            },
            "hierarchical_bounded_critique": {
                "factual_correctness": {"mean_reviewer_score_rate": 0.8},
                "calculation_correctness": {"mean_reviewer_score_rate": 0.8},
                "evidence_completeness": {"mean_reviewer_score_rate": 0.5},
                "coverage_discipline": {"mean_reviewer_score_rate": 0.8},
                "cross_level_consistency": {"mean_reviewer_score_rate": 0.9},
                "anomaly_classification": {"mean_reviewer_score_rate": 1.0},
            },
        }
        operational = {
            "single_agent": {"cost_estimate_usd": 1.0, "latency_ms_total": 1.0},
            "hierarchical_bounded_critique": {"cost_estimate_usd": 5.0, "latency_ms_total": 5.0},
        }

        result = preliminary_verdict(scores, operational)

        self.assertEqual(result["verdict"], "multi_agent_not_yet_justified")
        self.assertEqual(result["preferred_under_current_pilot"], "single_agent")


if __name__ == "__main__":
    unittest.main()
