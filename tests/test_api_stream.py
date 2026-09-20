"""Integration tests for POST /api/analyze/stream SSE endpoint and Query-Adaptive execution."""

from __future__ import annotations

import json
import unittest
from fastapi.testclient import TestClient

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisResponse, AnalysisSessionEventDTO, ObservableActivityDTO
from thesis_api.settings import Settings


class ApiStreamIntegrationTests(unittest.TestCase):
    """Test suite verifying /api/analyze/stream endpoint and query-adaptive execution."""

    def setUp(self) -> None:
        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path="data/processed/finance_master_v2.sqlite",
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def _parse_sse_events(self, text: str) -> list[tuple[str, dict]]:
        """Parse raw SSE text into list of (event_type, payload_dict) tuples and validate schema."""
        raw_blocks = [b.strip() for b in text.strip().split("\n\n") if b.strip()]
        events = []
        for block in raw_blocks:
            event_type = None
            event_data = None
            for line in block.split("\n"):
                if line.startswith("event:"):
                    event_type = line.split("event:", 1)[1].strip()
                elif line.startswith("data:"):
                    raw_data = line.split("data:", 1)[1].strip()
                    event_data = json.loads(raw_data)

            self.assertIsNotNone(event_type, f"Missing event type in SSE block:\n{block}")
            self.assertIsNotNone(event_data, f"Missing data in SSE block:\n{block}")

            # Verify 100% adherence to AnalysisSessionEventDTO schema
            dto = AnalysisSessionEventDTO.model_validate(event_data)
            self.assertEqual(dto.type, event_type)
            self.assertIsNotNone(dto.event_id)
            self.assertGreater(dto.sequence, 0)
            self.assertGreaterEqual(dto.occurred_at_ms, 0)

            events.append((event_type, event_data))

        return events

    def test_stream_company_only_adaptive_gating(self) -> None:
        """Solo query should only invoke company specialist, omitting macro and sector."""
        payload = {
            "query": "Phân tích sức khỏe tài chính và các chỉ tiêu CAMEL của ACB năm 2024",
            "target_ticker": "ACB",
            "peer_tickers": [],
            "period": "2024",
        }
        response = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertEqual(response.headers.get("cache-control"), "no-cache")
        self.assertEqual(response.headers.get("x-accel-buffering"), "no")

        events = self._parse_sse_events(response.text)
        self.assertGreaterEqual(len(events), 10)

        # Verify consecutive sequence numbering
        sequences = [e[1]["sequence"] for e in events]
        self.assertEqual(sequences, list(range(1, len(events) + 1)))

        # Verify lifecycle event progression
        event_types = [e[0] for e in events]
        self.assertEqual(event_types[0], "USER_REQUEST_CONFIRMED")
        self.assertEqual(event_types[1], "PLANNING_STARTED")
        self.assertEqual(event_types[2], "PLAN_CREATED")
        self.assertIn("REVIEW_STARTED", event_types)
        self.assertIn("SYNTHESIS_STARTED", event_types)
        self.assertIn("SYNTHESIS_COMPLETED", event_types)
        self.assertEqual(event_types[-1], "REPORT_READY")

        # Verify query-adaptive capability gating
        invocations = [
            e[1]["payload"]["specialistId"]
            for e in events
            if e[0] == "SPECIALIST_INVOKED"
        ]
        self.assertEqual(invocations, ["company"])
        self.assertNotIn("macro", invocations)
        self.assertNotIn("sector", invocations)

        # No revision events for standard solo query
        self.assertNotIn("REVIEW_FEEDBACK_CREATED", event_types)
        self.assertNotIn("REVISION_REQUESTED", event_types)

        # Verify final report artifact in REPORT_READY
        report_ready_payload = events[-1][1]["payload"]
        self.assertIn("reportId", report_ready_payload)
        self.assertIn("report", report_ready_payload)

        report = report_ready_payload["report"]
        validated_report = AnalysisResponse.model_validate(report)
        self.assertEqual(validated_report.status, "completed")
        self.assertIsNone(validated_report.macro_context)
        self.assertIsNone(validated_report.sector_benchmark)
        self.assertEqual(validated_report.analysis_plan.required_capabilities, ["company"])
        self.assertEqual(validated_report.analysis_plan.applicable_links, [])
        self.assertGreater(len(validated_report.limitations), 0)
        self.assertEqual(validated_report.revision_summary.rounds_executed, 0)
        self.assertEqual(validated_report.revision_summary.status, "passed")

    def test_stream_peer_comparison_adaptive_gating(self) -> None:
        """Peer comparison query should activate company and sector capabilities."""
        payload = {
            "query": "So sánh hiệu quả hoạt động (ROE, NIM) và rủi ro nợ xấu (NPL) giữa ACB và TCB năm 2024",
            "target_ticker": "ACB",
            "peer_tickers": ["TCB", "MBB"],
            "period": "2024",
        }
        response = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

        events = self._parse_sse_events(response.text)
        invocations = [
            e[1]["payload"]["specialistId"]
            for e in events
            if e[0] == "SPECIALIST_INVOKED"
        ]
        self.assertIn("company", invocations)
        self.assertIn("sector", invocations)
        self.assertNotIn("macro", invocations)

        report_ready_payload = events[-1][1]["payload"]
        report = report_ready_payload["report"]
        validated_report = AnalysisResponse.model_validate(report)
        self.assertIsNone(validated_report.macro_context)
        self.assertIsNotNone(validated_report.sector_benchmark)
        self.assertIn("company", validated_report.analysis_plan.required_capabilities)
        self.assertIn("sector", validated_report.analysis_plan.required_capabilities)
        self.assertIn("peer_comparison", validated_report.analysis_plan.applicable_links)
        self.assertGreaterEqual(len(validated_report.company_insights), 2)

    def test_stream_full_hierarchical_with_revision_cycle(self) -> None:
        """Full hierarchical query activates macro, sector, company, and triggers revision cycle."""
        payload = {
            "query": "Đánh giá toàn diện tác động chính sách tiền tệ NHNN đến NIM và nợ xấu (NPL) của ACB và TCB năm 2024",
            "target_ticker": "ACB",
            "peer_tickers": ["TCB", "MBB"],
            "period": "2024",
        }
        response = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

        events = self._parse_sse_events(response.text)
        event_types = [e[0] for e in events]

        # Verify all 3 specialists invoked
        invocations = [
            e[1]["payload"]["specialistId"]
            for e in events
            if e[0] == "SPECIALIST_INVOKED"
        ]
        self.assertEqual(set(invocations), {"macro", "sector", "company"})

        # Verify revision lifecycle events
        self.assertIn("REVIEW_FEEDBACK_CREATED", event_types)
        self.assertIn("REVISION_REQUESTED", event_types)
        self.assertIn("REVISION_ACTIVITY", event_types)
        self.assertIn("REVISION_COMPLETED", event_types)

        # Check revision payload structure
        rev_req = next(e[1]["payload"] for e in events if e[0] == "REVISION_REQUESTED")
        self.assertEqual(rev_req["round"], 1)
        self.assertEqual(rev_req["maxRounds"], 2)
        self.assertIn("reason", rev_req)

        # Verify report artifact
        report_ready_payload = events[-1][1]["payload"]
        report = report_ready_payload["report"]
        validated_report = AnalysisResponse.model_validate(report)
        self.assertIsNotNone(validated_report.macro_context)
        self.assertIsNotNone(validated_report.sector_benchmark)
        self.assertEqual(validated_report.revision_summary.rounds_executed, 1)
        self.assertEqual(validated_report.revision_summary.status, "revised_and_passed")
        self.assertEqual(validated_report.revision_summary.revised_capabilities, ["company"])
        self.assertGreaterEqual(len(validated_report.atomic_claims), 2)

    def test_stream_observable_activities_and_artifacts(self) -> None:
        """Validate ObservableActivityDTO and specialist output artifacts adhere to contracts."""
        payload = {
            "query": "Phân tích tài chính ACB năm 2024",
        }
        response = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(response.status_code, 200)

        events = self._parse_sse_events(response.text)

        # Check activity events
        activity_events = [e for e in events if e[0] == "SPECIALIST_ACTIVITY"]
        self.assertGreaterEqual(len(activity_events), 1)
        for _, event_data in activity_events:
            activity_dict = event_data["payload"]["activity"]
            activity_dto = ObservableActivityDTO.model_validate(activity_dict)
            self.assertIsNotNone(activity_dto.id)
            self.assertIn(activity_dto.type, ["DATA_RETRIEVAL", "VALIDATION", "INSIGHT_GENERATION", "REVISION"])

        # Check output created events
        output_events = [e for e in events if e[0] == "SPECIALIST_OUTPUT_CREATED"]
        self.assertGreaterEqual(len(output_events), 1)
        for _, event_data in output_events:
            artifact = event_data["payload"]["artifact"]
            self.assertIn("headline", artifact)
            self.assertIsInstance(artifact["findings"], list)
            self.assertGreaterEqual(artifact["evidenceCount"], 1)
            self.assertGreaterEqual(artifact["version"], 1)


if __name__ == "__main__":
    unittest.main()
