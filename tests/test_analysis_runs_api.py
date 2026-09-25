"""Integration tests for analysis_runs persistence and API endpoints."""

from __future__ import annotations

import tempfile
import unittest
import sqlite3
import hashlib
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from thesis_api.main import create_app
from thesis_api.settings import Settings
from thesis_api.database import (
    ensure_analysis_runs_table,
    save_analysis_run,
    list_analysis_runs,
    get_analysis_run,
    get_analysis_report,
)
from test_api_analyze import _ExplicitOfflineAcceptingCritic, _ExplicitOfflineAnalysisWriter, _fixture_provider_binding, _gold_fixture


class AnalysisRunsApiTests(unittest.TestCase):
    """Test suite verifying analysis_runs persistence, querying, and API endpoints."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = _gold_fixture(Path(self.temp_dir.name) / "test_finance.sqlite")
        self.runs_path = Path(self.temp_dir.name) / "analysis-runs.sqlite"

        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(self.runs_path),
            openai_api_key="test-key",
        )
        self.app = create_app(self.settings, analysis_writer=_ExplicitOfflineAnalysisWriter())
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_database_functions_crud(self) -> None:
        ensure_analysis_runs_table(self.runs_path)
        runs_empty = list_analysis_runs(self.runs_path)
        initial_count = len(runs_empty)

        save_analysis_run(
            db_path=self.runs_path,
            run_id="run-test-123",
            created_at="2026-09-23T12:00:00Z",
            query="Phan tich ACB 2024",
            target_ticker="ACB",
            peer_tickers=["TCB", "MBB"],
            period="2024",
            status="completed",
            report_json={"report_id": "rep-test-123", "target_ticker": "ACB"},
            events_json=[{"type": "USER_REQUEST_CONFIRMED"}],
            model_used="test-model",
            latency_ms=120,
        )

        runs = list_analysis_runs(self.runs_path)
        self.assertEqual(len(runs), initial_count + 1)
        self.assertEqual(runs[0]["run_id"], "run-test-123")
        self.assertEqual(runs[0]["target_ticker"], "ACB")

        run_detail = get_analysis_run(self.runs_path, "run-test-123")
        self.assertIsNotNone(run_detail)
        self.assertEqual(run_detail["query"], "Phan tich ACB 2024")
        self.assertEqual(run_detail["report"]["report_id"], "rep-test-123")
        self.assertEqual(len(run_detail["events"]), 1)

        report = get_analysis_report(self.runs_path, "run-test-123")
        self.assertIsNotNone(report)
        self.assertEqual(report["report_id"], "rep-test-123")

        report_by_rep_id = get_analysis_report(self.runs_path, "rep-test-123")
        self.assertIsNotNone(report_by_rep_id)

    def test_get_runs_endpoint(self) -> None:
        save_analysis_run(
            db_path=self.runs_path,
            run_id="run-api-test-1",
            created_at="2026-09-23T12:00:00Z",
            query="Danh gia ACB va VCB",
            target_ticker="ACB",
            peer_tickers=["VCB"],
            period="2024",
            status="completed",
            report_json={"report_id": "rep-api-test-1"},
            events_json=[],
            model_used="deterministic",
            latency_ms=150,
        )

        res = self.client.get("/api/runs")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertIsInstance(items, list)
        self.assertTrue(any(r["run_id"] == "run-api-test-1" for r in items))

    def test_history_reads_do_not_create_tables_in_the_snapshot(self) -> None:
        before = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            exists_before = before.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='analysis_runs'"
            ).fetchone()
        finally:
            before.close()
        self.assertIsNone(exists_before)

        self.assertEqual(self.client.get("/api/runs").json(), [])
        self.assertEqual(self.client.get("/api/runs/not-present").status_code, 404)
        self.assertEqual(self.client.get("/api/reports/not-present").status_code, 404)

        after = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            exists_after = after.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='analysis_runs'"
            ).fetchone()
        finally:
            after.close()
        self.assertIsNone(exists_after)

    def test_get_run_by_id_endpoint_and_404(self) -> None:
        save_analysis_run(
            db_path=self.runs_path,
            run_id="run-api-test-2",
            created_at="2026-09-23T12:01:00Z",
            query="So sanh MBB va TCB",
            target_ticker="MBB",
            peer_tickers=["TCB"],
            period="2024",
            status="completed",
            report_json={"report_id": "rep-api-test-2", "summary": "OK"},
            events_json=[{"type": "PLANNING_STARTED"}],
            model_used="deterministic",
            latency_ms=200,
        )

        res = self.client.get("/api/runs/run-api-test-2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["run_id"], "run-api-test-2")
        self.assertEqual(data["report"]["summary"], "OK")
        self.assertEqual(len(data["events"]), 1)

        res_404 = self.client.get("/api/runs/non-existent-run")
        self.assertEqual(res_404.status_code, 404)

    def test_get_report_by_id_endpoint_and_404(self) -> None:
        save_analysis_run(
            db_path=self.runs_path,
            run_id="rep-api-test-3",
            created_at="2026-09-23T12:02:00Z",
            query="Danh gia ROE VCB",
            target_ticker="VCB",
            peer_tickers=[],
            period="2024",
            status="completed",
            report_json={"report_id": "rep-api-test-3", "status": "completed"},
            events_json=[],
            model_used="deterministic",
            latency_ms=100,
        )

        res = self.client.get("/api/reports/rep-api-test-3")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["report_id"], "rep-api-test-3")

        res_404 = self.client.get("/api/reports/unknown-report-xyz")
        self.assertEqual(res_404.status_code, 404)

    def test_analyze_stream_persists_run(self) -> None:
        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=_ExplicitOfflineAcceptingCritic(),
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            stream_res = self.client.post(
                "/api/analyze/stream",
                json={
                    "query": "Analyze ROE of ACB in 2024 Q4",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
        self.assertEqual(stream_res.status_code, 200)
        self.assertIn("REPORT_READY", stream_res.text)

        runs = self.client.get("/api/runs").json()
        self.assertGreaterEqual(len(runs), 1)
        acb_runs = [r for r in runs if r["target_ticker"] == "ACB"]
        self.assertGreaterEqual(len(acb_runs), 1)

    def test_sync_and_sse_persist_history_without_changing_accepted_snapshot(self) -> None:
        def digest(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        def schema(path: Path) -> list[tuple[str, str, str]]:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                return connection.execute(
                    "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
                ).fetchall()
            finally:
                connection.close()

        accepted_hash = digest(self.db_path)
        accepted_schema = schema(self.db_path)
        payload = {
            "query": "Analyze ROE of ACB in 2024 Q4",
            "target_ticker": "ACB",
            "period": "2024_Q4",
        }
        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=_ExplicitOfflineAcceptingCritic(),
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            first = self.client.post("/api/analyze", json=payload)
            second = self.client.post("/api/analyze", json=payload)
            streamed = self.client.post("/api/analyze/stream", json=payload)

        self.assertEqual(first.json()["status"], "completed", first.text)
        self.assertEqual(second.json()["status"], "completed", second.text)
        self.assertIn("REPORT_READY", streamed.text)
        self.assertNotIn("RUN_BLOCKED", streamed.text)
        self.assertEqual(digest(self.db_path), accepted_hash)
        self.assertEqual(schema(self.db_path), accepted_schema)
        runs = self.client.get("/api/runs").json()
        self.assertEqual(len(runs), 3)
        for run in runs:
            detail = self.client.get(f"/api/runs/{run['run_id']}")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()["report"]["status"], "completed")

    def test_persistence_failures_never_return_report_ready(self) -> None:
        payload = {
            "query": "Analyze ROE of ACB in 2024 Q4",
            "target_ticker": "ACB",
            "period": "2024_Q4",
        }
        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=_ExplicitOfflineAcceptingCritic(),
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ), patch(
            "thesis_api.service.save_analysis_run",
            side_effect=OSError("disk full"),
        ):
            sync = self.client.post("/api/analyze", json=payload)
            streamed = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(sync.json()["status"], "error")
        self.assertIn("analysis_run_persistence_failed", sync.json()["limitations"][0])
        self.assertNotIn("REPORT_READY", streamed.text)
        self.assertIn("RUN_BLOCKED", streamed.text)
        self.assertIn("analysis_run_persistence_failed", streamed.text)


if __name__ == "__main__":
    unittest.main()
