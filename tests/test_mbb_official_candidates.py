import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_mbb_official_candidates import build


class MbbOfficialCandidateTests(unittest.TestCase):
    def test_build_emits_pending_roa_and_two_roe_variants_per_quarter(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "MBB_candidates.jsonl"
            rows = build(output)
            self.assertEqual(len(rows), 12)
            self.assertTrue(all(row["quality_status"] == "pending_validation" for row in rows))
            self.assertTrue(all(row["extraction_status"] == "visual_candidate_not_gold" for row in rows))
            roa = [row for row in rows if row["metric"] == "bank.roa"]
            roe = [row for row in rows if row["metric"] == "bank.roe"]
            self.assertEqual(len(roa), 4)
            self.assertEqual(len(roe), 8)
            self.assertAlmostEqual(roa[0]["value"], 2.2185, places=4)
            self.assertEqual({row["variant"] for row in roe}, {"parent_attributable_equity", "total_consolidated_equity"})
            parsed = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(parsed), 12)


if __name__ == "__main__":
    unittest.main()
