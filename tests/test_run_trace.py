"""Tests for ER-5: Structured agent execution trace persistence, streaming, and cost tracking."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from thesis_api.database import (
    ensure_analysis_runs_table,
    get_analysis_run,
    get_analysis_run_trace,
    list_analysis_runs,
    save_analysis_run,
)
from thesis_api.main import create_app
from thesis_api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    RunTraceDTO,
    TraceStepDTO,
)
from thesis_api.service import AnalysisEngine, stream_analysis_query
from thesis_api.settings import Settings
from thesis_api.cost_tracker import (
    LLMUsageTracker,
    wrap_llm_client,
    _extract_usage,
)

from test_api_analyze import (
    _ExplicitOfflineAcceptingCritic,
    _ExplicitOfflineAnalysisWriter,
    _RevisionScenarioCritic,
    _fixture_provider_binding,
    _gold_fixture,
)


class RunTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "accepted-fixture.sqlite"
        _gold_fixture(self.database_path)
        self.runs_path = Path(self.directory.name) / "analysis-runs.sqlite"
        self.settings = Settings(
            app_env="test",
            sqlite_db_path=str(self.database_path),
            analysis_runs_db_path=str(self.runs_path),
            openai_api_key="test-key",
            analysis_arm="hierarchical_with_critique",
        )
        self.writer = _ExplicitOfflineAnalysisWriter()
        self.critic = _ExplicitOfflineAcceptingCritic()
        self.app = create_app(
            self.settings,
            analysis_writer=self.writer,
            semantic_critic=self.critic,
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.directory.cleanup()

    def test_offline_happy_path_trace_order_and_continuity(self) -> None:
        """Verify full sequence of trace kinds, continuous seq, and monotonic t_ms."""
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            response = self.client.post(
                "/api/analyze",
                json={
                    "query": "Phân tích ROE của ACB năm 2024",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
            self.assertEqual(response.status_code, 200)
            report = response.json()
            report_id = report["report_id"]

            trace_res = self.client.get(f"/api/runs/{report_id}/trace")
            self.assertEqual(trace_res.status_code, 200)
            trace = trace_res.json()

            # Verify top-level trace attributes
            self.assertEqual(trace["run_id"], report_id)
            self.assertEqual(trace["status"], "completed")
            self.assertEqual(trace["arm"], "hierarchical_with_critique")
            self.assertTrue(trace["question_type"])
            self.assertGreaterEqual(trace["duration_ms"], 0)

            steps = trace["steps"]
            self.assertGreater(len(steps), 0)

            # Verify seq is continuous from 1 to len(steps)
            for idx, step in enumerate(steps, 1):
                self.assertEqual(step["seq"], idx, f"Step seq at index {idx-1} should be {idx}")

            # Verify t_ms is non-decreasing (monotonic)
            t_values = [step["t_ms"] for step in steps]
            for i in range(1, len(t_values)):
                self.assertGreaterEqual(t_values[i], t_values[i - 1], "t_ms must be non-decreasing")

            # Verify presence of expected kinds in chronological order
            kinds = [s["kind"] for s in steps]
            self.assertEqual(kinds[0], "plan")
            self.assertIn("assign", kinds)
            self.assertIn("tool_result", kinds)
            self.assertIn("draft", kinds)
            self.assertIn("verify", kinds)
            self.assertIn("compose", kinds)
            self.assertIn("accept", kinds)
            self.assertEqual(kinds[-1], "report_ready")

            # Verify plan step detail
            plan_step = steps[0]
            self.assertEqual(plan_step["actor"], "orchestrator")
            self.assertIn("question_type", plan_step["detail"])
            self.assertIn("tools", plan_step["detail"])
            tools = plan_step["detail"]["tools"]
            self.assertGreater(len(tools), 0)
            self.assertTrue(all("label" in t and "agent" in t for t in tools))

            # Verify tool_result detail has backfilled source_note_no for cited facts
            tool_steps = [s for s in steps if s["kind"] == "tool_result"]
            self.assertGreater(len(tool_steps), 0)
            backfilled_notes = [
                fact.get("source_note_no")
                for ts in tool_steps
                for fact in ts["detail"].get("facts", [])
                if fact.get("source_note_no") is not None
            ]
            self.assertGreater(len(backfilled_notes), 0, "At least one cited fact must have backfilled source_note_no")

    def test_revision_trace_has_critique_issue_and_revision_steps(self) -> None:
        """Verify critique_issue and revision steps appear when critic requests changes."""
        revision_critic = _RevisionScenarioCritic(resolve_after_revision=True)
        app = create_app(
            self.settings,
            analysis_writer=self.writer,
            semantic_critic=revision_critic,
        )
        client = TestClient(app)
        try:
            with patch(
                "thesis_api.service._load_provider",
                side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
            ):
                response = client.post(
                    "/api/analyze",
                    json={
                        "query": "Phân tích ROE của ACB năm 2024",
                        "target_ticker": "ACB",
                        "period": "2024_Q4",
                    },
                )
                self.assertEqual(response.status_code, 200)
                report_id = response.json()["report_id"]

                trace_res = client.get(f"/api/runs/{report_id}/trace")
                self.assertEqual(trace_res.status_code, 200)
                trace = trace_res.json()
                kinds = [s["kind"] for s in trace["steps"]]

                self.assertIn("critique_issue", kinds)
                issue_steps = [s for s in trace["steps"] if s["kind"] == "critique_issue"]
                self.assertEqual(issue_steps[0]["actor"], "critic")
                self.assertIn("issue_type", issue_steps[0]["detail"])
                self.assertIn("severity", issue_steps[0]["detail"])

                self.assertIn("accept", kinds)
                accept_steps = [s for s in trace["steps"] if s["kind"] == "accept"]
                self.assertGreaterEqual(len(accept_steps), 1)
        finally:
            client.close()

    def test_blocked_run_persisted_with_vietnamese_message_and_suggestions(self) -> None:
        """Verify blocked runs are persisted with status='error' and a blocked trace step."""
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            # Query asking for a period outside the fixture
            response = self.client.post(
                "/api/analyze",
                json={
                    "query": "Phân tích ROE của ACB năm 2030",
                    "target_ticker": "ACB",
                    "period": "2030_Q1",
                },
            )
            self.assertEqual(response.status_code, 200)
            report = response.json()
            self.assertEqual(report["status"], "error")
            report_id = report["report_id"]

            # Error info in report
            self.assertIn("error", report)
            self.assertEqual(report["error"]["code"], "unsupported_period")
            self.assertTrue(report["error"]["message"])
            self.assertIsInstance(report["error"]["suggestions"], list)

            # Verify persisted in database
            run_record = get_analysis_run(self.runs_path, report_id)
            self.assertIsNotNone(run_record)
            self.assertEqual(run_record["status"], "error")
            self.assertEqual(run_record["error_code"], "unsupported_period")

            # Verify trace endpoint
            trace_res = self.client.get(f"/api/runs/{report_id}/trace")
            self.assertEqual(trace_res.status_code, 200)
            trace = trace_res.json()
            self.assertEqual(trace["status"], "error")
            self.assertEqual(len(trace["steps"]), 1)
            blocked_step = trace["steps"][0]
            self.assertEqual(blocked_step["kind"], "blocked")
            self.assertEqual(blocked_step["actor"], "system")
            self.assertEqual(blocked_step["detail"]["code"], "unsupported_period")
            self.assertTrue(blocked_step["summary"])

    def test_get_run_trace_endpoint_200_and_404(self) -> None:
        """Verify GET /api/runs/{id}/trace returns 200 for existing run, 404 for missing."""
        # Non-existent run
        res = self.client.get("/api/runs/run-non-existent-9999/trace")
        self.assertEqual(res.status_code, 404)
        self.assertIn("detail", res.json())

        # Existing run
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            analyze_res = self.client.post(
                "/api/analyze",
                json={"query": "Phân tích ACB 2024", "target_ticker": "ACB", "period": "2024_Q4"},
            )
            run_id = analyze_res.json()["report_id"]
            trace_res = self.client.get(f"/api/runs/{run_id}/trace")
            self.assertEqual(trace_res.status_code, 200)
            data = trace_res.json()
            self.assertEqual(data["run_id"], run_id)
            self.assertIsInstance(data["steps"], list)

    def test_idempotent_schema_migration(self) -> None:
        """Verify ensure_analysis_runs_table idempotently upgrades legacy tables without data loss."""
        migration_db = Path(self.directory.name) / "legacy_migration.sqlite"
        conn = sqlite3.connect(migration_db)
        try:
            # Create legacy schema without ER-5 columns
            conn.execute("""
                CREATE TABLE analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    query TEXT NOT NULL,
                    target_ticker TEXT NOT NULL,
                    peer_tickers TEXT,
                    period TEXT NOT NULL,
                    status TEXT NOT NULL,
                    report_json TEXT,
                    events_json TEXT,
                    model_used TEXT,
                    latency_ms INTEGER
                );
            """)
            conn.execute("""
                INSERT INTO analysis_runs (
                    run_id, created_at, query, target_ticker, peer_tickers, period, status, report_json
                ) VALUES (
                    'legacy-run-1', '2026-09-01T00:00:00Z', 'Query test', 'ACB', '[]', '2024_Q4', 'completed', '{"report_id": "legacy-run-1"}'
                );
            """)
            conn.commit()
        finally:
            conn.close()

        # Run migration once
        ensure_analysis_runs_table(migration_db)

        # Verify new columns exist
        conn = sqlite3.connect(migration_db)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(analysis_runs);")
            columns = {row[1]: row[2] for row in cur.fetchall()}
            expected_new = [
                "trace_json", "error_code", "duration_ms", "model_calls",
                "input_tokens", "output_tokens", "arm", "question_type"
            ]
            for col in expected_new:
                self.assertIn(col, columns, f"Column {col} must exist after migration")

            # Verify existing data is preserved
            cur.execute("SELECT run_id, query, status, trace_json FROM analysis_runs WHERE run_id = 'legacy-run-1';")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "legacy-run-1")
            self.assertEqual(row[1], "Query test")
            self.assertEqual(row[2], "completed")
            self.assertIsNone(row[3])
        finally:
            conn.close()

        # Run migration a second time (idempotency check: must not raise error)
        ensure_analysis_runs_table(migration_db)

    def test_sse_stream_trace_steps_match_persisted_count(self) -> None:
        """Verify SSE stream emits TRACE_STEP events matching persisted trace steps count."""
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            res = self.client.post(
                "/api/analyze/stream",
                json={"query": "Phân tích ACB 2024", "target_ticker": "ACB", "period": "2024_Q4"},
            )
            self.assertEqual(res.status_code, 200)

            events: list[dict[str, Any]] = []
            for block in res.text.split("\n\n"):
                block = block.strip()
                if not block:
                    continue
                for line in block.split("\n"):
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

            trace_step_events = [e for e in events if e.get("type") == "TRACE_STEP"]
            self.assertGreater(len(trace_step_events), 0)

            # Verify TRACE_STEP appears before REPORT_READY
            types = [e.get("type") for e in events]
            last_trace_idx = max(i for i, t in enumerate(types) if t == "TRACE_STEP")
            report_ready_idx = types.index("REPORT_READY")
            self.assertLess(last_trace_idx, report_ready_idx)

            # Verify count matches persisted trace
            report_id = next(e["payload"]["reportId"] for e in events if e.get("type") == "REPORT_READY")
            persisted_trace = get_analysis_run_trace(self.runs_path, report_id)
            self.assertIsNotNone(persisted_trace)
            self.assertEqual(len(trace_step_events), len(persisted_trace["steps"]))

    def test_sse_stream_blocked_event_has_error_object(self) -> None:
        """Verify RUN_BLOCKED SSE event carries error object with code, message, and suggestions."""
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            res = self.client.post(
                "/api/analyze/stream",
                json={"query": "Phân tích ACB 2030", "target_ticker": "ACB", "period": "2030_Q1"},
            )
            self.assertEqual(res.status_code, 200)

            events: list[dict[str, Any]] = []
            for block in res.text.split("\n\n"):
                block = block.strip()
                if not block:
                    continue
                for line in block.split("\n"):
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

            blocked_event = next((e for e in events if e.get("type") == "RUN_BLOCKED"), None)
            self.assertIsNotNone(blocked_event)
            payload = blocked_event["payload"]
            self.assertIn("error", payload)
            err = payload["error"]
            self.assertEqual(err["code"], "unsupported_period")
            self.assertTrue(err["message"])
            self.assertIsInstance(err["suggestions"], list)

    def test_privacy_and_security_no_prompts_or_reasoning_in_trace(self) -> None:
        """Verify recursively that no trace steps contain prompt, instructions, or reasoning keys."""
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            res = self.client.post(
                "/api/analyze",
                json={"query": "Phân tích ACB 2024", "target_ticker": "ACB", "period": "2024_Q4"},
            )
            report_id = res.json()["report_id"]
            trace = self.client.get(f"/api/runs/{report_id}/trace").json()

        forbidden_keys = {
            "prompt", "instructions", "raw_output", "reasoning",
            "system_prompt", "user_prompt", "secret", "password", "api_key"
        }

        def assert_no_forbidden(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    k_lower = str(k).lower()
                    for f in forbidden_keys:
                        self.assertNotIn(
                            f, k_lower,
                            f"Forbidden key '{f}' found in trace at {path}.{k}"
                        )
                    assert_no_forbidden(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    assert_no_forbidden(item, f"{path}[{idx}]")

        assert_no_forbidden(trace, "trace")

    def test_token_and_cost_tracking_exactness(self) -> None:
        """Verify token counts are extracted exactly from client response.usage and never estimated."""
        tracker = LLMUsageTracker()

        class FakeUsage:
            prompt_tokens = 120
            completion_tokens = 45

        class FakeResponseWithUsage:
            usage = FakeUsage()

        class FakeResponseWithoutUsage:
            usage = None

        class FakeClient:
            def __init__(self):
                self.calls = 0

            class Chat:
                class Completions:
                    @staticmethod
                    def create(*args, **kwargs):
                        return FakeResponseWithUsage()
                completions = Completions()

            chat = Chat()

        raw_client = FakeClient()
        wrapped = wrap_llm_client(raw_client, tracker, role_getter=lambda: "company")

        # Make call with usage
        wrapped.chat.completions.create(model="test", messages=[])
        self.assertEqual(tracker.model_calls, 1)
        self.assertEqual(tracker.total_input_tokens, 120)
        self.assertEqual(tracker.total_output_tokens, 45)

        # Make call without usage
        class FakeClientNoUsage:
            class Chat:
                class Completions:
                    @staticmethod
                    def create(*args, **kwargs):
                        return FakeResponseWithoutUsage()
                completions = Completions()
            chat = Chat()

        tracker_no_usage = LLMUsageTracker()
        wrapped_no_usage = wrap_llm_client(FakeClientNoUsage(), tracker_no_usage, role_getter=lambda: "company")
        wrapped_no_usage.chat.completions.create(model="test", messages=[])
        self.assertEqual(tracker_no_usage.model_calls, 1)
        # MUST BE None, never estimated!
        self.assertIsNone(tracker_no_usage.total_input_tokens)
        self.assertIsNone(tracker_no_usage.total_output_tokens)


if __name__ == "__main__":
    unittest.main()
