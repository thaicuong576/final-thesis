"""Offline tests for private Supabase Storage analysis run history persistence and hydration."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from fastapi.testclient import TestClient
from pydantic import SecretStr

try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


from thesis_api.main import create_app
from thesis_api.run_history_storage import (
    download_run_record,
    get_remote_prefix,
    get_run_object_path,
    hydrate_run_history,
    is_remote_run_history_configured,
    list_remote_runs,
    upload_run_to_storage,
    wait_for_pending_uploads,
)
from thesis_api.settings import Settings
from test_api_analyze import (
    _ExplicitOfflineAcceptingCritic,
    _ExplicitOfflineAnalysisWriter,
    _gold_fixture,
)


class _FakeResponse:
    def __init__(self, payload: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._payload = payload
        self.status = status
        self._offset = 0
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class FakeSupabaseStorageRouter:
    """In-memory mock router for Supabase Storage REST API."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.upload_calls: list[dict[str, object]] = []
        self.list_calls: list[dict[str, object]] = []
        self.download_calls: list[dict[str, object]] = []
        self.should_fail_upload = False
        self.upload_error: Exception | None = None

    def handle(self, request: Request, timeout: float = 10.0):
        url = request.full_url
        method = request.get_method()

        # 1. Handle list: POST /storage/v1/object/list/{bucket}
        if "/storage/v1/object/list/" in url and method == "POST":
            body = json.loads(request.data.decode("utf-8")) if request.data else {}
            self.list_calls.append({"url": url, "body": body})
            prefix = body.get("prefix", "").strip("/")
            limit = body.get("limit", 500)

            matching = []
            for path, data in self.objects.items():
                if prefix and not path.startswith(f"{prefix}/"):
                    continue
                filename = path.rsplit("/", 1)[-1]
                matching.append(
                    {
                        "name": filename,
                        "id": path,
                        "created_at": "2026-09-30T10:00:00Z",
                        "metadata": {"size": len(data)},
                    }
                )
            matching = matching[:limit]
            return _FakeResponse(json.dumps(matching).encode("utf-8"), status=200)

        # 2. Handle upload: POST /storage/v1/object/{bucket}/{object_path}
        if "/storage/v1/object/" in url and method == "POST":
            if self.should_fail_upload:
                if self.upload_error:
                    raise self.upload_error
                raise HTTPError(url, 500, "Internal Server Error", {}, None)

            parts = url.split("/storage/v1/object/")[1].split("/", 1)
            bucket = parts[0]
            obj_path = parts[1] if len(parts) > 1 else ""
            data = request.data or b""
            self.objects[obj_path] = data
            self.upload_calls.append(
                {
                    "url": url,
                    "bucket": bucket,
                    "path": obj_path,
                    "headers": dict(request.headers),
                    "data": data,
                }
            )
            return _FakeResponse(b'{"message": "Successfully uploaded"}', status=200)

        # 3. Handle download: GET /storage/v1/object/{bucket}/{object_path}
        if "/storage/v1/object/" in url and method == "GET":
            parts = url.split("/storage/v1/object/")[1].split("/", 1)
            bucket = parts[0]
            obj_path = parts[1] if len(parts) > 1 else ""
            self.download_calls.append({"url": url, "bucket": bucket, "path": obj_path})
            if obj_path in self.objects:
                return _FakeResponse(self.objects[obj_path], status=200)
            raise HTTPError(url, 404, "Not Found", {}, None)

        raise ValueError(f"Unhandled fake request: {method} {url}")


