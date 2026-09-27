"""Hydrate and verify an accepted SQLite snapshot from private object storage."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class SnapshotBootstrapError(RuntimeError):
    """The configured accepted snapshot could not be safely hydrated."""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHUNK_SIZE = 1024 * 1024
_MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024


def _secret_value(value: Any) -> str:
    if value is None:
        return ""
    getter = getattr(value, "get_secret_value", None)
    if callable(getter):
        value = getter()
    return str(value).strip()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_id(path: Path) -> str:
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        row = connection.execute("SELECT snapshot_id FROM snapshot_metadata LIMIT 1").fetchone()
    except (OSError, sqlite3.Error) as exc:
        raise SnapshotBootstrapError("Downloaded snapshot is not readable SQLite.") from exc
    finally:
        if connection is not None:
            connection.close()
    if not row or not row[0]:
        raise SnapshotBootstrapError("Downloaded snapshot has no snapshot_metadata identity.")
    return str(row[0])


def _validate_sqlite(path: Path, *, expected_snapshot_id: str, expected_sha256: str) -> None:
    if not path.is_file():
        raise SnapshotBootstrapError("Accepted snapshot file is missing after download.")
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise SnapshotBootstrapError(
            "Accepted snapshot SHA-256 does not match EXPECTED_SQLITE_SHA256."
        )
    try:
        uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise SnapshotBootstrapError("Accepted snapshot failed SQLite integrity validation.") from exc
    if not integrity or integrity[0] != "ok":
        raise SnapshotBootstrapError("Accepted snapshot failed SQLite integrity validation.")
    if _snapshot_id(path) != expected_snapshot_id:
        raise SnapshotBootstrapError(
            "Accepted snapshot identity does not match EXPECTED_DATASET_SNAPSHOT_ID."
        )


def _storage_object_url(supabase_url: str, bucket: str, object_path: str) -> str:
    base = supabase_url.strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        raise SnapshotBootstrapError("SUPABASE_URL must be an HTTP(S) URL.")
    return (
        f"{base}/storage/v1/object/{quote(bucket, safe='')}/"
        f"{quote(object_path, safe='/')}"
    )


def _download_to(path: Path, *, url: str, service_role_key: str) -> None:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        },
        method="GET",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310: URL is validated above.
            status = getattr(response, "status", 200)
            if status != 200:
                raise SnapshotBootstrapError(f"Supabase snapshot download returned HTTP {status}.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > _MAX_SNAPSHOT_BYTES:
                raise SnapshotBootstrapError("Supabase snapshot exceeds the configured size limit.")
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
            ) as temporary:
                temp_path = Path(temporary.name)
                total = 0
                while chunk := response.read(_CHUNK_SIZE):
                    total += len(chunk)
                    if total > _MAX_SNAPSHOT_BYTES:
                        raise SnapshotBootstrapError("Supabase snapshot exceeds the configured size limit.")
                    temporary.write(chunk)
        os.replace(temp_path, path)
        temp_path = None
    except HTTPError as exc:
        raise SnapshotBootstrapError(f"Supabase snapshot download returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise SnapshotBootstrapError("Supabase snapshot download failed before receiving the file.") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def ensure_snapshot_available(
    target_path: Path,
    *,
    supabase_url: str | None,
    bucket: str | None,
    object_path: str | None,
    service_role_key: Any,
    expected_snapshot_id: str | None,
    expected_sha256: str | None,
) -> bool:
    """Ensure a configured accepted snapshot exists and passes immutable checks.

    Returns ``False`` when bootstrap is not configured, preserving local/test
    behavior. Once any bootstrap setting is supplied, all settings are required
    and failures raise ``SnapshotBootstrapError`` before the app serves traffic.
    """

    values = (
        supabase_url,
        bucket,
        object_path,
        _secret_value(service_role_key),
        expected_snapshot_id,
        expected_sha256,
    )
    if not any(str(value or "").strip() for value in values):
        return False

    url = str(supabase_url or "").strip()
    bucket_value = str(bucket or "").strip()
    object_value = str(object_path or "").strip()
    key = _secret_value(service_role_key)
    snapshot_id = str(expected_snapshot_id or "").strip()
    expected_hash = str(expected_sha256 or "").strip().lower()
    if not all((url, bucket_value, object_value, key, snapshot_id, expected_hash)):
        raise SnapshotBootstrapError(
            "Supabase snapshot bootstrap requires URL, bucket, object, service key, snapshot ID, and SHA-256."
        )
    if not _SHA256_RE.fullmatch(expected_hash):
        raise SnapshotBootstrapError("EXPECTED_SQLITE_SHA256 must be a 64-character hexadecimal SHA-256.")

    destination = Path(target_path).expanduser().resolve()
    if destination.is_file():
        try:
            _validate_sqlite(destination, expected_snapshot_id=snapshot_id, expected_sha256=expected_hash)
        except SnapshotBootstrapError:
            # A stale or partial local copy is never served; recover from the
            # immutable remote object and validate it before replacement.
            pass
        else:
            return True
    elif destination.exists():
        raise SnapshotBootstrapError("SQLITE_DB_PATH exists but is not a regular file.")

    download_url = _storage_object_url(url, bucket_value, object_value)
    temp_destination = destination.with_name(f".{destination.name}.download")
    _download_to(temp_destination, url=download_url, service_role_key=key)
    try:
        _validate_sqlite(temp_destination, expected_snapshot_id=snapshot_id, expected_sha256=expected_hash)
        os.replace(temp_destination, destination)
    finally:
        try:
            temp_destination.unlink(missing_ok=True)
        except OSError:
            pass
    return True


def ensure_snapshot_from_settings(settings: Any) -> bool:
    """Apply bootstrap configuration from the application settings object."""

    return ensure_snapshot_available(
        settings.get_sqlite_path(),
        supabase_url=getattr(settings, "supabase_url", None),
        bucket=getattr(settings, "supabase_storage_bucket", None),
        object_path=getattr(settings, "supabase_storage_object", None),
        service_role_key=getattr(settings, "supabase_service_role_key", None),
        expected_snapshot_id=getattr(settings, "expected_dataset_snapshot_id", None),
        expected_sha256=getattr(settings, "expected_sqlite_sha256", None),
    )
