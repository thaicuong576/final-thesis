"""Unit tests for pure financial filing validation layer.

Phase: INGEST-2 (D-086).
Tests each validation check code (pass, fail, edge/boundary cases),
synthetic row sets, and real bank data (ACB FY2025).
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
import unittest

from thesis_data.filing_extract import CandidateRow, INPUT_METRICS, METRIC_LABELS_VI, RowIssue
from thesis_data.filing_validate import CheckResult, ValidationResult, validate_filing_rows


def _make_valid_20_rows(confirmed: bool = True) -> list[CandidateRow]:
    """Build a baseline set of 20 fully consistent candidate rows."""
    # Target period: 2025_Q4, Prior period: 2024_Q4
    # Realistically scaled bank figures in billion VND
    values_target = {
        "bank.input.npl_group_3_balance": "100.0",
        "bank.input.npl_group_4_balance": "150.0",
        "bank.input.npl_group_5_balance": "250.0",
        "bank.input.gross_customer_loans": "25000.0",  # NPL = 500 / 25000 = 2%
        "bank.input.loan_loss_provisions": "600.0",   # 0 <= 600 <= 25000
        "bank.input.profit_after_tax": "1500.0",      # 1400 + 100 = 1500
        "bank.input.total_assets": "50000.0",         # > loans, > equity
        "bank.input.parent_attributable_profit": "1400.0",
        "bank.input.total_equity": "5000.0",          # > nci
        "bank.input.non_controlling_interests": "100.0",
    }
    values_prior = {
        "bank.input.npl_group_3_balance": "90.0",
        "bank.input.npl_group_4_balance": "130.0",
        "bank.input.npl_group_5_balance": "230.0",
        "bank.input.gross_customer_loans": "22000.0",
        "bank.input.loan_loss_provisions": "550.0",
        "bank.input.profit_after_tax": "1300.0",
        "bank.input.total_assets": "45000.0",
        "bank.input.parent_attributable_profit": "1200.0",
        "bank.input.total_equity": "4500.0",
        "bank.input.non_controlling_interests": "100.0",
    }

    rows: list[CandidateRow] = []
    for m in INPUT_METRICS:
        # Target
        t_val = values_target[m]
        rows.append(
            CandidateRow(
                row_id=f"{m}:target",
                metric_id=m,
                label_vi=METRIC_LABELS_VI[m],
                period_role="target",
                period_id="2025_Q4",
                value_billion_vnd=t_val,
                extracted_value_billion_vnd=t_val,
                raw_text=f"{METRIC_LABELS_VI[m]} {t_val} 000",
                row_label=METRIC_LABELS_VI[m],
                page=10,
                source="ocr",
                status="candidate",
                edited=False,
                confirmed=confirmed,
            )
        )
        # Prior
        p_val = values_prior[m]
        rows.append(
            CandidateRow(
                row_id=f"{m}:prior",
                metric_id=m,
                label_vi=METRIC_LABELS_VI[m],
                period_role="prior",
                period_id="2024_Q4",
                value_billion_vnd=p_val,
                extracted_value_billion_vnd=p_val,
                raw_text=f"{METRIC_LABELS_VI[m]} {p_val} 000",
                row_label=METRIC_LABELS_VI[m],
                page=10,
                source="ocr",
                status="candidate",
                edited=False,
                confirmed=confirmed,
            )
        )

    return rows


class TestFilingValidatePure(unittest.TestCase):
    def test_baseline_valid_set_passes(self) -> None:
        rows = _make_valid_20_rows(confirmed=True)
        res = validate_filing_rows(rows)
        self.assertEqual(res.status, "pass")
        self.assertTrue(res.ready_to_confirm)
        self.assertEqual(len(res.blocking_reasons_vi), 0)

    def test_missing_required_checks(self) -> None:
        # 1. Missing value
        rows = _make_valid_20_rows(confirmed=True)
        rows[0] = CandidateRow(
            row_id=rows[0].row_id,
            metric_id=rows[0].metric_id,
            label_vi=rows[0].label_vi,
            period_role=rows[0].period_role,
            period_id=rows[0].period_id,
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            confirmed=False,
        )
        res = validate_filing_rows(rows)
        self.assertEqual(res.status, "fail")
        self.assertFalse(res.ready_to_confirm)
        self.assertTrue(any(c.code == "missing_required" for c in res.checks))

        # 2. non_controlling_interests can be 0 if explicitly confirmed
        rows = _make_valid_20_rows(confirmed=True)
        for i, r in enumerate(rows):
            if r.metric_id == "bank.input.non_controlling_interests":
                rows[i] = CandidateRow(
                    row_id=r.row_id,
                    metric_id=r.metric_id,
                    label_vi=r.label_vi,
                    period_role=r.period_role,
                    period_id=r.period_id,
                    value_billion_vnd="0.0",
                    extracted_value_billion_vnd="0.0",
                    raw_text="0",
                    row_label=r.row_label,
                    page=r.page,
                    source="user",
                    status="candidate",
                    edited=True,
                    confirmed=True,
                )
            elif r.metric_id == "bank.input.parent_attributable_profit":
                # PAT = parent + 0 => parent = PAT
                pat_val = "1500.0" if r.period_role == "target" else "1300.0"
                rows[i] = CandidateRow(
                    row_id=r.row_id,
                    metric_id=r.metric_id,
                    label_vi=r.label_vi,
                    period_role=r.period_role,
                    period_id=r.period_id,
                    value_billion_vnd=pat_val,
                    extracted_value_billion_vnd=pat_val,
                    raw_text=pat_val,
                    row_label=r.row_label,
                    page=r.page,
                    source=r.source,
                    status="candidate",
                    confirmed=True,
                )
        res_zero = validate_filing_rows(rows)
        self.assertEqual(res_zero.status, "pass")
        self.assertTrue(res_zero.ready_to_confirm)

    def test_pat_equals_parent_plus_nci(self) -> None:
        rows = _make_valid_20_rows(confirmed=True)
        # PAT is 1500.0. Parent is 1400.0. NCI is 100.0.
        # Test near-tolerance threshold: tolerance = max(0.01, 0.0001 * 1500) = 0.15 billion VND
        # Sát ngưỡng (within tol: 0.10 diff) -> pass
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.profit_after_tax:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="1500.10", extracted_value_billion_vnd="1500.10",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_near = validate_filing_rows(rows)
        self.assertFalse(any(c.code == "pat_equals_parent_plus_nci" for c in res_near.checks))

        # Exceeds tolerance (diff 1.0 > 0.15) -> error
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.profit_after_tax:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="1550.0", extracted_value_billion_vnd="1550.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_fail = validate_filing_rows(rows)
        self.assertEqual(res_fail.status, "fail")
        self.assertFalse(res_fail.ready_to_confirm)
        c = next(c for c in res_fail.checks if c.code == "pat_equals_parent_plus_nci")
        self.assertEqual(c.severity, "error")

    def test_npl_sum_le_loans(self) -> None:
        # Gross loans = 25000.
        # 1. NPL = 500 (2%) -> pass (no check or info)
        rows = _make_valid_20_rows(confirmed=True)
        res = validate_filing_rows(rows)
        self.assertFalse(any(c.code == "npl_sum_le_loans" for c in res.checks))

        # 2. Sát ngưỡng cảnh báo / warning: ratio between 10% and 25%
        # NPL sum = 3000 (12% of 25000) -> warning
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.npl_group_5_balance:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="2750.0", extracted_value_billion_vnd="2750.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_warn = validate_filing_rows(rows)
        c_warn = next((c for c in res_warn.checks if c.code == "npl_sum_le_loans"), None)
        self.assertIsNotNone(c_warn)
        self.assertEqual(c_warn.severity, "warning")
        self.assertEqual(res_warn.status, "warn")
        self.assertTrue(res_warn.ready_to_confirm)  # warnings do not block ready_to_confirm

        # 3. Exceeds 25% or > gross loans -> error
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.npl_group_5_balance:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="10000.0", extracted_value_billion_vnd="10000.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_err = validate_filing_rows(rows)
        c_err = next(c for c in res_err.checks if c.code == "npl_sum_le_loans")
        self.assertEqual(c_err.severity, "error")
        self.assertEqual(res_err.status, "fail")
        self.assertFalse(res_err.ready_to_confirm)

    def test_provisions_range(self) -> None:
        rows = _make_valid_20_rows(confirmed=True)
        # Provisions > gross loans (30000 > 25000)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.loan_loss_provisions:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="30000.0", extracted_value_billion_vnd="30000.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res = validate_filing_rows(rows)
        c = next(c for c in res.checks if c.code == "provisions_range")
        self.assertEqual(c.severity, "error")

    def test_accounting_inequalities(self) -> None:
        # assets <= loans
        rows = _make_valid_20_rows(confirmed=True)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.total_assets:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="20000.0", extracted_value_billion_vnd="20000.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res = validate_filing_rows(rows)
        self.assertTrue(any(c.code == "assets_gt_loans" for c in res.checks))

        # equity < nci
        rows = _make_valid_20_rows(confirmed=True)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.non_controlling_interests:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="6000.0", extracted_value_billion_vnd="6000.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_nci = validate_filing_rows(rows)
        self.assertTrue(any(c.code == "equity_ge_nci" for c in res_nci.checks))

    def test_magnitude_range(self) -> None:
        # total assets < 100 billion (wrong scale / billion parsed as million or typo)
        rows = _make_valid_20_rows(confirmed=True)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.total_assets:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="50.0", extracted_value_billion_vnd="50.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res = validate_filing_rows(rows)
        c = next(c for c in res.checks if c.code == "magnitude_range")
        self.assertEqual(c.severity, "error")

        # negative profit is allowed (loss)
        rows = _make_valid_20_rows(confirmed=True)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.profit_after_tax:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="-500.0", extracted_value_billion_vnd="-500.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
            elif r.row_id == "bank.input.parent_attributable_profit:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="-600.0", extracted_value_billion_vnd="-600.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res_loss = validate_filing_rows(rows)
        # pat = -500, parent = -600, nci = 100. -500 == -600 + 100.
        # Should not have magnitude_range error on profit
        self.assertFalse(any(c.code == "magnitude_range" for c in res_loss.checks))

    def test_yoy_change_warning(self) -> None:
        rows = _make_valid_20_rows(confirmed=True)
        # Total loans increased from 10,000 to 28,000 (+180% > 150%)
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.gross_customer_loans:prior":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="8000.0", extracted_value_billion_vnd="8000.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", confirmed=True,
                )
        res = validate_filing_rows(rows)
        c = next((c for c in res.checks if c.code == "yoy_change"), None)
        self.assertIsNotNone(c)
        self.assertEqual(c.severity, "warning")

    def test_value_in_page_text(self) -> None:
        rows = _make_valid_20_rows(confirmed=True)
        # Value doesn't appear in text and unedited
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.total_assets:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="50000.0", extracted_value_billion_vnd="50000.0",
                    raw_text="No numbers here at all", row_label="Khong co so", page=12,
                    source="ocr", status="candidate", edited=False, confirmed=True,
                )
        res = validate_filing_rows(rows, page_texts={12: "Trang nay khong co so nao"})
        c = next((c for c in res.checks if c.code == "value_in_page_text"), None)
        self.assertIsNotNone(c)
        self.assertEqual(c.severity, "warning")

        # But if edited=True and source="user", check is exempted
        for i, r in enumerate(rows):
            if r.row_id == "bank.input.total_assets:target":
                rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="50000.0", extracted_value_billion_vnd="50000.0",
                    raw_text="No numbers here", row_label="Khong co so", page=12,
                    source="user", status="candidate", edited=True, confirmed=True,
                )
        res_exempt = validate_filing_rows(rows, page_texts={12: "Trang nay khong co so nao"})
        self.assertFalse(any(c.code == "value_in_page_text" for c in res_exempt.checks))

    def test_real_bank_data_acb_2025(self) -> None:
        csv_path = Path("data/onboarding/top10-2025/ACB-2025q4.csv")
        if not csv_path.exists():
            self.skipTest("ACB-2025q4.csv not found in worktree")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        candidate_rows: list[CandidateRow] = []
        for r in csv_rows:
            m_id = r["metric_id"]
            p_id = r["period_id"]
            role = "target" if p_id == "2025_Q4" else "prior"
            candidate_rows.append(
                CandidateRow(
                    row_id=f"{m_id}:{role}",
                    metric_id=m_id,
                    label_vi=METRIC_LABELS_VI.get(m_id, m_id),
                    period_role=role,
                    period_id=p_id,
                    value_billion_vnd=r["value"],
                    extracted_value_billion_vnd=r["value"],
                    raw_text=r["source_locator"],
                    row_label=r["source_locator"],
                    page=50,
                    source="user",
                    status="candidate",
                    edited=True,
                    confirmed=True,
                )
            )

        # ACB 2025 CSV has 15 rows (the 5 prior credit metrics are from 2024 comparison column)
        # Supplement the 5 prior credit rows from audited FY2024 figures (from quarterly-top10/inputs.csv)
        prior_credit_supplements = {
            "bank.input.gross_customer_loans": "571996.489",
            "bank.input.loan_loss_provisions": "6739.556",
            "bank.input.npl_group_3_balance": "923.291",
            "bank.input.npl_group_4_balance": "978.211",
            "bank.input.npl_group_5_balance": "6748.132",
        }
        existing_keys = {(r.metric_id, r.period_role) for r in candidate_rows}
        for m_id, val in prior_credit_supplements.items():
            if (m_id, "prior") not in existing_keys:
                candidate_rows.append(
                    CandidateRow(
                        row_id=f"{m_id}:prior",
                        metric_id=m_id,
                        label_vi=METRIC_LABELS_VI.get(m_id, m_id),
                        period_role="prior",
                        period_id="2024_Q4",
                        value_billion_vnd=val,
                        extracted_value_billion_vnd=val,
                        raw_text=val,
                        row_label=m_id,
                        page=50,
                        source="user",
                        status="candidate",
                        edited=True,
                        confirmed=True,
                    )
                )

        # 1. Base real ACB data should pass validation
        res = validate_filing_rows(candidate_rows)
        self.assertEqual(res.status, "pass")
        self.assertTrue(res.ready_to_confirm)

        # 2. Deliberately alter profit to trigger pat_equals_parent_plus_nci
        broken_rows = list(candidate_rows)
        for i, r in enumerate(broken_rows):
            if r.row_id == "bank.input.profit_after_tax:target":
                broken_rows[i] = CandidateRow(
                    row_id=r.row_id, metric_id=r.metric_id, label_vi=r.label_vi,
                    period_role=r.period_role, period_id=r.period_id,
                    value_billion_vnd="99999.0", extracted_value_billion_vnd="99999.0",
                    raw_text=r.raw_text, row_label=r.row_label, page=r.page,
                    source=r.source, status="candidate", edited=True, confirmed=True,
                )
        res_broken = validate_filing_rows(broken_rows)
        self.assertEqual(res_broken.status, "fail")
        self.assertFalse(res_broken.ready_to_confirm)
        self.assertTrue(any(c.code == "pat_equals_parent_plus_nci" for c in res_broken.checks))
