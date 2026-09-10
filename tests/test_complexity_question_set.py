import json
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_plan import load_complexity_question_set
from thesis_data.workload_contract import WorkloadTier


class ComplexityQuestionSetTests(unittest.TestCase):
    def payload(self):
        return {
            "schema_version": 1,
            "question_set_id": "complexity-v1",
            "status": "frozen",
            "scope": {
                "issuers": ["ACB", "TCB", "VPB"],
                "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                "core_metrics": ["bank.roa", "bank.roe"],
            },
            "questions": [
                {
                    "id": "ACB-composite",
                    "type": "composite_workload",
                    "prompt": "Analyze ACB.",
                    "workload": {
                        "question_id": "ACB-composite",
                        "tier": "tier_2",
                        "issuers": ["ACB"],
                        "periods": ["2024_Q1", "2024_Q2"],
                        "metric_ids": ["bank.roa", "bank.roe"],
                        "analysis_tasks": ["snapshot", "trend"],
                        "peer_tickers": ["ACB", "TCB", "VPB"],
                        "complexity_vector": {
                            "issuer_count": 1,
                            "period_count": 2,
                            "metric_count": 2,
                            "analysis_task_count": 2,
                            "cross_issuer_comparisons": 0,
                            "missing_conflict_checks": 0,
                            "evidence_groups": 0,
                        },
                    },
                }
            ],
        }

    def test_loader_accepts_composite_question_set_and_preserves_tier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(json.dumps(self.payload()), encoding="utf-8")
            question_set = load_complexity_question_set(path)

        self.assertEqual(question_set.question_set_id, "complexity-v1")
        self.assertEqual(question_set.questions[0].workload.tier, WorkloadTier.TIER_2)

    def test_loader_rejects_atomic_question_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            payload = self.payload()
            payload["questions"][0] = {
                "id": "atomic",
                "issuer": "ACB",
                "type": "company_snapshot",
                "period": "2024_Q1",
                "prompt": "atomic",
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_complexity_question_set(path)

    def test_frozen_project_set_has_three_tier2_and_one_tier3_workloads(self):
        path = Path(__file__).parents[1] / "experiments" / "question-set-complexity-v1.json"
        question_set = load_complexity_question_set(path)

        self.assertEqual(question_set.question_set_id, "pilot-2024-bank-complexity-v1")
        self.assertEqual(len(question_set.questions), 4)
        self.assertEqual(
            [question.workload.tier for question in question_set.questions],
            [WorkloadTier.TIER_2, WorkloadTier.TIER_2, WorkloadTier.TIER_2, WorkloadTier.TIER_3],
        )
        for question in question_set.questions:
            workload = question.workload
            self.assertEqual(len(workload.periods), 4)
            self.assertEqual(len(workload.metric_ids), 4)
            self.assertEqual(len(workload.analysis_tasks), 6)
            self.assertEqual(workload.peer_tickers, ("ACB", "TCB", "VPB"))


if __name__ == "__main__":
    unittest.main()
