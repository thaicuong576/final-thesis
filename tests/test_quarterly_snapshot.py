"""D-079: multi-period operational bank snapshot with interim TTM formulas."""

from __future__ import annotations

import csv
import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from thesis_data.canonical_snapshot import _expected_input_periods
from thesis_data.metrics import operational_derived_formula

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build_quarterly_snapshot", ROOT / "scripts" / "build_quarterly_snapshot.py")
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

URL = "https://example.org/{b}-{p}.pdf"


def _rows(bank: str, scale: int) -> list[list[str]]:
    """Two years of synthetic inputs (billion VND) for one bank."""
    rows = []
    for period, assets, equity, pat in (
        ("2023_Q2", None, None, 40), ("2023_Q4", 1000, 100, 90),
        ("2024_Q2", 1100, 110, 50), ("2024_Q4", 1200, 120, 110),
    ):
        p = {
            "bank.input.profit_after_tax": pat * scale,
            "bank.input.parent_attributable_profit": pat * scale - 1,
        }
        if assets:
            p.update({
                "bank.input.total_assets": assets * scale,
                "bank.input.total_equity": equity * scale,
                "bank.input.non_controlling_interests": 2,
            })
        if period.startswith("2024"):
            p.update({
                "bank.input.npl_group_3_balance": 3, "bank.input.npl_group_4_balance": 4,
                "bank.input.npl_group_5_balance": 5, "bank.input.gross_customer_loans": 600 * scale,
                "bank.input.loan_loss_provisions": 15,
            })
        for metric, value in p.items():
            basis = "ytd" if metric in builder.YTD else "point_in_time"
            rows.append([bank, metric, period, str(value), "billion_vnd", basis,
                         "pdf_page=3; printed_page=1; section=statement", URL.format(b=bank, p=period), ""])
    return rows


class QuarterlySnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.inputs = self.tmp / "inputs.csv"
        with self.inputs.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entity_id", "metric_id", "period_id", "value", "unit", "period_basis",
                        "source_locator", "source_url", "source_sha256"])
            for bank, scale in (("AAA", 1), ("BBB", 2), ("CCC", 3)):
                w.writerows(_rows(bank, scale))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_interim_formula_uses_ttm_flow_over_year_average(self) -> None:
        spec = operational_derived_formula("bank.roa", "roa-ttm-interim-v1")
        result = spec.calculate((Decimal(50), Decimal(40), Decimal(90), Decimal(1100), Decimal(1000)))
        self.assertEqual(result.value, Decimal("9.5238"))  # (50-40+90) / 1050
        self.assertEqual(result.formula_version, "roa-ttm-interim-v1")
        self.assertEqual(_expected_input_periods("2024_Q2", "interim_ttm", 5),
                         ("2024_Q2", "2023_Q2", "2023_Q4", "2024_Q2", "2023_Q4"))
        self.assertEqual(_expected_input_periods("2024_Q4", "annual_ytd", 3), ("2024_Q4", "2024_Q4", "2023_Q4"))

    def test_builds_quarterly_ratios_with_receipts_and_full_peer_group(self) -> None:
        out = self.tmp / "ops.sqlite"
        m = builder.build(self.inputs, out, ratio_periods={"2024_Q2", "2024_Q4"})
        self.assertEqual(m["banks"], ["AAA", "BBB", "CCC"])
        self.assertAlmostEqual(m["ratios"]["AAA"]["2024_Q2"]["bank.roa"], 9.5238, places=3)
        self.assertAlmostEqual(m["ratios"]["AAA"]["2024_Q4"]["bank.roa"], 10.0, places=3)  # 110 / 1100
        self.assertNotIn("2023_Q4", m["ratios"]["AAA"])
        conn = sqlite3.connect(out)
        try:
            members = [r[0] for r in conn.execute("SELECT entity_id FROM peer_universe_members ORDER BY entity_id")]
            receipts = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE derivation_method IS NOT NULL AND metadata_json LIKE '%receipt%'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(members, ["AAA", "BBB", "CCC"])
        self.assertGreater(receipts, 0)

    def test_rejects_protected_output_and_bad_rows(self) -> None:
        with self.assertRaises(builder.BuildError):
            builder.build(self.inputs, self.tmp / "gold-v5.sqlite")
        bad = self.tmp / "bad.csv"
        bad.write_text(self.inputs.read_text(encoding="utf-8").replace("pdf_page=3; printed_page=1", "statement", 1),
                       encoding="utf-8")
        with self.assertRaises(builder.BuildError):
            builder.build(bad, self.tmp / "ops.sqlite")


if __name__ == "__main__":
    unittest.main()
