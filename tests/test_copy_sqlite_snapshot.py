from __future__ import annotations

import hashlib
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.copy_sqlite_snapshot import copy_snapshot


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class CopySqliteSnapshotTests(unittest.TestCase):
    def test_snapshot_is_independent_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sqlite-snapshot-test-") as temp_dir:
            root = Path(temp_dir)
            source = root / "source.sqlite"
            destination = root / "worktree" / "snapshot.sqlite"

            with closing(sqlite3.connect(source)) as source_writer:
                self.assertEqual(
                    "wal",
                    source_writer.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower(),
                )
                source_writer.execute(
                    "CREATE TABLE facts (id INTEGER PRIMARY KEY, value TEXT)"
                )
                source_writer.execute("INSERT INTO facts(value) VALUES ('source')")
                source_writer.commit()
                self.assertTrue(source.with_name(f"{source.name}-wal").is_file())

                source_hash = _sha256(source)
                copy_snapshot(source, destination)

                self.assertEqual(source_hash, _sha256(source))
                self.assertFalse(os.path.samefile(source, destination))
                with closing(sqlite3.connect(destination)) as connection:
                    self.assertEqual(
                        "wal",
                        connection.execute("PRAGMA journal_mode").fetchone()[0].lower(),
                    )
                    connection.execute("INSERT INTO facts(value) VALUES ('destination')")
                    connection.commit()

                self.assertEqual(source_hash, _sha256(source))
                self.assertEqual(
                    1, source_writer.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
                )
                with closing(sqlite3.connect(destination)) as connection:
                    self.assertEqual(
                        2, connection.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
                    )

    def test_snapshot_replaces_existing_hardlink_and_unlinks_sidecars(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sqlite-hardlink-test-") as temp_dir:
            root = Path(temp_dir)
            source = root / "source.sqlite"
            destination = root / "worktree" / "snapshot.sqlite"
            destination.parent.mkdir(parents=True)

            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE facts (value TEXT NOT NULL)")
                connection.execute("INSERT INTO facts(value) VALUES ('source')")
                connection.commit()

            os.link(source, destination)
            for suffix in ("-wal", "-shm"):
                source_sidecar = source.with_name(f"{source.name}{suffix}")
                destination_sidecar = destination.with_name(f"{destination.name}{suffix}")
                source_sidecar.write_bytes(f"source{suffix}".encode())
                os.link(source_sidecar, destination_sidecar)

            self.assertTrue(os.path.samefile(source, destination))
            source_hash = _sha256(source)
            copy_snapshot(source, destination)

            self.assertFalse(os.path.samefile(source, destination))
            self.assertEqual(source_hash, _sha256(source))
            for suffix in ("-wal", "-shm"):
                source_sidecar = source.with_name(f"{source.name}{suffix}")
                destination_sidecar = destination.with_name(f"{destination.name}{suffix}")
                self.assertTrue(source_sidecar.is_file())
                self.assertFalse(destination_sidecar.exists())


if __name__ == "__main__":
    unittest.main()
