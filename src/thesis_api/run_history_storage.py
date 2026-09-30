"""Persist and hydrate analysis run history with private Supabase object storage."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .database import ensure_analysis_runs_table, save_analysis_run

logger = logging.getLogger(__name__)

_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_PENDING_FUTURES: set[concurrent.futures.Future[bool]] = set()


def _secret_value(value: Any) -> str:
    if value is None:
        return ""
    getter = getattr(value, "get_secret_value", None)
    if callable(getter):
        value = getter()
    return str(value).strip()


def is_remote_run_history_configured(settings: Any) -> bool:
    """Return True if required Supabase Storage configuration is present."""
    if settings is None:
        return False
    url = str(getattr(settings, "supabase_url", "") or "").strip()
    bucket = str(getattr(settings, "supabase_storage_bucket", "") or "").strip()
    key = _secret_value(getattr(settings, "supabase_service_role_key", None))
    return bool(url and bucket and key)


def get_remote_prefix(settings: Any) -> str:
    """Return normalized remote prefix path without leading or trailing slashes."""
    raw = str(getattr(settings, "run_history_remote_prefix", "run-history/") or "run-history/").strip()
    clean = raw.strip("/")
    return clean if clean else "run-history"


def get_run_object_path(run_id: str, settings: Any) -> str:
    """Resolve destination object path within bucket, enforcing snapshot safety."""
    clean_run_id = str(run_id).strip()
    if not clean_run_id:
        raise ValueError("run_id must not be empty.")
    if clean_run_id.endswith(".sqlite"):
        raise ValueError("Safety violation: run_id cannot be a .sqlite file.")
    prefix = get_remote_prefix(settings)
    object_path = f"{prefix}/{clean_run_id}.json"

    # Invariant: Never overwrite or collide with the analytical Gold snapshot object!
    snapshot_obj = str(getattr(settings, "supabase_storage_object", "") or "").strip()
    if snapshot_obj and object_path == snapshot_obj:
        raise ValueError(
            f"Safety violation: run history object path '{object_path}' collides with snapshot object."
        )
    if object_path.endswith(".sqlite"):
        raise ValueError("Safety violation: run history objects must not have .sqlite extension.")
    return object_path


def _storage_object_url(supabase_url: str, bucket: str, object_path: str) -> str:
    base = supabase_url.strip().rstrip("/")
    return f"{base}/storage/v1/object/{quote(bucket, safe='')}/{quote(object_path, safe='/')}"


def _storage_list_url(supabase_url: str, bucket: str) -> str:
    base = supabase_url.strip().rstrip("/")
    return f"{base}/storage/v1/object/list/{quote(bucket, safe='')}"


def upload_run_to_storage(
    record: dict[str, Any],
    settings: Any,
    *,
    timeout: float = 10.0,
) -> bool:
    """Upload one run record as a JSON object to private Supabase Storage."""
    if not is_remote_run_history_configured(settings):
        return False

    run_id = str(record.get("run_id") or "").strip()
    if not run_id:
        logger.warning("Cannot upload run history without valid run_id.")
        return False

    try:
        object_path = get_run_object_path(run_id, settings)
    except ValueError as exc:
        logger.warning("Run history path validation error for run %s: %s", run_id, exc)
        return False

    url = _storage_object_url(
        settings.supabase_url,
        settings.supabase_storage_bucket,
        object_path,
    )
    key = _secret_value(settings.supabase_service_role_key)

    try:
        payload_bytes = json.dumps(record, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=payload_bytes,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
                "x-upsert": "true",
            },
            method="POST",
        )
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status not in (200, 201):
                logger.warning("Supabase run history upload for %s returned HTTP %s", run_id, status)
                return False
        return True
    except HTTPError as exc:
        logger.warning("Supabase run history upload for %s failed with HTTP %s", run_id, exc.code)
        return False
    except URLError as exc:
        logger.warning("Supabase run history upload for %s network error: %s", run_id, type(exc).__name__)
        return False
    except Exception as exc:
        logger.warning("Supabase run history upload for %s failed: %s", run_id, type(exc).__name__)
        return False


def list_remote_runs(
    settings: Any,
    *,
    limit: int = 500,
    timeout: float = 10.0,
) -> list[str]:
    """List object paths of persisted run history records under the configured prefix."""
    if not is_remote_run_history_configured(settings):
        return []

    prefix = get_remote_prefix(settings)
    url = _storage_list_url(
        settings.supabase_url,
        settings.supabase_storage_bucket,
    )
    key = _secret_value(settings.supabase_service_role_key)

    try:
        list_body = json.dumps(
            {
                "prefix": prefix,
                "limit": limit,
                "sortBy": {"column": "created_at", "order": "desc"},
            }
        ).encode("utf-8")
        request = Request(
            url,
            data=list_body,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                logger.warning("Supabase run history list returned HTTP %s", status)
                return []
            content = response.read().decode("utf-8")
            data = json.loads(content)

        snapshot_obj = str(getattr(settings, "supabase_storage_object", "") or "").strip()
        results: list[str] = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name or not isinstance(name, str) or not name.endswith(".json"):
                    continue
                if name.startswith(f"{prefix}/"):
                    full_path = name
                else:
                    full_path = f"{prefix}/{name}"
                if snapshot_obj and full_path == snapshot_obj:
                    continue
                results.append(full_path)
        return results
    except Exception as exc:
        logger.warning("Supabase run history list failed: %s", type(exc).__name__)
        return []


def download_run_record(
    object_path: str,
    settings: Any,
    *,
    timeout: float = 10.0,
) -> dict[str, Any] | None:
    """Download and deserialize a single run JSON record from storage."""
    if not is_remote_run_history_configured(settings):
        return None

    snapshot_obj = str(getattr(settings, "supabase_storage_object", "") or "").strip()
    if snapshot_obj and object_path == snapshot_obj:
        logger.warning("Safety guard: Refusing to download snapshot object as run record: %s", object_path)
        return None

    url = _storage_object_url(
        settings.supabase_url,
        settings.supabase_storage_bucket,
        object_path,
    )
    key = _secret_value(settings.supabase_service_role_key)

    try:
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
            },
            method="GET",
        )
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                logger.warning("Download of %s returned HTTP %s", object_path, status)
                return None
            content = response.read().decode("utf-8")
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            return None
    except Exception as exc:
        logger.warning("Failed to download run record %s: %s", object_path, type(exc).__name__)
        return None


def hydrate_run_history(
    db_path: Path,
    settings: Any,
    *,
    limit: int = 500,
) -> int:
    """Hydrate remote run records into the local SQLite store at startup."""
    if not is_remote_run_history_configured(settings):
        return 0

    # Invariant: Never write run history into the Gold analytical snapshot!
    gold_getter = getattr(settings, "get_sqlite_path", None)
    if callable(gold_getter):
        resolved_gold = gold_getter().expanduser().resolve()
        resolved_target = Path(db_path).expanduser().resolve()
        if resolved_target == resolved_gold:
            raise ValueError("Safety violation: Cannot hydrate run history into SQLITE_DB_PATH (Gold snapshot).")

    ensure_analysis_runs_table(db_path)

    # Cache existing run_ids in SQLite to avoid downloading known runs
    existing_ids: set[str] = set()
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT run_id FROM analysis_runs").fetchall()
            existing_ids = {r[0] for r in rows if r[0]}
        finally:
            conn.close()
    except Exception:
        pass

    remote_paths = list_remote_runs(settings, limit=limit)
    if not remote_paths:
        return 0

    hydrated_count = 0
    for obj_path in remote_paths:
        filename = obj_path.rsplit("/", 1)[-1]
        stem = filename[:-5] if filename.endswith(".json") else filename
        if stem in existing_ids:
            continue

        record = download_run_record(obj_path, settings)
        if not record or not isinstance(record, dict) or not record.get("run_id"):
            continue

        try:
            save_analysis_run(
                db_path=db_path,
                run_id=record["run_id"],
                created_at=record.get("created_at") or "",
                query=record.get("query") or "",
                target_ticker=record.get("target_ticker") or "",
                peer_tickers=record.get("peer_tickers"),
                period=record.get("period") or "",
                status=record.get("status") or "completed",
                report_json=record.get("report_json"),
                events_json=record.get("events_json"),
                model_used=record.get("model_used"),
                latency_ms=record.get("latency_ms"),
                trace_json=record.get("trace_json"),
                error_code=record.get("error_code"),
                duration_ms=record.get("duration_ms"),
                model_calls=record.get("model_calls"),
                input_tokens=record.get("input_tokens"),
                output_tokens=record.get("output_tokens"),
                arm=record.get("arm"),
                question_type=record.get("question_type"),
            )
            existing_ids.add(record["run_id"])
            hydrated_count += 1
        except Exception as exc:
            logger.warning("Failed to store hydrated run %s: %s", record.get("run_id"), exc)

    logger.info("Hydrated %d runs from Supabase Storage into %s", hydrated_count, db_path)
    return hydrated_count


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = concurrent.futures.ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="run_history_uploader",
        )
    return _EXECUTOR


def schedule_remote_run_persist(
    record: dict[str, Any],
    settings: Any,
) -> concurrent.futures.Future[bool] | None:
    """Schedule background non-blocking upload of a run record."""
    if not is_remote_run_history_configured(settings):
        return None

    def _task() -> bool:
        return upload_run_to_storage(record, settings)

    executor = _get_executor()
    future = executor.submit(_task)
    _PENDING_FUTURES.add(future)
    future.add_done_callback(lambda f: _PENDING_FUTURES.discard(f))
    return future


def wait_for_pending_uploads(timeout: float = 5.0) -> None:
    """Block until pending background uploads finish (for testing and shutdown)."""
    futures = list(_PENDING_FUTURES)
    if not futures:
        return
    concurrent.futures.wait(futures, timeout=timeout)
