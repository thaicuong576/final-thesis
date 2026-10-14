"""Shared-credential authentication and rate-limiting gate for thesis API."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any

from fastapi import Request
from pydantic import BaseModel, Field, SecretStr

logger = logging.getLogger(__name__)


class AuthConfigurationError(ValueError):
    """Raised when authentication is enabled but required configuration is missing or weak."""


class LoginRequest(BaseModel):
    """Payload submitted to POST /api/auth/login."""

    username: str = Field(..., description="Login username")
    password: str = Field(..., description="Login password")


class LoginResponse(BaseModel):
    """Response returned by successful POST /api/auth/login."""

    access_token: str = Field(..., description="Stateless signed access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: str = Field(..., description="ISO 8601 UTC expiration timestamp")


class AuthStatusResponse(BaseModel):
    """Response returned by GET /api/auth/status."""

    required: bool = Field(..., description="Whether authentication is required for protected endpoints")


class AuthErrorResponse(BaseModel):
    """Standardized authentication error payload."""

    detail: str = Field(..., description="Human-readable explanation in Vietnamese")
    code: str = Field(..., description="Machine-readable error code")


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter by client IP with bounded capacity."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: float = 60.0,
        max_entries: int = 10000,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune_locked(self, now: float) -> None:
        """Prune expired timestamps, remove empty entries, and enforce max_entries cap."""
        cutoff = now - self.window_seconds
        # 1. Drop expired keys first
        expired_keys = [
            ip
            for ip, attempts in self._failures.items()
            if not [t for t in attempts if t > cutoff]
        ]
        for ip in expired_keys:
            self._failures.pop(ip, None)

        # Retain only active timestamps for surviving keys
        for ip, attempts in list(self._failures.items()):
            valid_attempts = [t for t in attempts if t > cutoff]
            if not valid_attempts:
                self._failures.pop(ip, None)
            else:
                self._failures[ip] = valid_attempts

        # 2. If still above cap, drop oldest entries (keys with oldest recent activity)
        if len(self._failures) > self.max_entries:
            sorted_keys = sorted(
                self._failures.keys(),
                key=lambda k: max(self._failures[k]) if self._failures[k] else 0.0,
            )
            excess = len(self._failures) - self.max_entries
            for k in sorted_keys[:excess]:
                self._failures.pop(k, None)

    def is_rate_limited(self, ip: str) -> bool:
        """Check whether the client IP has exceeded maximum failed attempts in the window."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            attempts = [t for t in self._failures.get(ip, []) if t > cutoff]
            if not attempts:
                self._failures.pop(ip, None)
                return False
            self._failures[ip] = attempts
            return len(attempts) >= self.max_attempts

    def record_failure(self, ip: str) -> None:
        """Record a failed login attempt for the client IP and enforce capacity cap."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            attempts = [t for t in self._failures.get(ip, []) if t > cutoff]
            attempts.append(now)
            self._failures[ip] = attempts
            if len(self._failures) > self.max_entries:
                self._prune_locked(now)

    def record_success(self, ip: str) -> None:
        """Clear failures on successful login."""
        with self._lock:
            self._failures.pop(ip, None)

    def reset(self) -> None:
        """Clear all rate limiting state (useful for tests)."""
        with self._lock:
            self._failures.clear()


default_rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, taking proxy forward headers into account.

    Uses the LAST non-empty entry of X-Forwarded-For because reverse proxies (such as
    Render) append the real client IP to the end of the chain, preventing spoofing
    from client-supplied initial entries.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]
    if request.client and request.client.host:
        return request.client.host.strip()
    return "unknown"


def _secret_str(value: str | SecretStr | None) -> str:
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return str(value)


def verify_credentials(
    username: str,
    password: str,
    *,
    expected_user: str,
    expected_password: str | SecretStr,
) -> bool:
    """Constant-time comparison for username and password without short-circuiting."""
    exp_user_bytes = expected_user.strip().encode("utf-8")
    actual_user_bytes = username.strip().encode("utf-8")
    exp_pwd_bytes = _secret_str(expected_password).encode("utf-8")
    actual_pwd_bytes = password.encode("utf-8")

    user_matches = hmac.compare_digest(actual_user_bytes, exp_user_bytes)
    pwd_matches = hmac.compare_digest(actual_pwd_bytes, exp_pwd_bytes)

    return user_matches and pwd_matches


def create_access_token(
    *,
    username: str,
    secret: str | SecretStr,
    ttl_hours: int = 12,
) -> tuple[str, str]:
    """Create a stateless HMAC-SHA256 signed access token and return (token, expires_at_iso)."""
    secret_bytes = _secret_str(secret).encode("utf-8")
    if len(secret_bytes) < 32:
        raise AuthConfigurationError("Token secret must be at least 32 characters.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)
    exp_timestamp = int(expires_at.timestamp())

    payload = {
        "sub": username,
        "exp": exp_timestamp,
        "iat": int(now.timestamp()),
    }
    raw_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
    signature = hmac.new(secret_bytes, encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()

    token = f"{encoded_payload}.{signature}"
    return token, expires_at.isoformat()


def verify_access_token(
    token: str,
    *,
    secret: str | SecretStr,
    expected_username: str | None = None,
) -> dict[str, Any] | None:
    """Verify stateless HMAC-SHA256 token signature, expiration, and username in constant time."""
    if not token or "." not in token:
        return None

    secret_bytes = _secret_str(secret).encode("utf-8")
    if len(secret_bytes) < 32:
        return None

    try:
        encoded_payload, signature = token.rsplit(".", 1)
        expected_sig = hmac.new(secret_bytes, encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add padding back if necessary
        padding = len(encoded_payload) % 4
        if padding:
            encoded_payload += "=" * (4 - padding)

        payload_bytes = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
        payload = json.loads(payload_bytes.decode("utf-8"))

        if not isinstance(payload, dict):
            return None

        exp = payload.get("exp")
        if not isinstance(exp, (int, float)) or time.time() >= exp:
            return None

        if expected_username is not None:
            sub = str(payload.get("sub", ""))
            if not hmac.compare_digest(sub.encode("utf-8"), expected_username.strip().encode("utf-8")):
                return None

        return payload
    except Exception:
        return None


def is_public_path(path: str, method: str = "GET") -> bool:
    """Check if the given request path and method are exempt from authentication.

    Public endpoints:
    - Any OPTIONS method (CORS preflight)
    - Root path: "/"
    - /api/version
    - /api/ready
    - /api/health
    - /api/auth/status
    - /api/auth/login
    - /api/onboarding/samples/* (safe filenames without directory traversal)

    All other paths (including /docs, /redoc, /openapi.json) require authentication when enabled.
    """
    if method == "OPTIONS":
        return True

    # Security check: reject paths with directory traversal, duplicate slashes, backslashes,
    # or percent-encoded traversal sequences (%2e, %2f, %5c).
    lower_path = path.lower()
    if any(bad in lower_path for bad in ("..", "//", "\\", "%2e", "%2f", "%5c")):
        return False

    clean_path = path.rstrip("/") if path != "/" else "/"

    if clean_path in (
        "/",
        "/api/version",
        "/api/ready",
        "/api/health",
        "/api/auth/status",
        "/api/auth/login",
    ):
        return True

    if clean_path.startswith("/api/onboarding/samples/"):
        return True

    return False
