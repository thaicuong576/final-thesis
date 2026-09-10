import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_mbb_official_candidates import build as build_candidates
from scripts.build_mbb_official_candidate_db import build_candidate_db


class MbbOfficialCandidateDbTests(unittest.TestCase):
    def test_materializes_pending_rows_and_sources_without_gold_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.jsonl"
            build_candidates(candidates)
            manifest = root / "sources.json"
            sources = []
            for period in ("Q1", "Q2", "Q3", "Q4"):
                pdf = root / f"MBB_{period}.pdf"
                pdf.write_bytes(b"pdf-fixture")
                sources.append({
                    "source_id": f"official-MBB-2024-{period}-consolidated",
                    "source_type": "filing",
                    "source_tier": "primary",
                    "url": f"https://example.test/{period}.pdf",
                    "retrieved_at_utc": "2026-09-07T00:00:00Z",
                    "local_path": str(pdf),
                    "content_hash": f"sha256:{period}",
                    "publisher": "MBB",
                    "license_note": "public disclosure",
                })
            manifest.write_text(json.dumps(sources), encoding="utf-8")
            output = root / "candidate.sqlite"

            result = build_candidate_db(candidates, manifest, output)

            self.assertEqual(result["candidate_rows"], 12)
            connection = sqlite3.connect(output)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM metric_observations").fetchone()[0], 12)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM source_records").fetchone()[0], 4)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM gold_labels").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT DISTINCT quality_status FROM metric_observations").fetchall(), [("pending_validation",)])
            self.assertEqual(connection.execute("SELECT status FROM snapshot_metadata").fetchone()[0], "candidate_pending_human_review")
            connection.close()

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.jsonl"
            build_candidates(candidates)
            manifest = root / "sources.json"
            manifest.write_text("[]", encoding="utf-8")
            output = root / "candidate.sqlite"
            with self.assertRaises(ValueError):
                build_candidate_db(candidates, manifest, output)


if __name__ == "__main__":
    unittest.main()
