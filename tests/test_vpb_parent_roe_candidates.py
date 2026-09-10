import unittest

from scripts.build_vpb_parent_roe_candidates import build_candidates


class VPBParentROECandidateTests(unittest.TestCase):
    def test_builds_four_parent_equity_candidates(self):
        rows = build_candidates()
        self.assertEqual(len(rows), 4)
        self.assertEqual([row["value"] for row in rows], [8.0671, 8.5867, 9.6445, 11.4117])
        self.assertTrue(all(row["variant"] == "parent_attributable_equity" for row in rows))
        self.assertTrue(all(row["quality_status"] == "pending_validation" for row in rows))

    def test_q1_parent_equity_subtracts_nci(self):
        row = build_candidates()[0]
        facts = row["input_facts"]
        self.assertEqual(facts["current_parent_attributable_equity"], 138197730)
        self.assertEqual(facts["prior_parent_attributable_equity"], 134631033)
        self.assertEqual(facts["parent_profit_ttm"], 11004682)


if __name__ == "__main__":
    unittest.main()
