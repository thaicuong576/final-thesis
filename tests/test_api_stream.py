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
from test_api_analyze import _fixture_provider_binding, _gold_fixture


class ApiStreamIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = _gold_fixture(Path(self.directory.name) / "accepted-gold.sqlite")
        self.client = TestClient(
            create_app(Settings(app_env="test", sqlite_db_path=str(self.db_path)))
        )

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
                "REVIEW_STARTED",
                "SYNTHESIS_STARTED",
                "SYNTHESIS_COMPLETED",
                "REPORT_READY",
            ],
        )
        self.assertFalse(any("REVISION" in event for event in event_types))
        report = AnalysisResponse.model_validate(events[-1][1]["payload"]["report"])
        self.assertEqual(report.status, "partial")
        self.assertEqual(report.analysis_plan.required_capabilities, ["company"])
        self.assertIsNone(report.revision_summary)
        self.assertTrue(all(item.stage1_status == "accepted" for item in report.atomic_claims))
        streamed_report_json = events[-1][1]["payload"]["report"]
        self.assertNotIn("confidence", streamed_report_json["atomic_claims"][0])
        self.assertNotIn("stage2_critique_status", streamed_report_json["atomic_claims"][0])

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
        self.assertNotIn("stage2_critique_status", sync_json["atomic_claims"][0])

    def test_missing_snapshot_terminates_with_run_blocked(self) -> None:
        missing = Path(self.directory.name) / "missing.sqlite"
        client = TestClient(create_app(Settings(app_env="test", sqlite_db_path=str(missing))))
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
