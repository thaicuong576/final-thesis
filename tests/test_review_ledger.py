import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_review_ledger import (
    REVIEW_LEDGER_FIELDS,
    REVIEWER_COPY_FIELDS,
    accepted_reviewer_prefix,
    apply_adjudication_overlay,
    apply_reviewer_addendum,
    audit_review_rows,
    audit_reviewer_copy_rows,
    build_review_ledger,
    build_reviewer_copy,
    build_reviewer_copy_from_rows,
    merge_reviewer_copies,
    write_reviewer_copy,
    write_review_ledger,
)


def _register_row(target_id: str = "VCB:2024_Q1:bank.npl_g35") -> dict[str, str]:
    ticker, period, metric = target_id.split(":", 2)
    return {
        "target_id": target_id,
        "ticker": ticker,
        "sector": "bank",
        "metric": metric,
        "period": period,
        "review_status": "pending_official_check",
        "vendor_observation_ids": "vendor-1",
        "vendor_value": "0.02",
        "vendor_unit": "vendor_ratio_decimal_or_native",
        "vendor_period_basis": "TTM",
        "vendor_source_id": "vendor-source",
        "vendor_source_url": "https://vendor.test/data",
        "vendor_source_locator": "data[0].npl",
        "official_value": "",
        "official_unit": "",
        "official_period_basis": "",
        "official_source_id": "",
        "official_source_url": "",
        "official_source_locator": "",
        "consolidation_basis": "",
        "definition_match": "",
        "reconciliation_result": "",
        "checker_id": "",
        "checked_at": "",
        "notes": "pending",
    }


def _completed_checker(row: dict[str, str], prefix: str, checker_id: str, decision: str) -> None:
    row[f"{prefix}_id"] = checker_id
    row[f"{prefix}_decision"] = decision
    row[f"{prefix}_checked_at"] = "2026-09-05T00:00:00Z"
    row[f"{prefix}_notes"] = "reviewed"
    if decision == "accepted":
        row[f"{prefix}_value"] = "1.2"
        row[f"{prefix}_unit"] = "%"
        row[f"{prefix}_period_basis"] = "point_in_time"
        row[f"{prefix}_source_id"] = "official-source"
        row[f"{prefix}_source_url"] = "https://issuer.test/filing"
        row[f"{prefix}_source_locator"] = "pdf_page:17;row:NPL"
        row[f"{prefix}_consolidation_basis"] = "consolidated"
        row[f"{prefix}_definition_match"] = "yes"


