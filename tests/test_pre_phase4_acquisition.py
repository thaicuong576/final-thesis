from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "pre-phase4-acquisition-v1.jsonl"
CANDIDATES = (
    ROOT
    / "data"
    / "reconciliation"
    / "pre-phase4-acquisition-v1"
    / "candidate-observations.jsonl"
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class PrePhase4AcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = read_jsonl(MANIFEST)
        self.candidates = read_jsonl(CANDIDATES)

    def test_manifest_has_unique_source_and_document_ids(self) -> None:
        source_ids = [row["source_id"] for row in self.records]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        document_ids = [row["document_id"] for row in self.records if row["record_type"] == "document"]
        self.assertEqual(len(document_ids), len(set(document_ids)))

    def test_all_retrieved_files_exist_and_hash_matches(self) -> None:
        for row in self.records:
            if row["record_type"] == "failed_route":
                self.assertIsNone(row["local_path"])
                self.assertIsNone(row["content_hash_sha256"])
                continue
            path = ROOT / row["local_path"]
            self.assertTrue(path.is_file(), row["local_path"])
            self.assertGreater(path.stat().st_size, 0, row["local_path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, row["content_hash_sha256"], row["local_path"])

    def test_candidates_reference_known_sources_or_explicit_missingness(self) -> None:
        source_ids = {row["source_id"] for row in self.records}
        for candidate in self.candidates:
            if candidate["source_id"] is not None:
                self.assertIn(candidate["source_id"], source_ids)
            if candidate["quality_status"] == "missing":
                self.assertIsNone(candidate["value"])
                self.assertIn("DATA_UNAVAILABLE", candidate["reason"])

    def test_no_candidate_is_silently_accepted(self) -> None:
        self.assertTrue(
            all(candidate["quality_status"] in {"review_required", "missing"} for candidate in self.candidates)
        )

    def test_credit_growth_candidates_preserve_period_and_semantics(self) -> None:
        macro = next(c for c in self.candidates if c["metric_id"] == "macro.credit_growth")
        self.assertEqual(macro["value"], 15.1)
        self.assertEqual(macro["as_of_date"], "2024-12-31")
        self.assertEqual(macro["period_basis"], "annual_change_vs_end_2023")
        self.assertEqual(macro["quality_status"], "review_required")

    def test_peer_sample_is_not_registered_as_native_sector(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8") + CANDIDATES.read_text(encoding="utf-8")
        self.assertNotIn("five-bank peer median", text.lower())

    def test_verify_is_read_only_and_idempotent(self) -> None:
        before_manifest = MANIFEST.read_bytes()
        before_candidates = CANDIDATES.read_bytes()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "acquire_pre_phase4.py"), "--verify"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(MANIFEST.read_bytes(), before_manifest)
        self.assertEqual(CANDIDATES.read_bytes(), before_candidates)


if __name__ == "__main__":
    unittest.main()
