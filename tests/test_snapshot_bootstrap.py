"""Offline tests for private Supabase snapshot hydration."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import SecretStr

from thesis_api.snapshot_bootstrap import (
    SnapshotBootstrapError,
    ensure_snapshot_available,
)


class _FakeResponse:
    status = 200

    def __init__(self, payload: bytes):
        self._payload = payload
        self._offset = 0
        self.headers: dict[str, str] = {}

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


def _snapshot_bytes(root: Path, snapshot_id: str = "snapshot-test-v1") -> bytes:
    source = root / "source.sqlite"
    connection = sqlite3.connect(source)
    try:
        connection.execute(
            "CREATE TABLE snapshot_metadata (snapshot_id TEXT NOT NULL, created_at TEXT)"
        )
        connection.execute(
            "INSERT INTO snapshot_metadata(snapshot_id, created_at) VALUES (?, ?)",
            (snapshot_id, "2026-09-27T00:00:00Z"),
        )
        connection.commit()
    finally:
        connection.close()
    return source.read_bytes()


def _kwargs(expected_hash: str, *, snapshot_id: str = "snapshot-test-v1") -> dict[str, object]:
    return {
        "supabase_url": "https://example.supabase.co",
        "bucket": "thesis-snapshots",
        "object_path": "accepted.sqlite",
        "service_role_key": SecretStr("test-only-secret"),
        "expected_snapshot_id": snapshot_id,
        "expected_sha256": expected_hash,
    }


class SnapshotBootstrapTests(unittest.TestCase):
    def test_unconfigured_bootstrap_is_a_noop(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "accepted.sqlite"
            self.assertFalse(
                ensure_snapshot_available(
                    target,
                    supabase_url=None,
                    bucket=None,
                    object_path=None,
                    service_role_key=None,
                    expected_snapshot_id=None,
                    expected_sha256=None,
                )
            )
            self.assertFalse(target.exists())

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_downloads_valid_private_object_and_validates_identity(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _snapshot_bytes(root)
            mocked_urlopen.return_value = _FakeResponse(payload)
            expected_hash = sha256(payload).hexdigest()

            result = ensure_snapshot_available(
                root / "accepted.sqlite",
                **_kwargs(expected_hash),
            )

            self.assertTrue(result)
            self.assertEqual((root / "accepted.sqlite").read_bytes(), payload)
            request = mocked_urlopen.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer test-only-secret")
            self.assertEqual(request.get_header("Apikey"), "test-only-secret")
            self.assertIn("/storage/v1/object/thesis-snapshots/accepted.sqlite", request.full_url)

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_canonical_snapshot_identity_is_read_from_dataset_metadata(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "canonical.sqlite"
            connection = sqlite3.connect(source)
            try:
                connection.execute("CREATE TABLE dataset_metadata (dataset_id TEXT, dataset_snapshot_id TEXT NOT NULL)")
                connection.execute("INSERT INTO dataset_metadata VALUES (?, ?)", ("ops", "ops-snapshot-v1"))
                connection.commit()
            finally:
                connection.close()
            payload = source.read_bytes()
            mocked_urlopen.return_value = _FakeResponse(payload)
            result = ensure_snapshot_available(
                root / "accepted.sqlite",
                **_kwargs(sha256(payload).hexdigest(), snapshot_id="ops-snapshot-v1"),
            )
            self.assertTrue(result)

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_matching_existing_file_skips_network(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _snapshot_bytes(root)
            target = root / "accepted.sqlite"
            target.write_bytes(payload)
            expected_hash = sha256(payload).hexdigest()

            self.assertTrue(ensure_snapshot_available(target, **_kwargs(expected_hash)))
            mocked_urlopen.assert_not_called()

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_stale_existing_file_is_replaced_after_remote_validation(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _snapshot_bytes(root)
            target = root / "accepted.sqlite"
            target.write_bytes(b"stale-local-copy")
            mocked_urlopen.return_value = _FakeResponse(payload)
            expected_hash = sha256(payload).hexdigest()

            self.assertTrue(ensure_snapshot_available(target, **_kwargs(expected_hash)))
            self.assertEqual(target.read_bytes(), payload)
            mocked_urlopen.assert_called_once()

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_hash_mismatch_does_not_publish_download(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _snapshot_bytes(root)
            mocked_urlopen.return_value = _FakeResponse(payload)

            with self.assertRaisesRegex(SnapshotBootstrapError, "SHA-256"):
                ensure_snapshot_available(
                    root / "accepted.sqlite",
                    **_kwargs("0" * 64),
                )
            self.assertFalse((root / "accepted.sqlite").exists())

    @patch("thesis_api.snapshot_bootstrap.urlopen")
    def test_missing_required_bootstrap_value_fails_closed(self, mocked_urlopen):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SnapshotBootstrapError, "requires URL"):
                ensure_snapshot_available(
                    Path(directory) / "accepted.sqlite",
                    supabase_url="https://example.supabase.co",
                    bucket="thesis-snapshots",
                    object_path="accepted.sqlite",
                    service_role_key=None,
                    expected_snapshot_id="snapshot-test-v1",
                    expected_sha256="0" * 64,
                )
            mocked_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