class ReviewLedgerTests(unittest.TestCase):
    def test_builds_two_checker_slots_without_mutating_register(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            output = root / "review-ledger.csv"
            fields = list(_register_row())
            with register.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(_register_row())

            rows = build_review_ledger(register)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["target_id"], "VCB:2024_Q1:bank.npl_g35")
            self.assertEqual(rows[0]["checker_a_decision"], "")
            self.assertEqual(rows[0]["checker_b_decision"], "")
            self.assertEqual(rows[0]["adjudication_decision"], "")
            self.assertEqual(set(rows[0]), set(REVIEW_LEDGER_FIELDS))

            write_review_ledger(rows, output)
            self.assertTrue(output.exists())
            self.assertEqual(_register_row()["review_status"], "pending_official_check")

    def test_review_requires_distinct_checker_ids_and_adjudicates_disagreement(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "accepted")
        _completed_checker(row, "checker_b", "checker-a", "missing")

        same_id = audit_review_rows([row])
        self.assertFalse(same_id.eligible)
        self.assertIn("same_checker_id", same_id.blockers)

        row["checker_b_id"] = "checker-b"
        disagreement = audit_review_rows([row])
        self.assertFalse(disagreement.eligible)
        self.assertIn("unadjudicated_disagreement", disagreement.blockers)

        row["adjudication_decision"] = "conflicting"
        row["adjudicator_id"] = "adjudicator-1"
        row["adjudicated_at"] = "2026-09-05T00:00:00Z"
        row["adjudication_reason"] = "The two sources use non-equivalent definitions."
        self.assertTrue(audit_review_rows([row]).eligible)

    def test_blind_reviewer_copies_merge_without_exposing_the_other_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            checker_a_path = root / "checker-a.csv"
            checker_b_path = root / "checker-b.csv"
            merged_path = root / "merged.csv"
            fields = list(_register_row())
            with register.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(_register_row())

            checker_a = build_reviewer_copy(register)
            checker_b = build_reviewer_copy(register)
            self.assertEqual(set(checker_a[0]), set(REVIEWER_COPY_FIELDS))
            _complete_copy(checker_a[0], "checker-a", "accepted")
            _complete_copy(checker_b[0], "checker-b", "accepted")
            write_reviewer_copy(checker_a, checker_a_path)
            write_reviewer_copy(checker_b, checker_b_path)

            self.assertTrue(audit_reviewer_copy_rows(checker_a).eligible)
            merged = merge_reviewer_copies(checker_a_path, checker_b_path)
            self.assertEqual(merged[0]["checker_a_id"], "checker-a")
            self.assertEqual(merged[0]["checker_b_id"], "checker-b")
            write_review_ledger(merged, merged_path)
            self.assertTrue(merged_path.exists())

            checker_b[0]["checker_id"] = "checker-a"
            write_reviewer_copy(checker_b, root / "checker-b-same-id.csv")
            with self.assertRaises(ValueError):
                merge_reviewer_copies(checker_a_path, root / "checker-b-same-id.csv")

    def test_blind_reviewer_copy_excludes_vendor_candidate_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            fields = list(_register_row())
            with register.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(_register_row())

            copy = build_reviewer_copy(register)[0]

            self.assertEqual(
                set(copy),
                {
                    "target_id",
                    "ticker",
                    "sector",
                    "metric",
                    "period",
                    "checker_id",
                    "decision",
                    "value",
                    "unit",
                    "period_basis",
                    "source_id",
                    "source_url",
                    "source_locator",
                    "consolidation_basis",
                    "definition_match",
                    "checked_at",
                    "notes",
                },
            )
            self.assertNotIn("vendor_value", copy)
            self.assertNotIn("vendor_source_url", copy)
            self.assertEqual(copy["notes"], "")

    def test_reviewer_copy_can_be_built_from_filtered_register_rows(self):
        rows = build_reviewer_copy_from_rows([_register_row()])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_id"], "VCB:2024_Q1:bank.npl_g35")
        self.assertNotIn("vendor_value", rows[0])
        self.assertEqual(rows[0]["decision"], "")

    def test_committed_blind_templates_have_no_prefilled_reviewer_fields(self):
        root = Path(__file__).resolve().parents[1] / "data" / "reconciliation" / "gold-bank-2025-pilot-v1"
        identity_fields = {"target_id", "ticker", "sector", "metric", "period"}
        reviewer_owned = [field for field in REVIEWER_COPY_FIELDS if field not in identity_fields]
        for filename in (
            "review-checker-a-blind-template-v2.csv",
            "review-checker-b-blind-template-v2.csv",
        ):
            with (root / filename).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 48)
            for row in rows:
                for field in reviewer_owned:
                    self.assertEqual(row[field], "", f"{filename} prefilled {field}")

    def test_accepted_decision_requires_source_mapping_fields(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        row["checker_a_id"] = "checker-a"
        row["checker_a_decision"] = "accepted"
        row["checker_a_checked_at"] = "2026-09-05T00:00:00Z"
        row["checker_a_notes"] = "accepted"
        audit = audit_review_rows([row])
        self.assertFalse(audit.eligible)
        self.assertIn("checker_b_incomplete", " ".join(audit.blockers))
        self.assertIn("accepted_missing_source_mapping", " ".join(audit.blockers))

    def test_accepted_value_or_source_disagreement_requires_adjudication(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "accepted")
        _completed_checker(row, "checker_b", "checker-b", "accepted")

        row["checker_b_value"] = "1.3"
        disagreement = audit_review_rows([row])
        self.assertFalse(disagreement.eligible)
        self.assertIn("accepted_mapping_disagreement", disagreement.blockers)

        row["checker_b_value"] = "1.2"
        row["checker_b_source_id"] = "another-official-source"
        disagreement = audit_review_rows([row])
        self.assertFalse(disagreement.eligible)
        self.assertIn("accepted_mapping_disagreement", disagreement.blockers)

    def test_adjudication_source_slot_resolves_accepted_mapping_disagreement(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "accepted")
        _completed_checker(row, "checker_b", "checker-b", "accepted")
        row["checker_b_value"] = "1.3"
        row["checker_b_source_id"] = "another-official-source"

        row["adjudication_decision"] = "accepted"
        row["adjudication_source_slot"] = "checker_b"
        row["adjudicator_id"] = "adjudicator-1"
        row["adjudicated_at"] = "2026-09-05T00:00:00Z"
        row["adjudication_reason"] = "Checker B's official mapping is the canonical source variant."

        audit = audit_review_rows([row])
        self.assertTrue(audit.eligible)
        self.assertEqual(accepted_reviewer_prefix(row), "checker_b")

    def test_adjudication_can_resolve_agreed_conflict_as_reasoned_missing(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "conflicting")
        _completed_checker(row, "checker_b", "checker-b", "conflicting")

        row["adjudication_decision"] = "missing"
        row["adjudicator_id"] = "adjudicator-1"
        row["adjudicated_at"] = "2026-09-05T00:00:00Z"
        row["adjudication_reason"] = "The official source exposes incompatible scope variants."

        audit = audit_review_rows([row])
        self.assertTrue(audit.eligible)
        self.assertIsNone(accepted_reviewer_prefix(row))

    def test_adjudication_overlay_preserves_checker_reviews_and_fills_only_adjudication(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "conflicting")
        _completed_checker(row, "checker_b", "checker-b", "conflicting")
        overlay = {
            "target_id": row["target_id"],
            "adjudication_decision": "missing",
            "adjudication_source_slot": "",
            "adjudicator_id": "adjudicator-1",
            "adjudicated_at": "2026-09-05T00:00:00Z",
            "adjudication_reason": "The official source exposes incompatible scope variants.",
        }

        result = apply_adjudication_overlay([row], [overlay])

        self.assertEqual(result[0]["checker_a_decision"], "conflicting")
        self.assertEqual(result[0]["checker_b_decision"], "conflicting")
        self.assertEqual(result[0]["adjudication_decision"], "missing")
        self.assertTrue(audit_review_rows(result).eligible)

    def test_reviewer_addendum_updates_new_checker_route_without_mutating_checker_a(self):
        row = build_review_ledger_from_rows([_register_row()])[0]
        _completed_checker(row, "checker_a", "checker-a", "missing")
        _completed_checker(row, "checker_b", "checker-b", "missing")
        addendum = {
            "target_id": row["target_id"],
            "ticker": "VCB",
            "sector": "bank",
            "metric": "bank.npl_g35",
            "period": "2024_Q1",
            "checker_id": "checker-b",
            "decision": "accepted",
            "value": "1.2",
            "unit": "%",
            "period_basis": "point_in_time",
            "source_id": "official-source",
            "source_url": "https://issuer.test/filing",
            "source_locator": "pdf_page:17;row:NPL",
            "consolidation_basis": "consolidated",
            "definition_match": "yes",
            "checked_at": "2026-09-05T00:00:00Z",
            "notes": "new official route reviewed",
        }

        result = apply_reviewer_addendum(
            [row],
            [addendum],
            adjudicator_id="adjudicator-1",
            adjudicated_at="2026-09-05T00:00:00Z",
            adjudication_reason="The addendum supplies a newly reviewed official route; select checker B.",
        )

        self.assertEqual(result[0]["checker_a_decision"], "missing")
        self.assertEqual(result[0]["checker_b_decision"], "accepted")
        self.assertEqual(result[0]["checker_b_value"], "1.2")
        self.assertEqual(result[0]["adjudication_decision"], "accepted")
        self.assertEqual(result[0]["adjudication_source_slot"], "checker_b")
        self.assertTrue(audit_review_rows(result).eligible)


def build_review_ledger_from_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Test helper that writes a temporary register before calling the public API."""
    with tempfile.TemporaryDirectory() as directory:
        register = Path(directory) / "register.csv"
        with register.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return build_review_ledger(register)


def _complete_copy(row: dict[str, str], checker_id: str, decision: str) -> None:
    row["checker_id"] = checker_id
    row["decision"] = decision
    row["checked_at"] = "2026-09-05T00:00:00Z"
    row["notes"] = "reviewed"
    if decision == "accepted":
        row.update(
            {
                "value": "1.2",
                "unit": "%",
                "period_basis": "point_in_time",
                "source_id": "official-source",
                "source_url": "https://issuer.test/filing",
                "source_locator": "pdf_page:17;row:NPL",
                "consolidation_basis": "consolidated",
                "definition_match": "yes",
            }
        )


if __name__ == "__main__":
    unittest.main()
