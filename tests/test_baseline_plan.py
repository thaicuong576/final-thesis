import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_plan import (
    audit_baseline_plan,
    build_baseline_plan,
    build_baseline_plan_from_file,
)
from thesis_data.question_set import load_question_set


class BaselinePlanTests(unittest.TestCase):
    def test_pilot_plan_expands_every_question_across_all_three_arms(self):
        question_path = Path(__file__).parents[1] / "experiments" / "question-set-v1.json"
        question_set = load_question_set(question_path)

        plan = build_baseline_plan(question_set, question_path, "PENDING_GOLD_SNAPSHOT")

        self.assertEqual(plan.status, "planned_not_executed")
        self.assertFalse(plan.comparative_result)
        self.assertEqual(len(plan.jobs), 42)
        self.assertEqual(
            {job.arm.value for job in plan.jobs},
            {"single_agent", "hierarchical_no_critique", "hierarchical_bounded_critique"},
        )
        self.assertEqual({job.question_set_sha256 for job in plan.jobs}, {plan.question_set_sha256})
        self.assertEqual(len({job.job_id for job in plan.jobs}), 42)

        macro_job = next(job for job in plan.jobs if job.question_id == "TCB_macro_to_bank_q4")
        self.assertEqual(macro_job.issuer, "TCB")
        self.assertEqual(macro_job.periods, ("2024_Q4",))
        self.assertEqual(macro_job.metric_ids, ("bank.roa", "bank.roe"))
        self.assertEqual(
            macro_job.macro_indicator_ids,
            ("macro.policy_rate", "macro.credit_growth"),
        )

        conflict_job = next(job for job in plan.jobs if job.question_id == "ACB_known_conflict_q2")
        self.assertEqual(conflict_job.metric_ids, ("bank.llr_coverage",))

    def test_plan_builder_from_file_is_deterministic(self):
        question_path = Path(__file__).parents[1] / "experiments" / "question-set-v1.json"

        first = build_baseline_plan_from_file(question_path, "PENDING_GOLD_SNAPSHOT")
        second = build_baseline_plan_from_file(question_path, "PENDING_GOLD_SNAPSHOT")

        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))

    def test_plan_cli_emits_noncomparative_json_without_mutating_question_set(self):
        project_root = Path(__file__).parents[1]
        question_path = project_root / "experiments" / "question-set-v1.json"
        before = question_path.read_bytes()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(project_root / "src")

        result = subprocess.run(
            [
                sys.executable,
                "scripts/plan_baseline_runs.py",
                str(question_path),
                "PENDING_GOLD_SNAPSHOT",
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["job_count"], 42)
        self.assertFalse(payload["comparative_result"])
        self.assertEqual(before, question_path.read_bytes())

    def test_plan_cli_refuses_to_overwrite_output(self):
        project_root = Path(__file__).parents[1]
        question_path = project_root / "experiments" / "question-set-v1.json"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(project_root / "src")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "baseline-plan.json"
            output.write_text("existing", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/plan_baseline_runs.py",
                    str(question_path),
                    "PENDING_GOLD_SNAPSHOT",
                    "--output",
                    str(output),
                ],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            preserved = output.read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(preserved, "existing")

    def test_committed_plan_passes_read_only_plan_level_validation(self):
        project_root = Path(__file__).parents[1]
        plan_path = project_root / "experiments" / "runs" / "baseline-plan-pilot-v1.json"
        question_path = project_root / "experiments" / "question-set-v1.json"

        audit = audit_baseline_plan(plan_path, question_path)

        self.assertTrue(audit.eligible, audit.blockers)
        self.assertEqual(audit.question_count, 14)
        self.assertEqual(audit.job_count, 42)
        self.assertEqual(audit.blockers, ())

    def test_committed_core_plan_passes_read_only_plan_level_validation(self):
        project_root = Path(__file__).parents[1]
        plan_path = project_root / "experiments" / "runs" / "baseline-plan-core-v1.json"
        question_path = project_root / "experiments" / "question-set-core-v1.json"

        audit = audit_baseline_plan(plan_path, question_path)

        self.assertTrue(audit.eligible, audit.blockers)
        self.assertEqual(audit.question_count, 13)
        self.assertEqual(audit.job_count, 39)
        self.assertEqual(audit.blockers, ())

    def test_plan_level_validation_rejects_question_set_hash_drift(self):
        project_root = Path(__file__).parents[1]
        question_path = project_root / "experiments" / "question-set-v1.json"
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.json"
            plan = json.loads(
                (project_root / "experiments" / "runs" / "baseline-plan-pilot-v1.json").read_text(
                    encoding="utf-8"
                )
            )
            plan["question_set_sha256"] = "0" * 64
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            audit = audit_baseline_plan(plan_path, question_path)

        self.assertFalse(audit.eligible)
        self.assertIn("plan_question_set_hash_mismatch", audit.blockers)

    def test_plan_validator_cli_is_read_only_and_reports_job_count(self):
        project_root = Path(__file__).parents[1]
        plan_path = project_root / "experiments" / "runs" / "baseline-plan-pilot-v1.json"
        question_path = project_root / "experiments" / "question-set-v1.json"
        before = plan_path.read_bytes()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(project_root / "src")

        result = subprocess.run(
            [
                sys.executable,
                "scripts/validate_baseline_plan.py",
                str(plan_path),
                str(question_path),
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["eligible"])
        self.assertEqual(payload["job_count"], 42)
        self.assertEqual(before, plan_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
