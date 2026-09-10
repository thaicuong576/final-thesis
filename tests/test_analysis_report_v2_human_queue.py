import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.aggregate_analysis_report_v2_human_review import aggregate
from scripts.validate_analysis_report_v2_human_queue import DIMENSION_PROMPTS, validate


class AnalysisReportV2HumanQueueTests(unittest.TestCase):
    def test_blank_queue_is_structurally_valid_but_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = {
                "blind_id": "arv2-test-1",
                "report": {
                    "packet_version": "analysis-report-v2-blind-packet-v1",
                    "scope": {"issuers": ["ACB"]},
                },
            }
            (root / "blind-packets.jsonl").write_text(
                json.dumps(packet) + "\n", encoding="utf-8"
            )
            (root / "private-identity-map.json").write_text(
                json.dumps({"arv2-test-1": {"arm": "single_agent"}}), encoding="utf-8"
            )
            with (root / "human-review-queue.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["row_number", "blind_id", "dimension", "prompt", "score", "decision_basis"],
                )
                writer.writeheader()
                for number, dimension in enumerate(("correctness", "usefulness", "evidence", "limitation"), start=1):
                    writer.writerow(
                        {
                            "row_number": number,
                            "blind_id": "arv2-test-1",
                            "dimension": dimension,
                            "prompt": DIMENSION_PROMPTS[dimension],
                            "score": "",
                            "decision_basis": "",
                        }
                    )
            result = validate(root)
            self.assertTrue(result["valid"])
            self.assertFalse(result["complete"])
            self.assertEqual(result["expected_rows"], 4)

    def test_score_outside_zero_to_four_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = {"blind_id": "arv2-test-1", "report": {"scope": {}}}
            (root / "blind-packets.jsonl").write_text(json.dumps(packet) + "\n", encoding="utf-8")
            (root / "private-identity-map.json").write_text(json.dumps({"arv2-test-1": {}}), encoding="utf-8")
            with (root / "human-review-queue.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["row_number", "blind_id", "dimension", "prompt", "score", "decision_basis"],
                )
                writer.writeheader()
                for number, dimension in enumerate(("correctness", "usefulness", "evidence", "limitation"), start=1):
                    writer.writerow(
                        {
                            "row_number": number,
                            "blind_id": "arv2-test-1",
                            "dimension": dimension,
                            "prompt": DIMENSION_PROMPTS[dimension],
                            "score": "5",
                            "decision_basis": "invalid test score",
                        }
                    )
            result = validate(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("score_out_of_range" in error for error in result["errors"]))

    def test_aggregation_preserves_operational_failures_outside_blind_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_ids = {"arv2-single", "arv2-multi"}
            with (root / "blind-packets.jsonl").open("w", encoding="utf-8") as handle:
                for blind_id in sorted(packet_ids):
                    handle.write(json.dumps({"blind_id": blind_id, "report": {"scope": {}}}) + "\n")
            identities = {
                "arv2-single": {
                    "arm": "single_agent",
                    "workload_tier": "tier_2",
                    "issuer_count": 1,
                    "question_id": "q1",
                    "cost_estimate_usd": 1.0,
                    "wall_clock_latency_ms": 100.0,
                    "input_tokens": 10,
                    "output_tokens": 10,
                    "status": "partial",
                },
                "arv2-multi": {
                    "arm": "hierarchical_no_critique",
                    "workload_tier": "tier_2",
                    "issuer_count": 1,
                    "question_id": "q1",
                    "cost_estimate_usd": 2.0,
                    "wall_clock_latency_ms": 200.0,
                    "input_tokens": 20,
                    "output_tokens": 20,
                    "status": "partial",
                },
            }
            (root / "private-identity-map.json").write_text(
                json.dumps(identities), encoding="utf-8"
            )
            with (root / "human-review-queue.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["row_number", "blind_id", "dimension", "prompt", "score", "decision_basis"],
                )
                writer.writeheader()
                number = 1
                for blind_id in sorted(packet_ids):
                    for dimension in ("correctness", "usefulness", "evidence", "limitation"):
                        writer.writerow(
                            {
                                "row_number": number,
                                "blind_id": blind_id,
                                "dimension": dimension,
                                "prompt": DIMENSION_PROMPTS[dimension],
                                "score": "4",
                                "decision_basis": "fixture basis",
                            }
                        )
                        number += 1
            (root / "operational-manifest-summary.json").write_text(
                json.dumps(
                    [
                        {
                            "arm": "single_agent",
                            "workload_tier": "tier_2",
                            "issuer_count": 1,
                            "quality_review_eligible": True,
                            "failure_status": None,
                        },
                        {
                            "arm": "hierarchical_no_critique",
                            "workload_tier": "tier_2",
                            "issuer_count": 1,
                            "quality_review_eligible": True,
                            "failure_status": None,
                        },
                        {
                            "arm": "hierarchical_no_critique",
                            "workload_tier": "tier_2",
                            "issuer_count": 1,
                            "quality_review_eligible": False,
                            "failure_status": "context_budget_exceeded",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            result = aggregate(root)
            multi = next(
                item
                for item in result["arm_summaries"]
                if item["arm"] == "hierarchical_no_critique"
            )
            candidate = result["crossover_candidates"][0]
            self.assertEqual(multi["planned_repetitions"], 2)
            self.assertEqual(multi["failed_repetitions"], 1)
            self.assertEqual(multi["failure_rate"], 0.5)
            self.assertEqual(multi["completion_adjusted_quality_mean"], 0.5)
            self.assertFalse(candidate["operationally_complete_comparison"])
            self.assertFalse(candidate["qualifies_as_crossover"])


if __name__ == "__main__":
    unittest.main()
