import unittest

from thesis_data.blind_scoring import score_composite_answer, sanitize_payload
from thesis_data.blind_aggregate import (
    aggregate_by_tier_and_arm,
    classify_break_even_region,
    compute_scaling_deltas,
)


class ComplexityBlindScoringTests(unittest.TestCase):
    def packet(self, *, complete=True):
        reference = {
            "workload_tier": "tier_2",
            "issuers": ["ACB"],
            "periods": ["2024_Q1"],
            "metric_ids": ["bank.roa"],
            "analysis_tasks": ["snapshot", "missing_conflict"],
            "cells": {
                "ACB|2024_Q1|snapshot": {
                    "metrics": {"bank.roa": 1.2},
                    "metric_units": {"bank.roa": "%"},
                    "metric_periods": {"bank.roa": "2024_Q1"},
                    "source_ids": ["source-1"],
                    "observation_ids": ["obs-1"],
                    "evidence_ids": ["evidence-1"],
                },
                "ACB|2024_Q1|missing_conflict": {
                    "metrics": {"bank.roa": None},
                    "missing_reason": "missing under fixture policy",
                },
            },
        }
        subreports = [
            {
                "issuer": "ACB",
                "period": "2024_Q1",
                "task": "snapshot",
                "status": "success",
                "payload": {
                    "agent_id": "answer",
                    "status": "success",
                    "ticker": "ACB",
                    "period": "2024_Q1",
                    "metrics": {"bank.roa": 1.2},
                    "metric_units": {"bank.roa": "%"},
                    "metric_periods": {"bank.roa": "2024_Q1"},
                    "sector_benchmarks": {},
                    "findings": [],
                    "evidence": [],
                    "quality_flags": [],
                    "observation_ids": ["obs-1"],
                    "source_ids": ["source-1"],
                },
                "missing_reasons": [],
                "observation_ids": ["obs-1"],
                "source_ids": ["source-1"],
                "evidence_ids": ["evidence-1"],
            },
            {
                "issuer": "ACB",
                "period": "2024_Q1",
                "task": "missing_conflict",
                "status": "partial",
                "payload": None,
                "missing_reasons": ["missing under fixture policy"],
                "observation_ids": [],
                "source_ids": [],
                "evidence_ids": [],
            },
        ]
        if not complete:
            subreports = subreports[:1]
        return {
            "blind_id": "answer-1",
            "question": {"id": "q", "type": "composite_workload"},
            "answer": {
                "agent_id": "answer",
                "status": "partial",
                "question_id": "q",
                "tier": "tier_2",
                "issuers": ["ACB"],
                "periods": ["2024_Q1"],
                "metric_ids": ["bank.roa"],
                "subreports": subreports,
                "missing_conflict_register": ["missing under fixture policy"],
                "anomaly_classifications": [],
                "findings": [],
                "quality_flags": [],
                "observation_ids": ["obs-1"],
                "source_ids": ["source-1"],
                "evidence_ids": ["evidence-1"],
            },
            "gold_reference": reference,
        }

    def test_composite_scoring_separates_coverage_from_factual_correctness(self):
        complete = score_composite_answer(self.packet(complete=True))
        incomplete = score_composite_answer(self.packet(complete=False))
        complete_by_dimension = {row["dimension"]: row for row in complete}
        incomplete_by_dimension = {row["dimension"]: row for row in incomplete}

        self.assertEqual(complete_by_dimension["task_coverage"]["score"], 1)
        self.assertEqual(incomplete_by_dimension["task_coverage"]["score"], 0)
        self.assertEqual(complete_by_dimension["factual_correctness"]["score"], 1)
        self.assertIn("missing_conflict_discipline", incomplete_by_dimension)

    def test_composite_packets_do_not_expose_arm_identity(self):
        payload = sanitize_payload({"agent_id": "orchestrator", "arm": "hierarchical", "subreports": []})
        self.assertEqual(payload["agent_id"], "answer")
        self.assertNotIn("arm", payload)

    def test_tier_aggregation_and_scaling_delta_do_not_mix_tiers(self):
        reviews = [
            {"blind_id": "a", "dimension": "task_coverage", "score": 1},
            {"blind_id": "b", "dimension": "task_coverage", "score": 0},
        ]
        manifests = [
            {"blind_id": "a", "workload_tier": "tier_2", "arm": "single_agent"},
            {"blind_id": "b", "workload_tier": "tier_3", "arm": "hierarchical_no_critique"},
        ]
        scores = aggregate_by_tier_and_arm(reviews, manifests)
        self.assertEqual(scores["tier_2"]["single_agent"]["task_coverage"]["score_rate"], 1.0)
        self.assertEqual(scores["tier_3"]["hierarchical_no_critique"]["task_coverage"]["score_rate"], 0.0)
        deltas = compute_scaling_deltas(scores)
        self.assertNotIn("tier_3", deltas.get("tier_2", {}))

    def test_break_even_classification_is_bounded_by_operational_data(self):
        deltas = {
            "tier_2": {
                "hierarchical_no_critique": {"task_coverage": 0.1, "factual_correctness": 0.0}
            }
        }
        operational = {
            "tier_2": {
                "single_agent": {"cost_estimate_usd": 1.0, "latency_ms_total": 1.0},
                "hierarchical_no_critique": {"cost_estimate_usd": 2.0, "latency_ms_total": 2.0},
            }
        }
        result = classify_break_even_region(deltas, operational)
        self.assertEqual(result["tier_2"]["candidate_arms"], ["hierarchical_no_critique"])
        self.assertEqual(result["tier_2"]["bounded_conclusion"], "candidate_only")


if __name__ == "__main__":
    unittest.main()
