import unittest
import time

from thesis_data.agent_runtime import AgentCallTelemetry
from thesis_data.composite_schema import CompositeAnalysisPayload
from thesis_data.composite_runner import (
    CompositeArmRunResult,
    bounded_verification_requests,
    build_arm_sop,
    run_composite_arm,
)
from thesis_data.composite_transport import CompositeProviderResponse
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)


class RecordingCompositeAdapter:
    retrieval_mode = "tool_calling"

    def __init__(self):
        self.requests = []

    def complete(self, spec, role, question_prompt="", prepared_context=None):
        self.requests.append((spec, role, question_prompt, prepared_context))
        if role == "company":
            allowed_tasks = {
                AnalysisTask.SNAPSHOT,
                AnalysisTask.TREND,
                AnalysisTask.MISSING_CONFLICT,
                AnalysisTask.ANOMALY_REVIEW,
                AnalysisTask.EVIDENCE_SUMMARY,
            }
        elif role == "sector":
            allowed_tasks = {AnalysisTask.PEER_COMPARISON, AnalysisTask.ANOMALY_REVIEW}
        else:
            allowed_tasks = set(spec.analysis_tasks)
        subreports = []
        for issuer in spec.issuers:
            for period in spec.periods:
                for task in spec.analysis_tasks:
                    if task not in allowed_tasks:
                        continue
                    subreports.append({
                        "issuer": issuer,
                        "period": period,
                        "task": task.value,
                        "status": "partial",
                        "payload": None,
                        "missing_reasons": [f"fixture:{role}"],
                        "observation_ids": [],
                        "source_ids": [],
                        "evidence_ids": [],
                    })
        payload = CompositeAnalysisPayload.model_validate({
            "agent_id": role,
            "status": "partial",
            "question_id": spec.question_id,
            "tier": spec.tier.value,
            "issuers": list(spec.issuers),
            "periods": list(spec.periods),
            "metric_ids": list(spec.metric_ids),
            "subreports": subreports,
            "missing_conflict_register": [],
            "anomaly_classifications": [],
            "findings": [role],
            "quality_flags": [],
            "observation_ids": [],
            "source_ids": [],
            "evidence_ids": [],
        })
        return CompositeProviderResponse(
            payload=payload,
            telemetry=AgentCallTelemetry(status="provided", input_tokens=10, output_tokens=5),
            effective_context={"results": []},
            role=role,
        )


class InvalidCompositeAdapter(RecordingCompositeAdapter):
    def complete(self, spec, role, question_prompt="", prepared_context=None):
        response = super().complete(spec, role, question_prompt, prepared_context)
        invalid = response.payload.model_copy(update={"question_id": "wrong-question"})
        return CompositeProviderResponse(
            payload=invalid,
            telemetry=response.telemetry,
            effective_context=response.effective_context,
            role=role,
        )


class SlowCompositeAdapter(RecordingCompositeAdapter):
    def complete(self, spec, role, question_prompt="", prepared_context=None):
        time.sleep(0.08)
        return super().complete(spec, role, question_prompt, prepared_context)


