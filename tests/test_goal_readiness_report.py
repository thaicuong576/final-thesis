import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_goal_readiness_report import review_copy_status


class GoalReadinessReportTests(unittest.TestCase):
    def test_blank_review_copy_is_not_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checker.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["target_id", "decision"])
                writer.writeheader()
                writer.writerows([{"target_id": "A", "decision": ""}, {"target_id": "B", "decision": ""}])
            result = review_copy_status(path)

        self.assertEqual(result["completed"], 0)
        self.assertFalse(result["eligible_for_merge"])

    def test_partially_completed_review_copy_remains_ineligible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checker.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["target_id", "decision"])
                writer.writeheader()
                writer.writerows([{"target_id": "A", "decision": "accepted"}, {"target_id": "B", "decision": ""}])
            result = review_copy_status(path)

        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["completion_rate"], 0.5)
        self.assertFalse(result["eligible_for_merge"])


if __name__ == "__main__":
    unittest.main()
