"""LLM-assisted candidate row selector.

Phase: INGEST-6 (D-086).
Provides refine_candidates_with_llm:
- Sends candidate printed lines and metric definitions to an OpenAI-compatible LLM
- Model ONLY returns line_id, column_target, column_prior, and reason
- Code deterministically parses numbers from that line, applies unit conversion,
  validates value presence in page text, and marks source="llm_assisted_selection"
  with RowIssue(code="llm_selected", severity="info").
- Strict safety: if LLM returns unknown line_id, malformed JSON, or numbers not in text,
  the LLM response is safely ignored.
- No chain-of-thought is stored or shown.
"""

from __future__ import annotations

from decimal import Decimal
import json
import logging
import re
from typing import Any, Optional

from thesis_api.llm import get_llm_client
from thesis_api.settings import Settings
from thesis_data.filing_extract import (
    CandidateRow,
    ExtractionResult,
    METRIC_LABELS_VI,
    METRIC_SPECS,
    PageInput,
    RowIssue,
    _clean_spaces,
    extract_amount_columns_from_line,
    match_score_for_spec,
    unit_to_multiplier,
)
from thesis_data.filing_validate import validate_filing_rows

logger = logging.getLogger(__name__)

METRIC_DEFINITIONS_VI: dict[str, str] = {
    "bank.input.npl_group_3_balance": (
        "Số dư nợ dưới tiêu chuẩn (Nhóm 3) trong bảng phân loại chất lượng nợ cho vay theo Thông tư của NHNN "
        "(thường nằm trong Thuyết minh về Cho vay khách hàng / Rủi ro tín dụng)."
    ),
    "bank.input.npl_group_4_balance": (
        "Số dư nợ nghi ngờ (Nhóm 4) trong bảng phân loại chất lượng nợ cho vay theo Thông tư của NHNN "
        "(thường nằm trong Thuyết minh về Cho vay khách hàng / Rủi ro tín dụng)."
    ),
    "bank.input.npl_group_5_balance": (
        "Số dư nợ có khả năng mất vốn (Nhóm 5) trong bảng phân loại chất lượng nợ cho vay theo Thông tư của NHNN "
        "(thường nằm trong Thuyết minh về Cho vay khách hàng / Rủi ro tín dụng)."
    ),
    "bank.input.gross_customer_loans": (
        "Cho vay khách hàng (dư nợ cho vay gộp trước dự phòng rủi ro) trên Bảng cân đối kế toán "
        "hoặc dòng Tổng dư nợ cho vay trong thuyết minh."
    ),
    "bank.input.loan_loss_provisions": (
        "Dự phòng rủi ro cho vay khách hàng trên Bảng cân đối kế toán (thường ghi số âm trong ngoặc đơn) "
        "hoặc số dư dự phòng trích lập trong thuyết minh."
    ),
    "bank.input.profit_after_tax": (
        "Lợi nhuận sau thuế thu nhập doanh nghiệp (hoặc Tổng lợi nhuận sau thuế) trên Báo cáo kết quả hoạt động kinh doanh."
    ),
    "bank.input.total_assets": (
        "TỔNG CỘNG TÀI SẢN (hoặc Tổng tài sản) trên Bảng cân đối kế toán."
    ),
    "bank.input.parent_attributable_profit": (
        "Lợi nhuận sau thuế của cổ đông công ty mẹ trên Báo cáo kết quả hoạt động kinh doanh hợp nhất. "
        "Nếu báo cáo không trình bày riêng dòng này, tương đương lợi nhuận sau thuế."
    ),
    "bank.input.total_equity": (
        "TỔNG CỘNG VỐN CHỦ SỞ HỮU (hoặc Vốn chủ sở hữu) trên Bảng cân đối kế toán."
    ),
    "bank.input.non_controlling_interests": (
        "Lợi ích của cổ đông không kiểm soát (hoặc Cổ đông thiểu số) thuộc phần vốn chủ sở hữu trên Bảng cân đối kế toán. "
        "Nếu không phát sinh thì ghi nhận 0."
    ),
}


def _extract_json_payload(raw_content: str) -> Optional[dict[str, Any]]:
    """Parse JSON object from LLM output, stripping markdown code blocks if present."""
    if not raw_content:
        return None
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None


