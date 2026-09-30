"""Database connectivity probe for infrastructure readiness."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Sequence, Tuple

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


def ensure_analysis_runs_table(db_path: Path) -> None:
    """Ensure the analysis_runs table and indexes exist in the SQLite database."""
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode = wal")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    query TEXT NOT NULL,
                    target_ticker TEXT NOT NULL,
                    peer_tickers TEXT,
                    period TEXT NOT NULL,
                    status TEXT NOT NULL,
                    report_json TEXT,
                    events_json TEXT,
                    model_used TEXT,
                    latency_ms INTEGER,
                    trace_json TEXT,
                    error_code TEXT,
                    duration_ms INTEGER,
                    model_calls INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    arm TEXT,
                    question_type TEXT
                );
                """
            )
            # Idempotently add columns if table was created by older schema
            columns = {row[1] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
            for col_name, col_type in (
                ("trace_json", "TEXT"),
                ("error_code", "TEXT"),
                ("duration_ms", "INTEGER"),
                ("model_calls", "INTEGER"),
                ("input_tokens", "INTEGER"),
                ("output_tokens", "INTEGER"),
                ("arm", "TEXT"),
                ("question_type", "TEXT"),
            ):
                if col_name not in columns:
                    conn.execute(f"ALTER TABLE analysis_runs ADD COLUMN {col_name} {col_type};")

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_runs_target ON analysis_runs(target_ticker, period);"
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Could not ensure analysis_runs table: %s", exc)
        raise


def save_analysis_run(
    db_path: Path,
    run_id: str,
    created_at: str,
    query: str,
    target_ticker: str,
    peer_tickers: Sequence[str] | str | None,
    period: str,
    status: str,
    report_json: str | dict[str, Any] | None = None,
    events_json: str | list[Any] | None = None,
    model_used: str | None = None,
    latency_ms: int | None = None,
    trace_json: str | dict[str, Any] | None = None,
    error_code: str | None = None,
    duration_ms: int | None = None,
    model_calls: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    arm: str | None = None,
    question_type: str | None = None,
) -> None:
    """Persist completed or in-flight analysis run into SQLite analysis_runs table."""
    ensure_analysis_runs_table(db_path)

    peers_str = (
        json.dumps(list(peer_tickers), ensure_ascii=False)
        if isinstance(peer_tickers, (list, tuple, set))
        else (peer_tickers or "[]")
    )
    rep_str = (
        json.dumps(report_json, ensure_ascii=False)
        if isinstance(report_json, dict)
        else (report_json or "{}")
    )
    evts_str = (
        json.dumps(events_json, ensure_ascii=False)
        if isinstance(events_json, list)
        else (events_json or "[]")
    )
    trace_str = (
        json.dumps(trace_json, ensure_ascii=False)
        if isinstance(trace_json, dict)
        else trace_json
    )

    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_runs (
                    run_id, created_at, query, target_ticker, peer_tickers,
                    period, status, report_json, events_json, model_used, latency_ms,
                    trace_json, error_code, duration_ms, model_calls, input_tokens,
                    output_tokens, arm, question_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    created_at,
                    query,
                    target_ticker,
                    peers_str,
                    period,
                    status,
                    rep_str,
                    evts_str,
                    model_used,
                    latency_ms,
                    trace_str,
                    error_code,
                    duration_ms,
                    model_calls,
                    input_tokens,
                    output_tokens,
                    arm,
                    question_type,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.error("Failed to save analysis run %s: %s", run_id, exc)
        raise


def list_analysis_runs(db_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    """List recent analysis runs sorted by created_at DESC."""
    runs: list[dict[str, Any]] = []
    if not db_path.exists():
        return runs

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
            ).fetchone()
            if table is None:
                return runs
            cur = conn.cursor()
            cur.execute(
                """
                SELECT run_id, created_at, query, target_ticker, peer_tickers,
                       period, status, latency_ms, model_used, error_code, duration_ms, arm, question_type
                FROM analysis_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            for row in cur.fetchall():
                peers_raw = row["peer_tickers"]
                peers: list[str] = []
                if peers_raw:
                    try:
                        peers = json.loads(peers_raw)
                    except Exception:
                        peers = [p.strip() for p in peers_raw.split(",") if p.strip()]
                row_keys = row.keys()
                runs.append(
                    {
                        "run_id": row["run_id"],
                        "created_at": row["created_at"],
                        "query": row["query"],
                        "target_ticker": row["target_ticker"],
                        "peer_tickers": peers,
                        "period": row["period"],
                        "status": row["status"],
                        "latency_ms": row["latency_ms"],
                        "model_used": row["model_used"],
                        "error_code": row["error_code"] if "error_code" in row_keys else None,
                        "duration_ms": row["duration_ms"] if "duration_ms" in row_keys else None,
                        "arm": row["arm"] if "arm" in row_keys else None,
                        "question_type": row["question_type"] if "question_type" in row_keys else None,
                    }
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to list analysis runs: %s", exc)

    return runs


def get_analysis_run(db_path: Path, run_id: str) -> dict[str, Any] | None:
    """Retrieve full analysis run with report and events by run_id."""
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
            ).fetchone()
            if table is None:
                return None
            cur = conn.cursor()
            cur.execute("SELECT * FROM analysis_runs WHERE run_id = ? LIMIT 1", (run_id,))
            row = cur.fetchone()
            if not row:
                return None

            peers_raw = row["peer_tickers"]
            peers: list[str] = []
            if peers_raw:
                try:
                    peers = json.loads(peers_raw)
                except Exception:
                    peers = [p.strip() for p in peers_raw.split(",") if p.strip()]

            report_obj: dict[str, Any] | None = None
            if row["report_json"]:
                try:
                    report_obj = json.loads(row["report_json"])
                except Exception:
                    report_obj = None

            events_obj: list[Any] = []
            if row["events_json"]:
                try:
                    events_obj = json.loads(row["events_json"])
                except Exception:
                    events_obj = []

            row_keys = row.keys()
            trace_obj: dict[str, Any] | None = None
            if "trace_json" in row_keys and row["trace_json"]:
                try:
                    trace_obj = json.loads(row["trace_json"])
                except Exception:
                    trace_obj = None

            return {
                "run_id": row["run_id"],
                "created_at": row["created_at"],
                "query": row["query"],
                "target_ticker": row["target_ticker"],
                "peer_tickers": peers,
                "period": row["period"],
                "status": row["status"],
                "report": report_obj,
                "report_json": report_obj,
                "events": events_obj,
                "events_json": events_obj,
                "model_used": row["model_used"],
                "latency_ms": row["latency_ms"],
                "trace_json": trace_obj,
                "error_code": row["error_code"] if "error_code" in row_keys else None,
                "duration_ms": row["duration_ms"] if "duration_ms" in row_keys else None,
                "model_calls": row["model_calls"] if "model_calls" in row_keys else None,
                "input_tokens": row["input_tokens"] if "input_tokens" in row_keys else None,
                "output_tokens": row["output_tokens"] if "output_tokens" in row_keys else None,
                "arm": row["arm"] if "arm" in row_keys else None,
                "question_type": row["question_type"] if "question_type" in row_keys else None,
            }
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to get analysis run %s: %s", run_id, exc)
        return None


def get_analysis_run_trace(db_path: Path, run_id: str) -> dict[str, Any] | None:
    """Retrieve structured execution trace for an analysis run."""
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
            ).fetchone()
            if table is None:
                return None
            cur = conn.cursor()
            cur.execute("SELECT * FROM analysis_runs WHERE run_id = ? LIMIT 1", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            row_keys = row.keys()
            trace_raw = row["trace_json"] if "trace_json" in row_keys else None
            if not trace_raw:
                return None

            try:
                trace_data = json.loads(trace_raw)
            except Exception:
                return None

            if isinstance(trace_data, dict) and "steps" in trace_data:
                if not trace_data.get("run_id"):
                    trace_data["run_id"] = row["run_id"]
                if not trace_data.get("status"):
                    trace_data["status"] = row["status"]
                if not trace_data.get("query"):
                    trace_data["query"] = row["query"]
                if not trace_data.get("created_at"):
                    trace_data["created_at"] = row["created_at"]
                if trace_data.get("duration_ms") is None:
                    trace_data["duration_ms"] = (
                        row["duration_ms"]
                        if ("duration_ms" in row_keys and row["duration_ms"] is not None)
                        else 0
                    )
                if "arm" not in trace_data:
                    trace_data["arm"] = row["arm"] if "arm" in row_keys else None
                if "question_type" not in trace_data:
                    trace_data["question_type"] = (
                        row["question_type"] if "question_type" in row_keys else None
                    )
                return trace_data

            if isinstance(trace_data, list):
                return {
                    "run_id": row["run_id"],
                    "status": row["status"],
                    "query": row["query"],
                    "created_at": row["created_at"],
                    "duration_ms": (
                        row["duration_ms"]
                        if ("duration_ms" in row_keys and row["duration_ms"] is not None)
                        else 0
                    ),
                    "arm": row["arm"] if "arm" in row_keys else None,
                    "question_type": (
                        row["question_type"] if "question_type" in row_keys else None
                    ),
                    "steps": trace_data,
                }
            return None
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to get analysis run trace %s: %s", run_id, exc)
        return None


def get_analysis_report(db_path: Path, report_id_or_run_id: str) -> dict[str, Any] | None:
    """Retrieve report JSON directly from analysis_runs table."""
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
            ).fetchone()
            if table is None:
                return None
            cur = conn.cursor()
            # 1. Match by run_id
            cur.execute("SELECT report_json FROM analysis_runs WHERE run_id = ? LIMIT 1", (report_id_or_run_id,))
            row = cur.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    pass

            # 2. Match by report_id embedded in report_json
            cur.execute(
                "SELECT report_json FROM analysis_runs WHERE report_json LIKE ? LIMIT 1",
                (f'%"report_id": "{report_id_or_run_id}"%',),
            )
            row = cur.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to get analysis report %s: %s", report_id_or_run_id, exc)

    return None
