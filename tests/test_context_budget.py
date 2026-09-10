import unittest

from thesis_data.context_budget import ContextBudgetError, compact_composite_context, json_chars


class ContextBudgetTests(unittest.TestCase):
    def test_compactor_preserves_numeric_facts_and_provenance(self):
        context = {
            "worker_payloads": {
                "company": {
                    "agent_id": "company",
                    "status": "success",
                    "question_id": "q",
                    "tier": "tier_3",
                    "issuers": ["ACB"],
                    "periods": ["2024_Q1"],
                    "metric_ids": ["bank.roa"],
                    "findings": ["long prose that may be removed"],
                    "data_slices": [
                        {
                            "agent_id": "company",
                            "ticker": "ACB",
                            "period": "2024_Q1",
                            "metrics": {"bank.roa": 1.2},
                            "source_ids": ["source-1"],
                            "observation_ids": ["obs-1"],
                        }
                    ],
                    "subreports": {
                        "ACB|2024_Q1|snapshot": {
                            "status": "success",
                            "payload_ref": "ACB|2024_Q1",
                            "payload": None,
                        }
                    },
                }
            }
        }
        compact = compact_composite_context(context, max_chars=10000)
        payload = compact["worker_payloads"]["company"]
        self.assertEqual(payload["data_slices"][0]["metrics"]["bank.roa"], 1.2)
        self.assertEqual(payload["data_slices"][0]["observation_ids"], ["obs-1"])
        self.assertEqual(payload["data_slices"][0]["source_ids"], ["source-1"])
        self.assertNotIn("findings", payload)
        self.assertLessEqual(json_chars(compact), 10000)

    def test_compactor_fails_closed_instead_of_truncating(self):
        with self.assertRaises(ContextBudgetError) as raised:
            compact_composite_context(
                {"worker_payloads": {"company": {"findings": ["x" * 1000]}}},
                max_chars=100,
            )
        self.assertIn("context_budget_exceeded", raised.exception.blockers)


if __name__ == "__main__":
    unittest.main()
