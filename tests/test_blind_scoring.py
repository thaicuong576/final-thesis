import unittest


class BlindScoringTests(unittest.TestCase):
    def test_select_published_payload_prefers_orchestrator_over_verification(self):
        from thesis_data.blind_scoring import select_published_payload

        manifest = {
            "arm": "hierarchical_bounded_critique",
            "payloads": [
                {"agent_id": "company", "status": "success"},
                {"agent_id": "orchestrator", "status": "partial"},
                {"agent_id": "verification", "status": "success"},
            ],
        }

        payload = select_published_payload(manifest)

        self.assertEqual(payload["agent_id"], "orchestrator")

    def test_select_published_payload_uses_single_agent_answer(self):
        from thesis_data.blind_scoring import select_published_payload

        manifest = {
            "arm": "single_agent",
            "payloads": [
                {"agent_id": "single_agent", "status": "success"},
            ],
        }

        self.assertEqual(select_published_payload(manifest)["agent_id"], "single_agent")

    def test_sanitize_payload_hides_role_identity_but_preserves_answer_content(self):
        from thesis_data.blind_scoring import sanitize_payload

        payload = {
            "agent_id": "orchestrator",
            "ticker": "ACB",
            "period": "2024_Q4",
            "metrics": {"bank.roe": 21.7459},
            "findings": ["observed"],
            "source_ids": ["source-1"],
        }

        sanitized = sanitize_payload(payload)

        self.assertEqual(sanitized["agent_id"], "answer")
        self.assertEqual(sanitized["metrics"], payload["metrics"])
        self.assertNotIn("arm", sanitized)
        self.assertNotIn("run_id", sanitized)

    def test_blind_id_is_deterministic_and_seed_bound(self):
        from thesis_data.blind_scoring import blind_id_for

        first = blind_id_for("ACB_snapshot_q4:single_agent", "blind-v1")
        second = blind_id_for("ACB_snapshot_q4:single_agent", "blind-v1")
        other = blind_id_for("ACB_snapshot_q4:single_agent", "blind-v2")

        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("answer-"))

    def test_load_provider_manifests_and_build_packets_hide_arm_identity(self):
        from pathlib import Path

        from thesis_data.blind_scoring import (
            build_blind_packets,
            load_provider_manifests,
        )

        root = Path(__file__).resolve().parents[1]
        run_dir = root / "experiments" / "outputs" / "provider" / "full-gpt-5.6-luna-20260906T085022Z"
        db_path = root / "data" / "processed" / "gold-bank-2025-pilot-v1-adjudicated-v2.sqlite"
        question_path = root / "experiments" / "question-set-core-v1.json"

        manifests = load_provider_manifests(run_dir)
        packets, private_map = build_blind_packets(
            run_dir, db_path, question_path, seed="blind-v1"
        )

        self.assertEqual(len(manifests), 39)
        self.assertEqual(len(packets), 39)
        self.assertEqual(len(private_map), 39)
        self.assertTrue(all("arm" not in packet for packet in packets))
        self.assertTrue(all(packet["answer"]["agent_id"] == "answer" for packet in packets))
        self.assertTrue(all("gold_reference" in packet for packet in packets))

    def test_structured_score_accepts_gold_value_and_missing_reason(self):
        from thesis_data.blind_scoring import score_structured_answer

        packet = {
            "blind_id": "answer-test",
            "question": {"id": "q", "type": "company_snapshot", "period": "2024_Q1"},
            "answer": {
                "metrics": {"bank.roa": None},
                "metric_units": {"bank.roa": "%"},
                "metric_periods": {"bank.roa": "2024_Q1"},
                "sector_benchmarks": {},
                "findings": ["bank.roa is unavailable under the Gold policy"],
                "quality_flags": ["missing_or_unaccepted"],
                "evidence": [],
                "observation_ids": [],
                "source_ids": [],
            },
            "gold_reference": {
                "company": {
                    "metrics": {"bank.roa": None},
                    "metric_units": {"bank.roa": "%"},
                    "metric_periods": {"bank.roa": "2024_Q1"},
                },
                "sector": None,
            },
        }

        rows = score_structured_answer(packet)

        by_dimension = {row["dimension"]: row for row in rows}
        self.assertEqual(by_dimension["factual_correctness"]["score"], 1)
        self.assertEqual(by_dimension["coverage_discipline"]["score"], 1)

    def test_operational_summary_aggregates_calls_by_arm(self):
        from thesis_data.blind_scoring import operational_summary

        manifests = [
            {
                "arm": "single_agent",
                "calls": [
                    {
                        "input_tokens": 10,
                        "output_tokens": 3,
                        "cost_estimate": 0.0000056,
                        "latency_ms": 12.0,
                        "tool_calls": [{"status": "success"}, {"status": "rejected"}],
                    }
                ],
                "payloads": [{"status": "success"}],
            }
        ]

        result = operational_summary(manifests)

        self.assertEqual(result["single_agent"]["input_tokens"], 10)
        self.assertEqual(result["single_agent"]["output_tokens"], 3)
        self.assertEqual(result["single_agent"]["tool_rejections"], 1)


if __name__ == "__main__":
    unittest.main()
