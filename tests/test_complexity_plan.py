import json
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_plan import (
    audit_complexity_plan,
    build_complexity_plan,
    load_complexity_question_set,
)
from thesis_data.experiment_contract import ExperimentArm


class ComplexityPlanTests(unittest.TestCase):
    def question_set(self, directory: str) -> Path:
        path = Path(directory) / "questions.json"
        payload = {
            "schema_version": 1,
            "question_set_id": "complexity-v1",
            "status": "frozen",
            "scope": {
                "issuers": ["ACB", "TCB"],
                "periods": ["2024_Q1", "2024_Q2"],
                "core_metrics": ["bank.roa"],
            },
            "questions": [
                {
                    "id": "ACB-composite",
                    "type": "composite_workload",
                    "prompt": "Analyze ACB.",
                    "workload": {
                        "question_id": "ACB-composite",
                        "tier": "tier_2",
                        "issuers": ["ACB"],
                        "periods": ["2024_Q1", "2024_Q2"],
                        "metric_ids": ["bank.roa"],
                        "analysis_tasks": ["snapshot"],
                        "peer_tickers": ["ACB", "TCB"],
                        "complexity_vector": {
                            "issuer_count": 1,
                            "period_count": 2,
                            "metric_count": 1,
                            "analysis_task_count": 1,
                            "cross_issuer_comparisons": 0,
                            "missing_conflict_checks": 0,
                            "evidence_groups": 0,
                        },
                    },
                }
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_builder_expands_each_composite_question_to_all_arms_with_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.question_set(directory)
            question_set = load_complexity_question_set(path)
            plan = build_complexity_plan(
                question_set,
                path,
                tuple(ExperimentArm),
                "gold-v1",
                "gpt-5.6-luna",
                total_call_ceilings={"tier_2": 6, "tier_3": 6},
            )

        self.assertEqual(len(plan.jobs), 3)
        self.assertTrue(all(job.max_total_calls == 6 for job in plan.jobs))
        self.assertTrue(all(job.model_id == "gpt-5.6-luna" for job in plan.jobs))
        self.assertFalse(plan.comparative_result)

    def test_audit_rejects_changed_question_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.question_set(directory)
            question_set = load_complexity_question_set(path)
            plan = build_complexity_plan(
                question_set,
                path,
                tuple(ExperimentArm),
                "gold-v1",
                "gpt-5.6-luna",
                total_call_ceilings={"tier_2": 6, "tier_3": 6},
            )
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            audit = audit_complexity_plan(plan_path, path)

        self.assertFalse(audit.eligible)
        self.assertIn("plan_question_set_hash_mismatch", audit.blockers)

    def test_complexity_builder_and_auditor_use_canonical_lf_hash_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf_path = self.question_set(directory)
            payload = json.loads(lf_path.read_text(encoding="utf-8"))
            lf_bytes = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            lf_path.write_bytes(lf_bytes)
            crlf_path = root / "questions-crlf.json"
            crlf_path.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))

            lf_set = load_complexity_question_set(lf_path)
            plan = build_complexity_plan(
                lf_set,
                lf_path,
                tuple(ExperimentArm),
                "gold-v1",
                "gpt-5.6-luna",
                total_call_ceilings={"tier_2": 6, "tier_3": 6},
            )
            crlf_set = load_complexity_question_set(crlf_path)
            crlf_plan = build_complexity_plan(
                crlf_set,
                crlf_path,
                tuple(ExperimentArm),
                "gold-v1",
                "gpt-5.6-luna",
                total_call_ceilings={"tier_2": 6, "tier_3": 6},
            )
            plan_path = root / "plan.json"
            plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
            crlf_plan_path = root / "plan-crlf.json"
            crlf_plan_path.write_text(crlf_plan.model_dump_json(), encoding="utf-8")

            audit_lf_plan_against_crlf = audit_complexity_plan(plan_path, crlf_path)
            audit_crlf_plan_against_lf = audit_complexity_plan(crlf_plan_path, lf_path)

        self.assertEqual(plan.question_set_sha256, crlf_plan.question_set_sha256)
        self.assertEqual(plan.question_set_hash_mode, "canonical_lf_utf8_sha256")
        self.assertTrue(
            all(
                job.question_set_hash_mode == "canonical_lf_utf8_sha256"
                for job in plan.jobs
            )
        )
        self.assertTrue(audit_lf_plan_against_crlf.eligible)
        self.assertTrue(audit_crlf_plan_against_lf.eligible)

    def test_existing_complexity_plans_validate_without_artifact_changes(self):
        root = Path(__file__).parents[1]
        question_path = root / "experiments" / "question-set-complexity-v1.json"
        for filename in (
            "complexity-plan-gold-v1.json",
            "complexity-plan-parallel-v1.json",
        ):
            with self.subTest(plan=filename):
                audit = audit_complexity_plan(
                    root / "experiments" / "runs" / filename,
                    question_path,
                )
                self.assertTrue(audit.eligible, audit.blockers)


if __name__ == "__main__":
    unittest.main()
