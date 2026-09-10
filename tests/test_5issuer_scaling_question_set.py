import tempfile
import unittest
from pathlib import Path

from scripts.build_5issuer_scaling_question_set import build_design, build_question_set
from thesis_data.baseline_plan import load_complexity_question_set


class FiveIssuerScalingQuestionSetTests(unittest.TestCase):
    def test_question_set_is_valid_and_has_five_repetitions_at_each_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "question-set.json"
            import json

            path.write_text(json.dumps(build_question_set()), encoding="utf-8")
            question_set = load_complexity_question_set(path)

            self.assertEqual(question_set.question_set_id, "pilot-2024-bank-scaling-5issuer-v1")
            self.assertEqual(len(question_set.questions), 25)
            self.assertEqual(question_set.scope.issuers, ("ACB", "TCB", "VPB", "MBB", "VCB"))
            counts = {}
            for question in question_set.questions:
                size = len(question.workload.issuers)
                counts[size] = counts.get(size, 0) + 1
            self.assertEqual(counts, {1: 5, 2: 5, 3: 5, 4: 5, 5: 5})

    def test_design_is_explicitly_gated_and_not_executed(self):
        design = build_design()
        self.assertEqual(design["planned_jobs"], 75)
        self.assertEqual(design["snapshot_gate"], "PENDING_GOLD_5_ISSUER")
        self.assertEqual(design["execution_status"], "not_executed")


if __name__ == "__main__":
    unittest.main()
