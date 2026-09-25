"""Integration tests for honest SSE terminal and Stage-1 semantics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisResponse, AnalysisSessionEventDTO
from thesis_api.settings import Settings
from test_api_analyze import (
    _ExplicitOfflineAcceptingCritic,
    _ExplicitOfflineAnalysisWriter,
    _RevisionScenarioCritic,
    _fixture_provider_binding,
    _gold_fixture,
    _stage1_claim,
)


class ApiStreamIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = _gold_fixture(Path(self.directory.name) / "accepted-gold.sqlite")
        self.critic_factory_patch = patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=_ExplicitOfflineAcceptingCritic(),
        )
        self.critic_factory_patch.start()
        self.addCleanup(self.critic_factory_patch.stop)
        settings = Settings(
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(Path(self.directory.name) / "analysis-runs.sqlite"),
            openai_api_key="test-key",
        )
        self.client = TestClient(create_app(settings, analysis_writer=_ExplicitOfflineAnalysisWriter()))
        self.addCleanup(self.client.close)

    def _parse(self, response_text: str) -> list[tuple[str, dict]]:
        result = []
        for block in response_text.strip().split("\n\n"):
            event_type = next(line.removeprefix("event:").strip() for line in block.splitlines() if line.startswith("event:"))
            payload = json.loads(next(line.removeprefix("data:").strip() for line in block.splitlines() if line.startswith("data:")))
            dto = AnalysisSessionEventDTO.model_validate(payload)
            self.assertEqual(dto.type, event_type)
            result.append((event_type, payload))
        return result

    def test_company_stream_contains_only_actions_that_ran(self) -> None:
        payload = {
            "query": "Analyze ROE and NPL of ACB in 2024 Q4",
            "target_ticker": "ACB",
            "period": "2024_Q4",
        }
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            streamed = self.client.post("/api/analyze/stream", json=payload)
            sync_response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(streamed.status_code, 200)
        self.assertIn("text/event-stream", streamed.headers["content-type"])
        self.assertEqual(streamed.headers.get("cache-control"), "no-cache")
        self.assertEqual(streamed.headers.get("x-accel-buffering"), "no")

        events = self._parse(streamed.text)
        event_types = [item[0] for item in events]
        self.assertEqual(
            event_types,
            [
                "USER_REQUEST_CONFIRMED",
                "PLANNING_STARTED",
                "PLAN_CREATED",
                "SPECIALIST_INVOKED",
                "SPECIALIST_STARTED",
                "SPECIALIST_ACTIVITY",
                "SPECIALIST_OUTPUT_CREATED",
                "SPECIALIST_COMPLETED",
                "SYNTHESIS_STARTED",
                "REVIEW_STARTED",
                "REVIEW_FEEDBACK_CREATED",
                "SYNTHESIS_COMPLETED",
                "REPORT_READY",
            ],
        )
        self.assertFalse(any("REVISION" in event for event in event_types))
        report = AnalysisResponse.model_validate(events[-1][1]["payload"]["report"])
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.analysis_plan.required_capabilities, ["company"])
        self.assertEqual(report.revision_summary.status, "passed")
        self.assertTrue(all(item.stage1_status == "accepted" for item in report.atomic_claims))
        streamed_report_json = events[-1][1]["payload"]["report"]
        self.assertNotIn("confidence", streamed_report_json["atomic_claims"][0])
        self.assertEqual(streamed_report_json["atomic_claims"][0]["stage2_critique_status"], "sound")

        sync_json = sync_response.json()
        sync = AnalysisResponse.model_validate(sync_json)
        self.assertEqual(sync.status, report.status)
        self.assertEqual(sync.analysis_plan.required_capabilities, report.analysis_plan.required_capabilities)
        self.assertEqual(
            {(item.metric, item.period, item.stage1_status) for item in sync.atomic_claims},
            {(item.metric, item.period, item.stage1_status) for item in report.atomic_claims},
        )
        self.assertEqual(
            {(item.metric, tuple(item.evidence_refs)) for item in sync.atomic_claims},
            {(item.metric, tuple(item.evidence_refs)) for item in report.atomic_claims},
        )
        self.assertEqual(
            [item.model_dump() for item in sync.evidence_trail],
            [item.model_dump() for item in report.evidence_trail],
        )
        self.assertEqual(sync_json["analysis_plan"]["dataset_snapshot_id"], streamed_report_json["analysis_plan"]["dataset_snapshot_id"])
        self.assertNotIn("confidence", sync_json["atomic_claims"][0])
        self.assertEqual(sync_json["atomic_claims"][0]["stage2_critique_status"], "sound")

    def test_stream_emits_real_targeted_revision_transitions(self) -> None:
        critic = _RevisionScenarioCritic(resolve_after_revision=True)
        original_stage1_claim = _stage1_claim
        calls = 0

        def inject_one_narrative_defect(**kwargs):
            nonlocal calls
            calls += 1
            claim, *rest = original_stage1_claim(**kwargs)
            if calls == 1:
                claim = claim.model_copy(update={
                    "claim_text": "Test-injected wording defect requiring a company recheck."
                })
            return (claim, *rest)

        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=critic,
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ), patch(
            "thesis_api.service._stage1_claim",
            side_effect=inject_one_narrative_defect,
        ):
            response = self.client.post(
                "/api/analyze/stream",
                json={
                    "query": "What is the return on equity for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )

        events = self._parse(response.text)
        event_types = [kind for kind, _ in events]
        self.assertIn("REVISION_REQUESTED", event_types)
        self.assertIn("REVISION_ACTIVITY", event_types)
        self.assertIn("REVISION_COMPLETED", event_types)
        self.assertLess(event_types.index("REVISION_REQUESTED"), event_types.index("REVISION_COMPLETED"))
        self.assertLess(event_types.index("REVISION_COMPLETED"), event_types.index("REPORT_READY"))
        revision_payload = next(payload["payload"] for kind, payload in events if kind == "REVISION_REQUESTED")
        self.assertEqual(revision_payload["targetSpecialists"], ["company"])
        self.assertNotIn("Test-injected wording defect", response.text)
        self.assertNotIn("test-only-revision-scenario", response.text)
        report = AnalysisResponse.model_validate(events[-1][1]["payload"]["report"])
        self.assertEqual(report.revision_summary.status, "revised_and_passed")

    def test_missing_snapshot_terminates_with_run_blocked(self) -> None:
        missing = Path(self.directory.name) / "missing.sqlite"
        settings = Settings(
            app_env="test", sqlite_db_path=str(missing),
            analysis_runs_db_path=str(Path(self.directory.name) / "missing-runs.sqlite"),
            openai_api_key="test-key",
        )
        client = TestClient(create_app(settings, analysis_writer=_ExplicitOfflineAnalysisWriter()))
        response = client.post(
            "/api/analyze/stream",
            json={"query": "Analyze ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        events = self._parse(response.text)
        self.assertEqual(events[-1][0], "RUN_BLOCKED")
        self.assertIn("accepted_snapshot_unavailable", events[-1][1]["payload"]["reason"])
        self.assertEqual(events[-1][1]["payload"]["status"], "error")
        self.assertNotIn("REPORT_READY", [item[0] for item in events])
        self.assertFalse(missing.exists())

    def test_missing_metric_locator_blocks_sync_and_sse_consistently(self) -> None:
        payload = {
            "query": "Analyze ROE of ACB in 2024 Q4",
            "target_ticker": "ACB",
            "period": "2024_Q4",
        }
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=False),
        ):
            stream = self.client.post("/api/analyze/stream", json=payload)
            sync = self.client.post("/api/analyze", json=payload)
        events = self._parse(stream.text)
        self.assertEqual(events[-1][0], "RUN_BLOCKED")
        self.assertIn("observation_locator_missing", events[-1][1]["payload"]["reason"])
        self.assertNotIn("REPORT_READY", [item[0] for item in events])
        self.assertEqual(sync.json()["status"], "error")
        self.assertEqual(sync.json()["atomic_claims"], [])
        self.assertEqual(events[-1][1]["payload"]["status"], sync.json()["status"])

    def test_unsupported_macro_scope_is_blocked_without_claim_or_revision_events(self) -> None:
        response = self.client.post(
            "/api/analyze/stream",
            json={"query": "SBV policy rate effect on ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        events = self._parse(response.text)
        self.assertEqual(events[-1][0], "RUN_BLOCKED")
        self.assertIn("unsupported_macro_scope", events[-1][1]["payload"]["reason"])
        self.assertNotIn("REVISION_REQUESTED", [item[0] for item in events])
        self.assertNotIn("REPORT_READY", [item[0] for item in events])


if __name__ == "__main__":
    unittest.main()
