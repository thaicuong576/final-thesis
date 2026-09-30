"""Deterministic Vietnamese summary generator for execution trace steps.

All trace step summaries must be generated programmatically in Vietnamese
without invoking language models or prompt templates.
"""

from __future__ import annotations

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
