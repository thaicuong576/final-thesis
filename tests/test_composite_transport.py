import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_tools import GoldToolRuntime
from thesis_data.composite_schema import CompositeAnalysisPayload
from thesis_data.composite_transport import (
    CompositeProviderResponse,
    OpenAICompositeTransport,
    _composite_response_schema,
    parse_composite_provider_payload,
)
from thesis_data.openai_transport import OpenAITransportError
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.schema import AgentStatus
from thesis_data.storage import create_gold_snapshot_schema
from thesis_data.workload_contract import (
    AnalysisTask,
    CompositeWorkloadSpec,
    ComplexityVector,
    WorkloadTier,
)


class FakeResponse:
    def __init__(self, output, output_text="", input_tokens=10, output_tokens=5):
        self.output = output
        self.output_text = output_text
        self.usage = type("Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens})()


class FakeClient:
    def __init__(self, responses):
        self.responses_queue = list(responses)
        self.calls = []

    class responses:
        pass

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses_queue.pop(0)


def bind_fake(client):
    client.responses.create = client._create


class CompositeTransportTests(unittest.TestCase):
    def spec(self, *, issuers=("VCB", "ACB"), periods=("2024_Q1", "2024_Q2")):
        return CompositeWorkloadSpec(
            question_id="q-composite-tier-3",
            tier=WorkloadTier.TIER_3,
            issuers=issuers,
            periods=periods,
            metric_ids=("bank.roa",),
            analysis_tasks=(AnalysisTask.SNAPSHOT,),
            peer_tickers=issuers,
            complexity_vector=ComplexityVector(
                issuer_count=len(issuers),
                period_count=len(periods),
                metric_count=1,
                analysis_task_count=1,
                cross_issuer_comparisons=0,
                missing_conflict_checks=0,
                evidence_groups=0,
            ),
        )

    def payload(self, spec=None):
        spec = spec or self.spec()
        subreports = []
        for issuer in spec.issuers:
            for period in spec.periods:
                subreports.append(
                    {
                        "issuer": issuer,
                        "period": period,
                        "task": "snapshot",
                        "status": "partial",
                        "payload": None,
                        "missing_reasons": ["fixture_missing_metric"],
                        "observation_ids": [],
                        "source_ids": [],
                        "evidence_ids": [],
                    }
                )
        return {
            "agent_id": "single_agent",
            "status": "partial",
            "question_id": spec.question_id,
            "tier": spec.tier.value,
            "issuers": list(spec.issuers),
            "periods": list(spec.periods),
            "metric_ids": list(spec.metric_ids),
            "subreports": subreports,
            "missing_conflict_register": ["fixture_missing_metric"],
            "anomaly_classifications": [],
            "findings": ["No numeric fact was available in the fixture."],
            "quality_flags": ["fixture"],
            "observation_ids": [],
            "source_ids": [],
            "evidence_ids": [],
        }

    def config(self, max_tool_calls=8):
        return ProviderExecutionConfig(
            adapter_id="openai-responses-composite-v1",
            provider_id="openai",
            model_id="gpt-5.6-luna",
            source_policy_id="primary-only-v1",
            environment="provider_backed",
            network_access="enabled",
            api_key_env_var="OPENAI_API_KEY",
            retrieval_mode="tool_calling",
            max_tool_calls=max_tool_calls,
        )

    def fixture(self, root: Path) -> Path:
        db = root / "gold.sqlite"
        create_gold_snapshot_schema(db)
        connection = sqlite3.connect(db)
        connection.execute("INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)", ("gold", "now", "gold", "{}"))
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://example.test", "now", "private", "hash", "issuer", "test", "valid", None),
        )
        connection.execute(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("obs-1", "VCB", "bank", "bank.roa", 1.2, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:1", "valid", None),
        )
        connection.commit()
        connection.close()
        return db

    def test_parser_requires_exact_subreport_coverage_and_scope(self):
        spec = self.spec()
        raw = self.payload(spec)
        parsed = parse_composite_provider_payload(json.dumps(raw), spec, "single_agent")
        self.assertIsInstance(parsed, CompositeAnalysisPayload)
        self.assertEqual(len(parsed.subreports), 4)

        missing = dict(raw)
        missing["subreports"] = raw["subreports"][:-1]
        with self.assertRaises(OpenAITransportError) as raised:
            parse_composite_provider_payload(json.dumps(missing), spec, "single_agent")
        self.assertIn("composite_subreport_coverage_invalid", raised.exception.blockers)

        extra = dict(raw)
        extra["subreports"] = list(raw["subreports"]) + [
            {**raw["subreports"][0], "issuer": "TCB"}
        ]
        with self.assertRaises(OpenAITransportError) as raised:
            parse_composite_provider_payload(json.dumps(extra), spec, "single_agent")
        self.assertIn("provider_payload_schema_invalid", raised.exception.blockers)

    def test_parser_rejects_invalid_json_and_wrong_agent(self):
        spec = self.spec()
        with self.assertRaises(OpenAITransportError) as raised:
            parse_composite_provider_payload("not-json", spec, "single_agent")
        self.assertEqual(raised.exception.blockers, ("provider_output_json_invalid",))

        wrong = self.payload(spec)
        wrong["agent_id"] = "company"
        with self.assertRaises(OpenAITransportError) as raised:
            parse_composite_provider_payload(json.dumps(wrong), spec, "single_agent")
        self.assertIn("composite_agent_id_mismatch", raised.exception.blockers)

    def test_composite_schema_stays_within_strict_output_subset(self):
        schema = _composite_response_schema(self.spec(), "single_agent")
        encoded = json.dumps(schema)
        self.assertNotIn("minItems", encoded)
        self.assertNotIn("maxItems", encoded)

        payload_properties = schema["$defs"]["AgentPayload"]["properties"]
        self.assertFalse(payload_properties["metrics"]["additionalProperties"])
        self.assertFalse(payload_properties["metric_units"]["additionalProperties"])
        self.assertFalse(payload_properties["metric_periods"]["additionalProperties"])
        self.assertFalse(payload_properties["sector_benchmarks"]["additionalProperties"])
        payload_variants = schema["$defs"]["CompositeSubreport"]["properties"]["payload"]["anyOf"]
        self.assertTrue(all("$ref" not in variant for variant in payload_variants))
        self.assertNotIn(
            "default",
            schema["$defs"]["CompositeSubreport"]["properties"]["status"],
        )
        self.assertEqual(schema["properties"]["subreports"]["type"], "array")
        self.assertEqual(schema["properties"]["subreports"]["items"]["type"], "object")
        self.assertEqual(
            len(schema["properties"]["subreports"]["items"]["required"]),
            10,
        )

    def test_parser_expands_normalized_subreport_object(self):
        spec = self.spec()
        raw = self.payload(spec)
        raw["subreports"] = {
            f"{item['issuer']}|{item['period']}|{item['task']}": {
                "status": item["status"],
                "payload": None,
                "payload_ref": None,
                "missing_reasons": item["missing_reasons"],
                "observation_ids": [],
                "source_ids": [],
                "evidence_ids": [],
            }
            for item in self.payload(spec)["subreports"]
        }
        parsed = parse_composite_provider_payload(json.dumps(raw), spec, "single_agent")
        self.assertEqual(len(parsed.subreports), 4)
        self.assertEqual(parsed.subreports[0].issuer, "VCB")

    def test_parser_compiles_task_refs_from_canonical_data_slices(self):
        spec = self.spec()
        raw = self.payload(spec)
        raw["subreports"] = []
        raw["data_slices"] = [
            {
                "agent_id": "single_agent",
                "status": "partial",
                "ticker": issuer,
                "period": period,
                "metrics": {"bank.roa": None},
                "metric_units": {"bank.roa": "%"},
                "metric_periods": {"bank.roa": period},
                "sector_benchmarks": {},
                "findings": [],
                "evidence": [],
                "quality_flags": ["fixture_missing_metric"],
                "observation_ids": [],
                "source_ids": [],
            }
            for issuer in spec.issuers
            for period in spec.periods
        ]
        parsed = parse_composite_provider_payload(json.dumps(raw), spec, "single_agent")
        self.assertEqual(len(parsed.subreports), 4)
        self.assertTrue(all(item.payload_ref for item in parsed.subreports))

    def test_orchestrator_compiles_compact_response_from_validated_workers(self):
        spec = self.spec()
        company = self.payload(spec)
        company["agent_id"] = "company"
        company["data_slices"] = [
            {
                "agent_id": "company",
                "status": "partial",
                "ticker": issuer,
                "period": period,
                "metrics": {"bank.roa": None},
                "metric_units": {"bank.roa": "%"},
                "metric_periods": {"bank.roa": period},
                "sector_benchmarks": {},
                "findings": [],
                "evidence": [],
                "quality_flags": ["fixture_missing_metric"],
                "observation_ids": [],
                "source_ids": [],
            }
            for issuer in spec.issuers
            for period in spec.periods
        ]
        company["subreports"] = [
            {
                **item,
                "task": "snapshot",
            }
            for item in company["subreports"]
        ]
        compact_orchestrator = self.payload(spec)
        compact_orchestrator["agent_id"] = "orchestrator"
        compact_orchestrator["subreports"] = []
        compact_orchestrator["data_slices"] = []
        parsed = parse_composite_provider_payload(
            json.dumps(compact_orchestrator),
            spec,
            "orchestrator",
            prepared_context={"worker_payloads": {"company": company}},
        )
        self.assertEqual(len(parsed.subreports), 4)
        self.assertEqual(len(parsed.data_slices), 4)
        self.assertTrue(all(item.payload_ref for item in parsed.subreports))
        self.assertTrue(all(item.agent_id == "orchestrator" for item in parsed.data_slices))

    def test_claim_provenance_is_recovered_only_from_nested_payload_ids(self):
        spec = self.spec()
        raw = self.payload(spec)
        raw["claims"] = [
            {
                "claim_id": "c1",
                "claim_type": "snapshot",
                "priority": "high",
                "title": "Fixture claim",
                "claim": "VCB has a bound fixture value.",
                "interpretation": "The value can be checked against the fixture.",
                "limitation": "Fixture only.",
                "support": "evidence_backed",
                "data_refs": ["VCB|2024_Q1|bank.roa"],
                "evidence_ids": ["e-1"],
                "source_ids": ["source-1"],
            }
        ]
        raw["subreports"][0]["evidence_ids"] = ["e-1"]
        raw["subreports"][0]["source_ids"] = ["source-1"]
        parsed = parse_composite_provider_payload(json.dumps(raw), spec, "single_agent")
        self.assertEqual(parsed.claims[0].support, "evidence_backed")
        self.assertIn("e-1", parsed.evidence_ids)
        self.assertIn("source-1", parsed.source_ids)

    def test_verification_payload_may_use_flagged_issuer_period_subset(self):
        spec = self.spec(issuers=("VCB", "ACB"), periods=("2024_Q1", "2024_Q2"))
        raw = self.payload(spec)
        raw["agent_id"] = "verification"
        raw["issuers"] = ["VCB"]
        raw["periods"] = ["2024_Q1"]
        raw["subreports"] = [raw["subreports"][0]]
        parsed = parse_composite_provider_payload(json.dumps(raw), spec, "verification")
        self.assertEqual(parsed.issuers, ("VCB",))
        self.assertEqual(parsed.periods, ("2024_Q1",))

    def test_composite_tool_loop_returns_typed_payload_and_telemetry(self):
        spec = self.spec(issuers=("VCB", "ACB"), periods=("2024_Q1",))
        output = self.payload(spec)
        client = FakeClient([
            FakeResponse([
                {
                    "type": "function_call",
                    "name": "get_company_metrics",
                    "call_id": "call-1",
                    "arguments": json.dumps({"ticker": "VCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]}),
                },
                {
                    "type": "function_call",
                    "name": "get_company_metrics",
                    "call_id": "call-2",
                    "arguments": json.dumps({"ticker": "ACB", "period": "2024_Q1", "metric_ids": ["bank.roa"]}),
                },
            ], input_tokens=20, output_tokens=7),
            FakeResponse([], output_text=json.dumps(output), input_tokens=30, output_tokens=11),
        ])
        bind_fake(client)

        with tempfile.TemporaryDirectory() as directory:
            transport = OpenAICompositeTransport(client, self.fixture(Path(directory)))
            response = transport.complete_composite(spec, "single_agent", "composite prompt", self.config())

        self.assertIsInstance(response, CompositeProviderResponse)
        self.assertEqual(response.payload.question_id, spec.question_id)
        self.assertEqual(response.telemetry.input_tokens, 50)
        self.assertEqual(response.telemetry.output_tokens, 18)
        self.assertEqual(len(response.tool_calls), 2)
        self.assertEqual(response.tool_calls[0].status, "success")
        self.assertEqual(len(client.calls), 2)

    def test_composite_tool_loop_rejects_out_of_scope_call(self):
        spec = self.spec(issuers=("VCB", "ACB"), periods=("2024_Q1",))
        client = FakeClient([
            FakeResponse([
                {
                    "type": "function_call",
                    "name": "get_company_metrics",
                    "call_id": "call-1",
                    "arguments": json.dumps({"ticker": "TCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]}),
                }
            ]),
            FakeResponse([], output_text=json.dumps(self.payload(spec))),
        ])
        bind_fake(client)
        with tempfile.TemporaryDirectory() as directory:
            transport = OpenAICompositeTransport(client, self.fixture(Path(directory)))
            response = transport.complete_composite(spec, "single_agent", "composite prompt", self.config())

        self.assertEqual(response.tool_calls[0].status, "rejected")
        self.assertEqual(response.effective_context["results"][0]["output"]["error"], "tool_query_rejected")

    def test_provider_bad_request_keeps_safe_api_diagnostic_metadata(self):
        class BadRequestError(Exception):
            status_code = 400
            code = "invalid_request_error"
            type = "invalid_request_error"
            param = "text.format.schema"
            body = {"error": {"code": "invalid_json_schema", "type": "invalid_request_error"}}

        class ErrorClient:
            class responses:
                pass

            def create(self, **kwargs):
                raise BadRequestError("sensitive request details")

        client = ErrorClient()
        client.responses.create = client.create
        with tempfile.TemporaryDirectory() as directory:
            transport = OpenAICompositeTransport(client, self.fixture(Path(directory)))
            with self.assertRaises(OpenAITransportError) as raised:
                transport.complete_composite(self.spec(), "single_agent", "prompt", self.config())

        self.assertIn("provider_request_failed:BadRequestError", raised.exception.blockers)
        self.assertIn("status_code=400", raised.exception.blockers)
        self.assertIn("code=invalid_request_error", raised.exception.blockers)
        self.assertIn("param=text.format.schema", raised.exception.blockers)
        self.assertNotIn("sensitive request details", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
