import json
from pathlib import Path
import tempfile
import unittest

from scripts.aggregate_scaling_complexity import aggregate


class ScalingAggregateTests(unittest.TestCase):
    def test_groups_by_issuer_count_and_preserves_first_pass_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "recovered"
            first_dir = root / "first"
            run_dir.mkdir()
            first_dir.mkdir()
            for index, issuer_count in enumerate((1, 2), start=1):
                (run_dir / f"{index}.json").write_text(
                    json.dumps(
                        {
                            "arm": "single_agent",
                            "question_id": f"q{index}",
                            "complexity_vector": {"issuer_count": issuer_count},
                            "failure_status": None,
                            "total_cost_estimate": 0.1,
                            "total_input_tokens": 10,
                            "total_output_tokens": 5,
                            "wall_clock_latency_ms": 60000,
                        }
                    ),
                    encoding="utf-8",
                )
            (first_dir / "failures.json").write_text(
                json.dumps([{"job_id": "q2:hierarchical_no_critique"}]), encoding="utf-8"
            )

            result = aggregate(run_dir, first_pass_dir=first_dir)

            self.assertEqual(result["manifest_count"], 2)
            self.assertEqual(result["first_pass_failure_count"], 1)
            self.assertEqual(result["by_issuer_count_and_arm"]["1"]["single_agent"]["completed_jobs"], 1)
            self.assertEqual(result["by_issuer_count_and_arm"]["2"]["single_agent"]["cost_per_completed_job_usd"], 0.1)


if __name__ == "__main__":
    unittest.main()
