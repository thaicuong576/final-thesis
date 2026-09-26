"""Unit and integration tests for thesis_api deployment shell."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thesis_api.database import check_database_connection
from thesis_api.main import create_app
from thesis_api.settings import Settings
from test_api_analyze import _fixture_provider_binding, _gold_fixture


class ThesisApiTests(unittest.TestCase):
    """Test suite verifying FastAPI endpoints, security, and connectivity probes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        missing_database = Path(self.temp_dir.name) / "not-configured.sqlite"
        self.settings = Settings(
            app_name="final-thesis-api",
            app_env="staging",
            database_url="postgresql://testuser:secretpassword@db.example.com:5432/testdb",
            cors_origins=["http://localhost:5173", "https://staging.final-thesis.vercel.app"],
            cors_origin_regex=r"https://.*final-thesis.*\.vercel\.app",
            app_revision="test-commit-sha-12345",
            openai_api_key="sk-mock-openai-secret-key",
            sqlite_db_path=str(missing_database),
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def test_health_returns_200_and_expected_payload(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "final-thesis-api")
        # Ensure health is cheap and contains no secrets
        self.assertNotIn("secret", response.text)
        self.assertNotIn("password", response.text)

    def test_version_returns_safe_metadata_and_no_secrets(self) -> None:
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("service"), "final-thesis-api")
        self.assertEqual(data.get("environment"), "staging")
        self.assertEqual(data.get("revision"), "test-commit-sha-12345")

        # Crucial security assertion: secrets must never leak in version metadata
        self.assertNotIn("secretpassword", response.text)
        self.assertNotIn("sk-mock-openai-secret-key", response.text)
        self.assertNotIn("database_url", data)
        self.assertNotIn("openai_api_key", data)

    def test_readiness_returns_200_when_accepted_snapshot_is_available(self) -> None:
        database = _gold_fixture(Path(self.temp_dir.name) / "accepted.sqlite")
        settings = Settings(
            app_env="test",
            sqlite_db_path=str(database),
            analysis_runs_db_path=str(Path(self.temp_dir.name) / "analysis-runs.sqlite"),
            openai_api_key="test-key",
            openai_base_url="https://example.test/v1",
            openai_model="test-model",
        )
        app = create_app(settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                response = client.get("/api/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertEqual(data.get("database"), "connected")

    def test_readiness_returns_503_when_accepted_snapshot_is_unavailable(self) -> None:
        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unavailable")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertIn("accepted", data.get("detail", "").casefold())

    def test_api_requires_explicit_accepted_snapshot_path(self) -> None:
        with patch.dict("os.environ", {"SQLITE_DB_PATH": ""}):
            settings = Settings(
                app_env="test",
                analysis_runs_db_path=str(Path(self.temp_dir.name) / "unconfigured-runs.sqlite"),
                openai_api_key="test-key",
            )
        app = create_app(settings)
        client = TestClient(app)
        with patch("thesis_api.service._load_provider") as load_provider:
            ready = client.get("/api/ready")
            analysis = client.post(
                "/api/analyze",
                json={
                    "query": "What is the return on equity for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
            stream = client.post(
                "/api/analyze/stream",
                json={
                    "query": "What is the return on equity for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
        self.assertEqual(ready.status_code, 503)
        self.assertEqual(ready.json()["status"], "unavailable")
        self.assertIsNone(ready.json()["dataset_snapshot_id"])
        self.assertIn("SQLITE_DB_PATH", ready.json()["detail"])
        self.assertEqual(analysis.json()["status"], "error")
        self.assertIn(
            "accepted_snapshot_path_unconfigured",
            analysis.json()["limitations"][0],
        )
        self.assertIn("event: RUN_BLOCKED", stream.text)
        self.assertNotIn("event: REPORT_READY", stream.text)
        load_provider.assert_not_called()
        client.close()

    def test_readiness_reports_connected_database_when_snapshot_is_not_runnable(self) -> None:
        database = _gold_fixture(
            Path(self.temp_dir.name) / "missing-locator.sqlite",
            include_metric_locators=False,
        )
        app = create_app(Settings(app_env="test", sqlite_db_path=str(database)))
        response = TestClient(app).get("/api/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unavailable")
        self.assertEqual(data.get("database"), "connected")
        self.assertEqual(data.get("dataset_snapshot_id"), "gold-snapshot-api-fixture")
        self.assertIn("not runnable", data.get("detail", "").casefold())

    def test_readiness_returns_503_when_database_url_unconfigured(self) -> None:
        unconfigured_settings = Settings(database_url=None)
        unconfigured_app = create_app(unconfigured_settings)
        client = TestClient(unconfigured_app)

        response = client.get("/api/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unavailable")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertIn("accepted", data.get("detail", "").casefold())

    def test_cors_headers_allowed_origin(self) -> None:
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.get("/api/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_preflight_options(self) -> None:
        headers = {
            "Origin": "https://staging.final-thesis.vercel.app",
            "Access-Control-Request-Method": "GET",
        }
        response = self.client.options("/api/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://staging.final-thesis.vercel.app",
        )

    def test_cors_custom_domain_allowed(self) -> None:
        default_settings = Settings()
        app = create_app(default_settings)
        client = TestClient(app)
        headers = {
            "Origin": "https://fin-ai.eddiephung.me",
            "Access-Control-Request-Method": "POST",
        }
        response = client.options("/api/analyze/stream", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://fin-ai.eddiephung.me",
        )

    def test_settings_cors_origins_parsing(self) -> None:
        # Comma-separated string
        s1 = Settings(CORS_ORIGINS="http://localhost:5173, https://example.com")
        self.assertEqual(s1.cors_origins, ["http://localhost:5173", "https://example.com"])

        # JSON list string
        s2 = Settings(CORS_ORIGINS='["http://localhost:5173", "https://example.com"]')
        self.assertEqual(s2.cors_origins, ["http://localhost:5173", "https://example.com"])

        # Empty string fallback
        s3 = Settings(CORS_ORIGINS="")
        self.assertEqual(s3.cors_origins, ["http://localhost:5173"])

    def test_settings_revision_fallback(self) -> None:
        # Explicit APP_REVISION
        s1 = Settings(APP_REVISION="sha-explicit", RENDER_GIT_COMMIT="sha-render")
        self.assertEqual(s1.get_revision(), "sha-explicit")

        # Fallback to RENDER_GIT_COMMIT
        s2 = Settings(APP_REVISION=None, RENDER_GIT_COMMIT="sha-render")
        self.assertEqual(s2.get_revision(), "sha-render")

        # Fallback to development
        s3 = Settings(APP_REVISION=None, RENDER_GIT_COMMIT=None)
        self.assertEqual(s3.get_revision(), "development")

    def test_database_probe_with_invalid_credentials_returns_false(self) -> None:
        # Non-routable or invalid database connection string should fail gracefully
        success, message = check_database_connection(
            "postgresql://invaliduser:invalidpass@127.0.0.1:59999/nonexistent",
            timeout_seconds=1,
        )
        self.assertFalse(success)
        self.assertIn("failed", message)
        # Ensure password is not present in message
        self.assertNotIn("invalidpass", message)


if __name__ == "__main__":
    unittest.main()
