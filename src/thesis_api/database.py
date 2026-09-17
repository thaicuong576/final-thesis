"""Database connectivity probe for infrastructure readiness."""

from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def check_database_connection(
    database_url: str | None,
    timeout_seconds: int = 5,
) -> Tuple[bool, str]:
    """Verify PostgreSQL connectivity using a lightweight SELECT 1 probe.

    Does not log or expose the connection string or credentials.
    """
    if not database_url or not database_url.strip():
        return False, "DATABASE_URL is not configured"

    try:
        import psycopg

        with psycopg.connect(
            conninfo=database_url.strip(),
            connect_timeout=timeout_seconds,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                row = cur.fetchone()
                if row is not None and row[0] == 1:
                    return True, "Database connection healthy"
                return False, "Unexpected database probe response"
    except Exception as exc:
        # Safe logging: log the error type and high-level description without connection string
        logger.warning("Database connectivity probe failed: %s: %s", type(exc).__name__, exc)
        return False, f"Database connectivity failed: {type(exc).__name__}"
