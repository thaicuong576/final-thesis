import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_vcb_official_candidates import audit
from scripts.build_vcb_official_candidates import build


class AuditVcbOfficialCandidatesTests(unittest.TestCase):
    def _manifest(self, root: Path) -> Path:
        rows = []
        for period in ("Q1", "Q2", "Q3", "Q4"):
            pdf = root / f"VCB_{period}.pdf"
            pdf.write_bytes(b"pdf-fixture")
            source_id = (
                "official-VCB-2024-Q4-consolidated-quarterly"
                if period == "Q4"
                else f"official-VCB-2024-{period}-consolidated"
            )
            rows.append({"source_id": source_id, "local_path": str(pdf)})
        path = root / "manifest.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_clean_candidate_package_is_consistent_but_not_gold_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidates.jsonl"
            build(candidate)
            report = audit(candidate, self._manifest(root))

        self.assertEqual(report["row_count"], 20)
        self.assertEqual(report["target_cell_count"], 16)
        self.assertEqual(report["formula_value_mismatches"], 0)
        self.assertEqual(report["missing_source_routes"], 0)
        self.assertEqual(report["pending_validation_rows"], 20)
        self.assertFalse(report["ready_for_gold"])
        self.assertIn("human_review_required", report["blockers"])

    def test_tampered_value_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidates.jsonl"
            build(candidate)
            rows = [json.loads(line) for line in candidate.read_text(encoding="utf-8").splitlines()]
            rows[0]["value"] = 999.0
            candidate.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            report = audit(candidate, self._manifest(root))

        self.assertEqual(report["formula_value_mismatches"], 1)
        self.assertIn("consistency_findings", report["blockers"])


if __name__ == "__main__":
    unittest.main()
