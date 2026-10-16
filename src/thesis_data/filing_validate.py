"""Pure accounting and consistency validation for financial filing candidate rows.

Phase: INGEST-2 (D-086).
Validates 20 candidate observation rows (10 UPLOAD-1 metrics x 2 periods) against:
- required metric completeness
- balance sheet & income statement accounting identities
- credit quality and provision bounds
- plausible magnitude ranges
- year-over-year balance consistency
- page text digit verification
- forwarded ingestion flags (unit, period mismatch, column identification)

This module is strictly pure logic: NO I/O, NO subprocesses, NO database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from .filing_extract import INPUT_METRICS, CandidateRow, METRIC_LABELS_VI

BALANCE_METRICS = (
    "bank.input.total_assets",
    "bank.input.total_equity",
    "bank.input.gross_customer_loans",
    "bank.input.loan_loss_provisions",
    "bank.input.npl_group_3_balance",
    "bank.input.npl_group_4_balance",
    "bank.input.npl_group_5_balance",
    "bank.input.non_controlling_interests",
)

PROFIT_METRICS = (
    "bank.input.profit_after_tax",
    "bank.input.parent_attributable_profit",
)

ROLE_LABELS_VI: dict[str, str] = {
    "target": "kỳ mục tiêu",
    "prior": "kỳ so sánh",
}


def role_vi(role: str) -> str:
    """Return human-readable Vietnamese label for period role."""
    return ROLE_LABELS_VI.get(role, role)


@dataclass(frozen=True)
class CheckResult:
    """Individual verification check result."""
    code: str
    severity: Literal["error", "warning", "info"]
    message_vi: str
    row_ids: list[str] = field(default_factory=list)
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message_vi": self.message_vi,
            "row_ids": self.row_ids,
        }
        if self.expected is not None:
            d["expected"] = self.expected
        if self.actual is not None:
            d["actual"] = self.actual
        return d


@dataclass(frozen=True)
class ValidationResult:
    """Overall validation summary for a set of filing candidate rows."""
    status: Literal["pass", "warn", "fail"]
    ready_to_confirm: bool
    blocking_reasons_vi: list[str]
    checks: list[CheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ready_to_confirm": self.ready_to_confirm,
            "blocking_reasons_vi": self.blocking_reasons_vi,
            "checks": [c.to_dict() for c in self.checks],
        }


def _parse_dec(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _get_row_prop(row: Any, prop: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(prop, default)
    return getattr(row, prop, default)


def _digits_of(s: str) -> str:
    return re.sub(r"\D", "", s)


def validate_filing_rows(
    rows: Sequence[Any],
    *,
    page_texts: Optional[Dict[int, str]] = None,
) -> ValidationResult:
    """Validate 20 candidate observation rows and return structured ValidationResult.

    Args:
        rows: Sequence of CandidateRow objects or equivalent dictionaries.
        page_texts: Optional mapping of 1-indexed page number to raw page text.
    """
    checks: list[CheckResult] = []
    blocking_reasons: list[str] = []

    # Index rows by (metric_id, period_role) and row_id
    rows_by_metric_role: dict[tuple[str, str], Any] = {}
    rows_by_id: dict[str, Any] = {}

    for r in rows:
        m_id = _get_row_prop(r, "metric_id")
        role = _get_row_prop(r, "period_role")
        r_id = _get_row_prop(r, "row_id")
        if m_id and role:
            rows_by_metric_role[(m_id, role)] = r
        if r_id:
            rows_by_id[r_id] = r

    # 1. missing_required:
    # Check all 10 input metrics x 2 periods.
    # All are required. non_controlling_interests may be 0 if explicitly entered and confirmed.
    unconfirmed_count = 0
    total_expected_rows = 20
    seen_row_count = len(rows)

    for role in ("target", "prior"):
        for m_id in INPUT_METRICS:
            r = rows_by_metric_role.get((m_id, role))
            label = METRIC_LABELS_VI.get(m_id, m_id)
            r_id = f"{m_id}:{role}"
            if r is None:
                checks.append(
                    CheckResult(
                        code="missing_required",
                        severity="error",
                        message_vi=f"Thiếu dòng chỉ tiêu bắt buộc '{label}' cho {role_vi(role)}.",
                        row_ids=[r_id],
                    )
                )
                continue

            val_str = _get_row_prop(r, "value_billion_vnd")
            val_dec = _parse_dec(val_str)
            is_confirmed = bool(_get_row_prop(r, "confirmed", False))
            if not is_confirmed:
                unconfirmed_count += 1

            if val_str is None or str(val_str).strip() == "":
                checks.append(
                    CheckResult(
                        code="missing_required",
                        severity="error",
                        message_vi=f"Chỉ tiêu '{label}' ({role_vi(role)}) chưa có giá trị.",
                        row_ids=[r_id],
                    )
                )
            elif m_id == "bank.input.non_controlling_interests" and val_dec == Decimal("0"):
                # Allowed to be 0 when user explicitly confirms
                if not is_confirmed:
                    # Still missing explicit confirmation
                    pass

    # Helper to retrieve decimal value
    def get_val(metric: str, role: str) -> tuple[Optional[Decimal], str]:
        r = rows_by_metric_role.get((metric, role))
        if r is None:
            return None, f"{metric}:{role}"
        r_id = _get_row_prop(r, "row_id") or f"{metric}:{role}"
        return _parse_dec(_get_row_prop(r, "value_billion_vnd")), r_id

    # 2. pat_equals_parent_plus_nci:
    # PAT = parent_attributable_profit + non_controlling_interests
    # Absolute tolerance: max(0.01 billion, 0.01% of PAT)
    for role in ("target", "prior"):
        pat, pat_id = get_val("bank.input.profit_after_tax", role)
        parent, parent_id = get_val("bank.input.parent_attributable_profit", role)
        nci, nci_id = get_val("bank.input.non_controlling_interests", role)

        if pat is not None and parent is not None and nci is not None:
            expected_pat = parent + nci
            tol = max(Decimal("0.01"), Decimal("0.0001") * abs(pat))
            diff = abs(pat - expected_pat)
            if diff > tol:
                checks.append(
                    CheckResult(
                        code="pat_equals_parent_plus_nci",
                        severity="error",
                        message_vi=(
                            f"Lợi nhuận sau thuế ({pat}) không bằng lợi nhuận cổ đông mẹ ({parent}) + "
                            f"lợi ích CĐKKS ({nci}) ở {role_vi(role)} (lệch {diff:.4f} tỷ, vượt dung sai {tol:.4f} tỷ)."
                        ),
                        row_ids=[pat_id, parent_id, nci_id],
                        expected=str(expected_pat),
                        actual=str(pat),
                    )
                )

    # 3. npl_sum_le_loans:
    # npl_group_3 + npl_group_4 + npl_group_5 <= gross_customer_loans
    # ratio in [0, 0.25]: > 0.25 is error; [0.10, 0.25] is warning
    for role in ("target", "prior"):
        g3, g3_id = get_val("bank.input.npl_group_3_balance", role)
        g4, g4_id = get_val("bank.input.npl_group_4_balance", role)
        g5, g5_id = get_val("bank.input.npl_group_5_balance", role)
        loans, loans_id = get_val("bank.input.gross_customer_loans", role)

        if g3 is not None and g4 is not None and g5 is not None and loans is not None:
            npl_sum = g3 + g4 + g5
            row_ids = [g3_id, g4_id, g5_id, loans_id]
            if loans <= Decimal("0"):
                checks.append(
                    CheckResult(
                        code="npl_sum_le_loans",
                        severity="error",
                        message_vi=f"Dư nợ cho vay khách hàng ở {role_vi(role)} phải lớn hơn 0 (thực tế: {loans}).",
                        row_ids=[loans_id],
                        expected="> 0",
                        actual=str(loans),
                    )
                )
            else:
                ratio = npl_sum / loans
                if npl_sum > loans or ratio > Decimal("0.25") or ratio < Decimal("0"):
                    checks.append(
                        CheckResult(
                            code="npl_sum_le_loans",
                            severity="error",
                            message_vi=(
                                f"Tổng nợ xấu nhóm 3+4+5 ({npl_sum}) vượt ngưỡng quy định so với dư nợ ({loans}), "
                                f"tỷ lệ {float(ratio) * 100:.2f}% ngoài khoảng [0%, 25%]."
                            ),
                            row_ids=row_ids,
                            expected="<= 25% dư nợ",
                            actual=f"{float(ratio) * 100:.2f}%",
                        )
                    )
                elif ratio >= Decimal("0.10"):
                    checks.append(
                        CheckResult(
                            code="npl_sum_le_loans",
                            severity="warning",
                            message_vi=(
                                f"Tỷ lệ nợ xấu nhóm 3+4+5 trên dư nợ cho vay ở {role_vi(role)} ở mức cao ({float(ratio) * 100:.2f}%), "
                                f"nằm trong khoảng cảnh báo [10%, 25%]."
                            ),
                            row_ids=row_ids,
                            expected="< 10%",
                            actual=f"{float(ratio) * 100:.2f}%",
                        )
                    )

    # 4. provisions_range:
    # 0 <= provisions <= gross_customer_loans
    for role in ("target", "prior"):
        prov, prov_id = get_val("bank.input.loan_loss_provisions", role)
        loans, loans_id = get_val("bank.input.gross_customer_loans", role)
        if prov is not None and loans is not None:
            if prov < Decimal("0") or prov > loans:
                checks.append(
                    CheckResult(
                        code="provisions_range",
                        severity="error",
                        message_vi=f"Dự phòng rủi ro cho vay ({prov}) nằm ngoài khoảng [0, dư nợ ({loans})] ở {role_vi(role)}.",
                        row_ids=[prov_id, loans_id],
                        expected=f"0 <= dự phòng <= {loans}",
                        actual=str(prov),
                    )
                )

    # 5. Basic accounting inequalities: assets_gt_loans, assets_gt_equity, equity_ge_nci
    for role in ("target", "prior"):
        assets, assets_id = get_val("bank.input.total_assets", role)
        loans, loans_id = get_val("bank.input.gross_customer_loans", role)
        equity, equity_id = get_val("bank.input.total_equity", role)
        nci, nci_id = get_val("bank.input.non_controlling_interests", role)

        if assets is not None and loans is not None and assets <= loans:
            checks.append(
                CheckResult(
                    code="assets_gt_loans",
                    severity="error",
                    message_vi=f"Tổng tài sản ({assets}) phải lớn hơn dư nợ cho vay ({loans}) ở {role_vi(role)}.",
                    row_ids=[assets_id, loans_id],
                    expected=f"Tổng tài sản > {loans}",
                    actual=str(assets),
                )
            )

        if assets is not None and equity is not None and assets <= equity:
            checks.append(
                CheckResult(
                    code="assets_gt_equity",
                    severity="error",
                    message_vi=f"Tổng tài sản ({assets}) phải lớn hơn tổng vốn chủ sở hữu ({equity}) ở {role_vi(role)}.",
                    row_ids=[assets_id, equity_id],
                    expected=f"Tổng tài sản > {equity}",
                    actual=str(assets),
                )
            )

        if equity is not None and nci is not None and equity < nci:
            checks.append(
                CheckResult(
                    code="equity_ge_nci",
                    severity="error",
                    message_vi=f"Tổng vốn chủ sở hữu ({equity}) phải lớn hơn hoặc bằng lợi ích CĐKKS ({nci}) ở {role_vi(role)}.",
                    row_ids=[equity_id, nci_id],
                    expected=f"Vốn chủ sở hữu >= {nci}",
                    actual=str(equity),
                )
            )

    # 6. magnitude_range:
    # total_assets in [100; 20,000,000] billion VND
    # all other values >= 0 except profit metrics
    for r in rows:
        m_id = _get_row_prop(r, "metric_id")
        r_id = _get_row_prop(r, "row_id") or ""
        role = _get_row_prop(r, "period_role") or ""
        val = _parse_dec(_get_row_prop(r, "value_billion_vnd"))
        if val is None:
            continue

        if m_id == "bank.input.total_assets":
            if val < Decimal("100") or val > Decimal("20000000"):
                checks.append(
                    CheckResult(
                        code="magnitude_range",
                        severity="error",
                        message_vi=(
                            f"Tổng tài sản ({val} tỷ) nằm ngoài thang đo hợp lý [100; 20.000.000] tỷ đồng "
                            f"(kiểm tra lỗi nhầm đơn vị triệu/nghìn đồng)."
                        ),
                        row_ids=[r_id],
                        expected="100 <= Tổng tài sản <= 20.000.000",
                        actual=str(val),
                    )
                )
        elif m_id not in PROFIT_METRICS:
            if val < Decimal("0"):
                label = METRIC_LABELS_VI.get(m_id, m_id)
                checks.append(
                    CheckResult(
                        code="magnitude_range",
                        severity="error",
                        message_vi=f"Chỉ tiêu '{label}' ({role_vi(role)}) có giá trị âm ({val}), không hợp lệ cho chỉ tiêu số dư.",
                        row_ids=[r_id],
                        expected=">= 0",
                        actual=str(val),
                    )
                )

    # 7. yoy_change:
    # Change outside [-60%, +150%] for all balance metrics is warning
    for m_id in BALANCE_METRICS:
        v_target, t_id = get_val(m_id, "target")
        v_prior, p_id = get_val(m_id, "prior")
        label = METRIC_LABELS_VI.get(m_id, m_id)

        if v_target is not None and v_prior is not None:
            if v_prior != Decimal("0"):
                change = (v_target - v_prior) / abs(v_prior)
                if change < Decimal("-0.60") or change > Decimal("1.50"):
                    pct = float(change) * 100
                    checks.append(
                        CheckResult(
                            code="yoy_change",
                            severity="warning",
                            message_vi=(
                                f"Chỉ tiêu '{label}' biến động {pct:+.1f}% so với kỳ trước, "
                                f"nằm ngoài khoảng thông thường [-60%, +150%]."
                            ),
                            row_ids=[t_id, p_id],
                            expected="-60% đến +150%",
                            actual=f"{pct:+.1f}%",
                        )
                    )
            elif v_target > Decimal("10"):
                # Jumped from 0 to a significant balance
                checks.append(
                    CheckResult(
                        code="yoy_change",
                        severity="warning",
                        message_vi=f"Chỉ tiêu '{label}' tăng từ 0 lên {v_target} tỷ, cần đối chiếu lại.",
                        row_ids=[t_id, p_id],
                        expected="Số dư tương đồng kỳ trước",
                        actual=f"{v_target} tỷ",
                    )
                )

    # 8. value_in_page_text:
    # Every unmodified extracted value must appear in page text
    for r in rows:
        r_id = _get_row_prop(r, "row_id") or ""
        edited = bool(_get_row_prop(r, "edited", False))
        source = _get_row_prop(r, "source")
        val_str = _get_row_prop(r, "value_billion_vnd")

        if edited or source == "user" or not val_str:
            continue

        page_num = _get_row_prop(r, "page")
        raw_text = _get_row_prop(r, "raw_text") or ""
        val_dec = _parse_dec(val_str)
        if val_dec is None:
            continue

        # Target digit patterns
        # In filings, values in billion VND may come from:
        # - exact digits in million VND: int(val_dec * 1000)
        # - or integer billion: int(val_dec)
        mil_digits = _digits_of(str(abs(int(round(float(val_dec) * 1000)))))
        bil_digits = _digits_of(str(abs(int(val_dec))))

        # Look in page_texts if provided, otherwise check raw_text on row
        page_content = ""
        if page_texts and page_num and page_num in page_texts:
            page_content = page_texts[page_num]

        search_corpus = page_content or raw_text
        corpus_digits = _digits_of(search_corpus)

        # Match check
        matched = False
        if mil_digits and len(mil_digits) >= 3 and mil_digits in corpus_digits:
            matched = True
        elif bil_digits and len(bil_digits) >= 3 and bil_digits in corpus_digits:
            matched = True
        elif not search_corpus:
            # If no text corpus at all and not edited, warn
            matched = False
        else:
            # Check leading 4 digits
            lead = mil_digits[:5] if len(mil_digits) >= 5 else mil_digits
            matched = bool(lead and lead in corpus_digits)

        if not matched:
            label = _get_row_prop(r, "label_vi") or r_id
            checks.append(
                CheckResult(
                    code="value_in_page_text",
                    severity="warning",
                    message_vi=(
                        f"Giá trị máy trích '{val_str}' của chỉ tiêu '{label}' "
                        f"chưa đối chiếu được chữ số trên trang {page_num or 'chưa rõ'}."
                    ),
                    row_ids=[r_id],
                )
            )

    # 9. Forwarded ingestion issues: period_mismatch, unit_unknown, column_not_identified
    for r in rows:
        r_id = _get_row_prop(r, "row_id") or ""
        issues = _get_row_prop(r, "issues") or []
        for iss in issues:
            iss_code = _get_row_prop(iss, "code")
            iss_sev = _get_row_prop(iss, "severity", "warning")
            iss_msg = _get_row_prop(iss, "message_vi", "")
            if iss_code in ("unit_unknown", "period_mismatch", "column_not_identified", "low_confidence_match"):
                fallback_map = {
                    "unit_unknown": "Chưa xác định đơn vị tiền tệ trên trang báo cáo",
                    "period_mismatch": "Kỳ báo cáo không khớp",
                    "column_not_identified": "Chưa xác định được cột số liệu",
                    "low_confidence_match": "Độ khớp dòng trích xuất thấp",
                }
                fallback_msg = fallback_map.get(iss_code, "Cảnh báo từ bước trích xuất")
                checks.append(
                    CheckResult(
                        code=iss_code,
                        severity=iss_sev,
                        message_vi=iss_msg or f"{fallback_msg}.",
                        row_ids=[r_id],
                    )
                )

    # Deduplicate checks with identical code and row_ids
    seen_checks: set[tuple[str, tuple[str, ...]]] = set()
    deduped_checks: list[CheckResult] = []
    for c in checks:
        key = (c.code, tuple(sorted(c.row_ids)))
        if key not in seen_checks:
            seen_checks.add(key)
            deduped_checks.append(c)

    # Aggregation rule:
    # status = fail if error; warn if warning; pass otherwise
    has_error = any(c.severity == "error" for c in deduped_checks)
    has_warning = any(c.severity == "warning" for c in deduped_checks)

    overall_status: Literal["pass", "warn", "fail"]
    if has_error:
        overall_status = "fail"
    elif has_warning:
        overall_status = "warn"
    else:
        overall_status = "pass"

    # ready_to_confirm = True when:
    # - no error checks
    # - all 20 rows are confirmed
    # - full 20 rows are present
    all_confirmed = (seen_row_count == total_expected_rows) and (unconfirmed_count == 0)
    ready_to_confirm = (not has_error) and all_confirmed

    if has_error:
        for c in deduped_checks:
            if c.severity == "error":
                blocking_reasons.append(c.message_vi)

    if unconfirmed_count > 0:
        blocking_reasons.append(f"Còn {unconfirmed_count}/{total_expected_rows} dòng chưa được người dùng xác nhận.")
    elif seen_row_count < total_expected_rows:
        blocking_reasons.append(f"Mới có {seen_row_count}/{total_expected_rows} dòng chỉ tiêu; cần đủ 20 dòng.")

    return ValidationResult(
        status=overall_status,
        ready_to_confirm=ready_to_confirm,
        blocking_reasons_vi=blocking_reasons,
        checks=deduped_checks,
    )
