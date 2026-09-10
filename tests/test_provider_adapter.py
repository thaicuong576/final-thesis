"""Tests for the provider-neutral structured response adapter boundary."""

from __future__ import annotations

import json
import unittest

from thesis_data.agent_runtime import (
    AgentCallRequest,
    AgentCallTelemetry,
    AgentCompletion,
)
from thesis_data.composite_transport import CompositeProviderResponse
from thesis_data.provider_adapter import (
    ProviderAdapterError,
    ProviderExecutionConfig,
    ProviderResponse,
    StructuredCompositeProviderAdapter,
    StructuredProviderAdapter,
)
from thesis_data.prompting import render_agent_prompt
from thesis_data.schema import AgentPayload, AgentStatus
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)


class RecordingTransport:
    def __init__(self, response: ProviderResponse | object, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[tuple[AgentCallRequest, str, ProviderExecutionConfig]] = []

    def complete(
        self,
        request: AgentCallRequest,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
    ) -> ProviderResponse | object:
        self.requests.append((request, rendered_prompt, config))
        if self.error is not None:
            raise self.error
        return self.response


class RecordingCompositeTransport:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def complete_composite(self, spec, role, rendered_prompt, config):
        self.requests.append((spec, role, rendered_prompt, config))
        return self.response


class ProviderAdapterTests(unittest.TestCase):
    def config(self, *, telemetry_required: bool = True) -> ProviderExecutionConfig:
        return ProviderExecutionConfig(
            adapter_id="structured-provider-v1",
            provider_id="test-provider",
            model_id="provider-model-v1",
            source_policy_id="primary-only-v1",
            environment="provider_backed",
            network_access="enabled",
            api_key_env_var="THESIS_PROVIDER_API_KEY",
            telemetry_required=telemetry_required,
        )

    def request(self) -> AgentCallRequest:
        return AgentCallRequest(
            role="company",
            ticker="VCB",
            period="2024_Q1",
            context={"facts": {}},
            metric_ids=("bank.npl_g35",),
            question_prompt="Report the requested metric.",
            prompt_version="prompt-contract-v1",
        )

    def payload(self) -> AgentPayload:
        return AgentPayload(
            agent_id="company",
            status=AgentStatus.SUCCESS,
            ticker="VCB",
            period="2024_Q1",
            findings=["validated response"],
        )

    def composite_spec(self) -> CompositeWorkloadSpec:
        return CompositeWorkloadSpec(
            question_id="q-composite-tier-2",
            tier=WorkloadTier.TIER_2,
            issuers=("VCB",),
            periods=("2024_Q1",),
            metric_ids=("bank.roa",),
            analysis_tasks=(AnalysisTask.SNAPSHOT,),
            complexity_vector=ComplexityVector(
                issuer_count=1,
                period_count=1,
                metric_count=1,
                analysis_task_count=1,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=0,
            ),
        )

    def composite_payload(self):
        spec = self.composite_spec()
        return {
            "agent_id": "company",
            "status": "partial",
            "question_id": spec.question_id,
            "tier": spec.tier.value,
            "issuers": ["VCB"],
            "periods": ["2024_Q1"],
            "metric_ids": ["bank.roa"],
            "subreports": [{
                "issuer": "VCB", "period": "2024_Q1", "task": "snapshot",
                "status": "partial", "payload": None,
                "missing_reasons": ["fixture"],
                "observation_ids": [], "source_ids": [], "evidence_ids": [],
            }],
            "missing_conflict_register": ["fixture"],
            "anomaly_classifications": [], "findings": [], "quality_flags": [],
            "observation_ids": [], "source_ids": [], "evidence_ids": [],
        }

    def test_structured_payload_preserves_payload_and_provider_telemetry(self):
        telemetry = AgentCallTelemetry(
            status="provided",
            latency_ms=120.5,
            input_tokens=30,
            output_tokens=12,
            cost_estimate=0.001,
        )
        transport = RecordingTransport(ProviderResponse(self.payload(), telemetry))

        completion = StructuredProviderAdapter(transport, self.config()).complete(self.request())

        self.assertIsInstance(completion, AgentCompletion)
        self.assertEqual(completion.payload, self.payload())
        self.assertEqual(completion.telemetry, telemetry)
        self.assertEqual(transport.requests[0][0], self.request())
        self.assertEqual(transport.requests[0][1], render_agent_prompt(self.request()))
        self.assertEqual(transport.requests[0][2], self.config())

    def test_json_payload_is_parsed_into_the_typed_contract(self):
        transport = RecordingTransport(
            ProviderResponse(json.dumps(self.payload().model_dump(mode="json")), AgentCallTelemetry())
        )

        completion = StructuredProviderAdapter(
            transport,
            self.config(telemetry_required=False),
        ).complete(self.request())

        self.assertEqual(completion.payload, self.payload())
        self.assertEqual(completion.telemetry.status, "unavailable")

    def test_malformed_json_fails_closed_at_the_adapter_boundary(self):
        transport = RecordingTransport(ProviderResponse("not-json", AgentCallTelemetry()))

        with self.assertRaises(ProviderAdapterError) as raised:
            StructuredProviderAdapter(transport, self.config()).complete(self.request())

        self.assertEqual(raised.exception.blockers, ("provider_response_json_invalid",))

    def test_payload_schema_failure_fails_closed_at_the_adapter_boundary(self):
        transport = RecordingTransport(
            ProviderResponse({"agent_id": "company"}, AgentCallTelemetry())
        )

        with self.assertRaises(ProviderAdapterError) as raised:
            StructuredProviderAdapter(transport, self.config()).complete(self.request())

        self.assertEqual(raised.exception.blockers, ("provider_payload_schema_invalid",))

    def test_required_telemetry_cannot_be_missing(self):
        transport = RecordingTransport(ProviderResponse(self.payload(), None))

        with self.assertRaises(ProviderAdapterError) as raised:
            StructuredProviderAdapter(transport, self.config()).complete(self.request())

        self.assertEqual(raised.exception.blockers, ("provider_telemetry_required",))

    def test_optional_telemetry_is_explicitly_marked_unavailable(self):
        transport = RecordingTransport(ProviderResponse(self.payload(), None))

        completion = StructuredProviderAdapter(
            transport,
            self.config(telemetry_required=False),
        ).complete(self.request())

        self.assertEqual(completion.telemetry, AgentCallTelemetry())

    def test_transport_failure_is_wrapped_without_exposing_provider_details(self):
        transport = RecordingTransport(
            ProviderResponse(self.payload(), AgentCallTelemetry()),
            error=RuntimeError("secret-looking provider failure"),
        )

        with self.assertRaises(ProviderAdapterError) as raised:
            StructuredProviderAdapter(transport, self.config()).complete(self.request())

        self.assertEqual(raised.exception.blockers, ("provider_transport_failed",))
        self.assertNotIn("secret-looking", str(raised.exception))

    def test_composite_adapter_preserves_typed_response_and_scope_prompt(self):
        from thesis_data.composite_schema import CompositeAnalysisPayload

        spec = self.composite_spec()
        response = CompositeProviderResponse(
            payload=CompositeAnalysisPayload.model_validate(self.composite_payload()),
            telemetry=AgentCallTelemetry(status="provided", input_tokens=4, output_tokens=2),
            effective_context={"results": []},
            role="company",
        )
        transport = RecordingCompositeTransport(response)

        completion = StructuredCompositeProviderAdapter(
            transport, self.config(), prompt_version="composite-prompt-v1"
        ).complete(spec, "company", "Analyze this composite request.")

        self.assertEqual(completion.payload.question_id, spec.question_id)
        self.assertEqual(completion.telemetry.input_tokens, 4)
        self.assertIn("Stage 1: decompose", transport.requests[0][2])
        self.assertIn("VCB", transport.requests[0][2])


if __name__ == "__main__":
    unittest.main()
