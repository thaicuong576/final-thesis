import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_runtime import AgentCallRequest
from thesis_data.openai_transport import OpenAIResponsesTransport, OpenAITransportError
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.schema import AgentPayload, AgentStatus
from thesis_data.storage import create_gold_snapshot_schema


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


class OpenAITransportTests(unittest.TestCase):
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

    def config(self, max_tool_calls=4):
        return ProviderExecutionConfig(
            adapter_id="openai-responses-tool-calling-v1",
            provider_id="openai",
            model_id="gpt-5.6-luna",
            source_policy_id="primary-only-v1",
            environment="provider_backed",
            network_access="enabled",
            api_key_env_var="OPENAI_API_KEY",
            retrieval_mode="tool_calling",
            max_tool_calls=max_tool_calls,
        )

    def request(self):
        return AgentCallRequest(
            role="company", ticker="VCB", period="2024_Q1", periods=("2024_Q1",),
            metric_ids=("bank.roa",), question_id="q1", question_prompt="Report ROA.",
            prompt_version="prompt-v1", context={"retrieval_mode": "closed_world_tool_calling"},
            peer_tickers=("VCB",),
        )

    def test_tool_loop_returns_payload_trace_and_usage(self):
        payload = AgentPayload(
            agent_id="company", status=AgentStatus.SUCCESS, ticker="VCB", period="2024_Q1",
            metrics={"bank.roa": 1.2}, metric_units={"bank.roa": "%"},
            metric_periods={"bank.roa": "2024_Q1"}, observation_ids=["obs-1"], source_ids=["source-1"],
        )
        client = FakeClient([
            FakeResponse([{"type": "function_call", "name": "get_company_metrics", "call_id": "call-1", "arguments": json.dumps({"ticker": "VCB", "period": "2024_Q1", "metric_ids": ["bank.roa"]})}]),
            FakeResponse([], output_text=payload.model_dump_json()),
        ])
        bind_fake(client)
        with tempfile.TemporaryDirectory() as directory:
            transport = OpenAIResponsesTransport(client, self.fixture(Path(directory)), ("VCB",))
            response = transport.complete(self.request(), "tool prompt", self.config())

        self.assertEqual(json.loads(response.payload)["metrics"]["bank.roa"], 1.2)
        self.assertEqual(response.tool_calls[0].name, "get_company_metrics")
        self.assertEqual(response.telemetry.status, "provided")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["model"], "gpt-5.6-luna")
        self.assertEqual(client.calls[0]["tools"][0]["strict"], True)

    def test_unknown_tool_fails_closed(self):
        client = FakeClient([FakeResponse([{"type": "function_call", "name": "arbitrary_sql", "call_id": "call-1", "arguments": "{}"}])])
        bind_fake(client)
        with tempfile.TemporaryDirectory() as directory:
            transport = OpenAIResponsesTransport(client, self.fixture(Path(directory)), ("VCB",))
            with self.assertRaises(OpenAITransportError) as raised:
                transport.complete(self.request(), "tool prompt", self.config())
        self.assertEqual(raised.exception.blockers, ("tool_not_allowed",))


if __name__ == "__main__":
    unittest.main()
