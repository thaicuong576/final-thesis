"""Vietnamese error messages and dynamic prompt suggestions."""

from __future__ import annotations

import re
from typing import Any

from .metric_presentation import get_metric_presentation

MESSAGES: dict[str, str] = {
    "unsupported_period": "Kỳ phân tích yêu cầu không có trong dữ liệu đã kiểm định. Các kỳ hiện có: {periods}.",
    "unsupported_metric": "Chỉ tiêu yêu cầu chưa có trong dữ liệu đã kiểm định. Các chỉ tiêu hiện có: {metrics}.",
    "unsupported_entity": "Ngân hàng yêu cầu không có trong danh sách hỗ trợ. Các ngân hàng hiện có: {entities}.",
    "metric_required": "Yêu cầu cần nêu rõ ít nhất một chỉ tiêu tài chính (ví dụ: nợ xấu, bao phủ, ROA, ROE).",
    "unsupported_macro_scope": "Chưa có dữ liệu vĩ mô đã kiểm định trong hệ thống.",
    "provider_failure": "Nhà cung cấp dữ liệu không thể xử lý yêu cầu này.",
    "adaptive_runtime_failure": "Hệ thống phân tích thích ứng không thể hoàn thành yêu cầu.",
    "analysis_writer_unconfigured": "Mô hình chuyên gia phân tích chưa được cấu hình.",
    "semantic_provider_unconfigured": "Mô hình phản biện ngữ nghĩa chưa được cấu hình.",
    "accepted_snapshot_unavailable": "Không tìm thấy snapshot dữ liệu hợp lệ đã được phê duyệt.",
    "target_entity_required": "Cần cung cấp ít nhất một ngân hàng có trong danh mục hỗ trợ.",
    "exact_period_required": "Cần cung cấp kỳ phân tích hợp lệ được hỗ trợ bởi hệ thống.",
    "upload_not_found": "Tệp tải lên không tồn tại hoặc đã bị xóa.",
    "upload_unaccepted": "Tệp tải lên chưa được chấp nhận hoặc có lỗi xác thực.",
    "upload_question_type_unsupported": "Dữ liệu tải lên chỉ hỗ trợ các dạng câu hỏi: tra cứu chỉ tiêu (lookup), hồ sơ ngân hàng (company_profile), và so sánh trực tiếp với 1 ngân hàng Gold (head_to_head).",
    "upload_period_mismatch": "Dữ liệu ngân hàng tải lên chỉ có số liệu cho kỳ được tải, không hỗ trợ kỳ khác.",
}


def _format_periods_summary(periods: list[str]) -> str:
    """Format catalog periods into a human-readable string like 'Q1–Q4/2024'."""
    quarters: list[tuple[int, int]] = []
    for p in periods:
        m = re.fullmatch(r"(\d{4})_Q([1-4])", p, re.I)
        if m:
            quarters.append((int(m.group(1)), int(m.group(2))))
    if quarters:
        years = {y for y, _ in quarters}
        if len(years) == 1:
            y = next(iter(years))
            qs = sorted(q for _, q in quarters)
            if qs == [1, 2, 3, 4]:
                return f"Q1–Q4/{y}"
            return f"Q{qs[0]}–Q{qs[-1]}/{y}" if len(qs) > 1 else f"Q{qs[0]}/{y}"
    return ", ".join(periods) if periods else "không có"


def get_error_message(code: str, catalog: Any = None, default: str | None = None) -> str:
    """Look up localized Vietnamese error message and format catalog placeholders."""
    template = MESSAGES.get(code)
    if template is None:
        return default or f"Lỗi hệ thống: {code}."

    if catalog is None:
        return template.replace("{periods}", "không xác định").replace("{metrics}", "không xác định").replace("{entities}", "không xác định")

    # Catalog periods
    catalog_periods = [p.period_id for p in catalog.periods]
    periods_str = _format_periods_summary(catalog_periods)

    # Catalog metrics
    metrics_str = ", ".join(
        get_metric_presentation(m.metric_id, m.display_name).label
        for m in catalog.metrics
        if not m.metric_id.startswith("bank.input.")
    )

    # Catalog entities
    entities_str = ", ".join(
        e.attributes.get("ticker", e.entity_id)
        for e in catalog.entities
        if e.entity_type.value == "company"
    )

    return (
        template.replace("{periods}", periods_str)
        .replace("{metrics}", metrics_str)
        .replace("{entities}", entities_str)
    )


def suggestions_for(catalog: Any) -> list[str]:
    """Generate 5 suggested questions, one per enabled question type, dynamically from catalog."""
    if catalog is None:
        return []

    company_entities = [
        e.attributes.get("ticker", e.entity_id)
        for e in catalog.entities
        if e.entity_type.value == "company"
    ]
    if not company_entities:
        return []

    e1 = company_entities[0]
    e2 = company_entities[1] if len(company_entities) > 1 else company_entities[0]
    e3 = company_entities[2] if len(company_entities) > 2 else company_entities[0]

    # Latest period
    catalog_periods = [p.period_id for p in catalog.periods]
    y, q = 2024, 4
    if catalog_periods:
        latest = catalog_periods[-1]
        m = re.fullmatch(r"(\d{4})_Q([1-4])", latest, re.I)
        if m:
            y, q = int(m.group(1)), int(m.group(2))

    # First higher_is_better metric for ranking
    hi_metric_label = "tỷ lệ bao phủ nợ xấu"
    for m in catalog.metrics:
        if m.metric_id.startswith("bank.input."):
            continue
        pres = get_metric_presentation(m.metric_id, m.display_name)
        if pres.direction == "higher_is_better":
            hi_metric_label = pres.label.lower()
            break

    return [
        f"Tỷ lệ nợ xấu của {e1} quý {q}/{y} là bao nhiêu?",
        f"Ngân hàng nào có {hi_metric_label} cao nhất quý {q}/{y}?",
        f"ROE của {e2} thay đổi thế nào trong năm {y}?",
        f"So sánh {e1} và {e3} quý {q}/{y}",
        f"Sức khỏe tài chính của {e1} so với các ngân hàng cùng nhóm, quý {q}/{y}",
    ]
