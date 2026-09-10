import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.run_complexity_pilot import _validate_plan_snapshot, select_complexity_jobs
from thesis_data.baseline_plan import load_complexity_plan
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class ComplexityRunnerPreflightTests(unittest.TestCase):
    def test_full_mode_question_retry_selects_only_requested_arm(self):
        plan = load_complexity_plan(
            Path("experiments/runs/complexity-plan-scaling-5issuer-v2.json")
        )
        selected = select_complexity_jobs(
            plan,
            mode="full",
            question_id="scale_2issuer_rep5_5issuer_v1",
            arm="hierarchical_bounded_critique",
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].arm.value, "hierarchical_bounded_critique")

    def test_plan_snapshot_mismatch_is_rejected_before_provider_setup(self):
        with self.assertRaisesRegex(RuntimeError, "plan snapshot_id"):
            _validate_plan_snapshot("PENDING_GOLD_5_ISSUER", "gold-bank-2025-pilot-v1-adjudicated-v2")

    def test_matching_plan_snapshot_is_accepted(self):
        _validate_plan_snapshot("gold-v1", "gold-v1")

    def test_gold_snapshot_metadata_can_be_checked_against_requested_scope(self):
        # This is a contract-level fixture for the guard added to
        # run_complexity_pilot.py: a three-issuer snapshot must not silently
        # serve a five-issuer question set.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            config = GoldConfig(
                tickers=("ACB", "TCB", "VPB"),
                periods=("2024_Q1",),
                required_metrics=("bank.roa",),
            )
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-3issuer", "2026-09-07T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"))),
            )
            connection.commit()
            row = connection.execute(
                "SELECT snapshot_id, config_json FROM snapshot_metadata WHERE status='gold'"
            ).fetchone()
            connection.close()

        self.assertEqual(row[0], "gold-3issuer")
        stored = GoldConfig.model_validate(json.loads(row[1]))
        self.assertNotEqual(stored.tickers, ("ACB", "TCB", "VPB", "MBB", "VCB"))


if __name__ == "__main__":
    unittest.main()
