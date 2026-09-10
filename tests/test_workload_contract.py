import unittest

from thesis_data.workload_contract import (
    AnalysisTask,
    ComplexityVector,
    CompositeWorkloadSpec,
    WorkloadTier,
)


class WorkloadContractTests(unittest.TestCase):
    def valid_tier_two(self) -> CompositeWorkloadSpec:
        return CompositeWorkloadSpec(
            question_id="ACB_composite_2024",
            tier=WorkloadTier.TIER_2,
            issuers=("ACB",),
            periods=("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
            metric_ids=("bank.npl_g35", "bank.roa", "bank.roe"),
            analysis_tasks=(
                AnalysisTask.SNAPSHOT,
                AnalysisTask.TREND,
                AnalysisTask.PEER_COMPARISON,
                AnalysisTask.MISSING_CONFLICT,
                AnalysisTask.ANOMALY_REVIEW,
                AnalysisTask.EVIDENCE_SUMMARY,
            ),
            peer_tickers=("ACB", "TCB", "VPB"),
            complexity_vector=ComplexityVector(
                issuer_count=1,
                period_count=4,
                metric_count=3,
                analysis_task_count=6,
                cross_issuer_comparisons=1,
                missing_conflict_checks=12,
                evidence_groups=4,
            ),
        )

    def test_valid_tier_two_round_trips_with_declared_complexity(self):
        spec = self.valid_tier_two()

        self.assertEqual(spec.tier, WorkloadTier.TIER_2)
        self.assertEqual(spec.complexity_vector.period_count, 4)
        self.assertEqual(spec.complexity_vector.analysis_task_count, 6)

    def test_valid_tier_three_requires_multiple_issuers(self):
        payload = self.valid_tier_two().model_dump(mode="json")
        payload.update(
            {
                "question_id": "bank_landscape_2024",
                "tier": "tier_3",
                "issuers": ["ACB", "TCB", "VPB"],
                "complexity_vector": {
                    "issuer_count": 3,
                    "period_count": 4,
                    "metric_count": 3,
                    "analysis_task_count": 6,
                    "cross_issuer_comparisons": 1,
                    "missing_conflict_checks": 36,
                    "evidence_groups": 12,
                },
            }
        )
        spec = CompositeWorkloadSpec.model_validate(payload)

        self.assertEqual(spec.tier, WorkloadTier.TIER_3)
        self.assertEqual(spec.issuers, ("ACB", "TCB", "VPB"))

    def test_tier_three_rejects_one_issuer(self):
        with self.assertRaisesRegex(ValueError, "tier_3 requires at least two issuers"):
            payload = self.valid_tier_two().model_dump(mode="json")
            payload.update({"question_id": "invalid", "tier": "tier_3"})
            CompositeWorkloadSpec.model_validate(payload)

    def test_tier_two_rejects_duplicate_analysis_tasks(self):
        with self.assertRaisesRegex(ValueError, "analysis_tasks must be unique"):
            payload = self.valid_tier_two().model_dump(mode="json")
            payload.update({"analysis_tasks": ["snapshot", "snapshot"]})
            CompositeWorkloadSpec.model_validate(payload)

    def test_complexity_vector_must_match_declared_scope(self):
        with self.assertRaisesRegex(ValueError, "complexity_vector issuer_count mismatch"):
            payload = self.valid_tier_two().model_dump(mode="json")
            payload.update(
                {
                    "complexity_vector": {
                        "issuer_count": 2,
                        "period_count": 4,
                        "metric_count": 3,
                        "analysis_task_count": 6,
                        "cross_issuer_comparisons": 1,
                        "missing_conflict_checks": 12,
                        "evidence_groups": 4,
                    }
                }
            )
            CompositeWorkloadSpec.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
