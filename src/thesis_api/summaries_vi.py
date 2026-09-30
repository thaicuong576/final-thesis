"""Deterministic Vietnamese summary generator for execution trace steps.

All trace step summaries must be generated programmatically in Vietnamese
without invoking language models or prompt templates.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

QUESTION_TYPE_LABELS_VI: dict[str, str] = {
    "lookup": "Tra cứu",
    "company_profile": "Hồ sơ doanh nghiệp",
    "ranking": "Xếp hạng",
    "trend": "Diễn biến",
    "head_to_head": "Đối đầu",
    "sector_theme": "Chủ đề toàn nhóm",
    "relationship": "Quan hệ chỉ tiêu",
}

TOOL_LABELS_VI: dict[str, str] = {
    "lookup": "tra cứu chỉ tiêu",
    "trend": "diễn biến chuỗi thời gian",
    "head_to_head": "so sánh đối đầu",
    "decomposition": "phân rã chỉ tiêu",
    "peer_position": "vị thế nhóm ngành",
    "ranking": "xếp hạng toàn nhóm",
    "dispersion": "độ phân tán",
    "relationship": "tương quan chỉ tiêu",
}

AGENT_LABELS_VI: dict[str, str] = {
    "orchestrator": "Điều phối viên",
    "company": "Doanh nghiệp",
    "sector": "Nhóm ngành",
    "macro": "Vĩ mô",
    "critic": "Phản biện",
    "verifier": "Kiểm tra",
    "system": "Hệ thống",
}

BLOCK_TYPE_LABELS_VI: dict[str, str] = {
    "headline": "tiêu đề",
    "answer": "câu trả lời",
    "key_points": "luận điểm",
    "section": "phần phân tích",
    "figure": "hình",
    "table": "bảng",
    "callout": "lưu ý",
}


def summary_plan(
    question_type: str,
    tools: Sequence[Any],
    active_agents: Sequence[str] | None = None,
) -> str:
    """Generate Vietnamese summary for plan step."""
    q_label = QUESTION_TYPE_LABELS_VI.get(question_type, question_type)
    agents = [AGENT_LABELS_VI.get(a, a) for a in (active_agents or ["company"])]
    agents_str = ", ".join(agents) if agents else "Doanh nghiệp"
    n_tools = len(tools)
    return f"Dạng câu hỏi: {q_label}. Gọi {agents_str} với {n_tools} phép phân tích"


def summary_assign(
    recipient: str,
    task: str | None = None,
    tools: Sequence[str] | None = None,
    round_no: int | None = None,
) -> str:
    """Generate Vietnamese summary for assign step."""
    if recipient == "critic":
        r = round_no or 1
        return f"Gửi bản nháp để kiểm tra chéo (vòng {r})"
    agent_label = AGENT_LABELS_VI.get(recipient, recipient)
    if task:
        return f"Giao việc: {task}"
    if tools:
        t_str = " · ".join(tools)
        return f"Giao việc: {t_str}"
    return f"Giao việc cho chuyên viên {agent_label}"


def summary_tool_result(
    tool_label: str,
    n_facts: int,
    extra: str | None = None,
) -> str:
    """Generate Vietnamese summary for tool_result step."""
    if extra:
        return f"Trả {n_facts} số liệu có nguồn, {extra}"
    return f"Trả {n_facts} số liệu có nguồn từ phép phân tích {tool_label}"


def summary_draft(
    role: str,
    n_sentences: int,
) -> str:
    """Generate Vietnamese summary for draft step."""
    del role
    return f"Gửi {n_sentences} nhận định nháp"


def summary_verify(
    numbers_matched: int,
    numbers_checked: int,
    dropped_count: int,
) -> str:
    """Generate Vietnamese summary for verify step."""
    if dropped_count > 0:
        return f"{numbers_matched}/{numbers_checked} số khớp dữ liệu gốc; loại {dropped_count} câu"
    return f"{numbers_matched}/{numbers_checked} số khớp dữ liệu gốc; tất cả câu đều đạt"


def summary_compose(
    kind: str,
    blocks: Sequence[Any] | None = None,
    composition_source: str | None = None,
) -> str:
    """Generate Vietnamese summary for compose step."""
    del composition_source
    kind_label = "ghi chú sàng lọc" if kind == "note" else "báo cáo tổng hợp"
    if not blocks:
        return f"Dựng {kind_label}"

    counts: dict[str, int] = {}
    for b in blocks:
        b_type = getattr(b, "type", None) or (b.get("type") if isinstance(b, dict) else "unknown")
        counts[b_type] = counts.get(b_type, 0) + 1

    parts: list[str] = []
    if "headline" in counts:
        parts.append("tiêu đề")
    if "figure" in counts:
        parts.append(f"{counts['figure']} hình")
    if "key_points" in counts or "answer" in counts:
        lp = counts.get("key_points", 0) + counts.get("answer", 0)
        parts.append(f"{lp} luận điểm")
    if "callout" in counts:
        parts.append(f"{counts['callout']} lưu ý")
    if "table" in counts:
        parts.append(f"{counts['table']} bảng")

    if parts:
        desc = ", ".join(parts)
        return f"Dựng {kind_label}: {desc}"
    return f"Dựng {kind_label}: {len(blocks)} khối nội dung"


def summary_critique_issue(
    description: str | None = None,
    issue_type: str | None = None,
    required_action: str | None = None,
) -> str:
    """Generate Vietnamese summary for critique_issue step."""
    del issue_type, required_action
    if description and description.strip():
        # Clean or shorten if very long
        clean = description.strip()
        if len(clean) > 80:
            clean = clean[:77] + "..."
        return f"Yêu cầu sửa: {clean}"
    return "Yêu cầu sửa 1 câu không có căn cứ"


def summary_cross_level_finding(
    count: int = 1,
) -> str:
    """Generate Vietnamese summary for cross_level_finding step."""
    return f"Phát hiện {count} điểm cần lưu ý giữa các chỉ tiêu"


def summary_revision(
    round_no: int = 1,
    author: str | None = None,
) -> str:
    """Generate Vietnamese summary for revision step."""
    del round_no, author
    return "Đã sửa theo phản biện"


def summary_accept(
    round_no: int = 1,
    open_issues: int = 0,
) -> str:
    """Generate Vietnamese summary for accept step."""
    if open_issues == 0:
        return f"Vòng {round_no}: chấp nhận, không còn vấn đề mở"
    return f"Vòng {round_no}: hoàn tất kiểm tra chéo ({open_issues} vấn đề chưa giải quyết)"


def summary_report_ready() -> str:
    """Generate Vietnamese summary for report_ready step."""
    return "Báo cáo sẵn sàng"


def summary_blocked(
    code_or_message: str | None = None,
    message: str | None = None,
    *,
    code: str | None = None,
) -> str:
    """Generate Vietnamese summary for blocked step."""
    del code
    if message:
        return message
    if code_or_message:
        return code_or_message
    return "Yêu cầu bị chặn"


def _extract_metric_name(text: str) -> str | None:
    t_lower = text.lower()
    if re.search(r"\broe\b", text, re.IGNORECASE):
        return "ROE"
    if re.search(r"\broa\b", text, re.IGNORECASE):
        return "ROA"
    if re.search(r"\b(?:tỷ lệ nợ xấu|nợ xấu|npl)\b", t_lower):
        return "tỷ lệ nợ xấu"
    if re.search(r"\b(?:tỷ lệ bao phủ nợ xấu|bao phủ nợ xấu|đệm bao phủ|đệm dự phòng|llr)\b", t_lower):
        return "tỷ lệ bao phủ nợ xấu"
    if re.search(r"\bcasa\b", t_lower):
        return "tỷ lệ CASA"
    if re.search(r"\bnim\b", text, re.IGNORECASE):
        return "NIM"
    if re.search(r"\bcir\b", text, re.IGNORECASE):
        return "tỷ lệ CIR"
    if re.search(r"\bldr\b", text, re.IGNORECASE):
        return "tỷ lệ LDR"
    return None


def _extract_period_name(text: str) -> str | None:
    m = re.search(r"\b(?:quý\s*([1-4])[/_](\d{4})|Q([1-4])[/_](\d{4})|(\d{4})[/_]Q([1-4]))\b", text, re.IGNORECASE)
    if m:
        q = m.group(1) or m.group(3) or m.group(6)
        y = m.group(2) or m.group(4) or m.group(5)
        return f"quý {q}/{y}"
    return None


def _format_single_critic_limitation(desc: str) -> str | None:
    if not desc or not desc.strip():
        return None
    raw = desc.strip()

    # Pattern 1: Single observation peer median / sample size limitation
    is_peer_median = bool(re.search(r"(?:trung vị ngành|trung vị|peer median|peer_median)", raw, re.IGNORECASE))
    is_single_obs = bool(re.search(r"(?:1 quan sát|một quan sát|chỉ có 1|chỉ có một|mẫu chỉ có 1|mẫu chỉ có một|đúng giá trị của|duy nhất)", raw, re.IGNORECASE))

    if is_peer_median and is_single_obs:
        metric = _extract_metric_name(raw)
        period = _extract_period_name(raw)
        if metric and period:
            return f"Trung vị ngành cho {metric} {period} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo."
        if metric:
            return f"Trung vị ngành cho {metric} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo."
        if period:
            return f"Trung vị ngành {period} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo."
        return "Trung vị ngành chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo."

    if is_peer_median and re.search(r"(?:cỡ mẫu|mẫu so sánh|số lượng quan sát hạn chế)", raw, re.IGNORECASE):
        return "Mẫu so sánh trung vị ngành có số lượng quan sát hạn chế, nên so sánh mang tính tham khảo."

    # Pattern 2: Internal technical identifiers or writer directives
    has_internal_id = bool(re.search(r"\b(?:sent-[a-zA-Z0-9_-]+|fact:[a-zA-Z0-9_:-]+|block[ _-]?\d+)\b", raw, re.IGNORECASE))
    has_writer_command = bool(re.search(r"\b(?:cần bổ sung|cần điều chỉnh|cần diễn đạt|cần kiểm tra|cần lưu ý|đề nghị|khuyến nghị)\b", raw, re.IGNORECASE))
    has_english_code = bool(re.search(r"\b(?:peer[ _]median|lead_count|observation_id|reporting_scope|unresolved_critique|delta_pp)\b", raw, re.IGNORECASE))

    if has_internal_id or has_writer_command or has_english_code:
        return None

    # Pattern 3: Clean Vietnamese limitation (strip any critic prefix if present)
    cleaned = re.sub(r"^(?:góp ý phản biện(?: chưa xử lý)?(?:\s*\([^)]*\))?\s*:\s*|phản biện\s*:\s*)", "", raw, flags=re.IGNORECASE).strip()
    if cleaned and len(cleaned) <= 160:
        return cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()

    return None


def format_critic_limitations(issues: Sequence[Any]) -> list[str]:
    """Convert critique issues into reader-facing Vietnamese limitations."""
    results: list[str] = []
    unhandled_count = 0
    seen: set[str] = set()

    for item in issues:
        desc = getattr(item, "description", None) or str(item)
        if not desc or not desc.strip():
            continue
        formatted = _format_single_critic_limitation(desc)
        if formatted:
            if formatted not in seen:
                seen.add(formatted)
                results.append(formatted)
        else:
            unhandled_count += 1

    if unhandled_count > 0:
        msg = (
            "Bộ phản biện còn 1 lưu ý chưa xử lý; xem quá trình phân tích."
            if unhandled_count == 1
            else f"Bộ phản biện còn {unhandled_count} lưu ý chưa xử lý; xem quá trình phân tích."
        )
        if msg not in seen:
            results.append(msg)

    return results


def clean_reader_facing_limitations(limitations: Sequence[str]) -> list[str]:
    """Sanitize limitation items to ensure no internal IDs or raw writer instructions leak."""
    results: list[str] = []
    unhandled_count = 0
    seen: set[str] = set()

    for item in limitations:
        if not item or not item.strip():
            continue
        raw = item.strip()

        has_internal_id = bool(re.search(r"\b(?:sent-[a-zA-Z0-9_-]+|block[ _-]?\d+)\b", raw, re.IGNORECASE))
        has_writer_command = bool(re.search(r"\b(?:cần bổ sung|cần điều chỉnh|cần diễn đạt|cần kiểm tra|đề nghị|khuyến nghị)\b", raw, re.IGNORECASE))
        is_critic_prefix = bool(re.search(r"^góp ý phản biện", raw, re.IGNORECASE))

        if has_internal_id or has_writer_command or is_critic_prefix:
            formatted = _format_single_critic_limitation(raw)
            if formatted:
                if formatted not in seen:
                    seen.add(formatted)
                    results.append(formatted)
            else:
                unhandled_count += 1
            continue

        if "fact:" in raw:
            raw = re.sub(r"fact:[a-zA-Z0-9_.:-]+", "chỉ tiêu", raw)

        if raw not in seen:
            seen.add(raw)
            results.append(raw)

    if unhandled_count > 0:
        msg = (
            "Bộ phản biện còn 1 lưu ý chưa xử lý; xem quá trình phân tích."
            if unhandled_count == 1
            else f"Bộ phản biện còn {unhandled_count} lưu ý chưa xử lý; xem quá trình phân tích."
        )
        if msg not in seen:
            results.append(msg)

    return results

