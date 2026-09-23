"""Integration tests for analysis_runs persistence and API endpoints."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
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


class AnalysisRunsApiTests(unittest.TestCase):
    """Test suite verifying analysis_runs persistence, querying, and API endpoints."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_finance.sqlite"

        source_db = Path("data/processed/finance_master_v2.sqlite")
        if source_db.exists():
            import shutil
            shutil.copyfile(source_db, self.db_path)
        else:
            ensure_analysis_runs_table(self.db_path)

        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_database_functions_crud(self) -> None:
        ensure_analysis_runs_table(self.db_path)
        runs_empty = list_analysis_runs(self.db_path)
        initial_count = len(runs_empty)

        save_analysis_run(
            db_path=self.db_path,
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

        runs = list_analysis_runs(self.db_path)
        self.assertEqual(len(runs), initial_count + 1)
        self.assertEqual(runs[0]["run_id"], "run-test-123")
        self.assertEqual(runs[0]["target_ticker"], "ACB")

        run_detail = get_analysis_run(self.db_path, "run-test-123")
        self.assertIsNotNone(run_detail)
        self.assertEqual(run_detail["query"], "Phan tich ACB 2024")
        self.assertEqual(run_detail["report"]["report_id"], "rep-test-123")
        self.assertEqual(len(run_detail["events"]), 1)

        report = get_analysis_report(self.db_path, "run-test-123")
        self.assertIsNotNone(report)
        self.assertEqual(report["report_id"], "rep-test-123")

        report_by_rep_id = get_analysis_report(self.db_path, "rep-test-123")
        self.assertIsNotNone(report_by_rep_id)

    def test_get_runs_endpoint(self) -> None:
        save_analysis_run(
            db_path=self.db_path,
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

    def test_get_run_by_id_endpoint_and_404(self) -> None:
        save_analysis_run(
            db_path=self.db_path,
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
            db_path=self.db_path,
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
        stream_res = self.client.post(
            "/api/analyze/stream",
            json={"query": "Danh gia ACB va MBB 2024", "target_ticker": "ACB", "peer_tickers": ["MBB"]},
        )
        self.assertEqual(stream_res.status_code, 200)

        runs = self.client.get("/api/runs").json()
        self.assertGreaterEqual(len(runs), 1)
        acb_runs = [r for r in runs if r["target_ticker"] == "ACB"]
        self.assertGreaterEqual(len(acb_runs), 1)


if __name__ == "__main__":
    unittest.main()
