import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.experiment_contract import (
    ExperimentArm,
    ExperimentRunConfig,
    audit_experiment_inputs,
)
from thesis_data.schema import GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class ExperimentContractTests(unittest.TestCase):
    def config(self, arm: ExperimentArm, question_id: str = "q1") -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id="run-001",
            snapshot_id="gold-v1",
            question_set_id="questions-v1",
            question_id=question_id,
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-v1",
            arm=arm,
            model_id="test-model",
            source_policy_id="primary-only-v1",
            max_critique_attempts=2 if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE else 0,
        )

    def gold_config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB",),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
            min_manual_labels=2,
            min_metric_coverage=1.0,
        )

    def create_gold_db(self, path: Path) -> None:
        config = self.gold_config()
        create_gold_snapshot_schema(path)
        connection = sqlite3.connect(path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-v1", "2026-09-04T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"), sort_keys=True)),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://example.test", "2026-09-04T00:00:00Z", "data/filing.pdf", "hash", "issuer", "public", "valid", None),
        )
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("obs-1", "VCB", "bank", "bank.npl_g35", 0.02, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("label-1", "obs-1", "value_check", 0.02, None, "checker-1", "2026-09-04T00:00:00", "page:10", "matched"),
                ("label-2", "obs-1", "value_check", 0.02, None, "checker-2", "2026-09-04T00:00:00", "page:10", "matched"),
            ),
        )
        connection.commit()
        connection.close()

    def question_file(
        self,
        directory: str,
        scope: dict | None = None,
        questions: list[dict] | None = None,
    ) -> Path:
        path = Path(directory) / "questions.json"
        scope = scope or {
            "issuers": ["VCB"],
            "periods": ["2024_Q1"],
            "core_metrics": ["bank.npl_g35"],
        }
        payload = {
            "schema_version": 1,
            "status": "test",
            "question_set_id": "questions-v1",
            "scope": scope,
            "questions": questions or [
                {
                    "id": "q1",
                    "issuer": "VCB",
                    "type": "company_snapshot",
                    "period": "2024_Q1",
                    "prompt": "test question",
                }
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_bounded_critique_arm_caps_attempts_at_two(self):
        config = self.config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE)
        self.assertEqual(config.max_critique_attempts, 2)

    def test_prompt_version_is_required_for_reproducible_runs(self):
        with self.assertRaises(ValueError):
            ExperimentRunConfig(
                run_id="run-001",
                snapshot_id="gold-v1",
                question_set_id="questions-v1",
                question_id="q1",
                rubric_version="rubric-v1",
                arm=ExperimentArm.SINGLE_AGENT,
                model_id="test-model",
                source_policy_id="primary-only-v1",
            )

    def test_non_critique_arm_rejects_nonzero_budget(self):
        with self.assertRaises(ValueError):
            ExperimentRunConfig(
                run_id="run-001",
                snapshot_id="gold-v1",
                question_set_id="questions-v1",
                question_id="q1",
                rubric_version="rubric-v1",
                arm=ExperimentArm.SINGLE_AGENT,
                model_id="test-model",
                source_policy_id="primary-only-v1",
                max_critique_attempts=1,
            )

    def test_candidate_snapshot_is_rejected_before_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.sqlite"
            create_gold_snapshot_schema(path)
            connection = sqlite3.connect(path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("candidate", "2026-09-04T00:00:00Z", "normalized_candidate_pending_validation", "{}"),
            )
            connection.commit()
            connection.close()
            question_path = self.question_file(directory)

            audit = audit_experiment_inputs(path, self.config(ExperimentArm.SINGLE_AGENT), question_path, self.gold_config())

        self.assertFalse(audit.eligible)
        self.assertIn("snapshot_not_gold", audit.blockers)
        self.assertIn("snapshot_id_mismatch", audit.blockers)

    def test_matching_gold_and_question_set_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_gold_db(path)
            question_path = self.question_file(
                directory,
                {"issuers": ["VCB"], "periods": ["2024_Q1"], "core_metrics": ["bank.npl_g35"]},
            )

            audit = audit_experiment_inputs(path, self.config(ExperimentArm.SINGLE_AGENT), question_path, self.gold_config())

        self.assertTrue(audit.eligible)
        self.assertEqual(audit.snapshot_id, "gold-v1")
        self.assertEqual(audit.question_count, 1)

    def test_question_scope_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_gold_db(path)
            question_path = self.question_file(
                directory,
                {"issuers": ["ACB"], "periods": ["2024_Q1"], "core_metrics": ["bank.npl_g35"]},
            )

            audit = audit_experiment_inputs(path, self.config(ExperimentArm.SINGLE_AGENT), question_path, self.gold_config())

        self.assertFalse(audit.eligible)
        self.assertIn("question_scope_mismatch", audit.blockers)

    def test_question_id_must_exist_in_question_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_gold_db(path)
            question_path = self.question_file(
                directory,
                {"issuers": ["VCB"], "periods": ["2024_Q1"], "core_metrics": ["bank.npl_g35"]},
            )
            audit = audit_experiment_inputs(
                path,
                self.config(ExperimentArm.SINGLE_AGENT, question_id="q-not-in-file"),
                question_path,
                self.gold_config(),
            )

        self.assertFalse(audit.eligible)
        self.assertIn("question_id_not_in_question_set", audit.blockers)

    def test_invalid_typed_question_set_is_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_gold_db(path)
            question_path = self.question_file(
                directory,
                {"issuers": ["VCB"], "periods": ["2024_Q1"], "core_metrics": ["bank.npl_g35"]},
            )
            question_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "test",
                        "question_set_id": "questions-v1",
                        "scope": {
                            "issuers": ["VCB"],
                            "periods": ["2024_Q1"],
                            "core_metrics": ["bank.npl_g35"],
                        },
                        "questions": [{"id": "q1"}],
                    }
                ),
                encoding="utf-8",
            )

            audit = audit_experiment_inputs(
                path,
                self.config(ExperimentArm.SINGLE_AGENT),
                question_path,
                self.gold_config(),
            )

        self.assertFalse(audit.eligible)
        self.assertIn("question_set_schema_invalid", audit.blockers)

    def test_pilot_question_set_covers_protocol_required_case_types(self):
        question_path = Path(__file__).parents[1] / "experiments" / "question-set-v1.json"
        payload = json.loads(question_path.read_text(encoding="utf-8"))
        questions = payload["questions"]
        question_types = {question["type"] for question in questions}

        self.assertTrue(
            {
                "company_snapshot",
                "peer_comparison",
                "macro_to_bank",
                "company_trend",
                "known_missing_or_conflict",
                "anomaly_review",
            }.issubset(question_types)
        )

        macro_questions = [question for question in questions if question["type"] == "macro_to_bank"]
        self.assertTrue(macro_questions)
        self.assertTrue(all(question.get("macro_indicator_ids") for question in macro_questions))

        known_case_questions = [
            question for question in questions if question["type"] == "known_missing_or_conflict"
        ]
        self.assertTrue(known_case_questions)
        self.assertTrue(all(question.get("target_cell") for question in known_case_questions))

        anomaly_trigger_ids = {
            trigger_id
            for question in questions
            if question["type"] == "anomaly_review"
            for trigger_id in question.get("trigger_ids", [])
        }
        self.assertTrue(
            {
                "company_metric_missing",
                "sector_benchmark_missing",
                "company_sector_deviation",
            }.issubset(anomaly_trigger_ids)
        )

    def test_macro_question_requires_accepted_period_aligned_macro_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.sqlite"
            self.create_gold_db(path)
            question_path = self.question_file(
                directory,
                {"issuers": ["VCB"], "periods": ["2024_Q1"], "core_metrics": ["bank.npl_g35"]},
                [
                    {
                        "id": "macro-q1",
                        "type": "macro_to_bank",
                        "issuer": "VCB",
                        "period": "2024_Q1",
                        "macro_indicator_ids": ["macro.policy_rate"],
                        "bank_metric_ids": ["bank.npl_g35"],
                        "causal_claim_policy": "association_only",
                        "prompt": "relate macro and bank facts",
                    }
                ],
            )

            audit = audit_experiment_inputs(
                path,
                self.config(ExperimentArm.SINGLE_AGENT, question_id="macro-q1"),
                question_path,
                self.gold_config(),
            )

        self.assertFalse(audit.eligible)
        self.assertIn("missing_accepted_macro_observation:2024_Q1:macro.policy_rate", audit.blockers)


if __name__ == "__main__":
    unittest.main()
