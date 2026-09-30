"""Modular report specification and schema validation.

Core pure mathematical/validation module:
- No sqlite3, openai, or langgraph imports.
- No fixed issuer literals.
- Enforces chart-dataset compatibility and block budget limits.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence
from pydantic import BaseModel, ConfigDict, Field


CHART_COMPATIBILITY: dict[str, set[str]] = {
    "kpi_strip": {"kpi"},
    "ranked_bar": {"ranked_list"},
    "line_trend": {"series"},
    "small_multiples": {"series_multi"},
    "scatter": {"paired"},
    "rank_heatmap": {"peer_table"},
    "grouped_bar": {"comparison_table", "peer_table"},
    "comparison_table": {"comparison_table", "peer_table"},
}

MAX_FIGURES = 4
MAX_KEY_POINTS = 5
MAX_SECTIONS = 3
MAX_CALLOUTS = 3
MAX_TOTAL_BLOCKS = 12


def _check_dataset_chart_fit(chart: str, dataset: Any) -> bool:
    """Verify if a chart type is mathematically and dimensionally compatible with a dataset."""
    shape = getattr(dataset, "shape", None) or (dataset.get("shape") if isinstance(dataset, dict) else "")
    allowed_shapes = CHART_COMPATIBILITY.get(chart, set())
    if shape not in allowed_shapes:
        return False

    rows = getattr(dataset, "rows", None) or (dataset.get("rows") if isinstance(dataset, dict) else [])
    valid_rows = [
        r for r in rows
        if (getattr(r, "status", None) or (r.get("status") if isinstance(r, dict) else "")) == "valid"
    ]

    if chart == "kpi_strip":
        return 1 <= len(rows) <= 6
    if chart == "ranked_bar":
        return len(valid_rows) >= 3
    if chart == "line_trend":
        periods = getattr(dataset, "periods", None) or (dataset.get("periods") if isinstance(dataset, dict) else [])
        return len(periods) >= 2
    if chart == "small_multiples":
        metrics = getattr(dataset, "metric_ids", None) or (dataset.get("metric_ids") if isinstance(dataset, dict) else [])
        periods = getattr(dataset, "periods", None) or (dataset.get("periods") if isinstance(dataset, dict) else [])
        return len(metrics) >= 2 and len(periods) >= 2
    if chart == "scatter":
        # Check valid points across both metrics
        entities_with_both = set()
        by_ent: dict[str, list[str]] = {}
        for r in valid_rows:
            ent = getattr(r, "entity_id", None) or (r.get("entity_id") if isinstance(r, dict) else "")
            met = getattr(r, "metric_id", None) or (r.get("metric_id") if isinstance(r, dict) else "")
            if ent and met:
                by_ent.setdefault(ent, []).append(met)
        for ent, mets in by_ent.items():
            if len(set(mets)) >= 2:
                entities_with_both.add(ent)
        return len(entities_with_both) >= 3
    if chart == "rank_heatmap":
        entities = {getattr(r, "entity_id", None) or (r.get("entity_id") if isinstance(r, dict) else "") for r in rows}
        metrics = getattr(dataset, "metric_ids", None) or (dataset.get("metric_ids") if isinstance(dataset, dict) else [])
        return len(entities) >= 3 and len(metrics) >= 2
    if chart in ("grouped_bar", "comparison_table"):
        entities = {getattr(r, "entity_id", None) or (r.get("entity_id") if isinstance(r, dict) else "") for r in rows}
        return 2 <= len(entities) <= 5

    return True


def validate_report_spec(
    spec: dict[str, Any],
    datasets: Mapping[str, Any],
    facts: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Validate, sanitize, and budget-limit a ReportSpec dictionary.

    Returns:
        (sanitized_spec_dict, list_of_dropped_blocks_info)
    """
    if not isinstance(datasets, Mapping):
        datasets = {getattr(d, "dataset_id", str(d)): d for d in datasets}
    if not isinstance(facts, Mapping):
        facts = {getattr(f, "fact_id", str(f)): f for f in facts}

    kind = spec.get("kind")
    if kind not in ("answer_card", "note"):
        kind = "note"

    raw_blocks = spec.get("blocks") or []
    clean_blocks: list[dict[str, Any]] = []
    dropped: list[dict[str, str]] = []

    figure_count = 0
    section_count = 0
    callout_count = 0

    for b in raw_blocks:
        if not isinstance(b, dict):
            dropped.append({"type": "unknown", "reason": "Khối không đúng cấu trúc dictionary."})
            continue

        b_type = b.get("type")

        # 1. Answer Block
        if b_type == "answer":
            if kind != "answer_card":
                dropped.append({"type": "answer", "reason": "Khối answer chỉ được phép ở kind answer_card."})
                continue
            v_fid = b.get("value_fact_id")
            if not v_fid or v_fid not in facts:
                dropped.append({"type": "answer", "reason": f"value_fact_id '{v_fid}' không tồn tại."})
                continue
            clean_blocks.append(b)

        # 2. Headline Block
        elif b_type == "headline":
            if kind != "note":
                dropped.append({"type": "headline", "reason": "Khối headline chỉ dùng cho kind note."})
                continue
            clean_blocks.append(b)

        # 3. Key Points Block
        elif b_type == "key_points":
            items = b.get("items") or []
            if not items:
                dropped.append({"type": "key_points", "reason": "Khối key_points không có mục con nào."})
                continue
            # Limit key point items <= MAX_KEY_POINTS
            clean_items = items[:MAX_KEY_POINTS]
            if len(items) > MAX_KEY_POINTS:
                dropped.append({
                    "type": "key_points_items",
                    "reason": f"Cắt bớt các ý kiến phụ vượt quá giới hạn {MAX_KEY_POINTS} ý.",
                })
            b_copy = dict(b)
            b_copy["items"] = clean_items
            clean_blocks.append(b_copy)

        # 4. Section Block
        elif b_type == "section":
            if section_count >= MAX_SECTIONS:
                dropped.append({"type": "section", "reason": f"Vượt quá ngân sách tối đa {MAX_SECTIONS} section."})
                continue
            section_count += 1
            clean_blocks.append(b)

        # 5. Callout Block
        elif b_type == "callout":
            if callout_count >= MAX_CALLOUTS:
                dropped.append({"type": "callout", "reason": f"Vượt quá ngân sách tối đa {MAX_CALLOUTS} callout."})
                continue
            callout_count += 1
            clean_blocks.append(b)

        # 6. Table Block
        elif b_type == "table":
            ds_id = b.get("dataset_id")
            if not ds_id or ds_id not in datasets:
                dropped.append({"type": "table", "reason": f"dataset_id '{ds_id}' không tồn tại."})
                continue
            clean_blocks.append(b)

        # 7. Figure Block
        elif b_type == "figure":
            if figure_count >= MAX_FIGURES:
                dropped.append({"type": "figure", "reason": f"Vượt quá ngân sách tối đa {MAX_FIGURES} hình minh họa."})
                continue

            ds_id = b.get("dataset_id")
            if not ds_id or ds_id not in datasets:
                dropped.append({"type": "figure", "reason": f"dataset_id '{ds_id}' không tồn tại trong danh mục."})
                continue

            dataset = datasets[ds_id]
            req_chart = b.get("chart", "")

            # Check compatibility
            is_fit = _check_dataset_chart_fit(req_chart, dataset)
            chosen_chart = req_chart
            if not is_fit:
                # Try fallback chart from dataset.allowed_charts
                allowed = getattr(dataset, "allowed_charts", None) or (dataset.get("allowed_charts") if isinstance(dataset, dict) else [])
                alt_fit = None
                for alt_c in allowed:
                    if _check_dataset_chart_fit(alt_c, dataset):
                        alt_fit = alt_c
                        break
                if alt_fit:
                    chosen_chart = alt_fit
                    dropped.append({
                        "type": "figure_chart_switch",
                        "reason": f"Đổi loại biểu đồ {req_chart} sang {alt_fit} do phù hợp hơn với cấu trúc dữ liệu.",
                    })
                else:
                    dropped.append({
                        "type": "figure",
                        "reason": f"Biểu đồ {req_chart} không tương thích với dữ liệu và không có biểu đồ thay thế.",
                    })
                    continue

            b_clean = dict(b)
            b_clean["chart"] = chosen_chart
            figure_count += 1
            b_clean["figure_no"] = figure_count
            clean_blocks.append(b_clean)

        else:
            dropped.append({"type": str(b_type), "reason": f"Loại khối '{b_type}' không được hỗ trợ."})

    # Total block budget limit <= MAX_TOTAL_BLOCKS
    if len(clean_blocks) > MAX_TOTAL_BLOCKS:
        dropped.append({
            "type": "block_budget_exceeded",
            "reason": f"Cắt bớt {len(clean_blocks) - MAX_TOTAL_BLOCKS} khối vượt quá giới hạn {MAX_TOTAL_BLOCKS} khối.",
        })
        clean_blocks = clean_blocks[:MAX_TOTAL_BLOCKS]

    # Re-number figures sequentially
    f_num = 1
    for cb in clean_blocks:
        if cb.get("type") == "figure":
            cb["figure_no"] = f_num
            f_num += 1

    # Validate structural requirements
    is_valid = True
    if kind == "answer_card":
        answers = [cb for cb in clean_blocks if cb.get("type") == "answer"]
        if len(answers) != 1:
            is_valid = False
            dropped.append({"type": "spec_structure", "reason": "Báo cáo answer_card phải có đúng 1 khối answer."})
    elif kind == "note":
        headlines = [cb for cb in clean_blocks if cb.get("type") == "headline"]
        content_blocks = [cb for cb in clean_blocks if cb.get("type") not in ("headline", "answer")]
        if len(headlines) != 1 or len(content_blocks) == 0:
            is_valid = False
            dropped.append({
                "type": "spec_structure",
                "reason": "Báo cáo note phải có đúng 1 khối headline và ít nhất 1 khối nội dung.",
            })

    result_spec = {
        "kind": kind,
        "note_label": spec.get("note_label"),
        "composition_source": spec.get("composition_source"),
        "blocks": clean_blocks,
        "is_valid": is_valid,
    }
    return result_spec, dropped
