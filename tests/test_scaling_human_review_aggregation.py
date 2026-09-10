import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "aggregate_complexity_score.py"
SPEC = importlib.util.spec_from_file_location("aggregate_complexity_score", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ScalingHumanReviewAggregationTests(unittest.TestCase):
    def write_queue(self, directory: Path, *, score: str = "", basis: str = "") -> Path:
        path = directory / "human-review-queue.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "row_number",
                    "blind_id",
                    "question_id",
                    "dimension",
                    "machine_score",
                    "final_score",
                    "decision_basis",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "row_number": "1",
                    "blind_id": "answer-1",
                    "question_id": "q-1",
                    "dimension": "task_coverage",
                    "machine_score": "1",
                    "final_score": score,
                    "decision_basis": basis,
                }
            )
        return path

    def test_blank_queue_is_withheld_from_quality_result(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            queue = self.write_queue(Path(raw_dir))
            reviews, summary = MODULE._read_human_reviews(queue)
        self.assertEqual(reviews, [])
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["valid_score_count"], 0)

    def test_complete_queue_emits_only_explicit_binary_human_score(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            queue = self.write_queue(Path(raw_dir), score="0", basis="missing required task")
            reviews, summary = MODULE._read_human_reviews(queue)
        self.assertTrue(summary["complete"])
        self.assertEqual(reviews, [{"blind_id": "answer-1", "dimension": "task_coverage", "score": 0}])


if __name__ == "__main__":
    unittest.main()
