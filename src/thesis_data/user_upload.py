"""User-supplied CSV onboarding validation and candidate builder.

Allows analysts to upload bank financial statement data in CSV format,
validates structure, primary source locators, reporting scope, recomputes
the 4 core ratios (NPL, LLR, ROA, ROE) using versioned deterministic formulas,
and generates operational candidates for materialization.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Literal
from urllib.parse import urlparse

from .canonical_snapshot import (
    CANONICAL_SNAPSHOT_SCHEMA_VERSION,
    _calculate_derived_receipt,
    _create_schema,
    _enum_value,
    _insert_observation,
    _json,
)
from .dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetSource,
    ObservationEvidenceRef,
    ObservationReview,
    canonical_observation_id,
)
from .evidence_contract import DatasetDocument
from .metrics import (
    calculate_llr,
    calculate_npl,
    calculate_npl_g35_balance,
    calculate_parent_attributable_equity,
    calculate_roa_ttm,
    calculate_roe_ttm,
)
from .onboarding_contract import (
    ONBOARDING_CONTRACT_VERSION,
    DatasetSnapshotStatus,
    OnboardingValidationReport,
    OnboardingValidationStatus,
    RawDatasetDescriptor,
    build_snapshot_metadata,
)
from .onboarding_validation import CanonicalDatasetCandidate
from .schema import QualityStatus


MAX_FILE_BYTES = 256 * 1024  # 256 KB
MAX_ROWS = 200

PRIMARY_RATIO_METRICS = (
    "bank.npl_g35",
    "bank.llr_coverage",
    "bank.roa",
    "bank.roe",
)

REQUIRED_TARGET_INPUTS = (
    "bank.input.npl_group_3_balance",
    "bank.input.npl_group_4_balance",
    "bank.input.npl_group_5_balance",
    "bank.input.gross_customer_loans",
    "bank.input.loan_loss_provisions",
    "bank.input.profit_after_tax",
    "bank.input.total_assets",
    "bank.input.parent_attributable_profit",
    "bank.input.total_equity",
    "bank.input.non_controlling_interests",
)

REQUIRED_PRIOR_INPUTS = (
    "bank.input.profit_after_tax",
    "bank.input.total_assets",
    "bank.input.parent_attributable_profit",
    "bank.input.total_equity",
    "bank.input.non_controlling_interests",
)

_RATIO_TOLERANCE = Decimal("0.00005")
_BALANCE_TOLERANCE = Decimal("0.0000001")

_PAGE_LOCATOR_RE = re.compile(
    r"(?:page|trang|pdf_page|printed_page|tr\.|p\.)\s*[=:]?\s*\d+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UploadRowIssue:
    row: int
    field: str
    message_vi: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "field": self.field,
            "message_vi": self.message_vi,
        }


@dataclass(frozen=True)
class UploadMetricItem:
    metric_id: str
    computed_value: float
    reported_value: float | None
    status: Literal["matched", "computed", "mismatched"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "computed_value": self.computed_value,
            "reported_value": self.reported_value,
            "status": self.status,
        }


@dataclass(frozen=True)
class UploadValidationResult:
    upload_id: str
    entity_id: str
    display_name: str
    period_id: str
    prior_period_id: str
    status: Literal["accepted", "rejected"]
    metrics: list[UploadMetricItem]
    row_issues: list[UploadRowIssue]
    limitations_vi: str
    candidate: CanonicalDatasetCandidate | None = None
    raw_descriptor: RawDatasetDescriptor | None = None
    report: OnboardingValidationReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "upload_id": self.upload_id,
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "status": self.status,
            "period_id": self.period_id,
            "metrics": [m.to_dict() for m in self.metrics],
            "row_issues": [i.to_dict() for i in self.row_issues],
            "limitations_vi": self.limitations_vi,
        }


def _prior_period(period_id: str) -> str:
    try:
        if "_Q" in period_id:
            year, quarter = period_id.split("_Q", 1)
            return f"{int(year) - 1}_Q{quarter}"
        if period_id.startswith("FY"):
            year = period_id[2:]
            return f"FY{int(year) - 1}"
    except Exception as exc:
        raise ValueError(f"Không thể xác định kỳ trước cho {period_id}") from exc
    raise ValueError(f"Định dạng kỳ không hỗ trợ: {period_id}")


def validate_and_parse_upload_csv(
    content: bytes | str,
    *,
    upload_id: str,
    form_entity_id: str | None = None,
    form_display_name: str | None = None,
) -> UploadValidationResult:
    """Validate uploaded CSV structure, locators, and ratios according to UPLOAD-1 rules."""
    row_issues: list[UploadRowIssue] = []

    # 1. Normalize bytes and text
    if isinstance(content, str):
        raw_bytes = content.encode("utf-8")
        text = content
    else:
        raw_bytes = content
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            row_issues.append(
                UploadRowIssue(
                    row=0,
                    field="encoding",
                    message_vi="Tệp phải được mã hóa chuẩn UTF-8 hoặc UTF-8 BOM.",
                )
            )
            return UploadValidationResult(
                upload_id=upload_id,
                entity_id=(form_entity_id or "").upper(),
                display_name=form_display_name or (form_entity_id or "").upper(),
                period_id="",
                prior_period_id="",
                status="rejected",
                metrics=[],
                row_issues=row_issues,
                limitations_vi="",
            )

    # 2. File size check
    if len(raw_bytes) > MAX_FILE_BYTES:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="file",
                message_vi=f"Kích thước tệp vượt quá giới hạn cho phép (tối đa 256 KB, thực tế: {len(raw_bytes)} bytes).",
            )
        )
        return UploadValidationResult(
            upload_id=upload_id,
            entity_id=(form_entity_id or "").upper(),
            display_name=form_display_name or (form_entity_id or "").upper(),
            period_id="",
            prior_period_id="",
            status="rejected",
            metrics=[],
            row_issues=row_issues,
            limitations_vi="",
        )

    # 3. Parse CSV rows
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="header",
                message_vi="Tệp CSV không có tiêu đề cột hợp lệ.",
            )
        )
        return UploadValidationResult(
            upload_id=upload_id,
            entity_id=(form_entity_id or "").upper(),
            display_name=form_display_name or (form_entity_id or "").upper(),
            period_id="",
            prior_period_id="",
            status="rejected",
            metrics=[],
            row_issues=row_issues,
            limitations_vi="",
        )

    raw_rows = list(reader)
    if not raw_rows:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="content",
                message_vi="Tệp CSV không chứa dòng dữ liệu nào.",
            )
        )
        return UploadValidationResult(
            upload_id=upload_id,
            entity_id=(form_entity_id or "").upper(),
            display_name=form_display_name or (form_entity_id or "").upper(),
            period_id="",
            prior_period_id="",
            status="rejected",
            metrics=[],
            row_issues=row_issues,
            limitations_vi="",
        )

    if len(raw_rows) > MAX_ROWS:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="row_count",
                message_vi=f"Số dòng dữ liệu vượt quá giới hạn (tối đa 200 dòng, thực tế: {len(raw_rows)}).",
            )
        )

    # Clean row headers
    cleaned_rows: list[dict[str, str]] = []
    for row in raw_rows:
        cleaned_row = {
            (k.strip() if k else ""): (v.strip() if v else "")
            for k, v in row.items()
            if k is not None
        }
        cleaned_rows.append(cleaned_row)

    # Determine entity_id
    detected_entity_ids: set[str] = set()
    for row in cleaned_rows:
        e = row.get("entity_id")
        if e:
            detected_entity_ids.add(e.upper())

    if len(detected_entity_ids) > 1:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="entity_id",
                message_vi=f"Tệp chứa nhiều mã ngân hàng khác nhau ({', '.join(sorted(detected_entity_ids))}). Một tệp chỉ được chứa số liệu của 1 ngân hàng.",
            )
        )

    effective_entity = (
        detected_entity_ids.pop()
        if len(detected_entity_ids) == 1
        else (form_entity_id.strip().upper() if form_entity_id else "")
    )

    if not effective_entity:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="entity_id",
                message_vi="Thiếu mã ngân hàng (entity_id). Cần khai báo cột entity_id hoặc cung cấp mã ngân hàng.",
            )
        )
    elif not re.fullmatch(r"^[A-Za-z0-9_]{3,10}$", effective_entity):
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="entity_id",
                message_vi=f"Mã ngân hàng '{effective_entity}' không hợp lệ (cần mã chứng khoán 3 ký tự).",
            )
        )

    display_name = form_display_name or effective_entity
    limitations_vi = (
        f"Số liệu {effective_entity} do người dùng cung cấp; hệ thống đã kiểm tra cấu trúc, "
        f"nguồn và tính lại chỉ tiêu, chưa được duyệt độc lập như bộ Gold."
    )

    # Determine target period
    period_counts: dict[str, int] = {}
    for row in cleaned_rows:
        p = row.get("period_id")
        if p and re.fullmatch(r"(?:\d{4}_Q[1-4]|FY\d{4})", p):
            period_counts[p] = period_counts.get(p, 0) + 1

    if not period_counts:
        row_issues.append(
            UploadRowIssue(
                row=0,
                field="period_id",
                message_vi="Tệp không chứa kỳ dữ liệu hợp lệ (dạng YYYY_Qn hoặc FYyyyy).",
            )
        )
        target_period = ""
        prior_period = ""
    else:
        # Target period is the latest period with data
        sorted_periods = sorted(period_counts.keys())
        target_period = sorted_periods[-1]
        try:
            prior_period = _prior_period(target_period)
        except ValueError as exc:
            row_issues.append(UploadRowIssue(row=0, field="period_id", message_vi=str(exc)))
            prior_period = ""

    # Validate each row individually
    parsed_obs_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for idx, row in enumerate(cleaned_rows, start=1):
        metric_id = row.get("metric_id", "")
        period_id = row.get("period_id", "")
        val_str = row.get("value", "")
        unit = row.get("unit", "")
        period_basis = row.get("period_basis", "")
        reporting_scope = row.get("reporting_scope", "")
        source_locator = row.get("source_locator", "")
        source_url = row.get("source_url", "")
        source_sha256 = row.get("source_sha256", "")

        # Row entity_id consistency
        row_entity = row.get("entity_id", "").upper()
        if row_entity and row_entity != effective_entity:
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="entity_id",
                    message_vi=f"Dòng có entity_id '{row_entity}' không khớp với mã chung '{effective_entity}'.",
                )
            )

        if not metric_id:
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="metric_id",
                    message_vi="Thiếu mã chỉ tiêu (metric_id).",
                )
            )
            continue

        if not period_id or not re.fullmatch(r"(?:\d{4}_Q[1-4]|FY\d{4})", period_id):
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="period_id",
                    message_vi=f"Kỳ dữ liệu '{period_id}' không hợp lệ (yêu cầu định dạng YYYY_Qn hoặc FYyyyy).",
                )
            )

        # Value validation
        val_num: float | None = None
        if val_str == "":
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="value",
                    message_vi="Giá trị số liệu (value) không được để trống.",
                )
            )
        else:
            try:
                val_num = float(val_str)
            except ValueError:
                row_issues.append(
                    UploadRowIssue(
                        row=idx,
                        field="value",
                        message_vi=f"Giá trị '{val_str}' không phải là số hợp lệ.",
                    )
                )

        # Unit validation
        is_ratio = metric_id in PRIMARY_RATIO_METRICS
        expected_unit = "percent" if is_ratio else "billion_vnd"
        if unit not in (expected_unit, "%" if is_ratio else None):
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="unit",
                    message_vi=f"Đơn vị '{unit}' không hợp lệ cho chỉ tiêu {metric_id} (yêu cầu '{expected_unit}').",
                )
            )

        # Reporting scope validation
        if reporting_scope not in ("consolidated", "separate"):
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="reporting_scope",
                    message_vi=f"Phạm vi báo cáo '{reporting_scope}' không hợp lệ (yêu cầu 'consolidated' hoặc 'separate').",
                )
            )

        # Source locator validation: must specify at least page/trang
        if not source_locator or not _PAGE_LOCATOR_RE.search(source_locator):
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="source_locator",
                    message_vi="Thiếu định vị trang nguồn sơ cấp (cần có số trang/page, ví dụ: 'tr. 36' hoặc 'pdf_page=38').",
                )
            )

        # Source URL validation
        if not source_url:
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="source_url",
                    message_vi="Thiếu đường dẫn tài liệu nguồn sơ cấp (source_url).",
                )
            )
        else:
            parsed_url = urlparse(source_url)
            if not parsed_url.scheme:
                row_issues.append(
                    UploadRowIssue(
                        row=idx,
                        field="source_url",
                        message_vi=f"Đường dẫn nguồn '{source_url}' không có giao thức hợp lệ (cần http://, https:// hoặc urn:).",
                    )
                )

        key = (metric_id, period_id)
        if key in parsed_obs_by_key:
            row_issues.append(
                UploadRowIssue(
                    row=idx,
                    field="metric_id",
                    message_vi=f"Trùng lặp chỉ tiêu {metric_id} cho kỳ {period_id}.",
                )
            )
        else:
            obs_id = row.get("observation_id") or f"{effective_entity.lower()}-{metric_id.replace('.', '-')}-{period_id.lower()}"
            parsed_obs_by_key[key] = {
                "observation_id": obs_id,
                "metric_id": metric_id,
                "period_id": period_id,
                "value": val_num,
                "value_decimal": Decimal(val_str) if val_num is not None else None,
                "unit": "percent" if is_ratio else "billion_vnd",
                "period_basis": period_basis or ("ttm" if metric_id in ("bank.roa", "bank.roe") else ("point_in_time" if is_ratio else "point_in_time")),
                "reporting_scope": reporting_scope,
                "source_locator": source_locator,
                "source_url": source_url,
                "source_sha256": source_sha256,
                "row_index": idx,
            }

    # Verify presence of all required input metrics
    if target_period and prior_period:
        for req_m in REQUIRED_TARGET_INPUTS:
            if (req_m, target_period) not in parsed_obs_by_key:
                row_issues.append(
                    UploadRowIssue(
                        row=0,
                        field="metric_id",
                        message_vi=f"Thiếu chỉ tiêu bắt buộc '{req_m}' cho kỳ mục tiêu {target_period}.",
                    )
                )

        for req_m in REQUIRED_PRIOR_INPUTS:
            if (req_m, prior_period) not in parsed_obs_by_key:
                row_issues.append(
                    UploadRowIssue(
                        row=0,
                        field="metric_id",
                        message_vi=f"Thiếu chỉ tiêu bắt buộc '{req_m}' cho kỳ trước {prior_period} (cần thiết để tính trung bình ROA/ROE).",
                    )
                )

    has_all_inputs = bool(
        target_period
        and prior_period
        and all(
            (m, target_period) in parsed_obs_by_key
            and parsed_obs_by_key[(m, target_period)]["value_decimal"] is not None
            for m in REQUIRED_TARGET_INPUTS
        )
        and all(
            (m, prior_period) in parsed_obs_by_key
            and parsed_obs_by_key[(m, prior_period)]["value_decimal"] is not None
            for m in REQUIRED_PRIOR_INPUTS
        )
    )

    if not has_all_inputs:
        return UploadValidationResult(
            upload_id=upload_id,
            entity_id=effective_entity,
            display_name=display_name,
            period_id=target_period,
            prior_period_id=prior_period,
            status="rejected",
            metrics=[],
            row_issues=row_issues,
            limitations_vi=limitations_vi,
        )

    # 4. Recompute derived intermediate balances and ratios
    g3 = parsed_obs_by_key[("bank.input.npl_group_3_balance", target_period)]["value_decimal"]
    g4 = parsed_obs_by_key[("bank.input.npl_group_4_balance", target_period)]["value_decimal"]
    g5 = parsed_obs_by_key[("bank.input.npl_group_5_balance", target_period)]["value_decimal"]
    gross_loans = parsed_obs_by_key[("bank.input.gross_customer_loans", target_period)]["value_decimal"]
    provisions = parsed_obs_by_key[("bank.input.loan_loss_provisions", target_period)]["value_decimal"]

    pat_curr = parsed_obs_by_key[("bank.input.profit_after_tax", target_period)]["value_decimal"]
    pat_prior = parsed_obs_by_key[("bank.input.profit_after_tax", prior_period)]["value_decimal"]
    assets_curr = parsed_obs_by_key[("bank.input.total_assets", target_period)]["value_decimal"]
    assets_prior = parsed_obs_by_key[("bank.input.total_assets", prior_period)]["value_decimal"]

    parent_profit_curr = parsed_obs_by_key[("bank.input.parent_attributable_profit", target_period)]["value_decimal"]
    parent_profit_prior = parsed_obs_by_key[("bank.input.parent_attributable_profit", prior_period)]["value_decimal"]
    equity_curr = parsed_obs_by_key[("bank.input.total_equity", target_period)]["value_decimal"]
    equity_prior = parsed_obs_by_key[("bank.input.total_equity", prior_period)]["value_decimal"]
    nci_curr = parsed_obs_by_key[("bank.input.non_controlling_interests", target_period)]["value_decimal"]
    nci_prior = parsed_obs_by_key[("bank.input.non_controlling_interests", prior_period)]["value_decimal"]

    # Calculate intermediate balances
    calc_npl_balance = calculate_npl_g35_balance(g3, g4, g5)
    calc_parent_equity_curr = calculate_parent_attributable_equity(equity_curr, nci_curr)
    calc_parent_equity_prior = calculate_parent_attributable_equity(equity_prior, nci_prior)

    # Check reported intermediate balances if present
    if ("bank.input.npl_g35_balance", target_period) in parsed_obs_by_key:
        rep_val = parsed_obs_by_key[("bank.input.npl_g35_balance", target_period)]["value_decimal"]
        if abs(rep_val - calc_npl_balance.value) > _BALANCE_TOLERANCE:
            row_issues.append(
                UploadRowIssue(
                    row=parsed_obs_by_key[("bank.input.npl_g35_balance", target_period)]["row_index"],
                    field="value",
                    message_vi=f"Giá trị nợ xấu nhóm 3–5 công bố ({rep_val}) không khớp tổng nhóm 3+4+5 ({calc_npl_balance.value}).",
                )
            )

    if ("bank.input.parent_attributable_equity", target_period) in parsed_obs_by_key:
        rep_val = parsed_obs_by_key[("bank.input.parent_attributable_equity", target_period)]["value_decimal"]
        if abs(rep_val - calc_parent_equity_curr.value) > _BALANCE_TOLERANCE:
            row_issues.append(
                UploadRowIssue(
                    row=parsed_obs_by_key[("bank.input.parent_attributable_equity", target_period)]["row_index"],
                    field="value",
                    message_vi=f"Vốn chủ sở hữu cổ đông mẹ công bố ({rep_val}) không khớp tổng vốn trừ CĐTSKT ({calc_parent_equity_curr.value}).",
                )
            )

    if ("bank.input.parent_attributable_equity", prior_period) in parsed_obs_by_key:
        rep_val = parsed_obs_by_key[("bank.input.parent_attributable_equity", prior_period)]["value_decimal"]
        if abs(rep_val - calc_parent_equity_prior.value) > _BALANCE_TOLERANCE:
            row_issues.append(
                UploadRowIssue(
                    row=parsed_obs_by_key[("bank.input.parent_attributable_equity", prior_period)]["row_index"],
                    field="value",
                    message_vi=f"Vốn chủ sở hữu cổ đông mẹ kỳ trước công bố ({rep_val}) không khớp tổng vốn trừ CĐTSKT ({calc_parent_equity_prior.value}).",
                )
            )

    # Compute 4 primary ratios
    calc_npl = calculate_npl(g3, g4, g5, gross_loans)
    calc_llr = calculate_llr(provisions, calc_npl_balance.value)
    avg_assets = (assets_curr + assets_prior) / Decimal("2")
    avg_equity = (calc_parent_equity_curr.value + calc_parent_equity_prior.value) / Decimal("2")
    calc_roa = calculate_roa_ttm(pat_curr, pat_prior, pat_prior, avg_assets)
    calc_roe = calculate_roe_ttm(parent_profit_curr, parent_profit_prior, parent_profit_prior, avg_equity)

    computed_results = {
        "bank.npl_g35": calc_npl,
        "bank.llr_coverage": calc_llr,
        "bank.roa": calc_roa,
        "bank.roe": calc_roe,
    }

    metrics_items: list[UploadMetricItem] = []
    for metric_id in PRIMARY_RATIO_METRICS:
        receipt = computed_results[metric_id]
        comp_val = round(float(receipt.value), 4) if receipt.value is not None else 0.0

        rep_row = parsed_obs_by_key.get((metric_id, target_period))
        if rep_row is not None:
            rep_dec = rep_row["value_decimal"]
            rep_val = float(rep_dec)
            diff = abs(rep_dec - receipt.value)
            if diff > _RATIO_TOLERANCE:
                row_issues.append(
                    UploadRowIssue(
                        row=rep_row["row_index"],
                        field="value",
                        message_vi=f"Giá trị công bố {rep_val} lệch so với giá trị tính lại {comp_val}% (vượt dung sai cho phép).",
                    )
                )
                m_status: Literal["matched", "computed", "mismatched"] = "mismatched"
            else:
                m_status = "matched"
        else:
            rep_val = None
            m_status = "computed"

        metrics_items.append(
            UploadMetricItem(
                metric_id=metric_id,
                computed_value=comp_val,
                reported_value=rep_val,
                status=m_status,
            )
        )

    if row_issues:
        return UploadValidationResult(
            upload_id=upload_id,
            entity_id=effective_entity,
            display_name=display_name,
            period_id=target_period,
            prior_period_id=prior_period,
            status="rejected",
            metrics=metrics_items,
            row_issues=row_issues,
            limitations_vi=limitations_vi,
        )

    # 5. Build candidate dataset for operational snapshot materialization
    candidate, raw_descriptor, report = _build_upload_candidate(
        upload_id=upload_id,
        entity_id=effective_entity,
        display_name=display_name,
        target_period=target_period,
        prior_period=prior_period,
        parsed_obs=parsed_obs_by_key,
        computed_results=computed_results,
        calc_npl_balance=calc_npl_balance,
        calc_parent_equity_curr=calc_parent_equity_curr,
        calc_parent_equity_prior=calc_parent_equity_prior,
        raw_bytes=raw_bytes,
    )

    return UploadValidationResult(
        upload_id=upload_id,
        entity_id=effective_entity,
        display_name=display_name,
        period_id=target_period,
        prior_period_id=prior_period,
        status="accepted",
        metrics=metrics_items,
        row_issues=[],
        limitations_vi=limitations_vi,
        candidate=candidate,
        raw_descriptor=raw_descriptor,
        report=report,
    )


def _build_upload_candidate(
    *,
    upload_id: str,
    entity_id: str,
    display_name: str,
    target_period: str,
    prior_period: str,
    parsed_obs: dict[tuple[str, str], dict[str, Any]],
    computed_results: dict[str, Any],
    calc_npl_balance: Any,
    calc_parent_equity_curr: Any,
    calc_parent_equity_prior: Any,
    raw_bytes: bytes,
) -> tuple[CanonicalDatasetCandidate, RawDatasetDescriptor, OnboardingValidationReport]:
    """Construct a full CanonicalDatasetCandidate with formula lineage for operational promotion."""
    dataset_id = f"user-upload-{entity_id.lower()}-{target_period.lower()}"
    content_hash = hashlib.sha256(raw_bytes).hexdigest().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    # Primary filing source
    first_source_url = next(
        (item["source_url"] for item in parsed_obs.values() if item.get("source_url")),
        "https://example.com/filing.pdf",
    )
    source_ref = f"source-{upload_id}"
    dataset_source = DatasetSource(
        source_ref=source_ref,
        source_type="filing",
        source_tier="primary",
        source_url=first_source_url,
        publisher=f"{entity_id} Investor Relations",
        retrieved_at=now_iso,
        content_hash=content_hash,
        validation_status=QualityStatus.VALID,
        notes="User-supplied bank financial statements",
    )

    raw_descriptor = RawDatasetDescriptor(
        raw_dataset_id=f"upload-{upload_id}-raw",
        source_type="filing",
        original_name=f"{entity_id}-user-upload.csv",
        content_hash=content_hash,
        ingested_at=now_dt,
    )

    metadata = build_snapshot_metadata(
        dataset_id,
        raw_descriptor,
        mapping_version="user-upload-v1",
        validation_version="user-upload-validation-v1",
        status=DatasetSnapshotStatus.CANDIDATE,
        created_at=now_dt,
    )

    document_id = f"document:{upload_id}"
    document = DatasetDocument(
        document_id=document_id,
        dataset_id=dataset_id,
        dataset_snapshot_id=metadata.dataset_snapshot_id,
        source_ref=source_ref,
        document_type="user_supplied_financial_filing",
        title=f"{entity_id} Audited Financial Filing ({target_period})",
        publisher=f"{entity_id} IR",
        content_hash=content_hash,
        metadata={"upload_id": upload_id},
    )

    # Map observation IDs to canonical observation IDs
    canonical_id_map: dict[tuple[str, str], str] = {}
    all_needed_keys = set(parsed_obs.keys()) | {
        ("bank.input.npl_g35_balance", target_period),
        ("bank.input.parent_attributable_equity", target_period),
        ("bank.input.parent_attributable_equity", prior_period),
        ("bank.npl_g35", target_period),
        ("bank.llr_coverage", target_period),
        ("bank.roa", target_period),
        ("bank.roe", target_period),
    }

    for metric_id, period_id in all_needed_keys:
        canonical_id_map[(metric_id, period_id)] = canonical_observation_id(
            metadata.dataset_snapshot_id,
            entity_id,
            period_id,
            metric_id,
        )

    observations: list[CanonicalObservation] = []
    evidence_rows: list[DatasetEvidence] = []

    # 1. Build direct input observations
    direct_keys = [
        (m, p)
        for (m, p) in parsed_obs.keys()
        if not m.startswith("bank.npl_g35")
        and not m.startswith("bank.llr_coverage")
        and not m.startswith("bank.roa")
        and not m.startswith("bank.roe")
        and m not in ("bank.input.npl_g35_balance", "bank.input.parent_attributable_equity")
    ]

    for m, p in direct_keys:
        row = parsed_obs[(m, p)]
        cid = canonical_id_map[(m, p)]
        loc = row["source_locator"]
        review = ObservationReview(
            reviewer_id="uploader",
            reviewed_at=now_iso,
            decision="matched_reported_value",
            primary_evidence=(
                ObservationEvidenceRef(
                    source_ref=source_ref,
                    locator=loc,
                ),
            ),
            resolution_note="User-supplied primary filing observation",
        )
        obs = CanonicalObservation(
            observation_id=cid,
            dataset_id=dataset_id,
            dataset_snapshot_id=metadata.dataset_snapshot_id,
            entity_id=entity_id,
            period_id=p,
            metric_id=m,
            value=row["value"],
            unit=row["unit"],
            source_ref=source_ref,
            source_locator=loc,
            period_basis=row["period_basis"],
            reporting_scope=row["reporting_scope"],
            review=review,
            validation_status=QualityStatus.VALID,
            metadata={"user_supplied": True},
        )
        observations.append(obs)
        evidence_rows.append(
            DatasetEvidence(
                evidence_id=f"evidence:{upload_id}:{cid}",
                source_ref=source_ref,
                document_id=document_id,
                entity_id=entity_id,
                period_id=p,
                metric_id=m,
                locator=loc,
                quote=f"{entity_id} {m} {p} value={row['value']}",
            )
        )

    # Helper for intermediate / derived rows
    def _add_derived(
        metric_id: str,
        period_id: str,
        val: float,
        formula_version: str,
        input_keys: tuple[tuple[str, str], ...],
        default_unit: str = "billion_vnd",
        period_basis: str = "point_in_time",
    ):
        cid = canonical_id_map[(metric_id, period_id)]
        first_input = parsed_obs.get(input_keys[0], {})
        loc = first_input.get("source_locator", "p. 1")
        review = ObservationReview(
            reviewer_id="uploader",
            reviewed_at=now_iso,
            decision="reproduced_derived_value",
            primary_evidence=(
                ObservationEvidenceRef(
                    source_ref=source_ref,
                    locator=loc,
                ),
            ),
            resolution_note=f"Recomputed from accepted inputs using {formula_version}",
        )
        obs = CanonicalObservation(
            observation_id=cid,
            dataset_id=dataset_id,
            dataset_snapshot_id=metadata.dataset_snapshot_id,
            entity_id=entity_id,
            period_id=period_id,
            metric_id=metric_id,
            value=val,
            unit=default_unit,
            source_ref=None,
            source_locator=loc,
            period_basis=period_basis,
            reporting_scope="consolidated",
            review=review,
            validation_status=QualityStatus.VALID,
            derivation_method=formula_version,
            input_observation_ids=tuple(canonical_id_map[k] for k in input_keys),
            metadata={"user_supplied": True},
        )
        observations.append(obs)
        evidence_rows.append(
            DatasetEvidence(
                evidence_id=f"evidence:{upload_id}:{cid}",
                source_ref=source_ref,
                document_id=document_id,
                entity_id=entity_id,
                period_id=period_id,
                metric_id=metric_id,
                locator=loc,
                quote=f"{entity_id} {metric_id} {period_id} value={val}",
            )
        )

    # 2. Derived intermediate balances
    _add_derived(
        "bank.input.npl_g35_balance",
        target_period,
        float(calc_npl_balance.value),
        calc_npl_balance.formula_version,
        (
            ("bank.input.npl_group_3_balance", target_period),
            ("bank.input.npl_group_4_balance", target_period),
            ("bank.input.npl_group_5_balance", target_period),
        ),
    )

    _add_derived(
        "bank.input.parent_attributable_equity",
        target_period,
        float(calc_parent_equity_curr.value),
        calc_parent_equity_curr.formula_version,
        (
            ("bank.input.total_equity", target_period),
            ("bank.input.non_controlling_interests", target_period),
        ),
    )

    _add_derived(
        "bank.input.parent_attributable_equity",
        prior_period,
        float(calc_parent_equity_prior.value),
        calc_parent_equity_prior.formula_version,
        (
            ("bank.input.total_equity", prior_period),
            ("bank.input.non_controlling_interests", prior_period),
        ),
    )

    # 3. Derived primary ratios
    _add_derived(
        "bank.npl_g35",
        target_period,
        float(computed_results["bank.npl_g35"].value),
        computed_results["bank.npl_g35"].formula_version,
        (
            ("bank.input.npl_group_3_balance", target_period),
            ("bank.input.npl_group_4_balance", target_period),
            ("bank.input.npl_group_5_balance", target_period),
            ("bank.input.gross_customer_loans", target_period),
        ),
        default_unit="percent",
        period_basis="point_in_time",
    )

    _add_derived(
        "bank.llr_coverage",
        target_period,
        float(computed_results["bank.llr_coverage"].value),
        computed_results["bank.llr_coverage"].formula_version,
        (
            ("bank.input.loan_loss_provisions", target_period),
            ("bank.input.npl_g35_balance", target_period),
        ),
        default_unit="percent",
        period_basis="point_in_time",
    )

    _add_derived(
        "bank.roa",
        target_period,
        float(computed_results["bank.roa"].value),
        computed_results["bank.roa"].formula_version,
        (
            ("bank.input.profit_after_tax", target_period),
            ("bank.input.profit_after_tax", prior_period),
            ("bank.input.total_assets", target_period),
            ("bank.input.total_assets", prior_period),
        ),
        default_unit="percent",
        period_basis="ttm",
    )

    _add_derived(
        "bank.roe",
        target_period,
        float(computed_results["bank.roe"].value),
        computed_results["bank.roe"].formula_version,
        (
            ("bank.input.parent_attributable_profit", target_period),
            ("bank.input.parent_attributable_profit", prior_period),
            ("bank.input.parent_attributable_equity", target_period),
            ("bank.input.parent_attributable_equity", prior_period),
        ),
        default_unit="percent",
        period_basis="ttm",
    )

    # Metrics definition
    all_metrics = sorted({obs.metric_id for obs in observations})
    metrics_list: list[DatasetMetric] = []
    for m in all_metrics:
        unit = "percent" if m in PRIMARY_RATIO_METRICS else "billion_vnd"
        metrics_list.append(
            DatasetMetric(
                metric_id=m,
                display_name=m.removeprefix("bank.input.").replace("_", " ").capitalize(),
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit=unit,
            )
        )

    candidate = CanonicalDatasetCandidate(
        metadata=metadata,
        source=dataset_source,
        entities=(
            DatasetEntity(
                entity_id=entity_id,
                entity_type=DatasetEntityType.COMPANY,
                display_name=display_name,
                attributes={"sector": "bank", "user_supplied": True},
            ),
        ),
        periods=(
            DatasetPeriod(period_id=prior_period, label=prior_period),
            DatasetPeriod(period_id=target_period, label=target_period),
        ),
        metrics=tuple(metrics_list),
        observations=tuple(observations),
        additional_sources=(),
        documents=(document,),
        evidence=tuple(evidence_rows),
    )

    report = OnboardingValidationReport(
        dataset_id=dataset_id,
        candidate_snapshot_id=metadata.dataset_snapshot_id,
        status=OnboardingValidationStatus.VALID,
        row_count=len(observations),
        candidate_observation_count=len(observations),
        missing_observation_count=0,
        rejected_row_count=0,
    )

    return candidate, raw_descriptor, report


_PROTECTED_STORE_STEMS = {
    "analysis_runs",
    "finance_master_v2",
    "gold_v5",
    "gold-v5",
}


def materialize_user_upload_snapshot(
    validation_result: UploadValidationResult,
    target_sqlite_path: Path,
) -> Path:
    """Materialize validated upload candidate into an isolated operational SQLite DB."""
    if validation_result.status != "accepted":
        raise ValueError("Chỉ có thể dựng snapshot cho tệp tải lên đã được chấp nhận.")
    if (
        validation_result.candidate is None
        or validation_result.raw_descriptor is None
        or validation_result.report is None
    ):
        raise ValueError("Thiếu dữ liệu ứng viên để dựng snapshot.")

    target_path = Path(target_sqlite_path).resolve()
    if target_path.stem.lower() in _PROTECTED_STORE_STEMS:
        raise ValueError("Upload operational snapshot cannot name a protected Gold or run-history store")
    for env_var in ("SQLITE_DB_PATH", "ANALYSIS_RUNS_DB_PATH"):
        configured = os.environ.get(env_var)
        if configured and target_path == Path(configured).resolve():
            raise ValueError("Upload operational snapshot cannot alias a configured analytical or run-history store")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path.unlink()

    candidate = validation_result.candidate
    obs_by_id = {o.observation_id: o for o in candidate.observations}
    for item in candidate.observations:
        if item.derivation_method:
            receipt = _calculate_derived_receipt(item, obs_by_id)
            item.calculation_receipt = receipt

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(target_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        _create_schema(conn)

        manifest_hash = hashlib.sha256(
            f"{candidate.metadata.dataset_snapshot_id}:{len(candidate.observations)}".encode("utf-8")
        ).hexdigest()

        conn.execute(
            """
            INSERT INTO dataset_metadata (
                dataset_id, dataset_snapshot_id, contract_version, schema_version,
                status, created_at, source_content_hash, mapping_version,
                validation_version, content_manifest_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.metadata.dataset_id,
                candidate.metadata.dataset_snapshot_id,
                ONBOARDING_CONTRACT_VERSION,
                CANONICAL_SNAPSHOT_SCHEMA_VERSION,
                "accepted",
                candidate.metadata.created_at.isoformat(),
                candidate.metadata.source_content_hash,
                candidate.metadata.mapping_version,
                candidate.metadata.validation_version,
                manifest_hash,
            ),
        )

        for source in candidate.all_sources:
            conn.execute(
                """
                INSERT INTO sources (
                    source_ref, source_type, source_tier, source_url, publisher,
                    retrieved_at, content_hash, validation_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.source_ref,
                    source.source_type,
                    _enum_value(source.source_tier),
                    source.source_url,
                    source.publisher,
                    source.retrieved_at,
                    source.content_hash,
                    _enum_value(source.validation_status),
                    source.notes,
                ),
            )

        for entity in candidate.entities:
            conn.execute(
                "INSERT INTO entities VALUES (?, ?, ?, ?)",
                (
                    entity.entity_id,
                    _enum_value(entity.entity_type),
                    entity.display_name,
                    _json(entity.attributes),
                ),
            )

        for period in candidate.periods:
            conn.execute(
                "INSERT INTO periods VALUES (?, ?)",
                (period.period_id, period.label),
            )

        for metric in candidate.metrics:
            conn.execute(
                "INSERT INTO metrics VALUES (?, ?, ?, ?)",
                (
                    metric.metric_id,
                    metric.display_name,
                    _enum_value(metric.analytical_level),
                    metric.default_unit,
                ),
            )

        for observation in candidate.observations:
            _insert_observation(conn, observation)

        for document in candidate.documents:
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document.contract_version,
                    document.document_id,
                    document.dataset_id,
                    document.dataset_snapshot_id,
                    document.source_ref,
                    document.document_type,
                    document.title,
                    document.publisher,
                    document.content_hash,
                    _json(document.metadata),
                ),
            )

        for ev in candidate.evidence:
            conn.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ev.evidence_id,
                    candidate.metadata.dataset_id,
                    candidate.metadata.dataset_snapshot_id,
                    ev.source_ref,
                    ev.document_id,
                    ev.entity_id,
                    ev.period_id,
                    ev.metric_id,
                    ev.locator,
                    ev.quote,
                ),
            )

        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        if target_path.exists():
            try:
                target_path.unlink()
            except OSError:
                pass
        raise
    finally:
        if conn is not None:
            conn.close()

    return target_path


def generate_template_csv() -> str:
    """Generate blank template CSV with required headers and inputs."""
    headers = [
        "observation_id",
        "entity_id",
        "metric_id",
        "value",
        "unit",
        "period_id",
        "period_basis",
        "reporting_scope",
        "source_locator",
        "source_url",
        "source_sha256",
    ]
    rows = [
        ["", "", "bank.input.npl_group_3_balance", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.npl_group_4_balance", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.npl_group_5_balance", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.gross_customer_loans", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.loan_loss_provisions", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.profit_after_tax", "", "billion_vnd", "2024_Q4", "annual", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.profit_after_tax", "", "billion_vnd", "2023_Q4", "annual", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.total_assets", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.total_assets", "", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.parent_attributable_profit", "", "billion_vnd", "2024_Q4", "annual", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.parent_attributable_profit", "", "billion_vnd", "2023_Q4", "annual", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.total_equity", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.total_equity", "", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.non_controlling_interests", "", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.input.non_controlling_interests", "", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.npl_g35", "", "percent", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.llr_coverage", "", "percent", "2024_Q4", "point_in_time", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.roa", "", "percent", "2024_Q4", "ttm", "consolidated", "tr. ...", "https://...", ""],
        ["", "", "bank.roe", "", "percent", "2024_Q4", "ttm", "consolidated", "tr. ...", "https://...", ""],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def generate_ctg_sample_csv() -> str:
    """Generate valid CTG 2024 Q4 sample in upload format (adapted from reconciliation CSV)."""
    headers = [
        "observation_id",
        "entity_id",
        "metric_id",
        "value",
        "unit",
        "period_id",
        "period_basis",
        "reporting_scope",
        "source_locator",
        "source_url",
        "source_sha256",
    ]
    url = "https://investor.vietinbank.vn/documents/20126/214683/BCTC%2Bhop%2Bnhat%2Bkiem%2Btoan%2Bnam%2B2024.pdf"
    sha = "36513DD8B060712B188F9EAB03B1A7F9479AB21E63866DD95E45759D03EC5369"
    rows = [
        ["ctg-input-group-3-2024q4", "CTG", "bank.input.npl_group_3_balance", "2817.03", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-input-group-4-2024q4", "CTG", "bank.input.npl_group_4_balance", "4824.119", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-input-group-5-2024q4", "CTG", "bank.input.npl_group_5_balance", "13348.618", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-input-gross-loans-2024q4", "CTG", "bank.input.gross_customer_loans", "1721954.714", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-input-provisions-2024q4", "CTG", "bank.input.loan_loss_provisions", "36664.125", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=39; printed_page=37; section=Note 11", url, sha],
        ["ctg-input-npl-balance-2024q4", "CTG", "bank.input.npl_g35_balance", "20989.767", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-input-pat-2024q4", "CTG", "bank.input.profit_after_tax", "25482.567", "billion_vnd", "2024_Q4", "annual", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
        ["ctg-input-pat-2023q4", "CTG", "bank.input.profit_after_tax", "20044.622", "billion_vnd", "2023_Q4", "annual", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
        ["ctg-input-assets-2024q4", "CTG", "bank.input.total_assets", "2385387.732", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=7; printed_page=5; section=Consolidated balance sheet", url, sha],
        ["ctg-input-assets-2023q4", "CTG", "bank.input.total_assets", "2032613.606", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "pdf_page=7; printed_page=5; section=Consolidated balance sheet", url, sha],
        ["ctg-input-parent-profit-2024q4", "CTG", "bank.input.parent_attributable_profit", "25348.215", "billion_vnd", "2024_Q4", "annual", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
        ["ctg-input-parent-profit-2023q4", "CTG", "bank.input.parent_attributable_profit", "19903.55", "billion_vnd", "2023_Q4", "annual", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
        ["ctg-input-total-equity-2024q4", "CTG", "bank.input.total_equity", "148504.708", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-input-total-equity-2023q4", "CTG", "bank.input.total_equity", "125871.82", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-input-nci-2024q4", "CTG", "bank.input.non_controlling_interests", "970.729", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-input-nci-2023q4", "CTG", "bank.input.non_controlling_interests", "861.22", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-input-parent-equity-2024q4", "CTG", "bank.input.parent_attributable_equity", "147533.979", "billion_vnd", "2024_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-input-parent-equity-2023q4", "CTG", "bank.input.parent_attributable_equity", "125010.6", "billion_vnd", "2023_Q4", "point_in_time", "consolidated", "pdf_page=8; printed_page=6; section=Consolidated balance sheet", url, sha],
        ["ctg-bank-npl-g35-2024q4", "CTG", "bank.npl_g35", "1.219", "percent", "2024_Q4", "point_in_time", "consolidated", "pdf_page=38; printed_page=36; section=Note 10", url, sha],
        ["ctg-bank-llr-coverage-2024q4", "CTG", "bank.llr_coverage", "174.6762", "percent", "2024_Q4", "point_in_time", "consolidated", "pdf_page=39; printed_page=37; section=Note 11", url, sha],
        ["ctg-bank-roa-2024q4", "CTG", "bank.roa", "1.1536", "percent", "2024_Q4", "ttm", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
        ["ctg-bank-roe-2024q4", "CTG", "bank.roe", "18.6012", "percent", "2024_Q4", "ttm", "consolidated", "pdf_page=10; printed_page=8; section=Consolidated income statement", url, sha],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def generate_ctg_error_sample_csv() -> str:
    """Generate CTG sample with exactly 3 deliberate errors per UPLOAD-1 spec.

    1. Dòng gross_customer_loans thiếu trang nguồn ('Báo cáo tài chính kiểm toán năm 2024' không có số trang)
    2. Dòng loan_loss_provisions sai đơn vị ('triệu_vnd' thay vì 'billion_vnd')
    3. Dòng npl_g35 giá trị công bố lệch ('2.5' thay vì 1.2190%)
    """
    valid_text = generate_ctg_sample_csv()
    reader = csv.DictReader(io.StringIO(valid_text))
    rows = list(reader)
    fieldnames = reader.fieldnames or []

    for row in rows:
        m = row.get("metric_id")
        if m == "bank.input.gross_customer_loans":
            # 1. Thiếu trang nguồn
            row["source_locator"] = "Báo cáo tài chính kiểm toán năm 2024 phần phân tích nợ"
        elif m == "bank.input.loan_loss_provisions":
            # 2. Sai đơn vị
            row["unit"] = "triệu_vnd"
        elif m == "bank.npl_g35":
            # 3. Giá trị công bố lệch
            row["value"] = "2.5"

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
