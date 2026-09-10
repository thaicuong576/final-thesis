import unittest

from thesis_data.anomaly import detect_anomaly_triggers


class AnomalyTriggerTests(unittest.TestCase):
    def test_missing_company_and_sector_values_create_explicit_triggers(self):
        facts = {
            "company": {
                "metrics": {"bank.npl_g35": None},
                "metric_units": {"bank.npl_g35": "unknown"},
            },
            "sector": {
                "sector_benchmarks": {"bank.npl_g35": None},
                "metric_units": {"bank.npl_g35": "unknown"},
            },
        }

        triggers = detect_anomaly_triggers(facts, ("bank.npl_g35",))

        self.assertEqual(
            [trigger.rule_id for trigger in triggers],
            ["company_metric_missing", "sector_benchmark_missing"],
        )
        self.assertEqual(
            [trigger.affected_agents for trigger in triggers],
            [("company",), ("sector",)],
        )
        self.assertTrue(all(trigger.verification_request for trigger in triggers))

    def test_numeric_deviation_requires_explicit_same_unit_threshold(self):
        facts = {
            "company": {
                "metrics": {"bank.npl_g35": 4.0},
                "metric_units": {"bank.npl_g35": "%"},
            },
            "sector": {
                "sector_benchmarks": {"bank.npl_g35": 2.0},
                "metric_units": {"bank.npl_g35": "%"},
            },
        }

        self.assertEqual(detect_anomaly_triggers(facts, ("bank.npl_g35",)), ())
        triggers = detect_anomaly_triggers(
            facts,
            ("bank.npl_g35",),
            deviation_thresholds={"bank.npl_g35": 1.0},
        )

        self.assertEqual([trigger.rule_id for trigger in triggers], ["company_sector_deviation"])
        self.assertIn("4", triggers[0].description)
        self.assertIn("2", triggers[0].description)

    def test_numeric_deviation_is_not_triggered_for_unknown_or_mismatched_units(self):
        base_facts = {
            "company": {"metrics": {"bank.npl_g35": 4.0}},
            "sector": {
                "sector_benchmarks": {"bank.npl_g35": 2.0},
                "metric_units": {"bank.npl_g35": "%"},
            },
        }

        self.assertEqual(
            detect_anomaly_triggers(
                base_facts,
                ("bank.npl_g35",),
                deviation_thresholds={"bank.npl_g35": 1.0},
            ),
            (),
        )

        mismatched_units = {
            "company": {
                "metrics": {"bank.npl_g35": 4.0},
                "metric_units": {"bank.npl_g35": "ratio"},
            },
            "sector": {
                "sector_benchmarks": {"bank.npl_g35": 2.0},
                "metric_units": {"bank.npl_g35": "%"},
            },
        }
        self.assertEqual(
            detect_anomaly_triggers(
                mismatched_units,
                ("bank.npl_g35",),
                deviation_thresholds={"bank.npl_g35": 1.0},
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
