"""Query-adaptive analytical planning with rules and model-based proposals."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Sequence

from thesis_data.analysis_plan import (
    ANALYSIS_PLAN_VERSION,
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisScope,
    ApplicableLink,
    ApplicableLinkType,
    CausalClaimPolicy,
    FulfillmentPolicy,
    InferenceCeiling,
    LinkLevel,
    MissingDataPolicy,
    RequirementType,
)
from thesis_data.dataset_contract import DatasetCapabilityCatalog, DatasetRef, SupportedOperation

from .analysis_tools_catalog import (
    DISABLED_QUESTION_TYPES,
    ENABLED_QUESTION_TYPES,
    TOOL_CATALOG,
)
from .metric_presentation import (
    DERIVED,
    get_metric_presentation,
)
from .query_understanding import ResolvedQuery
from .service import AnalysisBlocked, _is_lineage_only_metric


@dataclass(frozen=True)
class ToolCallSpec:
    tool: str
    params: dict[str, Any]


@dataclass(frozen=True)
class PlanSpec:
    question_type: str
    focus_entity: str | None
    entities: tuple[str, ...]
    metrics: tuple[str, ...]
    anchor_period: str
    periods: tuple[str, ...]
    tools: tuple[ToolCallSpec, ...]
    rationale: str
    limitations: tuple[str, ...] = ()


_MODEL_PLAN_PROMPT = (
    "Bạn là điều phối viên của một nhóm phân tích ngân hàng. Đọc câu hỏi và lập kế hoạch.\n"
    "Chọn đúng một question_type trong danh sách được bật, chọn công cụ trong danh mục (tối đa 5 lần gọi) với tham số hợp lệ,\n"
    "và viết 1 câu tiếng Việt giải thích lựa chọn (rationale).\n"
    "Ràng buộc:\n"
    '- Chỉ dùng ngân hàng, kỳ, chỉ tiêu có trong "catalog".\n'
    '- Nếu "da_nhan_dien" đã có ngân hàng/kỳ/chỉ tiêu tường minh thì phải giữ nguyên, không thay, không bỏ.\n'
    "- periods phải chứa mọi kỳ cần dùng, tối thiểu là anchor_period.\n"
    "- Được thêm công cụ bổ trợ nếu giúp trả lời sâu hơn (ví dụ decomposition khi hỏi về sinh lời), không thêm công cụ vô ích.\n"
    "- Không lập kế hoạch cho dữ liệu không có (vĩ mô, định giá).\n"
    'Trả về JSON: {"question_type":"…","focus_entity":…,"entities":[…],"metrics":[…],"anchor_period":"…","periods":[…],'
    '"tools":[{"tool":"…","params":{…}}],"rationale":"…"}'
)


# BANKING_SECTOR_TERMS: Canonical scope terms denoting the Vietnamese banking industry.
BANKING_SECTOR_TERMS: tuple[str, ...] = (
    "ngân hàng",
    "ngành ngân hàng",
    "nhóm ngân hàng",
    "các ngân hàng",
    "toàn ngành",
    "hệ thống ngân hàng",
)

# ANALYTIC_INTENT_CUES: Deterministic domain keywords indicating analytical financial intent
# (e.g. ranking, health, comparison, operational overview) for sector-level queries lacking
# an explicit entity or catalog metric name.
ANALYTIC_INTENT_CUES: tuple[str, ...] = (
    "tốt nhất",
    "tốt hơn",
    "an toàn",
    "tình hình",
    "so sánh",
    "xếp hạng",
    "đánh giá",
    "hoạt động",
    "sức khỏe",
    "chất lượng",
    "hiệu quả",
)

# NON_ANALYTIC_OVERRIDES: Deterministic keyword patterns for queries outside analytical scope
# (creative writing, translation, programming, non-catalog forecasting) that must fail closed
# even when a banking sector term is present.
NON_ANALYTIC_CREATIVE_CUES: tuple[str, ...] = (
    "sáng tác",
    "bài thơ",
    "làm thơ",
    "bài hát",
    "viết văn",
    "tiểu thuyết",
)

NON_ANALYTIC_TRANSLATION_CUES: tuple[str, ...] = (
    "dịch sang",
    "dịch đoạn",
    "dịch câu",
    "dịch bài",
    "dịch từ",
    "dịch văn",
    "tiếng anh",
    "translate",
    "translation",
)

NON_ANALYTIC_CODING_CUES: tuple[str, ...] = (
    "viết code",
    "code python",
    "lập trình",
    "viết hàm",
    "viết script",
    "script",
)

NON_ANALYTIC_FORECAST_CUES: tuple[str, ...] = (
    "dự báo",
    "tuần tới",
    "sẽ ra sao",
    "giá vàng",
    "giá xăng",
    "giá dầu",
)


def _has_non_analytic_override(raw_query: str, has_metrics: bool) -> bool:
    """Check if the query matches non-analytic intents that must fail closed."""
    if not raw_query:
        return False
    from .query_understanding import normalize_text, strip_accents

    norm = normalize_text(raw_query)
    norm_no_accents = strip_accents(norm)

    # 1. Creative writing: sáng tác, thơ, truyện, bài hát, viết văn, tiểu thuyết
    for cue in NON_ANALYTIC_CREATIVE_CUES:
        if cue in norm or strip_accents(cue) in norm_no_accents:
            return True
    if re.search(r"\b(?:thơ|tho|truyện|truyen)\b", norm_no_accents):
        return True

    # 2. Translation: dịch (excluding 'giao dịch'), tiếng anh, translate
    for cue in NON_ANALYTIC_TRANSLATION_CUES:
        if cue in norm or strip_accents(cue) in norm_no_accents:
            return True
    if re.search(r"(?<!giao\s)(?<!biến\s)(?<!dịch\s)\b(?:dịch|dich)\b", norm_no_accents):
        return True

    # 3. Coding: viết code, code python, lập trình, viết hàm, script
    for cue in NON_ANALYTIC_CODING_CUES:
        if cue in norm or strip_accents(cue) in norm_no_accents:
            return True

    # 4. Forecasting/prediction outside the catalog (active only when no catalog metric is present)
    if not has_metrics:
        for cue in NON_ANALYTIC_FORECAST_CUES:
            if cue in norm or strip_accents(cue) in norm_no_accents:
                return True

    return False


def validate_scope(
    resolved: ResolvedQuery,
    catalog: DatasetCapabilityCatalog,
    raw_query: str | None = None,
) -> None:
    """Validate that the query falls within the banking financial analysis domain.

    A query is in-scope if all non-analytic overrides pass AND at least one holds:
    1. It mentions at least one recognized banking entity or unrecognized potential ticker token.
    2. It specifies at least one explicit financial metric or domain topic.
    3. It targets supported or domain-level macroeconomic scope.
    4. It contains a banking-sector scope term AND an analytic-intent cue (allowing sector-level
       ranking/overview questions without explicit metrics to proceed to default planning).

    Queries matching non-analytic overrides (creative writing, translation, programming,
    non-catalog forecasting) fail closed immediately even if banking terms are present.
    """
    query_text = raw_query if raw_query is not None else getattr(resolved, "raw_query", "")

    has_entities = bool(resolved.entities) or bool(resolved.unknown_entity_tokens)
    has_metrics = bool(resolved.explicit_metrics) or bool(resolved.topic_metrics)
    has_macro = "macro" in resolved.flags

    from .messages_vi import get_error_message

    # Check non-analytic overrides first (overrides win over cues)
    if query_text and _has_non_analytic_override(query_text, has_metrics):
        raise AnalysisBlocked(
            "out_of_scope",
            get_error_message("out_of_scope", catalog),
        )

    # Condition 1: Entity, Metric, or Macro presence
    if has_entities or has_metrics or has_macro:
        return

    # Condition 2: Sector-level banking scope term + analytic-intent cue
    if query_text:
        from .query_understanding import normalize_text, strip_accents

        norm = normalize_text(query_text)
        norm_no_accents = strip_accents(norm)

        has_banking_term = any(
            term in norm or strip_accents(term) in norm_no_accents
            for term in BANKING_SECTOR_TERMS
        )
        has_analytic_cue = any(
            cue in norm or strip_accents(cue) in norm_no_accents
            for cue in ANALYTIC_INTENT_CUES
        )
        if has_banking_term and has_analytic_cue:
            return

    raise AnalysisBlocked(
        "out_of_scope",
        get_error_message("out_of_scope", catalog),
    )


def rules_plan(
    resolved: ResolvedQuery,
    catalog: DatasetCapabilityCatalog,
    raw_query: str | None = None,
) -> PlanSpec:
    """Generate a deterministic plan based on the resolved query and domain rules."""
    validate_scope(resolved, catalog, raw_query=raw_query)

    # 1. Unknown entity tokens
    if resolved.unknown_entity_tokens:
        labels = ", ".join(resolved.unknown_entity_tokens)
        raise AnalysisBlocked(
            "unsupported_entity",
            f"Entity {labels} is not present in the accepted snapshot.",
        )

    catalog_metrics = [
        m for m in catalog.metrics if not _is_lineage_only_metric(m.metric_id)
    ]
    catalog_metric_ids = tuple(m.metric_id for m in catalog_metrics)
    if not catalog_metric_ids:
        raise AnalysisBlocked("company_metrics_unavailable", "Catalog declares no runnable metrics.")

    # 2. Select Question Type
    flags = resolved.flags
    num_entities = len(resolved.entities)

    if num_entities == 0 and "macro" in flags and not resolved.explicit_metrics and not resolved.topic_metrics:
        if not any(m.analytical_level.value == "macro" for m in catalog.metrics):
            raise AnalysisBlocked(
                "unsupported_macro_scope",
                "Chưa có dữ liệu vĩ mô đã kiểm định trong hệ thống.",
            )

    if "lookup" in flags and num_entities >= 1:
        question_type = "lookup"
    elif "superlative" in flags and num_entities <= 1:
        question_type = "ranking"
    elif num_entities >= 2:
        question_type = "head_to_head"
    elif "trend" in flags and num_entities == 1:
        question_type = "trend"
    elif num_entities == 1:
        question_type = "company_profile"
    elif num_entities == 0:
        if "relationship" in flags and len(resolved.explicit_metrics) == 2:
            # relationship is disabled -> convert to ranking of metric_x with context [metric_y]
            question_type = "ranking"
        else:
            question_type = "ranking"
    else:
        question_type = "ranking"

    # 3. Select Metrics
    if resolved.explicit_metrics:
        metrics = resolved.explicit_metrics
    elif resolved.topic_metrics:
        metrics = resolved.topic_metrics
    else:
        if question_type == "ranking":
            metrics = (catalog_metric_ids[0],)
        elif question_type == "lookup":
            raise AnalysisBlocked(
                "metric_required",
                "Yêu cầu cần nêu rõ ít nhất một chỉ tiêu tài chính.",
            )
        else:
            metrics = catalog_metric_ids

    # 4. Select Periods
    anchor = resolved.anchor_period
    if question_type == "trend":
        trend_periods = (
            resolved.explicit_periods
            if len(resolved.explicit_periods) >= 2
            else resolved.context_periods
        )
        periods = trend_periods
    elif question_type in ("lookup", "ranking", "head_to_head"):
        periods = (anchor,)
    elif question_type == "company_profile":
        periods = resolved.context_periods
    else:
        periods = (anchor,)

    # 5. Build Tools
    tools: list[ToolCallSpec] = []
    focus_entity: str | None = None
    entities = resolved.entities

    if question_type == "lookup":
        focus_entity = entities[0] if entities else None
        tools.append(
            ToolCallSpec(
                tool="lookup",
                params={
                    "entities": list(entities[:3]),
                    "metrics": list(metrics[:4]),
                    "period": anchor,
                },
            )
        )
    elif question_type == "company_profile":
        target = entities[0]
        focus_entity = target
        tools.append(
            ToolCallSpec(
                tool="peer_position",
                params={
                    "entity": target,
                    "metrics": list(metrics[:4]),
                    "period": anchor,
                },
            )
        )
        tools.append(
            ToolCallSpec(
                tool="trend",
                params={
                    "entity": target,
                    "metrics": list(metrics[:4]),
                    "periods": list(resolved.context_periods),
                },
            )
        )
        if "bank.roe" in metrics and "bank.roa" in metrics:
            tools.append(
                ToolCallSpec(
                    tool="decomposition",
                    params={
                        "entities": [target],
                        "period": anchor,
                        "formula": "derived.roe_over_roa",
                    },
                )
            )
    elif question_type == "ranking":
        primary_metric = metrics[0]
        params: dict[str, Any] = {"metric": primary_metric, "period": anchor}
        if entities:
            focus_entity = entities[0]
            params["highlight_entity"] = focus_entity
        else:
            focus_entity = None
            primary_pres = get_metric_presentation(primary_metric)
            ctx_metrics: list[str] = []
            seen_groups = {primary_pres.group}
            for m_id in catalog_metric_ids:
                if m_id == primary_metric:
                    continue
                pres = get_metric_presentation(m_id)
                if pres.group not in seen_groups:
                    seen_groups.add(pres.group)
                    ctx_metrics.append(m_id)
                    if len(ctx_metrics) == 2:
                        break
            if ctx_metrics:
                params["context_metrics"] = ctx_metrics
        tools.append(ToolCallSpec(tool="ranking", params=params))
    elif question_type == "trend":
        target = entities[0]
        focus_entity = target
        tools.append(
            ToolCallSpec(
                tool="trend",
                params={
                    "entity": target,
                    "metrics": list(metrics[:4]),
                    "periods": list(periods),
                },
            )
        )
        tools.append(
            ToolCallSpec(
                tool="peer_position",
                params={
                    "entity": target,
                    "metrics": list(metrics[:4]),
                    "period": anchor,
                },
            )
        )
    elif question_type == "head_to_head":
        focus_entity = None
        h2h_entities = list(entities[:3])
        tools.append(
            ToolCallSpec(
                tool="head_to_head",
                params={
                    "entities": h2h_entities,
                    "metrics": list(metrics[:4]),
                    "period": anchor,
                },
            )
        )
        if "bank.roe" in metrics and "bank.roa" in metrics:
            tools.append(
                ToolCallSpec(
                    tool="decomposition",
                    params={
                        "entities": h2h_entities,
                        "period": anchor,
                        "formula": "derived.roe_over_roa",
                    },
                )
            )

    limitations: list[str] = []
    # 6. Macro flag
    if "macro" in flags and entities:
        limitations.append("Chưa có dữ liệu vĩ mô đã kiểm định; bỏ qua phân tích vĩ mô.")

    # 7. Why flag
    if "why" in flags:
        limitations.append(
            "Dữ liệu hiện có không đủ để kết luận nguyên nhân; báo cáo chỉ mô tả và so sánh."
        )
        if "bank.roe" in metrics:
            has_decomp = any(t.tool == "decomposition" for t in tools)
            if not has_decomp and "bank.roa" in catalog_metric_ids:
                d_entities = [entities[0]] if entities else []
                tools.append(
                    ToolCallSpec(
                        tool="decomposition",
                        params={
                            "entities": d_entities,
                            "period": anchor,
                            "formula": "derived.roe_over_roa",
                        },
                    )
                )

    rationale = (
        f"Kế hoạch phân tích dạng {question_type} cho "
        f"{focus_entity or (', '.join(entities) if entities else 'các ngân hàng')} "
        f"với {len(tools)} công cụ."
    )

    return PlanSpec(
        question_type=question_type,
        focus_entity=focus_entity,
        entities=entities,
        metrics=metrics,
        anchor_period=anchor,
        periods=periods,
        tools=tuple(tools),
        rationale=rationale,
        limitations=tuple(limitations),
    )


def validate_plan(
    spec: PlanSpec, resolved: ResolvedQuery, catalog: DatasetCapabilityCatalog
) -> list[str]:
    """Validate a candidate plan (from model or rules) against rules and catalog bounds."""
    errors: list[str] = []

    # 1. Question type enabled
    if spec.question_type in DISABLED_QUESTION_TYPES:
        errors.append(f"Question type {spec.question_type} is currently disabled.")
    elif spec.question_type not in ENABLED_QUESTION_TYPES:
        errors.append(f"Unknown question type {spec.question_type}.")

    # 2. Entity count matches question type
    n_entities = len(spec.entities)
    if spec.question_type == "lookup" and not (1 <= n_entities <= 3):
        errors.append(f"Lookup requires 1-3 entities, got {n_entities}.")
    elif spec.question_type == "company_profile" and n_entities != 1:
        errors.append(f"Company profile requires exactly 1 entity, got {n_entities}.")
    elif spec.question_type == "ranking" and not (0 <= n_entities <= 1):
        errors.append(f"Ranking requires 0 or 1 entity, got {n_entities}.")
    elif spec.question_type == "trend" and n_entities != 1:
        errors.append(f"Trend requires exactly 1 entity, got {n_entities}.")
    elif spec.question_type == "head_to_head" and not (2 <= n_entities <= 3):
        errors.append(f"Head to head requires 2-3 entities, got {n_entities}.")

    # 3. Catalog IDs validation
    catalog_company_ids = {
        e.entity_id for e in catalog.entities if e.entity_type.value == "company"
    }
    for e in spec.entities:
        if e not in catalog_company_ids:
            errors.append(f"Entity {e} is not in catalog.")
    if spec.focus_entity and spec.focus_entity not in catalog_company_ids:
        errors.append(f"Focus entity {spec.focus_entity} is not in catalog.")

    catalog_metric_ids = {
        m.metric_id for m in catalog.metrics if not _is_lineage_only_metric(m.metric_id)
    }
    for m in spec.metrics:
        if m not in catalog_metric_ids:
            errors.append(f"Metric {m} is not in catalog.")

    catalog_period_ids = {p.period_id for p in catalog.periods}
    if spec.anchor_period not in catalog_period_ids:
        errors.append(f"Anchor period {spec.anchor_period} is not in catalog.")
    for p in spec.periods:
        if p not in catalog_period_ids:
            errors.append(f"Period {p} is not in catalog.")

    # 4. Do not alter or drop explicit items from resolved query
    if resolved.entities:
        if not set(resolved.entities).issubset(set(spec.entities)):
            errors.append("Spec dropped explicit entities resolved from query.")
        if spec.focus_entity and spec.focus_entity != resolved.entities[0]:
            errors.append("Spec altered the explicit focus entity.")
    if resolved.explicit_periods:
        all_spec_periods = set(spec.periods) | ({spec.anchor_period} if spec.anchor_period else set())
        if not set(resolved.explicit_periods).issubset(all_spec_periods):
            errors.append("Spec dropped explicit periods resolved from query.")
    if resolved.explicit_metrics:
        if not set(resolved.explicit_metrics).issubset(set(spec.metrics)):
            errors.append("Spec dropped explicit metrics resolved from query.")

    # 5. Tools validation
    if len(spec.tools) > 5:
        errors.append(f"Tool calls exceed maximum of 5: got {len(spec.tools)}.")

    has_trend_tool = False
    for tool_call in spec.tools:
        tool_name = tool_call.tool
        if tool_name not in TOOL_CATALOG:
            errors.append(f"Tool {tool_name} is not in tool catalog.")
            continue
        tool_def = TOOL_CATALOG[tool_name]
        if not tool_def.enabled:
            errors.append(f"Tool {tool_name} is disabled.")
        for req_param in tool_def.required_params:
            if req_param not in tool_call.params:
                errors.append(f"Tool {tool_name} missing required parameter '{req_param}'.")
        if tool_name == "trend":
            has_trend_tool = True
            trend_p = tool_call.params.get("periods", ())
            if len(trend_p) < 2:
                errors.append(f"Trend tool requires at least 2 periods, got {len(trend_p)}.")

    if (spec.question_type == "trend" or has_trend_tool) and len(spec.periods) < 2:
        errors.append(f"Trend question type requires at least 2 periods, got {len(spec.periods)}.")

    # 6. The plan must carry the tool its question type is answered with; otherwise a
    #    proposed plan can label an overview as a profile yet only run a value lookup,
    #    leaving the report without peer position or signals.
    tool_names = {t.tool for t in spec.tools}
    required_tool = {
        "lookup": "lookup",
        "company_profile": "peer_position",
        "ranking": "ranking",
        "trend": "trend",
        "head_to_head": "head_to_head",
    }.get(spec.question_type)
    if required_tool and required_tool not in tool_names:
        errors.append(f"Question type {spec.question_type} requires the {required_tool} tool.")
    # A lookup answers a named metric or an explicit "how much" question; an overview
    # question ("Tổng quan MBB…") stays a profile, as the deterministic rules classify it.
    if spec.question_type == "lookup" and not (resolved.explicit_metrics or "lookup" in resolved.flags):
        errors.append("Lookup requires a metric named in the question.")

    return errors


_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question_type": {"type": "string"},
        "focus_entity": {"type": ["string", "null"]},
        "entities": {"type": "array", "items": {"type": "string"}},
        "metrics": {"type": "array", "items": {"type": "string"}},
        "anchor_period": {"type": "string"},
        "periods": {"type": "array", "items": {"type": "string"}},
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "params": {
                        "type": "object",
                        "properties": {
                            "entity": {"type": ["string", "null"]},
                            "entities": {"type": ["array", "null"], "items": {"type": "string"}},
                            "metric": {"type": ["string", "null"]},
                            "metrics": {"type": ["array", "null"], "items": {"type": "string"}},
                            "period": {"type": ["string", "null"]},
                            "periods": {"type": ["array", "null"], "items": {"type": "string"}},
                            "highlight_entity": {"type": ["string", "null"]},
                            "context_metrics": {"type": ["array", "null"], "items": {"type": "string"}},
                            "formula": {"type": ["string", "null"]},
                            "metric_x": {"type": ["string", "null"]},
                            "metric_y": {"type": ["string", "null"]},
                        },
                        "required": [
                            "entity",
                            "entities",
                            "metric",
                            "metrics",
                            "period",
                            "periods",
                            "highlight_entity",
                            "context_metrics",
                            "formula",
                            "metric_x",
                            "metric_y",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": ["tool", "params"],
                "additionalProperties": False,
            },
        },
        "rationale": {"type": "string"},
    },
    "required": [
        "question_type",
        "focus_entity",
        "entities",
        "metrics",
        "anchor_period",
        "periods",
        "tools",
        "rationale",
    ],
    "additionalProperties": False,
}


def model_plan(
    question: str,
    resolved: ResolvedQuery,
    catalog: DatasetCapabilityCatalog,
    client: Any = None,
    model: str = "deepseek-v4-pro-0813",
) -> PlanSpec | None:
    """Call language model once to propose a plan, returning None if client is unavailable or errors."""
    if client is None:
        return None

    from .analysis_writer import _clean_json_text

    # Construct concise payload
    catalog_companies = [
        {"id": e.entity_id, "name": e.display_name}
        for e in catalog.entities
        if e.entity_type.value == "company"
    ]
    catalog_metrics = [
        {"id": m.metric_id, "label": get_metric_presentation(m.metric_id).label}
        for m in catalog.metrics
        if not _is_lineage_only_metric(m.metric_id)
    ]
    catalog_periods = [p.period_id for p in catalog.periods]

    payload = {
        "question": question,
        "da_nhan_dien": {
            "entities": list(resolved.entities),
            "explicit_periods": list(resolved.explicit_periods),
            "anchor_period": resolved.anchor_period,
            "explicit_metrics": list(resolved.explicit_metrics),
            "flags": sorted(list(resolved.flags)),
        },
        "catalog": {
            "entities": catalog_companies,
            "metrics": catalog_metrics,
            "periods": catalog_periods,
        },
        "enabled_question_types": list(ENABLED_QUESTION_TYPES),
        "tools_catalog": [
            {
                "tool": t.name,
                "agent": t.agent,
                "required_params": list(t.required_params),
                "optional_params": list(t.optional_params),
            }
            for t in TOOL_CATALOG.values()
            if t.enabled
        ],
    }

    from .settings import get_settings

    try:
        response = client.responses.create(
            model=model,
            instructions=_MODEL_PLAN_PROMPT,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            text={"format": {"type": "json_schema", "name": "analysis_plan", "strict": True, "schema": _PLAN_SCHEMA}},
            max_output_tokens=get_settings().analysis_writer_max_output_tokens,
            store=False,
        )
        output_text = getattr(response, "output_text", None)
        if output_text is None:
            choices = getattr(response, "choices", None)
            if choices and hasattr(choices[0], "message"):
                output_text = choices[0].message.content
        if not isinstance(output_text, str) or not output_text.strip():
            return None

        clean_text = _clean_json_text(output_text)
        data = json.loads(clean_text)
        if not isinstance(data, dict):
            return None

        tool_specs = []
        for item in data.get("tools", []):
            if not isinstance(item, dict):
                continue
            raw_params = item.get("params", {})
            if isinstance(raw_params, dict):
                clean_params = {k: v for k, v in raw_params.items() if v is not None}
            else:
                clean_params = {}
            tool_specs.append(ToolCallSpec(tool=item.get("tool", ""), params=clean_params))

        anchor_val = data.get("anchor_period") or resolved.anchor_period
        periods_val = list(data.get("periods", []))
        if not periods_val and anchor_val:
            periods_val = [anchor_val]

        return PlanSpec(
            question_type=data.get("question_type", ""),
            focus_entity=data.get("focus_entity"),
            entities=tuple(data.get("entities", ())),
            metrics=tuple(data.get("metrics", ())),
            anchor_period=anchor_val,
            periods=tuple(periods_val),
            tools=tuple(tool_specs),
            rationale=data.get("rationale", ""),
        )
    except Exception:
        return None


def plan_question(
    question: str,
    catalog: DatasetCapabilityCatalog,
    settings: Any = None,
    client: Any = None,
) -> tuple[PlanSpec, str, list[str], ResolvedQuery]:
    """Resolve and plan an analytical question with model proposal and deterministic rules fallback."""
    from .query_understanding import resolve_query

    resolved = resolve_query(question, catalog)
    validate_scope(resolved, catalog, raw_query=question)
    planner_mode = getattr(settings, "planner_mode", "model_with_fallback")

    fallback_reasons: list[str] = []
    if planner_mode == "model_with_fallback":
        has_api_key = bool(
            getattr(settings, "openai_api_key", None)
            and getattr(settings, "openai_api_key", "").strip()
        )
        if client is None and not has_api_key:
            fallback_reasons = ["model_unconfigured"]
        else:
            model_name = getattr(settings, "openai_model", "deepseek-v4-pro-0813")
            proposed = model_plan(question, resolved, catalog, client=client, model=model_name)
            if proposed is not None:
                if not proposed.periods and proposed.anchor_period:
                    proposed = PlanSpec(
                        question_type=proposed.question_type,
                        focus_entity=proposed.focus_entity,
                        entities=proposed.entities,
                        metrics=proposed.metrics,
                        anchor_period=proposed.anchor_period,
                        periods=(proposed.anchor_period,),
                        tools=proposed.tools,
                        rationale=proposed.rationale,
                        limitations=proposed.limitations,
                    )
                errors = validate_plan(proposed, resolved, catalog)
                if not errors:
                    return proposed, "model", [], resolved
                fallback_reasons = errors
            else:
                fallback_reasons = ["model_error"]

    rules_result = rules_plan(resolved, catalog, raw_query=question)
    return rules_result, "rules", fallback_reasons, resolved


def build_analysis_plan(
    spec: PlanSpec,
    catalog: DatasetCapabilityCatalog,
    dataset_ref: DatasetRef,
    query_text: str = "",
    peer_tickers: tuple[str, ...] | list[str] = (),
) -> tuple[AnalysisPlan, str | None, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Build a frozen AnalysisPlan conforming to Stage-1 claim contracts."""
    anchor = spec.anchor_period

    # Identify all entities and metrics across tools
    company_entities = {
        e.entity_id for e in catalog.entities if e.entity_type.value == "company"
    }

    used_entities: set[str] = set()
    used_metrics: set[str] = set(spec.metrics)
    needs_peer_benchmark = False

    for tool_call in spec.tools:
        t = tool_call.tool
        p = tool_call.params
        if t == "ranking":
            used_entities.update(company_entities)
            used_metrics.add(p.get("metric", ""))
            for cm in p.get("context_metrics", ()):
                used_metrics.add(cm)
            needs_peer_benchmark = True
        elif t in ("peer_position", "trend"):
            used_entities.add(p.get("entity", ""))
            used_metrics.update(p.get("metrics", ()))
            if t == "peer_position":
                needs_peer_benchmark = True
        elif t in ("lookup", "head_to_head", "decomposition"):
            used_entities.update(p.get("entities", ()))
            used_metrics.update(p.get("metrics", ()))
            if t == "decomposition":
                formula_key = p.get("formula", "")
                if formula_key in DERIVED:
                    df = DERIVED[formula_key]
                    used_metrics.add(df.numerator)
                    used_metrics.add(df.denominator)

    used_entities.discard("")
    used_metrics.discard("")

    company_metric_ids = tuple(
        m.metric_id for m in catalog.metrics if m.metric_id in used_metrics
    )

    # Resolve peer universe
    peer_universe_id: str | None = None
    peer_ids: tuple[str, ...] = ()
    _query_lower = query_text.lower()
    is_comparison_active = (
        bool(peer_tickers)
        or spec.question_type in ("ranking", "head_to_head")
        or (
            spec.question_type == "company_profile"
            and any(
                k in _query_lower
                for k in (
                    "so sánh", "so sanh", "so với", "so voi",
                    "cùng nhóm", "cung nhom", "peer", "peers", "compare", "comparison",
                )
            )
        )
    )
    if is_comparison_active and (needs_peer_benchmark or spec.question_type in ("ranking", "head_to_head")):
        if catalog.peer_universes:
            universe = catalog.peer_universes[0]
            peer_universe_id = universe.peer_universe_id
            if spec.question_type == "head_to_head":
                peer_ids = tuple(e for e in spec.entities if e != spec.focus_entity)
            elif peer_tickers:
                peer_ids = tuple(t.strip().upper() for t in peer_tickers if t.strip() and t.strip().upper() != spec.focus_entity)
            else:
                peer_ids = tuple(e for e in universe.entity_ids if e != spec.focus_entity) if spec.focus_entity else tuple(universe.entity_ids)

    entities_list: list[str] = []
    if spec.focus_entity:
        entities_list.append(spec.focus_entity)
    for e in spec.entities:
        if e not in entities_list:
            entities_list.append(e)
    for e in used_entities:
        if e not in entities_list:
            entities_list.append(e)
    for e in peer_ids:
        if e not in entities_list:
            entities_list.append(e)
    if peer_universe_id and peer_universe_id not in entities_list:
        entities_list.append(peer_universe_id)

    # Build requirements: each (entity, metric, anchor) -> FACTUAL_OBSERVATION
    requirements: list[AnalysisRequirement] = []
    seen_req_ids: set[str] = set()

    for entity in used_entities:
        if entity not in company_entities:
            continue
        for metric_id in company_metric_ids:
            req_id = f"company:{entity}:{anchor}:{metric_id}"
            if req_id not in seen_req_ids:
                seen_req_ids.add(req_id)
                # Assign agent: SECTOR if ranking or head_to_head, else COMPANY
                req_agent = (
                    AnalysisAgent.SECTOR
                    if spec.question_type in ("ranking", "head_to_head")
                    else AnalysisAgent.COMPANY
                )
                requirements.append(
                    AnalysisRequirement(
                        requirement_id=req_id,
                        requirement_type=RequirementType.FACTUAL_OBSERVATION,
                        description=f"Report accepted {metric_id} observation for {entity} at {anchor}.",
                        required_agents=(req_agent,),
                        entities=(entity,),
                        periods=(anchor,),
                        metric_ids=(metric_id,),
                        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                        fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                        missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
                    )
                )

    if peer_universe_id and (needs_peer_benchmark or spec.question_type == "ranking"):
        for peer in peer_ids:
            for metric_id in company_metric_ids:
                peer_in_id = f"peer-input:{peer}:{anchor}:{metric_id}"
                if peer_in_id not in seen_req_ids:
                    seen_req_ids.add(peer_in_id)
                    requirements.append(
                        AnalysisRequirement(
                            requirement_id=peer_in_id,
                            requirement_type=RequirementType.FACTUAL_OBSERVATION,
                            description=f"Verify the accepted {metric_id} peer input for {peer} at {anchor}.",
                            required_agents=(AnalysisAgent.SECTOR,),
                            entities=(peer,),
                            periods=(anchor,),
                            metric_ids=(metric_id,),
                            inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                            fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                            missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
                        )
                    )
        for metric_id in company_metric_ids:
            median_req_id = f"peer-median:{peer_universe_id}:{anchor}:{metric_id}"
            if median_req_id not in seen_req_ids:
                seen_req_ids.add(median_req_id)
                requirements.append(
                    AnalysisRequirement(
                        requirement_id=median_req_id,
                        requirement_type=RequirementType.COMPARISON,
                        description=f"Report provider-derived peer median for {metric_id} at {anchor}.",
                        required_agents=(AnalysisAgent.SECTOR,),
                        entities=(peer_universe_id,),
                        periods=(anchor,),
                        metric_ids=(metric_id,),
                        inference_ceiling=InferenceCeiling.COMPARISON_ALLOWED,
                        fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                        missing_data_policy=MissingDataPolicy.REJECT_MISSING,
                    )
                )

    # Applicable links
    links: list[ApplicableLink] = []
    if peer_universe_id and spec.focus_entity:
        for idx, metric_id in enumerate(company_metric_ids, start=1):
            links.append(
                ApplicableLink(
                    link_id=f"peer-link:{idx}:{metric_id}",
                    link_type=ApplicableLinkType.COMPANY_TO_PEER_BENCHMARK,
                    source_level=LinkLevel.COMPANY,
                    target_level=LinkLevel.PEER_BENCHMARK,
                    source_entities=(spec.focus_entity,),
                    target_entities=(peer_universe_id,),
                    source_periods=(anchor,),
                    target_periods=(anchor,),
                    source_metric_ids=(metric_id,),
                    target_metric_ids=(metric_id,),
                    description=f"Compare {spec.focus_entity} {metric_id} with accepted {peer_universe_id} median.",
                )
            )

    normalized_q = query_text.strip() or f"{spec.question_type} analysis"
    query_id = "query-" + hashlib.sha256(
        f"{dataset_ref.dataset_snapshot_id}\0{normalized_q}\0{anchor}".encode("utf-8")
    ).hexdigest()[:16]

    plan = AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        query_id=query_id,
        normalized_question=normalized_q,
        scope=AnalysisScope(
            entities=tuple(entities_list),
            periods=(anchor,),
            company_metric_ids=company_metric_ids,
            macro_indicator_ids=(),
            comparison_universe=(peer_universe_id,) if peer_universe_id else (),
        ),
        requirements=tuple(requirements),
        applicable_links=tuple(links),
        requested_outputs=(
            "structured_facts",
            "comparison" if peer_universe_id else "limitations",
            "evidence_trace",
        ),
        causal_claim_policy=(
            CausalClaimPolicy.ASSOCIATION_ONLY if links else CausalClaimPolicy.NO_CAUSAL_INFERENCE
        ),
    )

    target_val = spec.focus_entity or (spec.entities[0] if spec.entities else None)
    return plan, target_val, (anchor,), company_metric_ids, peer_ids, ()