class RunHistoryStorageTests(unittest.TestCase):
    """Test suite verifying run history persistence to and hydration from Supabase Storage."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = _gold_fixture(Path(self.temp_dir.name) / "test_gold.sqlite")
        self.runs_path = Path(self.temp_dir.name) / "analysis_runs.sqlite"
        self.router = FakeSupabaseStorageRouter()

    def tearDown(self) -> None:
        wait_for_pending_uploads(timeout=2.0)
        self.temp_dir.cleanup()

    def _configured_settings(self, runs_path: Path | None = None) -> Settings:
        import hashlib
        expected_sha = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        return Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(runs_path or self.runs_path),
            openai_api_key="test-key",
            planner_mode="rules_only",
            supabase_url="https://test.supabase.co",
            supabase_storage_bucket="thesis-snapshots",
            supabase_storage_object="gold-snapshot.sqlite",
            supabase_service_role_key=SecretStr("mock-service-role-key-test"),
            expected_dataset_snapshot_id="gold-snapshot-api-fixture",
            expected_sqlite_sha256=expected_sha,
            run_history_remote_prefix="run-history/",
        )

    def test_configuration_helpers(self) -> None:
        configured = self._configured_settings()
        self.assertTrue(is_remote_run_history_configured(configured))
        self.assertEqual(get_remote_prefix(configured), "run-history")
        self.assertEqual(get_run_object_path("run_abc", configured), "run-history/run_abc.json")

        unconfigured = Settings(
            app_name="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(self.runs_path),
        )
        self.assertFalse(is_remote_run_history_configured(unconfigured))

    @patch("thesis_api.run_history_storage.urlopen")
    def test_end_to_end_persist_and_hydrate_after_restart(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = self.router.handle
        settings = self._configured_settings()

        app = create_app(
            settings,
            analysis_writer=_ExplicitOfflineAnalysisWriter(),
            semantic_critic=_ExplicitOfflineAcceptingCritic(),
        )

        with TestClient(app) as client:
            resp = client.post("/api/analyze", json={"query": "Phân tích ACB trong năm 2024"})
            self.assertEqual(resp.status_code, 200, resp.text)
            report_data = resp.json()
            run_id = report_data["report_id"]

        wait_for_pending_uploads(timeout=5.0)

        # 1. Verify upload took place to fake Supabase Storage
        expected_path = f"run-history/{run_id}.json"
        self.assertIn(expected_path, self.router.objects)
        uploaded_record = json.loads(self.router.objects[expected_path].decode("utf-8"))
        self.assertEqual(uploaded_record["run_id"], run_id)
        self.assertEqual(uploaded_record["target_ticker"], "ACB")
        self.assertEqual(uploaded_record["status"], "completed")
        self.assertIn("report_json", uploaded_record)
        self.assertIn("trace_json", uploaded_record)

        # Verify authorization headers were attached without leaking secret
        call = self.router.upload_calls[0]
        self.assertEqual(call["headers"]["Authorization"], "Bearer mock-service-role-key-test")
        self.assertEqual(call["headers"]["Apikey"], "mock-service-role-key-test")
        self.assertEqual(call["headers"]["X-upsert"], "true")

        # 2. Simulate server cold start / ephemeral restart:
        # Create a completely fresh, separate directory with an uncreated SQLite runs path
        with tempfile.TemporaryDirectory() as fresh_tmp:
            fresh_runs_path = Path(fresh_tmp) / "fresh_analysis_runs.sqlite"
            self.assertFalse(fresh_runs_path.exists())

            restarted_settings = self._configured_settings(runs_path=fresh_runs_path)
            restarted_app = create_app(
                restarted_settings,
                analysis_writer=_ExplicitOfflineAnalysisWriter(),
                semantic_critic=_ExplicitOfflineAcceptingCritic(),
            )

            # Entering TestClient context invokes lifespan -> hydrates run history!
            with TestClient(restarted_app) as restarted_client:
                # GET /api/runs (Report Library)
                runs_resp = restarted_client.get("/api/runs")
                self.assertEqual(runs_resp.status_code, 200)
                runs_list = runs_resp.json()
                self.assertGreaterEqual(len(runs_list), 1)
                self.assertEqual(runs_list[0]["run_id"], run_id)
                self.assertEqual(runs_list[0]["target_ticker"], "ACB")

                # GET /api/analysis-runs (Alias)
                alias_resp = restarted_client.get("/api/analysis-runs")
                self.assertEqual(alias_resp.status_code, 200)
                self.assertEqual(alias_resp.json()[0]["run_id"], run_id)

                # GET /api/runs/{run_id} (Full run detail)
                detail_resp = restarted_client.get(f"/api/runs/{run_id}")
                self.assertEqual(detail_resp.status_code, 200)
                detail_data = detail_resp.json()
                self.assertEqual(detail_data["run_id"], run_id)
                self.assertIsNotNone(detail_data["report"])

                # GET /api/runs/{run_id}/trace (Trace steps)
                trace_resp = restarted_client.get(f"/api/runs/{run_id}/trace")
                self.assertEqual(trace_resp.status_code, 200)
                trace_data = trace_resp.json()
                self.assertEqual(trace_data["run_id"], run_id)
                self.assertIn("steps", trace_data)

                # GET /api/reports/{run_id} (Report artifact)
                rep_resp = restarted_client.get(f"/api/reports/{run_id}")
                self.assertEqual(rep_resp.status_code, 200)
                self.assertEqual(rep_resp.json()["report_id"], run_id)

    @patch("thesis_api.run_history_storage.urlopen")
    def test_blocked_run_is_persisted_and_hydrated(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = self.router.handle
        settings = self._configured_settings()

        app = create_app(
            settings,
            analysis_writer=_ExplicitOfflineAnalysisWriter(),
            semantic_critic=_ExplicitOfflineAcceptingCritic(),
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/analyze",
                json={"query": "Analyze ROE of XYZ", "target_ticker": "XYZ", "period": "2024_Q4"},
            )
            self.assertEqual(resp.status_code, 200)
            report_data = resp.json()
            self.assertEqual(report_data["status"], "error")
            run_id = report_data["report_id"]

        wait_for_pending_uploads(timeout=5.0)

        expected_path = f"run-history/{run_id}.json"
        self.assertIn(expected_path, self.router.objects)
        uploaded = json.loads(self.router.objects[expected_path].decode("utf-8"))
        self.assertEqual(uploaded["status"], "error")

        # Hydrate into clean store
        with tempfile.TemporaryDirectory() as fresh_tmp:
            fresh_runs_path = Path(fresh_tmp) / "fresh_analysis_runs.sqlite"
            restarted_settings = self._configured_settings(runs_path=fresh_runs_path)
            restarted_app = create_app(
                restarted_settings,
                analysis_writer=_ExplicitOfflineAnalysisWriter(),
            )
            with TestClient(restarted_app) as restarted_client:
                runs_resp = restarted_client.get("/api/runs")
                self.assertEqual(runs_resp.status_code, 200)
                runs = runs_resp.json()
                self.assertEqual(runs[0]["run_id"], run_id)
                self.assertEqual(runs[0]["status"], "error")

    @patch("thesis_api.run_history_storage.urlopen")
    def test_unconfigured_supabase_retains_local_only_behavior(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = self.router.handle
        unconfigured_settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(self.runs_path),
            openai_api_key="test-key",
            planner_mode="rules_only",
        )

        app = create_app(
            unconfigured_settings,
            analysis_writer=_ExplicitOfflineAnalysisWriter(),
            semantic_critic=_ExplicitOfflineAcceptingCritic(),
        )

        with TestClient(app) as client:
            # /api/ready remains healthy
            ready_resp = client.get("/api/ready")
            self.assertEqual(ready_resp.status_code, 200)

            resp = client.post("/api/analyze", json={"query": "Phân tích ACB trong năm 2024"})
            self.assertEqual(resp.status_code, 200)

        wait_for_pending_uploads(timeout=2.0)
        self.assertEqual(len(self.router.upload_calls), 0)
        self.assertEqual(len(self.router.objects), 0)

        # Local SQLite still has the run
        conn = sqlite3.connect(self.runs_path)
        count = conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    @patch("thesis_api.run_history_storage.urlopen")
    def test_upload_failure_does_not_fail_request(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = self.router.handle
        self.router.should_fail_upload = True
        self.router.upload_error = HTTPError("url", 500, "Storage Down", {}, None)

        settings = self._configured_settings()
        app = create_app(
            settings,
            analysis_writer=_ExplicitOfflineAnalysisWriter(),
            semantic_critic=_ExplicitOfflineAcceptingCritic(),
        )

        with TestClient(app) as client:
            resp = client.post("/api/analyze", json={"query": "Phân tích ACB trong năm 2024"})
            self.assertEqual(resp.status_code, 200)

        wait_for_pending_uploads(timeout=2.0)

        # Local SQLite run was still stored successfully despite remote upload failure
        conn = sqlite3.connect(self.runs_path)
        count = conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_safety_invariants(self) -> None:
        settings = self._configured_settings()

        # 1. Invariant: Refuse hydration into Gold snapshot
        with self.assertRaises(ValueError):
            hydrate_run_history(self.db_path, settings)

        # 2. Invariant: Refuse run history path that collides with snapshot object
        settings_collision = Settings(
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(self.runs_path),
            supabase_url="https://test.supabase.co",
            supabase_storage_bucket="thesis-snapshots",
            supabase_storage_object="run-history/collision.json",
            supabase_service_role_key=SecretStr("mock-key"),
            run_history_remote_prefix="run-history/",
        )
        with self.assertRaises(ValueError):
            get_run_object_path("collision", settings_collision)

        # 3. Invariant: Refuse .sqlite extension for run objects
        with self.assertRaises(ValueError):
            get_run_object_path("invalid.sqlite", settings)

        # 4. Invariant: download_run_record refuses snapshot object
        self.assertIsNone(download_run_record("gold-snapshot.sqlite", settings))

    @patch("thesis_api.run_history_storage.urlopen")
    def test_idempotent_hydration_skips_already_cached_runs(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = self.router.handle
        settings = self._configured_settings()

        # Seed router with 2 run objects
        for rid in ("run_01", "run_02"):
            rec = {
                "run_id": rid,
                "created_at": "2026-09-30T10:00:00Z",
                "query": "test query",
                "target_ticker": "ACB",
                "period": "2024",
                "status": "completed",
            }
            upload_run_to_storage(rec, settings)

        self.assertEqual(len(self.router.objects), 2)

        # First hydration: downloads both runs
        hydrated_first = hydrate_run_history(self.runs_path, settings)
        self.assertEqual(hydrated_first, 2)
        downloads_first = len(self.router.download_calls)
        self.assertEqual(downloads_first, 2)

        # Second hydration: both runs already present in SQLite -> 0 downloads needed!
        hydrated_second = hydrate_run_history(self.runs_path, settings)
        self.assertEqual(hydrated_second, 0)
        self.assertEqual(len(self.router.download_calls), downloads_first)


if __name__ == "__main__":
    unittest.main()
