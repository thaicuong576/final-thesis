import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_review_ledger import REVIEW_LEDGER_FIELDS
from scripts.merge_disjoint_review_ledgers import (
    merge_disjoint_review_ledgers,
    merge_disjoint_review_ledgers_many,
)


def _row(target_id: str, decision: str = "missing") -> dict[str, str]:
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
    for prefix, checker_id in (("checker_a", "checker-A"), ("checker_b", "checker-B")):
        row[f"{prefix}_id"] = checker_id
        row[f"{prefix}_decision"] = decision
        row[f"{prefix}_checked_at"] = "2026-09-07T00:00:00Z"
        row[f"{prefix}_notes"] = "independently reviewed"
    return row


def _write(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class MergeDisjointReviewLedgerTests(unittest.TestCase):
    def test_merges_disjoint_ledgers_in_register_order_and_preserves_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            prior = root / "prior.csv"
            incremental = root / "incremental.csv"
            targets = [
                "MBB:2024_Q1:bank.roa",
                "MBB:2024_Q1:bank.npl_g35",
            ]
            _write(register, [{"target_id": target} for target in targets], ["target_id"])
            prior_row = _row(targets[0])
            prior_row.update(
                {
                    "adjudication_decision": "missing",
                    "adjudicator_id": "adjudicator-1",
                    "adjudicated_at": "2026-09-07T00:00:00Z",
                    "adjudication_reason": "carried forward from prior packet",
                }
            )
            _write(prior, [prior_row], list(REVIEW_LEDGER_FIELDS))
            _write(incremental, [_row(targets[1])], list(REVIEW_LEDGER_FIELDS))

            merged = merge_disjoint_review_ledgers(prior, incremental, register)

        self.assertEqual([row["target_id"] for row in merged], targets)
        self.assertEqual(merged[0]["adjudication_reason"], "carried forward from prior packet")
        self.assertEqual(merged[1]["checker_a_decision"], "missing")

    def test_refuses_overlapping_ledgers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            prior = root / "prior.csv"
            incremental = root / "incremental.csv"
            target = "MBB:2024_Q1:bank.roa"
            _write(register, [{"target_id": target}], ["target_id"])
            _write(prior, [_row(target)], list(REVIEW_LEDGER_FIELDS))
            _write(incremental, [_row(target)], list(REVIEW_LEDGER_FIELDS))

            with self.assertRaisesRegex(ValueError, "overlap"):
                merge_disjoint_review_ledgers(prior, incremental, register)

    def test_refuses_incomplete_incremental_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            prior = root / "prior.csv"
            incremental = root / "incremental.csv"
            targets = [
                "MBB:2024_Q1:bank.roa",
                "MBB:2024_Q1:bank.npl_g35",
            ]
            _write(register, [{"target_id": target} for target in targets], ["target_id"])
            _write(prior, [_row(targets[0])], list(REVIEW_LEDGER_FIELDS))
            incomplete = _row(targets[1])
            incomplete["checker_b_decision"] = ""
            _write(incremental, [incomplete], list(REVIEW_LEDGER_FIELDS))

            with self.assertRaisesRegex(ValueError, "not eligible"):
                merge_disjoint_review_ledgers(prior, incremental, register)

    def test_merges_three_disjoint_ledgers_as_one_atomic_union(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            paths = [root / f"ledger-{index}.csv" for index in range(3)]
            targets = [
                "ACB:2024_Q1:bank.roa",
                "MBB:2024_Q1:bank.roa",
                "VCB:2024_Q1:bank.roa",
            ]
            _write(register, [{"target_id": target} for target in targets], ["target_id"])
            for path, target in zip(paths, targets):
                _write(path, [_row(target)], list(REVIEW_LEDGER_FIELDS))

            merged = merge_disjoint_review_ledgers_many(paths, register)

        self.assertEqual([row["target_id"] for row in merged], targets)

    def test_many_merge_rejects_partial_union(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register = root / "register.csv"
            prior = root / "prior.csv"
            incremental = root / "incremental.csv"
            targets = [
                "ACB:2024_Q1:bank.roa",
                "MBB:2024_Q1:bank.roa",
                "VCB:2024_Q1:bank.roa",
            ]
            _write(register, [{"target_id": target} for target in targets], ["target_id"])
            _write(prior, [_row(targets[0])], list(REVIEW_LEDGER_FIELDS))
            _write(incremental, [_row(targets[1])], list(REVIEW_LEDGER_FIELDS))

            with self.assertRaisesRegex(ValueError, "union does not equal"):
                merge_disjoint_review_ledgers_many((prior, incremental), register)


if __name__ == "__main__":
    unittest.main()
