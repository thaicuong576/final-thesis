import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_vcb_official_candidates import build as build_candidates
from scripts.build_vcb_official_review_packet import (
    NAVIGATION_FIELDS,
    REGISTER_FIELDS,
    build_packet,
)


class VcbOfficialReviewPacketTests(unittest.TestCase):
    def _source_manifest(self, root: Path) -> Path:
        rows = []
        for period in ("Q1", "Q2", "Q3", "Q4"):
            pdf = root / f"VCB_{period}.pdf"
            pdf.write_bytes(b"pdf-fixture")
            source_id = (
                "official-VCB-2024-Q4-consolidated-quarterly"
                if period == "Q4"
                else f"official-VCB-2024-{period}-consolidated"
            )
            rows.append({
                "source_id": source_id,
                "source_type": "filing",
                "source_tier": "primary",
                "publisher": "VCB",
                "url": f"https://example.test/vcb-{period}.pdf",
                "filename": pdf.name,
                "local_path": str(pdf),
                "quality_status": "retrieved_pending_validation",
            })
        manifest = root / "sources.json"
        manifest.write_text(json.dumps(rows), encoding="utf-8")
        return manifest

    def test_packet_groups_20_candidates_into_16_blind_review_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidates.jsonl"
            build_candidates(candidate_path)
            output_dir = root / "review"

            result = build_packet(candidate_path, self._source_manifest(root), output_dir)

            self.assertEqual(result["target_cell_count"], 16)
            self.assertEqual(result["candidate_observation_count"], 20)
            with (output_dir / "VCB_official_review-register-v1.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                register = list(csv.DictReader(handle))
            self.assertEqual(len(register), 16)
            self.assertEqual(set(register[0]), set(REGISTER_FIELDS))
            roe = [row for row in register if row["metric"] == "bank.roe"]
            self.assertEqual(len(roe), 4)
            self.assertTrue(all(len(json.loads(row["candidate_observation_ids"])) == 2 for row in roe))

            for filename in (
                "VCB_official_checker-a-blind-v1.csv",
                "VCB_official_checker-b-blind-v1.csv",
            ):
                with (output_dir / filename).open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), 16)
                self.assertNotIn("candidate_values", rows[0])
                self.assertTrue(all(row["decision"] == "" and row["notes"] == "" for row in rows))

            with (output_dir / "VCB_official_source-navigation-v1.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                navigation = list(csv.DictReader(handle))
            self.assertEqual(len(navigation), 16)
            self.assertEqual(set(navigation[0]), set(NAVIGATION_FIELDS))
            self.assertEqual(
                {row["page_numbers"] for row in navigation},
                {"4,5,7,8", "30", "30,31", "28", "28,29", "31", "31,32"},
            )

    def test_packet_refuses_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidates.jsonl"
            build_candidates(candidate_path)
            source_manifest = self._source_manifest(root)
            output_dir = root / "review"
            build_packet(candidate_path, source_manifest, output_dir)
            with self.assertRaises(FileExistsError):
                build_packet(candidate_path, source_manifest, output_dir)


if __name__ == "__main__":
    unittest.main()