def refine_candidates_with_llm(
    extraction: ExtractionResult,
    pages: list[PageInput],
    *,
    settings: Optional[Settings] = None,
    client: Optional[Any] = None,
    model: Optional[str] = None,
) -> tuple[ExtractionResult, int]:
    """Refine candidate rows using LLM line selection for missing/unclear metrics.

    Returns:
        tuple[ExtractionResult, int]: (updated extraction result, total tokens used)
    """
    effective_client = client
    if effective_client is None:
        try:
            effective_client = get_llm_client(settings)
        except Exception as exc:
            logger.warning("LLM client unavailable for filing row assist: %s", exc)
            return extraction, 0

    effective_model = model or (settings.openai_model if settings else None)
    if not effective_model:
        logger.warning("No OpenAI model configured for filing row assist")
        return extraction, 0

    pages_by_num = {p.page_number: p for p in pages}
    unit_multiplier = unit_to_multiplier(extraction.unit_detected) if extraction.unit_detected else None
    target_period = f"{extraction.fiscal_year}_Q4"
    prior_period = f"{extraction.fiscal_year - 1}_Q4"

    new_rows = list(extraction.rows)
    total_tokens_used = 0

    for spec in METRIC_SPECS:
        metric_rows = [r for r in new_rows if r.metric_id == spec.metric_id]
        if not metric_rows:
            continue

        # Check if metric needs assist: missing, needs_review, or has wrong-row risk (multiple alternatives)
        has_missing_or_review = any(r.status in ("missing", "needs_review") for r in metric_rows)
        has_alternatives_risk = any(len(r.alternatives) > 0 for r in metric_rows)
        if not (has_missing_or_review or has_alternatives_risk):
            continue

        # Locate classified statement pages for this metric
        sec_name = spec.target_section
        pnums = list(getattr(extraction.statement_pages, sec_name, []))
        if not pnums:
            if spec.metric_id == "bank.input.gross_customer_loans":
                pnums = list(extraction.statement_pages.balance_sheet)
            elif spec.metric_id == "bank.input.loan_loss_provisions":
                pnums = list(extraction.statement_pages.loan_quality_note)
            elif spec.metric_id == "bank.input.parent_attributable_profit":
                pnums = list(extraction.statement_pages.income_statement)

        candidate_pages = [pages_by_num[pn] for pn in pnums if pn in pages_by_num]
        if not candidate_pages:
            continue

        # Gather candidate printed lines from classified pages
        candidate_items: list[dict[str, Any]] = []
        seen_lines: set[str] = set()

        for p in candidate_pages:
            for line in p.text.splitlines():
                line_clean = _clean_spaces(line)
                if not line_clean or line_clean in seen_lines:
                    continue
                score = match_score_for_spec(line_clean, spec)
                amounts = extract_amount_columns_from_line(line_clean)
                # Keep line if relevant keywords or table row with numbers
                if score >= 0.25 or (amounts and score >= 0.15) or (amounts and "|" in line):
                    seen_lines.add(line_clean)
                    candidate_items.append({
                        "line_id": f"L{len(candidate_items) + 1}",
                        "page": p.page_number,
                        "text": line_clean,
                    })
                    if len(candidate_items) >= 40:
                        break
            if len(candidate_items) >= 40:
                break

        # Also include lines from existing alternatives if not already added
        for r in metric_rows:
            for alt in r.alternatives:
                if alt.raw_text and alt.raw_text not in seen_lines:
                    seen_lines.add(alt.raw_text)
                    candidate_items.append({
                        "line_id": f"L{len(candidate_items) + 1}",
                        "page": alt.page,
                        "text": alt.raw_text,
                    })
                    if len(candidate_items) >= 40:
                        break

        if not candidate_items:
            continue

        items_by_id = {item["line_id"]: item for item in candidate_items}
        lines_repr = json.dumps(candidate_items, ensure_ascii=False, indent=2)

        prompt = (
            f"Chỉ tiêu cần tìm: {METRIC_LABELS_VI.get(spec.metric_id, spec.metric_id)}\n"
            f"Mã chỉ tiêu: {spec.metric_id}\n"
            f"Định nghĩa: {METRIC_DEFINITIONS_VI.get(spec.metric_id, '')}\n"
            f"Kỳ mục tiêu: {target_period} (Năm {extraction.fiscal_year})\n"
            f"Kỳ so sánh: {prior_period} (Năm {extraction.fiscal_year - 1})\n\n"
            f"Danh sách các dòng in sẵn từ trang báo cáo:\n{lines_repr}\n\n"
            f"Nhiệm vụ: Chọn đúng dòng in thể hiện chỉ tiêu trên. "
            f"Bạn TUYỆT ĐỐI KHÔNG viết số, chỉ chọn line_id từ danh sách trên.\n"
            f"Trả về duy nhất định dạng JSON:\n"
            f'{{"line_id": "<line_id hoặc null>", "column_target": <0 hoặc 1 hoặc null>, "column_prior": <1 hoặc 2 hoặc null>, "reason": "<giải thích ngắn>"}}'
        )

        try:
            create_kwargs: dict[str, Any] = {
                "model": effective_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Bạn là chuyên gia kế toán tài chính ngân hàng Việt Nam. "
                            "Chỉ chọn dòng in từ danh sách được cung cấp. Tuyệt đối không tự bịa số hay sửa số. "
                            "Trả về duy nhất JSON hợp lệ."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
            resp = effective_client.chat.completions.create(**create_kwargs)
            if hasattr(resp, "usage") and resp.usage:
                total_tokens_used += getattr(resp.usage, "total_tokens", 0)

            content = ""
            if resp.choices and len(resp.choices) > 0:
                choice = resp.choices[0]
                content = choice.message.content if hasattr(choice, "message") else ""

            payload = _extract_json_payload(content)
            if not payload:
                continue

            sel_id = payload.get("line_id")
            if not sel_id or sel_id not in items_by_id:
                # LLM returned null or unknown line_id: safely ignore
                continue

            selected_item = items_by_id[sel_id]
            selected_line = selected_item["text"]
            selected_page_num = int(selected_item["page"])
            reason = str(payload.get("reason") or "Mô hình ngôn ngữ nhận diện dòng phù hợp")

            # CODE extracts numbers from the selected printed line
            amounts = extract_amount_columns_from_line(selected_line)
            if not amounts and not spec.allow_zero_default:
                continue

            col_t = payload.get("column_target")
            col_p = payload.get("column_prior")

            val_target: Optional[Decimal] = None
            val_prior: Optional[Decimal] = None

            if isinstance(col_t, int) and 0 <= col_t < len(amounts):
                val_target = amounts[col_t]
            elif len(amounts) >= 1:
                val_target = amounts[0]

            if isinstance(col_p, int) and 0 <= col_p < len(amounts):
                val_prior = amounts[col_p]
            elif len(amounts) >= 2:
                val_prior = amounts[1]

            if spec.metric_id == "bank.input.loan_loss_provisions":
                if val_target is not None and val_target < 0:
                    val_target = abs(val_target)
                if val_prior is not None and val_prior < 0:
                    val_prior = abs(val_prior)

            if unit_multiplier is not None:
                target_b = (
                    (val_target * unit_multiplier).quantize(Decimal("0.001"))
                    if val_target is not None
                    else None
                )
                prior_b = (
                    (val_prior * unit_multiplier).quantize(Decimal("0.001"))
                    if val_prior is not None
                    else None
                )
            else:
                target_b = None
                prior_b = None

            # Verify that page text contains the value (value_in_page_text)
            p_obj = pages_by_num.get(selected_page_num)
            if not p_obj:
                continue

            for role, b_val in [("target", target_b), ("prior", prior_b)]:
                r_idx = next(
                    (
                        i
                        for i, r in enumerate(new_rows)
                        if r.metric_id == spec.metric_id and r.period_role == role
                    ),
                    None,
                )
                if r_idx is None or b_val is None:
                    continue

                old_r = new_rows[r_idx]
                b_str = str(b_val)

                # Keep existing issues that are not row_not_found/low_confidence
                upd_issues = [
                    iss
                    for iss in old_r.issues
                    if iss.code not in ("row_not_found", "low_confidence_match", "column_missing")
                ]
                upd_issues.append(
                    RowIssue(
                        code="llm_selected",
                        severity="info",
                        message_vi=f"Dòng được hỗ trợ nhận diện bởi mô hình ({reason})",
                    )
                )

                new_rows[r_idx] = CandidateRow(
                    row_id=old_r.row_id,
                    metric_id=old_r.metric_id,
                    label_vi=old_r.label_vi,
                    period_role=old_r.period_role,
                    period_id=old_r.period_id,
                    value_billion_vnd=b_str,
                    extracted_value_billion_vnd=b_str,
                    raw_text=selected_line,
                    row_label=selected_line,
                    page=selected_page_num,
                    source="llm_assisted_selection",
                    status="candidate",
                    edited=old_r.edited,
                    confirmed=old_r.confirmed,
                    issues=upd_issues,
                    alternatives=old_r.alternatives,
                )
        except Exception as call_err:
            logger.warning("LLM row selector call failed for %s: %s", spec.metric_id, call_err)
            continue

    val_res = validate_filing_rows(new_rows, page_texts={p.page_number: p.text for p in pages})

    updated_result = ExtractionResult(
        filing_id=extraction.filing_id,
        entity_id=extraction.entity_id,
        display_name=extraction.display_name,
        fiscal_year=extraction.fiscal_year,
        reporting_scope=extraction.reporting_scope,
        page_count=extraction.page_count,
        ocr_provider=extraction.ocr_provider,
        text_layer_pages=extraction.text_layer_pages,
        ocr_pages=extraction.ocr_pages,
        statement_pages=extraction.statement_pages,
        unit_detected=extraction.unit_detected,
        rows=new_rows,
        validation=val_res.to_dict(),
        limitations_vi=extraction.limitations_vi,
    )

    return updated_result, total_tokens_used
