"""Unit and integration tests for thesis_api deployment shell."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from thesis_api.database import check_database_connection
from thesis_api.main import create_app
from thesis_api.settings import Settings


class ThesisApiTests(unittest.TestCase):
    """Test suite verifying FastAPI endpoints, security, and connectivity probes."""

    def setUp(self) -> None:
        self.settings = Settings(
            app_name="final-thesis-api",
            app_env="staging",
            database_url="postgresql://testuser:secretpassword@db.example.com:5432/testdb",
            cors_origins=["http://localhost:5173", "https://staging.final-thesis.vercel.app"],
            cors_origin_regex=r"https://.*final-thesis.*\.vercel\.app",
            app_revision="test-commit-sha-12345",
            openai_api_key="sk-mock-openai-secret-key",
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

    @patch("thesis_api.main.check_database_connection")
    def test_readiness_returns_200_when_database_connected(
        self,
        mock_check_db: unittest.mock.MagicMock,
    ) -> None:
        mock_check_db.return_value = (True, "Database connection healthy")
        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertEqual(data.get("database"), "connected")
        mock_check_db.assert_called_once_with(self.settings.database_url)

    @patch("thesis_api.main.check_database_connection")
    def test_readiness_returns_503_when_database_fails(
        self,
        mock_check_db: unittest.mock.MagicMock,
    ) -> None:
        mock_check_db.return_value = (False, "Database connectivity failed: ConnectionRefusedError")
        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unavailable")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertIn("ConnectionRefusedError", data.get("detail", ""))

    def test_readiness_returns_503_when_database_url_unconfigured(self) -> None:
        unconfigured_settings = Settings(database_url=None)
        unconfigured_app = create_app(unconfigured_settings)
        client = TestClient(unconfigured_app)

        response = client.get("/api/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unavailable")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertEqual(data.get("detail"), "DATABASE_URL is not configured")

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
