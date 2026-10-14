"""Unit and offline integration tests for shared-credential login gate (AUTH-1)."""

from __future__ import annotations

import logging
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


from thesis_api.auth import (
    AuthConfigurationError,
    InMemoryRateLimiter,
    create_access_token,
    default_rate_limiter,
    get_client_ip,
    is_public_path,
    verify_access_token,
    verify_credentials,
)
from thesis_api.main import create_app
from thesis_api.settings import Settings
from test_api_analyze import _fixture_provider_binding, _gold_fixture


class AuthApiTests(unittest.TestCase):
    """Test suite verifying shared-credential login gate, tokens, rate limits, and public path rules."""

    def setUp(self) -> None:
        default_rate_limiter.reset()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Generate unique throwaway test credentials for each test run
        self.test_user = "test_analyst_user"
        self.test_password = "throwaway_secret_password_12345"
        self.test_token_secret = "a" * 32  # 32 characters minimum secret
        self.test_db = _gold_fixture(Path(self.temp_dir.name) / "test_auth.sqlite")

        self.auth_enabled_settings = Settings(
            _env_file=None,
            app_env="test",
            SQLITE_DB_PATH=str(self.test_db),
            analysis_runs_db_path=str(Path(self.temp_dir.name) / "runs.sqlite"),
            planner_mode="rules_only",
            openai_api_key="test-key",
            openai_base_url="https://example.test/v1",
            openai_model="test-model",
            AUTH_ENABLED=True,
            APP_LOGIN_USER=self.test_user,
            APP_LOGIN_PASSWORD=self.test_password,
            AUTH_TOKEN_SECRET=self.test_token_secret,
            AUTH_TOKEN_TTL_HOURS=12,
        )

    def tearDown(self) -> None:
        default_rate_limiter.reset()

    def test_auth_disabled_by_default(self) -> None:
        """When AUTH_ENABLED=false, endpoints are unblocked and auth status reports required=false."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            SQLITE_DB_PATH=str(self.test_db),
            analysis_runs_db_path=str(Path(self.temp_dir.name) / "runs.sqlite"),
            planner_mode="rules_only",
            openai_api_key="test-key",
            openai_base_url="https://example.test/v1",
            openai_model="test-model",
            AUTH_ENABLED=False,
        )

        app = create_app(settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path, **kw: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                # Auth status endpoint
                status_res = client.get("/api/auth/status")
                self.assertEqual(status_res.status_code, 200)
                self.assertFalse(status_res.json()["required"])

                # Protected endpoint accessible without token
                cap_res = client.get("/api/capabilities")
                self.assertEqual(cap_res.status_code, 200)

                # Public endpoint
                ready_res = client.get("/api/ready")
                self.assertEqual(ready_res.status_code, 200)
                self.assertFalse(ready_res.json().get("auth_required"))

    def test_auth_enabled_status_endpoint(self) -> None:
        """When AUTH_ENABLED=true, GET /api/auth/status returns required=true without auth."""
        app = create_app(self.auth_enabled_settings)
        with TestClient(app) as client:
            res = client.get("/api/auth/status")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["required"])

    def test_auth_validation_fails_closed_on_missing_or_weak_configuration(self) -> None:
        """Startup and validation fail when auth is enabled but required variables are missing or weak."""
        # Missing user
        with self.assertRaises(ValueError):
            s = Settings(_env_file=None, AUTH_ENABLED=True, APP_LOGIN_USER="", APP_LOGIN_PASSWORD="pwd", AUTH_TOKEN_SECRET="s"*32)
            s.validate_auth_configuration()

        # Missing password
        with self.assertRaises(ValueError):
            s = Settings(_env_file=None, AUTH_ENABLED=True, APP_LOGIN_USER="usr", APP_LOGIN_PASSWORD="", AUTH_TOKEN_SECRET="s"*32)
            s.validate_auth_configuration()

        # Missing or short secret (<32 chars)
        with self.assertRaises(ValueError):
            s = Settings(_env_file=None, AUTH_ENABLED=True, APP_LOGIN_USER="usr", APP_LOGIN_PASSWORD="pwd", AUTH_TOKEN_SECRET="too_short")
            s.validate_auth_configuration()

        # Non-positive TTL
        with self.assertRaises(ValueError):
            s = Settings(_env_file=None, AUTH_ENABLED=True, APP_LOGIN_USER="usr", APP_LOGIN_PASSWORD="pwd", AUTH_TOKEN_SECRET="s"*32, AUTH_TOKEN_TTL_HOURS=0)
            s.validate_auth_configuration()

        # Startup lifespan fails closed when auth config is invalid
        invalid_settings = Settings(
            _env_file=None,
            app_env="test",
            SQLITE_DB_PATH=str(self.test_db),
            AUTH_ENABLED=True,
            APP_LOGIN_USER="usr",
            APP_LOGIN_PASSWORD="",  # invalid
            AUTH_TOKEN_SECRET="s"*32,
            planner_mode="rules_only",
        )
        invalid_app = create_app(invalid_settings)
        with self.assertRaises(AuthConfigurationError):
            with TestClient(invalid_app):
                pass

        # Direct ready probe query without active lifespan reports unavailable
        client = TestClient(invalid_app, raise_server_exceptions=False)
        ready_res = client.get("/api/ready")
        self.assertEqual(ready_res.status_code, 503)
        self.assertEqual(ready_res.json().get("status"), "unavailable")
        self.assertTrue(ready_res.json().get("auth_required"))


    def test_login_successful_and_returns_bearer_token(self) -> None:
        """Valid credentials return 200 with access_token, bearer token_type, and expires_at."""
        app = create_app(self.auth_enabled_settings)
        with TestClient(app) as client:
            res = client.post("/api/auth/login", json={"username": self.test_user, "password": self.test_password})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("access_token", data)
            self.assertEqual(data.get("token_type"), "bearer")
            self.assertIn("expires_at", data)

            token = data["access_token"]
            verified = verify_access_token(
                token,
                secret=self.test_token_secret,
                expected_username=self.test_user,
            )
            self.assertIsNotNone(verified)
            self.assertEqual(verified["sub"], self.test_user)

    def test_login_invalid_credentials_returns_401_without_leaking_reason(self) -> None:
        """Incorrect username or password returns 401 with generic invalid_credentials."""
        app = create_app(self.auth_enabled_settings)
        with TestClient(app) as client:
            # Wrong username
            res1 = client.post("/api/auth/login", json={"username": "wrong_user", "password": self.test_password})
            self.assertEqual(res1.status_code, 401)
            self.assertEqual(res1.json().get("code"), "invalid_credentials")

            # Wrong password
            res2 = client.post("/api/auth/login", json={"username": self.test_user, "password": "wrong_password"})
            self.assertEqual(res2.status_code, 401)
            self.assertEqual(res2.json().get("code"), "invalid_credentials")

            # Check identical error code and Vietnamese message
            self.assertEqual(res1.json(), res2.json())

    def test_rate_limiting_enforces_maximum_5_failures_in_60_seconds(self) -> None:
        """Exceeding 5 failed login attempts from the same IP within 60s triggers 429."""
        app = create_app(self.auth_enabled_settings)
        with TestClient(app) as client:
            headers = {"x-forwarded-for": "198.51.100.42"}

            # First 5 failed attempts return 401
            for attempt in range(5):
                res = client.post(
                    "/api/auth/login",
                    json={"username": self.test_user, "password": "wrong_password"},
                    headers=headers,
                )
                self.assertEqual(res.status_code, 401, f"Attempt {attempt+1} should return 401")

            # 6th attempt returns 429
            res6 = client.post(
                "/api/auth/login",
                json={"username": self.test_user, "password": "wrong_password"},
                headers=headers,
            )
            self.assertEqual(res6.status_code, 429)
            self.assertEqual(res6.json().get("code"), "too_many_attempts")

            # Even with correct credentials, rate-limited IP is blocked
            res_correct = client.post(
                "/api/auth/login",
                json={"username": self.test_user, "password": self.test_password},
                headers=headers,
            )
            self.assertEqual(res_correct.status_code, 429)

            # Different IP is not blocked
            other_headers = {"x-forwarded-for": "198.51.100.99"}
            res_other = client.post(
                "/api/auth/login",
                json={"username": self.test_user, "password": self.test_password},
                headers=other_headers,
            )
            self.assertEqual(res_other.status_code, 200)

    def test_protected_endpoints_require_token_when_auth_enabled(self) -> None:
        """Protected endpoints reject requests without token or with invalid token with 401 auth_required."""
        app = create_app(self.auth_enabled_settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path, **kw: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                # 1. Missing Authorization header
                res = client.get("/api/capabilities")
                self.assertEqual(res.status_code, 401)
                self.assertEqual(res.json().get("code"), "auth_required")

                # 2. Non-bearer authorization
                res_basic = client.get("/api/capabilities", headers={"Authorization": "Basic dXNlcjpwYXNz"})
                self.assertEqual(res_basic.status_code, 401)
                self.assertEqual(res_basic.json().get("code"), "auth_required")

                # 3. Invalid token signature
                res_bad = client.get("/api/capabilities", headers={"Authorization": "Bearer invalid.token.payload"})
                self.assertEqual(res_bad.status_code, 401)
                self.assertEqual(res_bad.json().get("code"), "auth_required")

                # 4. Stream endpoint /api/analyze/stream without token
                res_stream = client.post(
                    "/api/analyze/stream",
                    json={"query": "ACB ROE 2024", "analysis_type": "company"},
                )
                self.assertEqual(res_stream.status_code, 401)
                self.assertEqual(res_stream.json().get("code"), "auth_required")

                # 5. Onboarding template endpoint without token
                res_tpl = client.get("/api/onboarding/template.csv")
                self.assertEqual(res_tpl.status_code, 401)

                # 6. Valid token accesses protected endpoints
                token, _ = create_access_token(
                    username=self.test_user,
                    secret=self.test_token_secret,
                )
                res_ok = client.get("/api/capabilities", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(res_ok.status_code, 200)

    def test_public_endpoints_exempt_from_auth(self) -> None:
        """Public endpoints are accessible without Authorization header even when AUTH_ENABLED=true."""
        app = create_app(self.auth_enabled_settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path, **kw: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                # /api/health
                res_health = client.get("/api/health")
                self.assertEqual(res_health.status_code, 200)

                # /api/version
                res_ver = client.get("/api/version")
                self.assertEqual(res_ver.status_code, 200)

                # /api/ready
                res_ready = client.get("/api/ready")
                self.assertEqual(res_ready.status_code, 200)
                self.assertTrue(res_ready.json().get("auth_required"))

                # /api/auth/status
                res_auth_stat = client.get("/api/auth/status")
                self.assertEqual(res_auth_stat.status_code, 200)

                # /api/onboarding/samples/ctg-2024q4.csv
                res_sample = client.get("/api/onboarding/samples/ctg-2024q4.csv")
                self.assertEqual(res_sample.status_code, 200)
                self.assertIn("text/csv", res_sample.headers.get("content-type", ""))

                # CORS OPTIONS preflight request
                res_options = client.options(
                    "/api/analyze",
                    headers={
                        "Origin": "http://localhost:5173",
                        "Access-Control-Request-Method": "POST",
                    },
                )
                self.assertEqual(res_options.status_code, 200)

    def test_token_expiration_and_tamper_resistance(self) -> None:
        """Expired or tampered tokens are rejected."""
        # Expired token (TTL negative)
        expired_token, _ = create_access_token(
            username=self.test_user,
            secret=self.test_token_secret,
            ttl_hours=-1,
        )
        self.assertIsNone(verify_access_token(expired_token, secret=self.test_token_secret))

        # Tampered payload
        valid_token, _ = create_access_token(
            username=self.test_user,
            secret=self.test_token_secret,
            ttl_hours=12,
        )
        payload_part, sig_part = valid_token.split(".")
        tampered_token = f"{payload_part}modified.{sig_part}"
        self.assertIsNone(verify_access_token(tampered_token, secret=self.test_token_secret))

        # Wrong secret
        other_secret = "b" * 32
        self.assertIsNone(verify_access_token(valid_token, secret=other_secret))

    def test_secrets_never_logged(self) -> None:
        """Secrets and passwords never appear in application logs during auth workflows."""
        class _CapturingHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records: list[str] = []

            def emit(self, record):
                self.records.append(self.format(record))

        handler = _CapturingHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            app = create_app(self.auth_enabled_settings)
            with TestClient(app) as client:
                # Login attempt with credentials
                client.post("/api/auth/login", json={"username": self.test_user, "password": self.test_password})
                # Failed login
                client.post("/api/auth/login", json={"username": self.test_user, "password": "wrong_secret_12345"})

            all_logs = " \n ".join(handler.records)
            self.assertNotIn(self.test_password, all_logs)
            self.assertNotIn("wrong_secret_12345", all_logs)
            self.assertNotIn(self.test_token_secret, all_logs)
        finally:
            root_logger.removeHandler(handler)

    def test_rate_limit_spoofing_uses_last_forwarded_ip_and_shares_counter(self) -> None:
        """Rotating leftmost X-Forwarded-For does not bypass rate limiter; last IP is used."""
        app = create_app(self.auth_enabled_settings)
        with TestClient(app) as client:
            real_client_ip = "203.0.113.195"
            # 5 failed attempts with different leftmost IPs but same real last IP
            for i in range(5):
                headers = {"x-forwarded-for": f"10.0.0.{i+1}, {real_client_ip}"}
                res = client.post(
                    "/api/auth/login",
                    json={"username": self.test_user, "password": "wrong_password"},
                    headers=headers,
                )
                self.assertEqual(res.status_code, 401, f"Attempt {i+1} should fail with 401")

            # 6th attempt with another leftmost IP but same last IP gets 429
            res6 = client.post(
                "/api/auth/login",
                json={"username": self.test_user, "password": "wrong_password"},
                headers={"x-forwarded-for": f"10.0.0.99, {real_client_ip}"},
            )
            self.assertEqual(res6.status_code, 429)
            self.assertEqual(res6.json().get("code"), "too_many_attempts")

    def test_rate_limiter_table_capacity_cap(self) -> None:
        """In-memory rate limiter prunes expired entries first and caps total entries at max_entries."""
        limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=60.0, max_entries=10)
        now = time.time()
        # Add 5 expired entries (older than 60s)
        with limiter._lock:
            for i in range(5):
                limiter._failures[f"expired_{i}"] = [now - 120.0]

        # Add 8 active entries
        for i in range(8):
            limiter.record_failure(f"active_{i}")

        # Total was 5 expired + 8 active = 13. Cap is 10.
        # Pruning dropped the 5 expired keys, leaving 8 active keys <= 10.
        self.assertLessEqual(len(limiter._failures), 10)
        for i in range(5):
            self.assertNotIn(f"expired_{i}", limiter._failures)

        # Now add 10 more active entries (total active > 10).
        # Should drop oldest active entries to maintain <= 10 keys.
        for i in range(8, 18):
            limiter.record_failure(f"active_{i}")

        self.assertEqual(len(limiter._failures), 10)

        # Also verify default_rate_limiter or large limiter caps at 10,000
        limiter_large = InMemoryRateLimiter(max_entries=10000)
        for i in range(10005):
            limiter_large.record_failure(f"ip_{i}")
        self.assertEqual(len(limiter_large._failures), 10000)

    def test_public_path_traversal_rejection(self) -> None:
        """Paths containing directory traversal or unsafe encodings are rejected from public exemption."""
        app = create_app(self.auth_enabled_settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path, **kw: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                # 1. Directory traversal ../..
                res_dotdot = client.get("/api/onboarding/samples/../../runs")
                self.assertEqual(res_dotdot.status_code, 401)
                self.assertEqual(res_dotdot.json().get("code"), "auth_required")

                # 2. Percent-encoded traversal %2e%2e
                res_encoded = client.get("/api/onboarding/samples/%2e%2e/runs")
                self.assertEqual(res_encoded.status_code, 401)
                self.assertEqual(res_encoded.json().get("code"), "auth_required")

                # 3. Duplicate slashes //
                res_slash = client.get("/api/onboarding/samples//x.csv")
                self.assertEqual(res_slash.status_code, 401)
                self.assertEqual(res_slash.json().get("code"), "auth_required")

                # Direct unit verification of is_public_path
                self.assertFalse(is_public_path("/api/onboarding/samples/../../runs"))
                self.assertFalse(is_public_path("/api/onboarding/samples/%2e%2e/runs"))
                self.assertFalse(is_public_path("/api/onboarding/samples/%2E%2E/runs"))
                self.assertFalse(is_public_path("/api/onboarding/samples//x.csv"))
                self.assertFalse(is_public_path("/api/onboarding/samples\\x.csv"))
                self.assertFalse(is_public_path("/api/onboarding/samples/%5cx.csv"))
                self.assertFalse(is_public_path("/api/onboarding/samples/%2fx.csv"))

    def test_docs_and_non_api_paths_under_auth(self) -> None:
        """Non-/api/ routes (except '/') including /docs, /redoc, /openapi.json require auth when enabled."""
        app = create_app(self.auth_enabled_settings)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path, **kw: _fixture_provider_binding(path, expose_locator=True),
        ):
            with TestClient(app) as client:
                # Without token: 401
                self.assertEqual(client.get("/docs").status_code, 401)
                self.assertEqual(client.get("/redoc").status_code, 401)
                self.assertEqual(client.get("/openapi.json").status_code, 401)

                # Root path '/' is public (not 401; returns 404 because no root route is registered)
                root_res = client.get("/")
                self.assertNotEqual(root_res.status_code, 401)

                # With valid token: 200
                token, _ = create_access_token(
                    username=self.test_user,
                    secret=self.test_token_secret,
                )
                headers = {"Authorization": f"Bearer {token}"}
                self.assertEqual(client.get("/docs", headers=headers).status_code, 200)
                self.assertEqual(client.get("/openapi.json", headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()

