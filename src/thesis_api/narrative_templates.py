"""Deterministic narrative templates and fallback report layouts.

Pure formatting and template generation module for application layer:
- Humanizes facts into Vietnamese analytical descriptions and values.
- Produces verifier-compliant fallback sentences.
- Assembles default ReportSpec structures for each question type.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from thesis_data.report_facts import CrossLevelCandidate, Fact, SignalResult
from .analysis_tools import ToolResult
from .metric_presentation import format_metric_display_name, get_metric_presentation
from .schemas import (
    AnswerBlockDTO,
    CalloutBlockDTO,
    FigureBlockDTO,
    HeadlineBlockDTO,
    KeyPointItemDTO,
    KeyPointsBlockDTO,
    ReportSpecDTO,
    SentenceDTO,
)


def period_vi(period: str) -> str:
    """Format canonical period string into standard Vietnamese."""
    if not period:
        return ""
    if "_to_" in period:
        p1, p2 = period.split("_to_")
        return f"từ {period_vi(p1)} đến {period_vi(p2)}"
    parts = period.split("_")
    if len(parts) == 2 and parts[1].startswith("Q"):
        q_num = parts[1][1:]
        return f"quý {q_num}/{parts[0]}"
    if period.startswith("FY"):
        return f"năm {period[2:]}"
    if period.isdigit() and len(period) == 4:
        return f"năm {period}"
    return period


def fmt(val: float | None, decimals: int = 1, show_sign: bool = False, unit: str = "") -> str:
    """Format float number with Vietnamese comma decimal separator."""
    if val is None:
        return ""
    rounded = round(float(val), decimals)
    formatted = f"{rounded:.{decimals}f}".replace(".", ",")
    sign = "+" if (show_sign and rounded > 0) else ""
    return f"{sign}{formatted}{unit}"


def display_fact(fact: Fact) -> str:
    """Format fact value into exact display string for models and reports."""
    if fact.value is None and fact.fact_type != "peer_rank":
        return ""
    f_type = fact.fact_type
    pres = get_metric_presentation(fact.metric_id)

    if f_type in ("value", "peer_median"):
        return fmt(fact.value, decimals=pres.decimals, show_sign=False, unit="%")
    if f_type == "peer_rank":
        r_val = fact.rank_better or fact.rank_desc or int(round(fact.value or 1))
        return f"hạng {r_val}/{fact.denominator}"
    if f_type == "spread":
        return fmt(abs(fact.value or 0.0), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
    if f_type in ("gap_to_median", "delta", "median_delta", "pairwise_gap"):
        return fmt(fact.value, decimals=pres.delta_decimals, show_sign=True, unit=" điểm %")
    if f_type == "ratio_to_median":
        return f"{fmt(fact.value, decimals=1, show_sign=False)} lần"
    if f_type == "derived_ratio":
        return f"{fmt(fact.value, decimals=2, show_sign=False)} lần"
    if f_type == "lead_count":
        return f"{int(round(fact.value or 0))}/{fact.denominator} chỉ tiêu"
    return str(fact.value)


def describe_fact(fact: Fact) -> str:
    """Produce human-readable metadata description of a fact."""
    pres = get_metric_presentation(fact.metric_id)
    p_vi = period_vi(fact.period)
    ent = fact.entity_id or fact.universe_id or ""
    f_type = fact.fact_type
    m_name_lower = format_metric_display_name(fact.metric_id, lowercase=True)
    m_name_norm = format_metric_display_name(fact.metric_id, lowercase=False)
    denom_str = f"nhóm {fact.denominator} ngân hàng" if fact.denominator else "toàn nhóm"

    if f_type == "value":
        return f"{m_name_norm} của {ent} trong {p_vi}" if ent else f"{m_name_norm} trong {p_vi}"
    if f_type == "peer_median":
        return f"Trung vị {m_name_lower} {denom_str} trong {p_vi}"
    if f_type == "peer_rank":
        r_val = fact.rank_better or fact.rank_desc or int(round(fact.value or 1))
        return f"Xếp hạng {r_val}/{fact.denominator} về {m_name_lower} của {ent} trong {p_vi}"
    if f_type == "gap_to_median":
        return f"Chênh lệch {m_name_lower} của {ent} so với trung vị nhóm trong {p_vi}"
    if f_type == "delta":
        from_p = period_vi(fact.from_period or "")
        if from_p:
            return f"Mức thay đổi {m_name_lower} của {ent} từ {from_p} đến {p_vi}"
        return f"Mức thay đổi {m_name_lower} của {ent} trong {p_vi}"
    if f_type == "median_delta":
        from_p = period_vi(fact.from_period or "")
        if from_p:
            return f"Mức thay đổi trung vị {m_name_lower} từ {from_p} đến {p_vi}"
        return f"Mức thay đổi trung vị {m_name_lower} trong {p_vi}"
    if f_type == "pairwise_gap":
        return f"Chênh lệch {m_name_lower} giữa {ent} và {fact.other_entity_id} trong {p_vi}"
    if f_type == "spread":
        return f"Chênh lệch cao nhất – thấp nhất về {m_name_lower} {denom_str} trong {p_vi}"
    if f_type == "ratio_to_median":
        _rv = fact.value or 0.0
        _rw = "gấp" if _rv >= 1.0 else "bằng"
        return f"Tỷ lệ {m_name_lower} của {ent} {_rw} {fmt(_rv, 1)} lần trung vị trong {p_vi}"
    if f_type == "derived_ratio":
        return f"Tỷ lệ {m_name_norm} của {ent} trong {p_vi}"
    if f_type == "lead_count":
        return f"Số chỉ tiêu vượt trội của {ent} so với {fact.other_entity_id} trong {p_vi}"
    return f"{m_name_norm} của {ent} ({p_vi})" if ent else f"{m_name_norm} ({p_vi})"


def make_fallback_sentence(
    fact: Fact,
    author: str = "orchestrator",
    seq: int = 1,
) -> SentenceDTO:
    """Generate a strictly verifier-compliant sentence from a single fact."""
    pres = get_metric_presentation(fact.metric_id)
    disp = display_fact(fact)
    p_vi = period_vi(fact.period)
    ent = fact.entity_id or ""
    f_type = fact.fact_type
    m_name_lower = format_metric_display_name(fact.metric_id, lowercase=True)
    m_name_upper = format_metric_display_name(fact.metric_id, lowercase=False)
    denom_str = f"nhóm {fact.denominator} ngân hàng" if fact.denominator else "toàn nhóm"

    if f_type == "value":
        if ent:
            text = f"{m_name_upper} của {ent} đạt {disp} trong {p_vi}."
        else:
            text = f"{m_name_upper} đạt {disp} trong {p_vi}."
    elif f_type == "peer_median":
        text = f"Trung vị {m_name_lower} của {denom_str} đạt {disp} trong {p_vi}."
    elif f_type == "peer_rank":
        r_val = fact.rank_better or fact.rank_desc or int(round(fact.value or 1))
        denom = fact.denominator or 5
        text = f"{ent} xếp hạng {r_val}/{denom} về {m_name_lower} trong {p_vi}."
    elif f_type == "gap_to_median":
        val = fact.value or 0.0
        flat = pres.flat_threshold_pp
        abs_disp = fmt(abs(val), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
        if val > flat:
            text = f"{ent} có {m_name_lower} cao hơn trung vị nhóm {abs_disp} trong {p_vi}."
        elif val < -flat:
            text = f"{ent} có {m_name_lower} thấp hơn trung vị nhóm {abs_disp} trong {p_vi}."
        else:
            text = f"{ent} có {m_name_lower} ngang trung vị nhóm trong {p_vi}."
    elif f_type == "spread":
        text = f"Chênh lệch cao nhất – thấp nhất về {m_name_lower} của {denom_str} là {disp} trong {p_vi}."
    elif f_type == "ratio_to_median":
        _ratio_val = fact.value or 0.0
        _ratio_str = fmt(_ratio_val, 1, show_sign=False)
        if _ratio_val >= 1.0:
            text = f"{m_name_upper} của {ent} gấp {_ratio_str} lần trung vị nhóm trong {p_vi}."
        else:
            text = f"{m_name_upper} của {ent} bằng {_ratio_str} lần trung vị nhóm trong {p_vi}."
    elif f_type == "delta":
        val = fact.value or 0.0
        flat = pres.flat_threshold_pp
        abs_disp = fmt(abs(val), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
        from_p = period_vi(fact.from_period or "")
        to_p = p_vi
        time_str = f"từ {from_p} đến {to_p}" if from_p else f"so với quý trước trong {to_p}"
        if val > flat:
            text = f"{m_name_upper} của {ent} tăng {abs_disp} {time_str}."
        elif val < -flat:
            text = f"{m_name_upper} của {ent} giảm {abs_disp} {time_str}."
        else:
            text = f"{m_name_upper} của {ent} đi ngang {time_str}."
    elif f_type == "derived_ratio":
        text = f"{m_name_upper} của {ent} là {disp} trong {p_vi}."
    elif f_type == "lead_count":
        text = f"{ent} nhỉnh hơn {fact.other_entity_id} ở {disp} trong {p_vi}."
    elif f_type == "pairwise_gap":
        val = fact.value or 0.0
        flat = pres.flat_threshold_pp
        abs_disp = fmt(abs(val), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
        other = fact.other_entity_id or ""
        if val > flat:
            text = f"{ent} có {m_name_lower} cao hơn {other} {abs_disp} trong {p_vi}."
        elif val < -flat:
            text = f"{ent} có {m_name_lower} thấp hơn {other} {abs_disp} trong {p_vi}."
        else:
            text = f"{ent} có {m_name_lower} tương đương {other} trong {p_vi}."
    elif f_type == "median_delta":
        val = fact.value or 0.0
        flat = pres.flat_threshold_pp
        abs_disp = fmt(abs(val), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
        from_p = period_vi(fact.from_period or "")
        time_str = f"từ {from_p} đến {p_vi}" if from_p else f"so với quý trước trong {p_vi}"
        if val > flat:
            text = f"Trung vị {m_name_lower} của nhóm tăng {abs_disp} {time_str}."
        elif val < -flat:
            text = f"Trung vị {m_name_lower} của nhóm giảm {abs_disp} {time_str}."
        else:
            text = f"Trung vị {m_name_lower} của nhóm đi ngang {time_str}."
    else:
        text = f"{m_name_upper} của {ent} ghi nhận giá trị {disp} trong {p_vi}." if ent else f"{m_name_upper} ghi nhận giá trị {disp} trong {p_vi}."

    return SentenceDTO(
        sentence_id=f"sent-fb-{seq}",
        text=text,
        fact_ids=[fact.fact_id],
        author=author,  # type: ignore
        source="deterministic_fallback",
        revision=0,
    )


def default_report_spec(
    question_type: str,
    tool_results: Sequence[ToolResult],
    signals: Sequence[SignalResult],
    findings: Sequence[CrossLevelCandidate],
) -> ReportSpecDTO:
    """Construct deterministic fallback ReportSpec layout per PR-4 §3 table."""
    all_facts: list[Fact] = []
    datasets_by_id: dict[str, Any] = {}
    for tr in tool_results:
        all_facts.extend(tr.facts)
        for ds in tr.datasets:
            datasets_by_id[ds.dataset_id] = ds

    facts_by_id = {f.fact_id: f for f in all_facts}
    used_takeaway_fids: set[str] = set()
    seq = 1

    # Detect anchor period from single-period facts
    anchor_period_raw: str | None = None
    for f in all_facts:
        if f.period and "_to_" not in f.period:
            if not anchor_period_raw or f.period > anchor_period_raw:
                anchor_period_raw = f.period
    anchor_p_vi = period_vi(anchor_period_raw or "") if anchor_period_raw else "kỳ phân tích"

    # 1. Lookup: answer_card with direct value and rank/delta context
    if question_type == "lookup":
        val_fact = next((f for f in all_facts if f.fact_type == "value"), None)
        if not val_fact:
            val_fact = all_facts[0] if all_facts else Fact(fact_id="f_empty", fact_type="value", value=0.0)

        ent = val_fact.entity_id or ""
        p_vi = period_vi(val_fact.period)
        m_name_upper = format_metric_display_name(val_fact.metric_id, lowercase=False)
        disp = display_fact(val_fact)
        pres = get_metric_presentation(val_fact.metric_id)

        rank_f = next((f for f in all_facts if f.fact_type == "peer_rank" and f.entity_id == ent and f.metric_id == val_fact.metric_id), None)
        if not rank_f:
            rank_f = next((f for f in all_facts if f.fact_type == "peer_rank"), None)

        if rank_f:
            r_val = rank_f.rank_better or rank_f.rank_desc or 1
            den = rank_f.denominator or 5
            superlative = ""
            if rank_f.rank_desc == den:
                superlative = " (thấp nhất nhóm)"
            elif rank_f.rank_desc == 1:
                superlative = " (cao nhất nhóm)"
            ans_text = f"{m_name_upper} của {ent} đạt {disp} trong {p_vi}, xếp hạng {r_val}/{den}{superlative}."
            cited_ids = [val_fact.fact_id, rank_f.fact_id]
        else:
            ans_text = f"{m_name_upper} của {ent} đạt {disp} trong {p_vi}."
            cited_ids = [val_fact.fact_id]

        ans_sent = SentenceDTO(
            sentence_id=f"sent-fb-{seq}",
            text=ans_text,
            fact_ids=cited_ids,
            author="company",
            source="deterministic_fallback",
            revision=0,
        )
        seq += 1
        context_sentences: list[SentenceDTO] = [ans_sent]

        delta_f = next((f for f in all_facts if f.fact_type == "delta" and f.entity_id == ent and f.metric_id == val_fact.metric_id), None)
        if delta_f:
            context_sentences.append(make_fallback_sentence(delta_f, author="company", seq=seq))
            seq += 1
        else:
            median_f = next((f for f in all_facts if f.fact_type == "peer_median" and f.metric_id == val_fact.metric_id), None)
            if median_f:
                context_sentences.append(make_fallback_sentence(median_f, author="sector", seq=seq))
                seq += 1

        answer_block = AnswerBlockDTO(
            type="answer",
            value_fact_id=val_fact.fact_id,
            sentences=context_sentences,
        )
        blocks: list[Any] = [answer_block]

        # Optional single figure for lookup
        ranked_ds = next((ds for ds in datasets_by_id.values() if ds.shape in ("ranked_list", "series")), None)
        if ranked_ds:
            rf_f = next((f for f in all_facts if f.metric_id in ranked_ds.metric_ids and f.fact_type in ("spread", "peer_median") and f.fact_id not in cited_ids), None)
            t_sent = make_fallback_sentence(rf_f, author="sector", seq=seq) if rf_f else None
            if t_sent:
                seq += 1
            blocks.append(
                FigureBlockDTO(
                    type="figure",
                    figure_no=1,
                    chart="ranked_bar" if ranked_ds.shape == "ranked_list" else "line_trend",
                    dataset_id=ranked_ds.dataset_id,
                    title=ranked_ds.title,
                    takeaway=t_sent,
                )
            )

        return ReportSpecDTO(
            kind="answer_card",
            note_label="Tra cứu chỉ tiêu",
            blocks=blocks,
            composition_source="deterministic_fallback",
        )

    # 2. Company Profile
    if question_type == "company_profile":
        blocks = []
        target = signals[0].fact_ids[0].split(":")[2] if (signals and signals[0].fact_ids and len(signals[0].fact_ids[0].split(":")) > 2) else "Ngân hàng"
        if target == "Ngân hàng":
            val_ent = next((f.entity_id for f in all_facts if f.entity_id), "Ngân hàng")
            target = val_ent

        # Headline from signals
        verdict_map = {
            "above_peers": "trên nhóm",
            "below_peers": "dưới nhóm",
            "in_line": "ngang nhóm",
        }
        hl_phrases: list[str] = []
        hl_fact_ids: list[str] = []
        sorted_signals = sorted(signals, key=lambda s: 0 if s.verdict in ("above_peers", "below_peers") else 1)
        for sig in sorted_signals[:2]:
            v_text = verdict_map.get(sig.verdict, "ngang nhóm")
            hl_phrases.append(f"{sig.label.lower()} {v_text}")
            hl_fact_ids.extend(sig.fact_ids)

        if hl_phrases:
            hl_text = f"{target}: {', '.join(hl_phrases)} trong {anchor_p_vi}."
            hl_sent = SentenceDTO(
                sentence_id="sent-fb-hl",
                text=hl_text,
                fact_ids=hl_fact_ids[:3] if hl_fact_ids else ([all_facts[0].fact_id] if all_facts else []),
                author="orchestrator",
                source="deterministic_fallback",
                revision=0,
            )
        else:
            first_val = next((f for f in all_facts if f.fact_type == "value" and f.entity_id == target), None)
            if first_val:
                hl_sent = make_fallback_sentence(first_val, author="orchestrator", seq=seq)
            else:
                hl_sent = SentenceDTO(
                    sentence_id="sent-fb-hl",
                    text=f"Báo cáo tổng quan vị thế tài chính của {target} trong {anchor_p_vi}.",
                    fact_ids=[all_facts[0].fact_id] if all_facts else [],
                    author="orchestrator",
                    source="deterministic_fallback",
                    revision=0,
                )
        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Key points from signals (prioritizing anchor_period facts)
        kp_items: list[KeyPointItemDTO] = []
        for sig in signals[:4]:
            sig_facts = [facts_by_id[fid] for fid in sig.fact_ids if fid in facts_by_id]
            anchor_sig_facts = [f for f in sig_facts if f.period == anchor_period_raw]
            chosen_fact = anchor_sig_facts[0] if anchor_sig_facts else (sig_facts[0] if sig_facts else None)
            if chosen_fact:
                s_sent = make_fallback_sentence(chosen_fact, author="sector", seq=seq)
                seq += 1
                v_vi = verdict_map.get(sig.verdict, sig.verdict.replace("_", " ").capitalize())
                kp_items.append(KeyPointItemDTO(title=f"{sig.label}: {v_vi.capitalize()}", sentences=[s_sent]))
        if kp_items:
            blocks.append(KeyPointsBlockDTO(type="key_points", items=kp_items))

        # Figures: scatter, rank_heatmap, small_multiples (distinct takeaways)
        fig_no = 1
        for ds_id, ds in datasets_by_id.items():
            if ds.shape in ("paired", "peer_table", "series_multi", "series"):
                chart_type = ds.allowed_charts[0] if ds.allowed_charts else "rank_heatmap"
                takeaway_fact = None
                if ds.shape == "paired":
                    takeaway_fact = next((f for f in all_facts if f.metric_id in ds.metric_ids and f.entity_id == target and f.fact_type in ("value", "derived_ratio", "gap_to_median") and f.fact_id not in used_takeaway_fids), None)
                elif ds.shape == "peer_table":
                    takeaway_fact = next((f for f in all_facts if f.metric_id in ds.metric_ids and f.entity_id == target and f.fact_type == "peer_rank" and f.fact_id not in used_takeaway_fids), None)
                elif ds.shape in ("series_multi", "series"):
                    takeaway_fact = next((f for f in all_facts if f.metric_id in ds.metric_ids and f.entity_id == target and f.fact_type == "delta" and f.fact_id not in used_takeaway_fids), None)

                if not takeaway_fact:
                    takeaway_fact = next((f for f in all_facts if f.metric_id in ds.metric_ids and f.value is not None and f.fact_id not in used_takeaway_fids), None)

                if takeaway_fact:
                    used_takeaway_fids.add(takeaway_fact.fact_id)
                    t_sent = make_fallback_sentence(takeaway_fact, author="orchestrator", seq=seq)
                    seq += 1
                else:
                    t_sent = None

                blocks.append(
                    FigureBlockDTO(
                        type="figure",
                        figure_no=fig_no,
                        chart=chart_type,  # type: ignore
                        dataset_id=ds_id,
                        title=ds.title,
                        takeaway=t_sent,
                    )
                )
                fig_no += 1
                if fig_no > 3:
                    break

        # Callouts for confirmed findings
        for fnd in findings[:2]:
            if fnd.status == "confirmed":
                fnd_facts = [facts_by_id[fid] for fid in fnd.fact_ids if fid in facts_by_id]
                c_sents = []
                if fnd.kind == "divergent_signals" and len(fnd_facts) >= 2:
                    above_f = next((f for f in fnd_facts if (f.fact_type == "gap_to_median" and (f.value or 0) > 0) or (f.fact_type == "peer_rank" and (f.rank_better or 1) <= 2)), None)
                    below_f = next((f for f in fnd_facts if (f.fact_type == "gap_to_median" and (f.value or 0) < 0) or (f.fact_type == "peer_rank" and (f.rank_better or 1) >= 4)), None)
                    f1 = above_f or fnd_facts[0]
                    f2 = below_f or fnd_facts[-1]
                    if f1.fact_id == f2.fact_id and len(fnd_facts) > 1:
                        f2 = fnd_facts[1]
                    c_sents.append(make_fallback_sentence(f1, author="critic", seq=seq))
                    seq += 1
                    c_sents.append(make_fallback_sentence(f2, author="critic", seq=seq))
                    seq += 1
                elif fnd_facts:
                    c_sents.append(make_fallback_sentence(fnd_facts[0], author="critic", seq=seq))
                    seq += 1

                blocks.append(
                    CalloutBlockDTO(
                        type="callout",
                        tone=fnd.severity if fnd.severity in ("notice", "warning") else "notice",  # type: ignore
                        title=fnd.text,
                        finding_id=fnd.finding_id,
                        sentences=c_sents,
                    )
                )

        return ReportSpecDTO(
            kind="note",
            note_label="Hồ sơ doanh nghiệp",
            blocks=blocks,
            composition_source="deterministic_fallback",
        )

    # 3. Ranking
    if question_type == "ranking":
        blocks = []
        top_rank = next((f for f in all_facts if f.fact_type == "peer_rank" and f.rank_better == 1), None)
        if top_rank:
            ent = top_rank.entity_id or ""
            p_vi = period_vi(top_rank.period)
            m_name_lower = format_metric_display_name(top_rank.metric_id, lowercase=True)
            pres = get_metric_presentation(top_rank.metric_id)
            superlative = "cao nhất"
            if pres.direction == "lower_is_better" or top_rank.rank_desc == top_rank.denominator:
                superlative = "thấp nhất"
            elif top_rank.metric_id == "bank.llr_coverage":
                superlative = "dày nhất"

            val_f = next((f for f in all_facts if f.fact_type == "value" and f.entity_id == ent and f.metric_id == top_rank.metric_id and f.period == top_rank.period), None)
            ratio_f = next((f for f in all_facts if f.fact_type == "ratio_to_median" and f.entity_id == ent and f.metric_id == top_rank.metric_id and f.period == top_rank.period), None)

            if val_f and ratio_f:
                val_str = display_fact(val_f)
                _rv = ratio_f.value or 0.0
                _ratio_word = "gấp" if _rv >= 1.0 else "bằng"
                ratio_val = fmt(_rv, 1, show_sign=False)
                hl_text = f"{ent} có {m_name_lower} {superlative}, đạt {val_str}, {_ratio_word} {ratio_val} lần trung vị nhóm trong {p_vi}."
                hl_sent = SentenceDTO(
                    sentence_id="sent-fb-hl",
                    text=hl_text,
                    fact_ids=[top_rank.fact_id, val_f.fact_id, ratio_f.fact_id],
                    author="orchestrator",
                    source="deterministic_fallback",
                    revision=0,
                )
            elif val_f:
                val_str = display_fact(val_f)
                hl_text = f"{ent} có {m_name_lower} {superlative}, đạt {val_str} trong {p_vi}."
                hl_sent = SentenceDTO(
                    sentence_id="sent-fb-hl",
                    text=hl_text,
                    fact_ids=[top_rank.fact_id, val_f.fact_id],
                    author="orchestrator",
                    source="deterministic_fallback",
                    revision=0,
                )
            else:
                hl_sent = make_fallback_sentence(top_rank, author="orchestrator", seq=seq)
        else:
            hl_sent = make_fallback_sentence(all_facts[0], author="orchestrator", seq=seq) if all_facts else SentenceDTO(sentence_id="sent-fb-1", text="Xếp hạng chỉ tiêu tài chính.", fact_ids=[], author="orchestrator", source="deterministic_fallback")
        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Figure ranked_bar with distinct takeaway (spread)
        ranked_ds = next((ds for ds in datasets_by_id.values() if ds.shape == "ranked_list"), None)
        if ranked_ds:
            spread_f = next((f for f in all_facts if f.fact_type == "spread"), None)
            if spread_f and spread_f.fact_id not in used_takeaway_fids:
                used_takeaway_fids.add(spread_f.fact_id)
                t_sent = make_fallback_sentence(spread_f, author="sector", seq=seq)
                seq += 1
            else:
                t_sent = None
            blocks.append(
                FigureBlockDTO(
                    type="figure",
                    figure_no=1,
                    chart="ranked_bar",
                    dataset_id=ranked_ds.dataset_id,
                    title=ranked_ds.title,
                    takeaway=t_sent,
                )
            )

        # Key points (spread, bottom rank)
        kp_items = []
        spread_f = next((f for f in all_facts if f.fact_type == "spread"), None)
        if spread_f:
            kp_items.append(KeyPointItemDTO(title="Khoảng biến thiên toàn nhóm", sentences=[make_fallback_sentence(spread_f, author="sector", seq=seq)]))
            seq += 1
        bot_rank = next((f for f in all_facts if f.fact_type == "peer_rank" and f.rank_better == f.denominator), None)
        if bot_rank:
            kp_items.append(KeyPointItemDTO(title="Vị trí đứng cuối", sentences=[make_fallback_sentence(bot_rank, author="sector", seq=seq)]))
            seq += 1
        if kp_items:
            blocks.append(KeyPointsBlockDTO(type="key_points", items=kp_items))

        # Callout cross_metric_extreme
        for fnd in findings:
            if fnd.kind == "cross_metric_extreme" and fnd.status == "confirmed":
                f_facts = [facts_by_id[fid] for fid in fnd.fact_ids if fid in facts_by_id]
                blocks.append(
                    CalloutBlockDTO(
                        type="callout",
                        tone="notice",
                        title=fnd.text,
                        finding_id=fnd.finding_id,
                        sentences=[make_fallback_sentence(f_facts[0], author="critic", seq=seq)] if f_facts else [],
                    )
                )
                seq += 1
                break

        return ReportSpecDTO(
            kind="note",
            note_label="Xếp hạng nhóm ngân hàng",
            blocks=blocks,
            composition_source="deterministic_fallback",
        )

    # 4. Trend
    if question_type == "trend":
        blocks = []
        target = next((f.entity_id for f in all_facts if f.entity_id), "")
        overall_delta = None
        deltas = [f for f in all_facts if f.fact_type == "delta" and f.entity_id == target and f.from_period and f.period]
        if deltas:
            deltas_sorted = sorted(deltas, key=lambda f: (f.from_period or "", f.period or ""))
            first_from = deltas_sorted[0].from_period
            last_to = deltas_sorted[-1].period
            overall_delta = next((f for f in deltas if f.from_period == first_from and f.period == last_to), deltas_sorted[-1])

        end_rank = next((f for f in all_facts if f.fact_type == "peer_rank" and f.entity_id == target and f.period == anchor_period_raw), None)

        if overall_delta and end_rank:
            ent = overall_delta.entity_id or ""
            m_name_upper = format_metric_display_name(overall_delta.metric_id, lowercase=False)
            val = overall_delta.value or 0.0
            pres = get_metric_presentation(overall_delta.metric_id)
            flat = pres.flat_threshold_pp
            abs_disp = fmt(abs(val), decimals=pres.delta_decimals, show_sign=False, unit=" điểm %")
            from_p = period_vi(overall_delta.from_period or "")
            to_p = period_vi(overall_delta.period or "")
            r_val = end_rank.rank_better or end_rank.rank_desc or 1
            den = end_rank.denominator or 5
            if val > flat:
                trend_str = f"tăng {abs_disp}"
            elif val < -flat:
                trend_str = f"giảm {abs_disp}"
            else:
                trend_str = "đi ngang"
            hl_text = f"{m_name_upper} của {ent} {trend_str} từ {from_p} đến {to_p}, xếp hạng {r_val}/{den} trong {to_p}."
            hl_sent = SentenceDTO(
                sentence_id="sent-fb-hl",
                text=hl_text,
                fact_ids=[overall_delta.fact_id, end_rank.fact_id],
                author="orchestrator",
                source="deterministic_fallback",
                revision=0,
            )
        elif overall_delta:
            hl_sent = make_fallback_sentence(overall_delta, author="orchestrator", seq=seq)
        else:
            first_f = all_facts[0] if all_facts else None
            hl_sent = make_fallback_sentence(first_f, author="orchestrator", seq=seq) if first_f else SentenceDTO(sentence_id="sent-fb-1", text="Diễn biến chỉ tiêu tài chính.", fact_ids=[], author="orchestrator", source="deterministic_fallback")

        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Figure line_trend with distinct takeaway
        series_ds = next((ds for ds in datasets_by_id.values() if ds.shape in ("series", "series_multi")), None)
        if series_ds:
            val_anchor_f = next((f for f in all_facts if f.metric_id in series_ds.metric_ids and f.entity_id == target and f.fact_type == "value" and f.period == anchor_period_raw and f.fact_id not in used_takeaway_fids), None)
            if val_anchor_f:
                used_takeaway_fids.add(val_anchor_f.fact_id)
                t_sent = make_fallback_sentence(val_anchor_f, author="orchestrator", seq=seq)
                seq += 1
            else:
                t_sent = None
            blocks.append(
                FigureBlockDTO(
                    type="figure",
                    figure_no=1,
                    chart="line_trend" if series_ds.shape == "series" else "small_multiples",
                    dataset_id=series_ds.dataset_id,
                    title=series_ds.title,
                    takeaway=t_sent,
                )
            )

        # Key points (sequential deltas)
        kp_items = []
        seq_deltas = [f for f in all_facts if f.fact_type == "delta" and f.entity_id == target and f != overall_delta]
        if not seq_deltas and overall_delta:
            seq_deltas = [overall_delta]
        for df in seq_deltas[:3]:
            from_p = period_vi(df.from_period or "")
            to_p = period_vi(df.period or "")
            kp_title = f"Biến động từ {from_p} đến {to_p}" if from_p else f"Biến động trong {to_p}"
            kp_items.append(KeyPointItemDTO(title=kp_title, sentences=[make_fallback_sentence(df, author="company", seq=seq)]))
            seq += 1
        if kp_items:
            blocks.append(KeyPointsBlockDTO(type="key_points", items=kp_items))

        return ReportSpecDTO(
            kind="note",
            note_label="Diễn biến theo chuỗi thời gian",
            blocks=blocks,
            composition_source="deterministic_fallback",
        )

    # 5. Head-to-Head
    blocks = []
    lead_f = max(
        [f for f in all_facts if f.fact_type == "lead_count"],
        key=lambda f: float(f.value or 0),
        default=None,
    )
    if lead_f:
        hl_sent = make_fallback_sentence(lead_f, author="orchestrator", seq=seq)
    else:
        hl_sent = make_fallback_sentence(all_facts[0], author="orchestrator", seq=seq) if all_facts else SentenceDTO(sentence_id="sent-fb-1", text="So sánh đối đầu.", fact_ids=[], author="orchestrator", source="deterministic_fallback")
    blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
    seq += 1

    # Figure comparison_table with distinct takeaway
    cmp_ds = next((ds for ds in datasets_by_id.values() if ds.shape in ("comparison_table", "peer_table")), None)
    if cmp_ds:
        pair_gap_f = next((f for f in all_facts if f.metric_id in cmp_ds.metric_ids and f.fact_type == "pairwise_gap" and f.fact_id not in used_takeaway_fids), None)
        if pair_gap_f:
            used_takeaway_fids.add(pair_gap_f.fact_id)
            t_sent = make_fallback_sentence(pair_gap_f, author="orchestrator", seq=seq)
            seq += 1
        else:
            t_sent = None
        blocks.append(
            FigureBlockDTO(
                type="figure",
                figure_no=1,
                chart="comparison_table",
                dataset_id=cmp_ds.dataset_id,
                title=cmp_ds.title,
                takeaway=t_sent,
            )
        )

    # Callout decomposition if available
    decomp_f = next((f for f in all_facts if f.fact_type == "derived_ratio"), None)
    if decomp_f:
        blocks.append(
            CalloutBlockDTO(
                type="callout",
                tone="notice",
                title="Phân rã hiệu quả đòn bẩy ROE/ROA",
                sentences=[make_fallback_sentence(decomp_f, author="company", seq=seq)],
            )
        )
        seq += 1

    return ReportSpecDTO(
        kind="note",
        note_label="So sánh đối đầu",
        blocks=blocks,
        composition_source="deterministic_fallback",
    )
