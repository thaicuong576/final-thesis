import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_mbb_official_credit_candidates import build


class MbbOfficialCreditCandidateTests(unittest.TestCase):
    def test_builds_eight_pending_credit_rows_with_reproducible_values(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "credit.jsonl"
            rows = build(output)
            parsed = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), 8)
        self.assertEqual(len(parsed), 8)
        self.assertEqual({row["quality_status"] for row in rows}, {"pending_validation"})
        values = {
            (row["period"], row["metric"]): row["value"]
            for row in rows
        }
        self.assertEqual(values[("2024_Q1", "bank.npl_g35")], 2.4856)
        self.assertEqual(values[("2024_Q2", "bank.npl_g35")], 1.6360)
        self.assertEqual(values[("2024_Q3", "bank.npl_g35")], 2.2342)
        self.assertEqual(values[("2024_Q4", "bank.npl_g35")], 1.6205)
        self.assertEqual(values[("2024_Q1", "bank.llr_coverage")], 80.0575)
        self.assertEqual(values[("2024_Q2", "bank.llr_coverage")], 101.7372)
        self.assertEqual(values[("2024_Q3", "bank.llr_coverage")], 68.7720)
        self.assertEqual(values[("2024_Q4", "bank.llr_coverage")], 92.2484)
        self.assertTrue(all(row["extraction_status"] == "visual_candidate_not_gold" for row in rows))


if __name__ == "__main__":
    unittest.main()
