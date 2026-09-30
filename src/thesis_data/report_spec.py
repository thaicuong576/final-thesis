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


def normalize_report_spec_dict(raw: dict[str, Any], question_type: str = "") -> dict[str, Any]:
    """Normalize model's flexible output into canonical ReportSpec-compatible dictionary.

    Accepts both canonical ReportSpec and historical/mismatched model variants:
    - Blocks with 'kind': 'answer_card' wrapping an 'answer' sub-object
    - Blocks with 'kind': 'note' wrapping 'headline', 'sentences', 'callouts'
    - Top-level legacy format with 'headline' / 'answer' at root
    """
    if not isinstance(raw, dict):
        return {"kind": "note", "note_label": None, "blocks": []}

    overall_kind = raw.get("kind")
    raw_blocks = raw.get("blocks")
    if not isinstance(raw_blocks, list):
        raw_blocks = []

    has_answer = False
    for b in raw_blocks:
        if isinstance(b, dict) and (b.get("kind") == "answer_card" or b.get("type") == "answer" or "answer" in b):
            has_answer = True
            break
    if "answer" in raw:
        has_answer = True

    if question_type:
        if question_type == "lookup":
            overall_kind = "answer_card"
        else:
            overall_kind = "note"
    elif raw.get("kind") in ("answer_card", "note"):
        overall_kind = raw["kind"]
    elif has_answer:
        overall_kind = "answer_card"
    else:
        overall_kind = "note"

    def _norm_sentence(s: Any) -> dict[str, Any] | None:
        if isinstance(s, str):
            s_str = s.strip()
            if s_str.startswith("sent-"):
                return {"sentence_id": s_str}
            return {"text": s_str, "fact_ids": []}
        if isinstance(s, dict):
            s_dict = dict(s)
            s_id = s_dict.get("sentence_id")
            text = s_dict.get("text")
            fids = s_dict.get("fact_ids")
            res: dict[str, Any] = {}
            if s_id is not None:
                res["sentence_id"] = str(s_id)
            if text is not None:
                res["text"] = str(text)
            if fids is not None:
                res["fact_ids"] = list(fids) if isinstance(fids, (list, tuple)) else []
            return res if res else None
        return None

    clean_blocks: list[dict[str, Any]] = []

    # Handle top-level legacy structure if raw_blocks is empty
    if not raw_blocks:
        if "answer" in raw:
            ans = raw["answer"]
            ans_text = ans.get("text", "") if isinstance(ans, dict) else str(ans)
            ans_fids = ans.get("fact_ids", []) if isinstance(ans, dict) else []
            val_fid = (ans.get("value_fact_id") if isinstance(ans, dict) else None) or (ans_fids[0] if ans_fids else "")
            clean_blocks.append({
                "type": "answer",
                "value_fact_id": val_fid,
                "sentences": [{"text": ans_text, "fact_ids": ans_fids}] if ans_text else [],
            })
        if "headline" in raw:
            hl = raw["headline"]
            hl_sent = _norm_sentence(hl) if isinstance(hl, dict) else ({"text": str(hl), "fact_ids": []} if hl else None)
            if hl_sent:
                clean_blocks.append({"type": "headline", "sentence": hl_sent})
        if "sentences" in raw and isinstance(raw["sentences"], list):
            s_list = [_norm_sentence(s) for s in raw["sentences"] if _norm_sentence(s)]
            if s_list:
                clean_blocks.append({"type": "section", "title": "Chi tiết phân tích", "sentences": s_list})

    # Process items in raw_blocks
    for item in raw_blocks:
        if not isinstance(item, dict):
            continue
        blk = dict(item)
        ikind = blk.get("kind")
        itype = blk.get("type")

        # Nested kind == "answer_card" or contains "answer" sub-object
        if ikind == "answer_card" or ("answer" in blk and itype != "answer"):
            ans = blk.get("answer") or {}
            if isinstance(ans, str):
                ans = {"text": ans, "fact_ids": []}
            ans_text = ans.get("text", "")
            ans_fids = ans.get("fact_ids", [])
            val_fid = ans.get("value_fact_id") or (ans_fids[0] if ans_fids else "")
            sentences = []
            if ans_text:
                sentences.append({"text": ans_text, "fact_ids": ans_fids})
            for s in ans.get("sentences", []):
                ns = _norm_sentence(s)
                if ns:
                    sentences.append(ns)
            for s in blk.get("sentences", []):
                ns = _norm_sentence(s)
                if ns:
                    sentences.append(ns)
            clean_blocks.append({
                "type": "answer",
                "value_fact_id": val_fid,
                "sentences": sentences,
            })
            chart = blk.get("chart")
            if isinstance(chart, dict):
                c_copy = dict(chart)
                c_copy.setdefault("type", "figure")
                clean_blocks.append(c_copy)
            continue

        # Nested kind == "note" or note-like block with headline/sentences
        if ikind == "note" or ("headline" in blk and itype != "headline"):
            hl = blk.get("headline")
            sec_sents = [_norm_sentence(s) for s in blk.get("sentences", []) if _norm_sentence(s)]
            if overall_kind == "note":
                if hl:
                    clean_blocks.append({
                        "type": "headline",
                        "sentence": _norm_sentence(hl) if isinstance(hl, dict) else {"text": str(hl), "fact_ids": []},
                    })
                if sec_sents:
                    clean_blocks.append({"type": "section", "title": "Chi tiết phân tích", "sentences": sec_sents})
            else:
                title_text = hl if isinstance(hl, str) else (hl.get("text") if isinstance(hl, dict) else "Chi tiết")
                clean_blocks.append({"type": "section", "title": str(title_text or "Chi tiết"), "sentences": sec_sents})

            for c in blk.get("callouts", []):
                if isinstance(c, dict):
                    c_copy = dict(c)
                    c_copy.setdefault("type", "callout")
                    clean_blocks.append(c_copy)

            chart = blk.get("chart")
            if isinstance(chart, dict):
                c_copy = dict(chart)
                c_copy.setdefault("type", "figure")
                clean_blocks.append(c_copy)
            continue

        # Canonical block types
        if itype in ("headline", "answer", "key_points", "section", "figure", "callout", "table"):
            if itype == "headline":
                if "sentence" in blk and isinstance(blk["sentence"], dict):
                    blk["sentence"] = _norm_sentence(blk["sentence"]) or blk["sentence"]
                elif "headline" in blk:
                    hl_val = blk.pop("headline")
                    blk["sentence"] = _norm_sentence(hl_val) if isinstance(hl_val, dict) else {"text": str(hl_val), "fact_ids": []}
            elif itype in ("answer", "section", "callout"):
                if "sentences" in blk and isinstance(blk["sentences"], list):
                    blk["sentences"] = [_norm_sentence(s) for s in blk["sentences"] if _norm_sentence(s)]
            elif itype == "key_points":
                if "items" in blk and isinstance(blk["items"], list):
                    for it in blk["items"]:
                        if isinstance(it, dict) and "sentences" in it:
                            it["sentences"] = [_norm_sentence(s) for s in it["sentences"] if _norm_sentence(s)]
            elif itype == "figure":
                if "takeaway" in blk and isinstance(blk["takeaway"], dict):
                    blk["takeaway"] = _norm_sentence(blk["takeaway"]) or blk["takeaway"]
            clean_blocks.append(blk)
            continue

        # Other block types that contain narrative text (takeaway, summary, paragraph, etc.)
        if "text" in blk or "sentences" in blk:
            s_list = []
            if "text" in blk:
                ns = _norm_sentence(blk)
                if ns:
                    s_list.append(ns)
            for s in blk.get("sentences", []):
                ns = _norm_sentence(s)
                if ns:
                    s_list.append(ns)
            if s_list:
                clean_blocks.append({
                    "type": "section",
                    "title": blk.get("title") or (str(itype).capitalize() if itype else "Chi tiết"),
                    "sentences": s_list,
                })
                continue

    # Enforce structural invariants for answer_card vs note
    if overall_kind == "answer_card":
        adjusted_blocks = []
        for b in clean_blocks:
            if b.get("type") == "headline":
                s_sent = b.get("sentence")
                adjusted_blocks.append({
                    "type": "section",
                    "title": "Chi tiết",
                    "sentences": [s_sent] if s_sent else [],
                })
            else:
                adjusted_blocks.append(b)
        clean_blocks = adjusted_blocks

        # Ensure exactly 1 answer block
        answers = [b for b in clean_blocks if b.get("type") == "answer"]
        if not answers:
            # Synthesize answer block from the first sentence available
            for idx, b in enumerate(clean_blocks):
                sents = b.get("sentences", [])
                if sents:
                    first_sent = sents[0]
                    val_fid = ""
                    if isinstance(first_sent, dict):
                        fids = first_sent.get("fact_ids", [])
                        if fids:
                            val_fid = fids[0]
                    ans_b = {
                        "type": "answer",
                        "value_fact_id": val_fid,
                        "sentences": [first_sent],
                    }
                    rem_sents = sents[1:]
                    if rem_sents:
                        b["sentences"] = rem_sents
                        clean_blocks.insert(idx, ans_b)
                    else:
                        clean_blocks[idx] = ans_b
                    break
        elif len(answers) > 1:
            kept = False
            adj = []
            for b in clean_blocks:
                if b.get("type") == "answer":
                    if not kept:
                        adj.append(b)
                        kept = True
                    else:
                        adj.append({
                            "type": "section",
                            "title": "Bổ sung",
                            "sentences": b.get("sentences", []),
                        })
                else:
                    adj.append(b)
            clean_blocks = adj

    elif overall_kind == "note":
        # Convert any answer blocks in note into section / headline
        adj = []
        for b in clean_blocks:
            if b.get("type") == "answer":
                sents = b.get("sentences", [])
                adj.append({
                    "type": "section",
                    "title": "Chi tiết phân tích",
                    "sentences": sents,
                })
            else:
                adj.append(b)
        clean_blocks = adj

        # Ensure exactly 1 headline block
        headlines = [b for b in clean_blocks if b.get("type") == "headline"]
        if not headlines:
            # Promote the first sentence of the first content block to headline
            for idx, b in enumerate(clean_blocks):
                sents = b.get("sentences", [])
                if sents:
                    first_s = sents[0]
                    hl_b = {"type": "headline", "sentence": first_s}
                    rem_s = sents[1:]
                    if rem_s:
                        b["sentences"] = rem_s
                        clean_blocks.insert(idx, hl_b)
                    else:
                        clean_blocks[idx] = hl_b
                    break
        elif len(headlines) > 1:
            kept = False
            adj = []
            for b in clean_blocks:
                if b.get("type") == "headline":
                    if not kept:
                        adj.append(b)
                        kept = True
                    else:
                        h_s = b.get("sentence")
                        adj.append({
                            "type": "section",
                            "title": "Tiêu điểm",
                            "sentences": [h_s] if h_s else [],
                        })
                else:
                    adj.append(b)
            clean_blocks = adj

        # Ensure at least 1 content block (section, key_points, figure, callout, table)
        content_blocks = [b for b in clean_blocks if b.get("type") not in ("headline", "answer")]
        if not content_blocks and clean_blocks:
            hl_s = clean_blocks[0].get("sentence")
            if hl_s:
                clean_blocks.append({
                    "type": "section",
                    "title": "Chi tiết phân tích",
                    "sentences": [hl_s],
                })

    return {
        "kind": overall_kind,
        "note_label": raw.get("note_label"),
        "blocks": clean_blocks,
    }

