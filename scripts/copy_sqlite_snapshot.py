"""Create an independent, integrity-checked SQLite snapshot.

The source is opened read-only and copied with SQLite's backup API so committed
WAL content is included consistently. The destination is replaced atomically
and configured for WAL without sharing source database, WAL, or SHM files.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def copy_snapshot(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    if source == destination:
        raise ValueError("source and destination must be different files")

    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash_before = sha256(source)
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".copying", dir=destination.parent
    )
    os.close(temp_fd)
    temp_path = Path(temp_name)

    try:
        source_uri = f"file:{source.as_posix()}?mode=ro"
        with closing(sqlite3.connect(source_uri, uri=True)) as source_db:
            source_check = source_db.execute("PRAGMA quick_check").fetchone()[0]
            if source_check != "ok":
                raise RuntimeError(f"source SQLite quick_check failed: {source_check}")
            with closing(sqlite3.connect(temp_path)) as destination_db:
                source_db.backup(destination_db)

        with closing(sqlite3.connect(temp_path)) as destination_db:
            destination_check = destination_db.execute("PRAGMA quick_check").fetchone()[0]
            if destination_check != "ok":
                raise RuntimeError(
                    f"destination SQLite quick_check failed: {destination_check}"
                )
            journal_mode = destination_db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            destination_db.execute("PRAGMA busy_timeout=30000")
            if str(journal_mode).lower() != "wal":
                raise RuntimeError(f"destination did not enter WAL mode: {journal_mode}")
            destination_db.commit()

        source_hash_after = sha256(source)
        if source_hash_after != source_hash_before:
            raise RuntimeError(
                "source database bytes changed during snapshot creation; retry when stable"
            )

        os.replace(temp_path, destination)
        for suffix in ("-wal", "-shm"):
            destination.with_name(f"{destination.name}{suffix}").unlink(missing_ok=True)
        if os.path.samefile(source, destination):
            raise RuntimeError("destination unexpectedly shares source file identity")

        print(
            "[DB] Created isolated SQLite snapshot "
            f"{destination} from source SHA-256 {source_hash_before}"
        )
    finally:
        temp_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        copy_snapshot(args.source, args.destination)
    except Exception as exc:
        print(f"copy_sqlite_snapshot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
