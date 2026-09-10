import unittest

from scripts.build_application_benchmark_report import build_report, to_markdown


class ApplicationBenchmarkReportTests(unittest.TestCase):
    def test_marks_current_sweep_as_no_confirmed_crossover(self):
        report = build_report(
            {
                "manifest_count": 2,
                "primary_quality_source": "reviewed.json",
                "human_review": {"valid_score_count": 4},
                "operational_by_tier": {
                    "tier_2": {
                        "single_agent": {"cost_per_completed_job_usd": 1, "throughput_completed_jobs_per_minute": 1, "failed_jobs": 0}
                    }
                },
                "human_scores_by_tier_and_arm": {},
            }
        )
        self.assertFalse(report["crossover"]["confirmed"])
        self.assertIn("no_confirmed", report["crossover"]["current_conclusion"])
        self.assertIn("Tier 2", to_markdown(report))


if __name__ == "__main__":
    unittest.main()
