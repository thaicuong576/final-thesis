import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_mbb_official_candidates import build as build_candidates
from scripts.build_mbb_official_review_packet import (
    REGISTER_FIELDS,
    NAVIGATION_FIELDS,
    build_packet,
)


class MbbOfficialReviewPacketTests(unittest.TestCase):
    def test_packet_groups_12_candidates_into_8_blind_review_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidates.jsonl"
            build_candidates(candidate_path)
            source_manifest = root / "sources.json"
            source_rows = []
            for period in ("Q1", "Q2", "Q3", "Q4"):
                local_pdf = root / f"MBB_{period}.pdf"
                local_pdf.write_bytes(b"pdf-fixture")
                source_rows.append({
                    "source_id": f"official-MBB-2024-{period}-consolidated",
                    "source_type": "filing",
                    "source_tier": "primary",
                    "publisher": "MBB",
                    "url": f"https://example.test/mbb-{period}.pdf",
                    "filename": local_pdf.name,
                    "local_path": str(local_pdf),
                    "quality_status": "retrieved_pending_validation",
                })
            source_manifest.write_text(
                json.dumps(source_rows),
                encoding="utf-8",
            )
            output_dir = root / "review"

            result = build_packet(candidate_path, source_manifest, output_dir)

            self.assertEqual(result["target_cell_count"], 8)
            self.assertEqual(result["candidate_observation_count"], 12)
            with (output_dir / "MBB_official_review-register-v1.csv").open(encoding="utf-8", newline="") as handle:
                register = list(csv.DictReader(handle))
            self.assertEqual(len(register), 8)
            self.assertEqual(set(register[0]), set(REGISTER_FIELDS))
            roe = [row for row in register if row["metric"] == "bank.roe"]
            self.assertEqual(len(roe), 4)
            self.assertTrue(all(len(json.loads(row["candidate_observation_ids"])) == 2 for row in roe))

            for filename in ("MBB_official_checker-a-blind-v1.csv", "MBB_official_checker-b-blind-v1.csv"):
                with (output_dir / filename).open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), 8)
                self.assertNotIn("candidate_values", rows[0])
                self.assertTrue(all(row["decision"] == "" and row["notes"] == "" for row in rows))

            with (output_dir / "MBB_official_source-navigation-v1.csv").open(encoding="utf-8", newline="") as handle:
                navigation = list(csv.DictReader(handle))
            self.assertEqual(len(navigation), 8)
            self.assertEqual(set(navigation[0]), set(NAVIGATION_FIELDS))
            self.assertTrue(all(row["page_numbers"] == "3,4,6" for row in navigation))

    def test_packet_refuses_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidates.jsonl"
            build_candidates(candidate_path)
            source_manifest = root / "sources.json"
            source_rows = []
            for period in ("Q1", "Q2", "Q3", "Q4"):
                pdf = root / f"MBB_{period}.pdf"
                pdf.write_bytes(b"pdf-fixture")
                source_rows.append({
                    "source_id": f"official-MBB-2024-{period}-consolidated",
                    "local_path": str(pdf),
                })
            source_manifest.write_text(json.dumps(source_rows), encoding="utf-8")
            output_dir = root / "review"
            build_packet(candidate_path, source_manifest, output_dir)
            with self.assertRaises(FileExistsError):
                build_packet(candidate_path, source_manifest, output_dir)


if __name__ == "__main__":
    unittest.main()
