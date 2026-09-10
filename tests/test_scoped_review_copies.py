import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_scoped_reviewer_copies import build_scoped_reviewer_copies
from scripts.build_review_ledger import REVIEWER_COPY_FIELDS


def _register_rows() -> list[dict[str, str]]:
    rows = []
    for ticker in ("ACB", "TCB"):
        for period in ("2024_Q1", "2024_Q2"):
            rows.append(
                {
                    "target_id": f"{ticker}:{period}:bank.npl_g35",
                    "ticker": ticker,
                    "sector": "bank",
                    "metric": "bank.npl_g35",
                    "period": period,
                    "review_status": "pending_official_check",
                    "vendor_value": "0.02",
                    "notes": "vendor candidate only",
                }
            )
    rows.append(
        {
            "target_id": "VPB:2024_Q1:bank.npl_g35",
            "ticker": "VPB",
            "sector": "bank",
            "metric": "bank.npl_g35",
            "period": "2024_Q1",
            "review_status": "pending_official_check",
            "vendor_value": "0.03",
            "notes": "vendor candidate only",
        }
    )
    return rows


class ScopedReviewCopyTests(unittest.TestCase):
    def _write_inputs(self, root: Path, status: str = "proposed_metric_reduction_pending_advisor_confirmation") -> tuple[Path, Path]:
        register = root / "register.csv"
        rows = _register_rows()
        with register.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        scope = root / "scope.json"
        scope.write_text(
            json.dumps(
                {
                    "scope_id": "fallback-4-test",
                    "status": status,
                    "target_cell_count": 4,
                    "issuers": ["ACB", "TCB"],
                    "periods": [
                        {"period": "2024_Q1"},
                        {"period": "2024_Q2"},
                    ],
                    "primary_metrics": ["bank.npl_g35"],
                }
            ),
            encoding="utf-8",
        )
        return register, scope

    def test_materializes_only_scope_cells_as_blank_blind_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register, scope = self._write_inputs(root)
            output_dir = root / "review"

            result = build_scoped_reviewer_copies(register, scope, output_dir)

            self.assertEqual(result["scope_id"], "fallback-4-test")
            self.assertEqual(result["target_cell_count"], 4)
            for filename in ("review-checker-a-blind-template-v1.csv", "review-checker-b-blind-template-v1.csv"):
                with (output_dir / filename).open("r", encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), 4)
                self.assertEqual(set(rows[0]), set(REVIEWER_COPY_FIELDS))
                self.assertNotIn("VPB:2024_Q1:bank.npl_g35", {row["target_id"] for row in rows})
                for row in rows:
                    self.assertEqual(row["decision"], "")
                    self.assertEqual(row["notes"], "")
            self.assertTrue((output_dir / "scope-review-manifest.json").exists())

    def test_refuses_a_scope_that_is_not_pending_advisor_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            register, scope = self._write_inputs(root, status="gold")

            with self.assertRaises(ValueError):
                build_scoped_reviewer_copies(register, scope, root / "review")


if __name__ == "__main__":
    unittest.main()
