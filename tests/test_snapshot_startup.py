"""Fail-closed validation tests for explicitly pinned SQLite snapshots."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from thesis_api.service import AnalysisBlocked, AnalysisEngine, _validate_configured_snapshot
from thesis_api.settings import Settings


def _make_snapshot(path: Path, snapshot_id: str = "fixture-snapshot-v1") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE snapshot_metadata "
            "(snapshot_id TEXT, created_at_utc TEXT, status TEXT, config_json TEXT)"
        )
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (snapshot_id, "2026-09-27T00:00:00Z", "fixture", "{}"),
        )
        connection.commit()
    finally:
        connection.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(snapshot_id: str):
    return SimpleNamespace(dataset_ref=SimpleNamespace(dataset_snapshot_id=snapshot_id))


class SnapshotStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.snapshot_path = self.root / "accepted.sqlite"
        self.snapshot_hash = _make_snapshot(self.snapshot_path)

    def _settings(self, **overrides) -> Settings:
        values = {
            "sqlite_db_path": str(self.snapshot_path),
            "expected_dataset_snapshot_id": "fixture-snapshot-v1",
            "expected_sqlite_sha256": self.snapshot_hash,
            "analysis_runs_db_path": str(self.root / "runs.sqlite"),
            "openai_api_key": "offline-test-key",
        }
        values.update(overrides)
        return Settings(**values)

    def test_missing_expected_snapshot_id_fails_closed(self) -> None:
        settings = self._settings(expected_dataset_snapshot_id=None)
        with self.assertRaises(AnalysisBlocked) as raised:
            _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "expected_snapshot_id_unconfigured")
        self.assertIn("EXPECTED_DATASET_SNAPSHOT_ID", raised.exception.detail)

    def test_provider_snapshot_id_must_match_expected_identity(self) -> None:
        settings = self._settings(expected_dataset_snapshot_id="other-snapshot")
        with patch("thesis_api.service._load_provider", return_value=_binding("fixture-snapshot-v1")):
            with self.assertRaises(AnalysisBlocked) as raised:
                _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "accepted_snapshot_id_mismatch")
        self.assertIn("EXPECTED_DATASET_SNAPSHOT_ID", raised.exception.detail)

    def test_raw_file_hash_must_match_expected_digest(self) -> None:
        settings = self._settings(expected_sqlite_sha256="0" * 64)
        with patch("thesis_api.service._load_provider", return_value=_binding("fixture-snapshot-v1")):
            with self.assertRaises(AnalysisBlocked) as raised:
                _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "accepted_snapshot_hash_mismatch")

    def test_missing_expected_hash_fails_closed(self) -> None:
        settings = self._settings(expected_sqlite_sha256=None)
        with self.assertRaises(AnalysisBlocked) as raised:
            _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "expected_snapshot_hash_unconfigured")

    def test_wal_sidecar_makes_snapshot_unavailable(self) -> None:
        Path(f"{self.snapshot_path}-wal").write_bytes(b"pending sqlite changes")
        settings = self._settings()
        with self.assertRaises(AnalysisBlocked) as raised:
            _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "accepted_snapshot_mutable")

    def test_integrity_check_failure_blocks_snapshot(self) -> None:
        self.snapshot_path.write_bytes(b"not a sqlite database")
        settings = self._settings(expected_sqlite_sha256=hashlib.sha256(self.snapshot_path.read_bytes()).hexdigest())
        with self.assertRaises(AnalysisBlocked) as raised:
            _validate_configured_snapshot(self.snapshot_path, settings)
        self.assertEqual(raised.exception.code, "accepted_snapshot_integrity_failed")

    def test_startup_keeps_run_store_separate_and_validation_is_cached(self) -> None:
        settings = self._settings()
        engine = AnalysisEngine(self.snapshot_path, settings)
        run_path = settings.get_analysis_runs_path(dataset_path=self.snapshot_path)
        self.assertNotEqual(run_path, self.snapshot_path.resolve())
        source_digest = hashlib.sha256(self.snapshot_path.read_bytes()).hexdigest()
        with patch("thesis_api.service._load_provider", return_value=_binding("fixture-snapshot-v1")) as load, patch(
            "thesis_api.service._capabilities_payload",
            return_value={"analysis_available": True, "database_status": "connected"},
        ):
            engine.initialize_runtime()
            engine.get_capabilities()
            engine.get_capabilities()
        self.assertEqual(load.call_count, 1)
        self.assertTrue(run_path.is_file())
        self.assertEqual(hashlib.sha256(self.snapshot_path.read_bytes()).hexdigest(), source_digest)

    def test_readiness_inspection_does_not_create_run_store_schema(self) -> None:
        settings = self._settings()
        engine = AnalysisEngine(self.snapshot_path, settings)
        run_path = settings.get_analysis_runs_path(dataset_path=self.snapshot_path)
        with patch("thesis_api.service._load_provider", return_value=_binding("fixture-snapshot-v1")), patch(
            "thesis_api.service._capabilities_payload",
            return_value={"analysis_available": True, "database_status": "connected"},
        ):
            engine.get_capabilities()
        self.assertFalse(run_path.exists())


if __name__ == "__main__":
    unittest.main()
