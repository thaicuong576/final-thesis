import unittest

from scripts.build_review_ledger import (
    REVIEW_LEDGER_FIELDS,
    audit_review_rows,
)
from scripts.replace_review_targets import replace_review_targets, replace_semantic_targets


def _row(target_id: str, decision: str, checker_id: str, value: str) -> dict[str, str]:
    ticker, period, metric = target_id.split(":", 2)
    row = {field: "" for field in REVIEW_LEDGER_FIELDS}
    row.update(
        {
            "target_id": target_id,
            "ticker": ticker,
            "sector": "bank",
            "metric": metric,
            "period": period,
        }
    )
    for prefix in ("checker_a", "checker_b"):
        row[f"{prefix}_id"] = f"{checker_id}-{prefix}"
        row[f"{prefix}_decision"] = decision
        row[f"{prefix}_checked_at"] = "2026-09-07T17:00:00+07:00"
        row[f"{prefix}_notes"] = "reviewed"
        if decision == "accepted":
            row[f"{prefix}_value"] = value
            row[f"{prefix}_unit"] = "%"
            row[f"{prefix}_period_basis"] = "ttm"
            row[f"{prefix}_source_id"] = "official-source"
            row[f"{prefix}_source_url"] = "https://issuer.test/filing"
            row[f"{prefix}_source_locator"] = "pdf_pages:4-8"
            row[f"{prefix}_consolidation_basis"] = "consolidated"
            row[f"{prefix}_definition_match"] = "yes"
    return row


class ReplaceReviewTargetsTests(unittest.TestCase):
    def test_replaces_only_unresolved_target_and_preserves_context(self):
        target = "MBB:2024_Q1:bank.roe"
        base = _row(target, "conflicting", "old-checker", "")
        base["register_review_status"] = "adjudicated_missing"
        base["adjudication_decision"] = "missing"
        base["adjudicator_id"] = "old-adjudicator"
        base["adjudicated_at"] = "2026-09-07T16:00:00+07:00"
        base["adjudication_reason"] = "old unresolved denominator"

        fresh = _row(target, "accepted", "fresh-checker", "21.2468")
        fresh["adjudication_decision"] = "accepted"
        fresh["adjudication_source_slot"] = "checker_b"
        fresh["adjudicator_id"] = "new-adjudicator"
        fresh["adjudicated_at"] = "2026-09-07T17:30:00+07:00"
        fresh["adjudication_reason"] = "frozen parent-attributable-equity convention"

        result = replace_review_targets([base], [fresh])

        self.assertEqual(result[0]["register_review_status"], "adjudicated_missing")
        self.assertEqual(result[0]["checker_a_decision"], "accepted")
        self.assertEqual(result[0]["checker_b_decision"], "accepted")
        self.assertEqual(result[0]["checker_b_value"], "21.2468")
        self.assertEqual(result[0]["adjudication_decision"], "accepted")
        self.assertTrue(audit_review_rows(result).eligible)

    def test_refuses_to_replace_already_accepted_target(self):
        target = "MBB:2024_Q1:bank.roe"
        base = _row(target, "accepted", "old-checker", "21.2468")
        fresh = _row(target, "accepted", "fresh-checker", "21.2468")
        fresh["adjudication_decision"] = "accepted"
        fresh["adjudication_source_slot"] = "checker_b"
        fresh["adjudicator_id"] = "new-adjudicator"
        fresh["adjudicated_at"] = "2026-09-07T17:30:00+07:00"
        fresh["adjudication_reason"] = "new review"

        with self.assertRaises(ValueError):
            replace_review_targets([base], [fresh])

    def test_semantic_replacement_requires_reason_and_marks_correction(self):
        target = "VPB:2024_Q1:bank.roe"
        base = _row(target, "accepted", "old-checker", "7.7845")
        fresh = _row(target, "accepted", "fresh-checker", "8.0671")
        fresh["adjudication_decision"] = "accepted"
        fresh["adjudication_source_slot"] = "checker_b"
        fresh["adjudicator_id"] = "semantic-adjudicator"
        fresh["adjudicated_at"] = "2026-09-07T18:00:00+07:00"
        fresh["adjudication_reason"] = "parent-equity convention"

        result = replace_semantic_targets(
            [base],
            [fresh],
            reason="harmonize VPB ROE denominator",
        )

        self.assertEqual(result[0]["checker_b_value"], "8.0671")
        self.assertIn("semantic_correction:harmonize VPB ROE denominator", result[0]["adjudication_reason"])
        self.assertIn("replaced_prior_decision:accepted", result[0]["adjudication_reason"])
        self.assertTrue(audit_review_rows(result).eligible)

        with self.assertRaises(ValueError):
            replace_semantic_targets([base], [fresh], reason=" ")


if __name__ == "__main__":
    unittest.main()
