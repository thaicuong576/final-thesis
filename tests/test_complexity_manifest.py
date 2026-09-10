import json
import tempfile
import unittest
from pathlib import Path

from thesis_data.composite_runner import run_composite_arm
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.run_manifest import (
    ExperimentRunManifest,
    build_composite_run_manifest,
)
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)
from tests.test_composite_runner import RecordingCompositeAdapter


class ComplexityManifestTests(unittest.TestCase):
    def spec(self):
        return CompositeWorkloadSpec(
            question_id="q-composite-tier-3",
            tier=WorkloadTier.TIER_3,
            issuers=("VCB", "ACB"),
            periods=("2024_Q1", "2024_Q2"),
            metric_ids=("bank.roa",),
            analysis_tasks=(AnalysisTask.SNAPSHOT, AnalysisTask.TREND),
            peer_tickers=("VCB", "ACB"),
            complexity_vector=ComplexityVector(
                issuer_count=2,
                period_count=2,
                metric_count=1,
                analysis_task_count=2,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=0,
            ),
        )

    def config(self, arm=ExperimentArm.HIERARCHICAL_NO_CRITIQUE, total=6):
        return ExperimentRunConfig(
            run_id="complexity-run",
            snapshot_id="gold-v1",
            question_set_id="complexity-v1",
            question_id="q-composite-tier-3",
            rubric_version="rubric-v1",
            prompt_version="composite-prompt-v1",
            arm=arm,
            model_id="gpt-5.6-luna",
            source_policy_id="primary-only-v1",
            max_total_calls=total,
        )

    def question_set_file(self, directory: str) -> Path:
        path = Path(directory) / "questions.json"
        path.write_text(json.dumps({"fixture": "question-set"}), encoding="utf-8")
        return path

    def test_composite_manifest_persists_scope_sop_subreports_and_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_composite_arm(self.spec(), self.config(), RecordingCompositeAdapter())
            manifest = build_composite_run_manifest(
                result,
                question_set_path=self.question_set_file(directory),
            )

        self.assertEqual(manifest.workload_tier, WorkloadTier.TIER_3)
        self.assertEqual(manifest.complexity_vector["issuer_count"], 2)
        self.assertEqual(manifest.arm_sop[0], "decompose")
        self.assertEqual(manifest.subreport_count, 8)
        self.assertEqual(manifest.total_tool_calls, 0)
        self.assertEqual(manifest.total_input_tokens, 30)
        self.assertEqual(manifest.total_output_tokens, 15)
        self.assertEqual(manifest.failure_status, None)
        self.assertEqual(len(manifest.payloads), 3)

    def test_composite_failure_is_recorded_without_fabricating_final_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_composite_arm(
                self.spec(), self.config(total=2), RecordingCompositeAdapter()
            )
            manifest = build_composite_run_manifest(
                result,
                question_set_path=self.question_set_file(directory),
            )

        self.assertEqual(manifest.failure_status, "call_budget_exhausted")
        self.assertEqual(manifest.subreport_count, 0)
        self.assertEqual(manifest.final_payload, None)

    def test_old_atomic_manifest_shape_still_deserializes(self):
        payload = {
            "environment": "offline_fixture",
            "comparative_result": False,
            "run_id": "old-run",
            "snapshot_id": "gold-v1",
            "question_set_id": "q-v1",
            "question_set_sha256": "a" * 64,
            "question_id": "q1",
            "rubric_version": "r1",
            "prompt_version": "p1",
            "arm": "single_agent",
            "model_id": "m1",
            "source_policy_id": "primary-only-v1",
            "ticker": "VCB",
            "period": "2024_Q1",
            "metric_ids": ["bank.roa"],
            "input_context_sha256": "b" * 64,
            "call_count": 0,
            "calls": [],
            "payloads": [],
            "recorded_at_utc": "2026-09-06T00:00:00Z",
        }
        manifest = ExperimentRunManifest.model_validate(payload)
        self.assertIsNone(manifest.workload_tier)
        self.assertEqual(manifest.total_tool_calls, 0)


if __name__ == "__main__":
    unittest.main()
