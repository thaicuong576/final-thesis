"""Analytical tools catalog and question types definition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ENABLED_QUESTION_TYPES: tuple[str, ...] = (
    "lookup",
    "company_profile",
    "ranking",
    "trend",
    "head_to_head",
)

DISABLED_QUESTION_TYPES: tuple[str, ...] = (
    "sector_theme",
    "relationship",
)

ALL_QUESTION_TYPES: tuple[str, ...] = ENABLED_QUESTION_TYPES + DISABLED_QUESTION_TYPES


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    agent: Literal["company", "sector"]
    description: str
    required_params: tuple[str, ...]
    optional_params: tuple[str, ...]
    enabled: bool = True


TOOL_CATALOG: dict[str, ToolDefinition] = {
    "lookup": ToolDefinition(
        name="lookup",
        agent="company",
        description="Tra cứu quan sát thực tế của 1-3 ngân hàng cho 1-4 chỉ tiêu tại một kỳ.",
        required_params=("entities", "metrics", "period"),
        optional_params=(),
    ),
    "peer_position": ToolDefinition(
        name="peer_position",
        agent="sector",
        description="Xác định vị thế và khoảng cách của một ngân hàng so với trung vị ngành tại một kỳ.",
        required_params=("entity", "metrics", "period"),
        optional_params=(),
    ),
    "ranking": ToolDefinition(
        name="ranking",
        agent="sector",
        description="Xếp hạng toàn bộ ngân hàng theo một chỉ tiêu, có thể làm nổi bật một ngân hàng hoặc kèm chỉ tiêu ngữ cảnh.",
        required_params=("metric", "period"),
        optional_params=("highlight_entity", "context_metrics"),
    ),
    "trend": ToolDefinition(
        name="trend",
        agent="company",
        description="Theo dõi diễn biến chuỗi thời gian 2-4 kỳ của một ngân hàng theo 1-4 chỉ tiêu.",
        required_params=("entity", "metrics", "periods"),
        optional_params=(),
    ),
    "head_to_head": ToolDefinition(
        name="head_to_head",
        agent="sector",
        description="So sánh đối đầu trực diện giữa 2-3 ngân hàng trên 1-4 chỉ tiêu tại một kỳ.",
        required_params=("entities", "metrics", "period"),
        optional_params=(),
    ),
    "decomposition": ToolDefinition(
        name="decomposition",
        agent="company",
        description="Phân rã chỉ tiêu tài chính phái sinh (ví dụ ROE/ROA) cho 1-3 ngân hàng tại một kỳ.",
        required_params=("entities", "period", "formula"),
        optional_params=(),
    ),
    "dispersion": ToolDefinition(
        name="dispersion",
        agent="sector",
        description="Phân tích độ phân tán của một chỉ tiêu trong toàn ngành tại một kỳ.",
        required_params=("metric", "period"),
        optional_params=(),
        enabled=False,
    ),
    "relationship": ToolDefinition(
        name="relationship",
        agent="sector",
        description="Phân tích mối quan hệ giữa 2 chỉ tiêu tại một kỳ.",
        required_params=("metric_x", "metric_y", "period"),
        optional_params=(),
        enabled=False,
    ),
}
