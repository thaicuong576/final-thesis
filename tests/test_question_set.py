import json
import os
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from thesis_data.question_set import load_question_set, question_set_sha256


class QuestionSetContractTests(unittest.TestCase):
    def test_pilot_question_set_is_typed_and_covers_declared_cases(self):
        path = Path(__file__).parents[1] / "experiments" / "question-set-v1.json"

        question_set = load_question_set(path)

        self.assertEqual(question_set.question_set_id, "pilot-2024-bank-qa-v1")
        self.assertEqual(len(question_set.questions), 14)
        self.assertEqual(
            {question.type.value for question in question_set.questions},
            {
                "company_snapshot",
                "company_trend",
                "peer_comparison",
                "anomaly_review",
                "macro_to_bank",
                "known_missing_or_conflict",
            },
        )
        self.assertEqual(
            {
                trigger_id
                for question in question_set.questions
                for trigger_id in question.trigger_ids
            },
            {
                "company_metric_missing",
                "sector_benchmark_missing",
                "company_sector_deviation",
            },
        )
        self.assertEqual(
            question_set_sha256(path),
            sha256(path.read_bytes()).hexdigest(),
        )

    def test_core_question_set_excludes_only_macro_extension(self):
        path = Path(__file__).parents[1] / "experiments" / "question-set-core-v1.json"

        question_set = load_question_set(path)

        self.assertEqual(question_set.question_set_id, "pilot-2024-bank-core-qa-v1")
        self.assertEqual(len(question_set.questions), 13)
        question_types = {question.type.value for question in question_set.questions}
        self.assertNotIn("macro_to_bank", question_types)
        self.assertIn("known_missing_or_conflict", question_types)

    def test_macro_question_requires_indicators_and_bank_metrics(self):
        payload = {
            "schema_version": 1,
            "question_set_id": "questions-v1",
            "status": "draft",
            "scope": {
                "issuers": ["VCB"],
                "periods": ["2024_Q1"],
                "core_metrics": ["bank.roa"],
            },
            "questions": [
                {
                    "id": "macro-q1",
                    "issuer": "VCB",
                    "type": "macro_to_bank",
                    "period": "2024_Q1",
                    "macro_indicator_ids": [],
                    "bank_metric_ids": ["bank.roa"],
                    "prompt": "macro",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "macro_indicator_ids"):
                load_question_set(path)

    def test_known_evidence_case_requires_a_matching_target_cell(self):
        payload = {
            "schema_version": 1,
            "question_set_id": "questions-v1",
            "status": "draft",
            "scope": {
                "issuers": ["VCB"],
                "periods": ["2024_Q1"],
                "core_metrics": ["bank.roa"],
            },
            "questions": [
                {
                    "id": "known-q1",
                    "issuer": "VCB",
                    "type": "known_missing_or_conflict",
                    "period": "2024_Q1",
                    "target_cell": {
                        "issuer": "ACB",
                        "period": "2024_Q1",
                        "metric": "bank.roa",
                    },
                    "case_kind": "known_conflict",
                    "prompt": "known case",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "target_cell"):
                load_question_set(path)

    def test_composite_workload_question_validates_declared_workload_scope(self):
        payload = {
            "schema_version": 1,
            "question_set_id": "complexity-v1",
            "status": "draft",
            "scope": {
                "issuers": ["ACB", "TCB", "VPB"],
                "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                "core_metrics": ["bank.roa", "bank.roe"],
            },
            "questions": [
                {
                    "id": "landscape-q1",
                    "type": "composite_workload",
                    "workload": {
                        "question_id": "landscape-q1",
                        "tier": "tier_3",
                        "issuers": ["ACB", "TCB", "VPB"],
                        "periods": ["2024_Q1", "2024_Q4"],
                        "metric_ids": ["bank.roa", "bank.roe"],
                        "analysis_tasks": ["snapshot", "trend", "peer_comparison"],
                        "peer_tickers": ["ACB", "TCB", "VPB"],
                        "complexity_vector": {
                            "issuer_count": 3,
                            "period_count": 2,
                            "metric_count": 2,
                            "analysis_task_count": 3,
                            "cross_issuer_comparisons": 1,
                            "missing_conflict_checks": 0,
                            "evidence_groups": 0,
                        },
                    },
                    "prompt": "Analyze the listed banks together.",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            question_set = load_question_set(path)

        self.assertEqual(question_set.questions[0].workload.tier.value, "tier_3")
        self.assertEqual(question_set.questions[0].workload.issuers, ("ACB", "TCB", "VPB"))

    def test_question_set_validator_cli_is_read_only_and_emits_hash(self):
        project_root = Path(__file__).parents[1]
        question_path = project_root / "experiments" / "question-set-v1.json"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(project_root / "src")

        result = subprocess.run(
            [sys.executable, "scripts/validate_question_set.py", str(question_path)],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["question_count"], 14)
        self.assertEqual(summary["question_set_sha256"], question_set_sha256(question_path))


if __name__ == "__main__":
    unittest.main()