class CompositeRunnerTests(unittest.TestCase):
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

    def config(self, arm, *, total=12, critiques=0):
        return ExperimentRunConfig(
            run_id=f"run-{arm.value}",
            snapshot_id="gold-v1",
            question_set_id="complexity-v1",
            question_id="q-composite-tier-3",
            rubric_version="rubric-v1",
            prompt_version="composite-prompt-v1",
            arm=arm,
            model_id="gpt-5.6-luna",
            source_policy_id="primary-only-v1",
            max_critique_attempts=critiques,
            max_total_calls=total,
        )

    def parallel_config(self, arm):
        config = self.config(arm)
        return config.model_copy(update={"worker_parallelism": 2})

    def test_single_agent_is_one_composite_stage(self):
        adapter = RecordingCompositeAdapter()
        result = run_composite_arm(self.spec(), self.config(ExperimentArm.SINGLE_AGENT), adapter)

        self.assertIsInstance(result, CompositeArmRunResult)
        self.assertEqual(result.call_count, 1)
        self.assertEqual([role for _, role, _, _ in adapter.requests], ["single_agent"])
        self.assertIsNotNone(result.final_payload)
        self.assertEqual(result.arm, ExperimentArm.SINGLE_AGENT)

    def test_hierarchical_no_critique_has_workers_but_no_verification(self):
        adapter = RecordingCompositeAdapter()
        result = run_composite_arm(
            self.spec(), self.config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE), adapter
        )

        self.assertEqual(
            [role for _, role, _, _ in adapter.requests],
            ["company", "sector", "orchestrator"],
        )
        self.assertFalse(any(role == "verification" for _, role, _, _ in adapter.requests))
        orchestrator_context = adapter.requests[2][3]
        self.assertEqual(set(orchestrator_context["worker_payloads"]), {"company", "sector"})
        self.assertIsNone(result.failure_status)

    def test_hierarchical_workers_run_in_parallel_and_record_wall_clock(self):
        adapter = SlowCompositeAdapter()
        started = time.monotonic()
        result = run_composite_arm(
            self.spec(),
            self.parallel_config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE),
            adapter,
        )
        elapsed = time.monotonic() - started
        self.assertIsNone(result.failure_status)
        observed_roles = [role for _, role, _, _ in adapter.requests]
        self.assertEqual(set(observed_roles[:2]), {"company", "sector"})
        self.assertEqual(observed_roles[2:], ["orchestrator"])
        self.assertLess(elapsed, 0.22)
        self.assertIsNotNone(result.wall_clock_latency_ms)
        self.assertGreater(result.wall_clock_latency_ms, 0)

    def test_bounded_critique_uses_only_trigger_backed_requests_and_cap(self):
        adapter = RecordingCompositeAdapter()
        result = run_composite_arm(
            self.spec(),
            self.config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE, critiques=2),
            adapter,
            triggers=("missing:VCB:2024_Q1:bank.roa", "anomaly:ACB:2024_Q2", "extra"),
        )

        roles = [role for _, role, _, _ in adapter.requests]
        self.assertEqual(roles[:3], ["company", "sector", "orchestrator"])
        self.assertEqual(roles[3:], ["verification", "verification"])
        self.assertEqual(result.critique_requests, (
            "missing:VCB:2024_Q1:bank.roa",
            "anomaly:ACB:2024_Q2",
        ))
        self.assertEqual(
            [prompt for _, role, prompt, _ in adapter.requests if role == "verification"],
            ["missing:VCB:2024_Q1:bank.roa", "anomaly:ACB:2024_Q2"],
        )

    def test_invalid_worker_payload_is_explicit_failure_and_not_published(self):
        result = run_composite_arm(
            self.spec(),
            self.config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE),
            InvalidCompositeAdapter(),
        )

        self.assertEqual(result.failure_status, "payload_validation_failed")
        self.assertIsNone(result.final_payload)

    def test_call_ceiling_is_shared_and_recorded(self):
        adapter = RecordingCompositeAdapter()
        result = run_composite_arm(
            self.spec(),
            self.config(ExperimentArm.HIERARCHICAL_NO_CRITIQUE, total=2),
            adapter,
        )

        self.assertEqual(result.call_count, 2)
        self.assertEqual(result.failure_status, "call_budget_exhausted")
        self.assertIsNone(result.final_payload)

    def test_sops_and_trigger_helper_are_deterministic(self):
        self.assertEqual(
            build_arm_sop(ExperimentArm.SINGLE_AGENT, self.spec()),
            ("decompose", "retrieve", "validate", "assemble", "synthesize"),
        )
        self.assertIn("verification", build_arm_sop(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE, self.spec()))
        payload = RecordingCompositeAdapter().complete(self.spec(), "orchestrator").payload
        self.assertEqual(
            bounded_verification_requests(
                self.spec(), payload, ("one", "two", "three"), 2
            ),
            ("one", "two"),
        )


if __name__ == "__main__":
    unittest.main()
