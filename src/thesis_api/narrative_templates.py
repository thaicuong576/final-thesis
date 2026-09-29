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
from .metric_presentation import get_metric_presentation
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
    if f_type in ("gap_to_median", "delta", "median_delta", "pairwise_gap", "spread"):
        return fmt(fact.value, decimals=pres.delta_decimals, show_sign=True, unit=" điểm %")
    if f_type == "ratio_to_median":
        return fmt(fact.value, decimals=1, show_sign=False, unit=" lần")
    if f_type == "derived_ratio":
        return fmt(fact.value, decimals=2, show_sign=False, unit=" lần")
    if f_type == "lead_count":
        return f"{int(round(fact.value or 0))}/{fact.denominator} chỉ tiêu"
    return str(fact.value)


def describe_fact(fact: Fact) -> str:
    """Produce human-readable metadata description of a fact."""
    pres = get_metric_presentation(fact.metric_id)
    p_vi = period_vi(fact.period)
    ent = fact.entity_id or fact.universe_id or ""
    f_type = fact.fact_type

    if f_type == "value":
        return f"{pres.label} của {ent} trong {p_vi}"
    if f_type == "peer_median":
        return f"Trung vị {pres.label} nhóm {fact.denominator or ''} ngân hàng trong {p_vi}"
    if f_type == "peer_rank":
        return f"Xếp hạng {pres.label} của {ent} so với {fact.denominator} ngân hàng trong {p_vi}"
    if f_type == "gap_to_median":
        return f"Chênh lệch {pres.label} của {ent} so với trung vị nhóm trong {p_vi}"
    if f_type == "delta":
        from_p = period_vi(fact.from_period or "")
        return f"Mức thay đổi {pres.label} của {ent} từ {from_p} đến {p_vi}"
    if f_type == "median_delta":
        from_p = period_vi(fact.from_period or "")
        return f"Mức thay đổi trung vị {pres.label} từ {from_p} đến {p_vi}"
    if f_type == "pairwise_gap":
        return f"Chênh lệch {pres.label} giữa {ent} và {fact.other_entity_id} trong {p_vi}"
    if f_type == "spread":
        return f"Khoảng biến thiên (spread) {pres.label} toàn nhóm trong {p_vi}"
    if f_type == "ratio_to_median":
        return f"Tỷ lệ {pres.label} của {ent} so với trung vị nhóm trong {p_vi}"
    if f_type == "derived_ratio":
        return f"Phân rã {pres.label} của {ent} trong {p_vi}"
    if f_type == "lead_count":
        return f"Số chỉ tiêu vượt trội của {ent} so với {fact.other_entity_id} trong {p_vi}"
    return f"{pres.label} · {ent} ({p_vi})"


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

    if f_type == "value":
        text = f"{pres.short_label} của {ent} đạt {disp} trong {p_vi}."
    elif f_type == "peer_rank":
        text = f"{ent} xếp {disp} về {pres.short_label} trong {p_vi}."
    elif f_type == "gap_to_median":
        text = f"Khoảng cách {pres.short_label} của {ent} so với trung vị nhóm là {disp} trong {p_vi}."
    elif f_type == "delta":
        text = f"{pres.short_label} của {ent} có mức thay đổi {disp} trong {p_vi}."
    elif f_type == "lead_count":
        text = f"{ent} nhỉnh hơn {fact.other_entity_id} ở {disp} trong {p_vi}."
    elif f_type == "derived_ratio":
        text = f"{pres.short_label} của {ent} đạt {disp} trong {p_vi}."
    else:
        text = f"{pres.short_label} của {ent} ghi nhận giá trị {disp} trong {p_vi}."

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
    seq = 1

    # 1. Lookup: answer_card: answer (value) + câu bối cảnh (hạng, delta nếu có)
    if question_type == "lookup":
        val_fact = next((f for f in all_facts if f.fact_type == "value"), None)
        if not val_fact:
            val_fact = all_facts[0] if all_facts else Fact(fact_id="f_empty", fact_type="value", value=0.0)

        context_sentences: list[SentenceDTO] = []
        rank_f = next((f for f in all_facts if f.fact_type == "peer_rank"), None)
        if rank_f:
            context_sentences.append(make_fallback_sentence(rank_f, author="company", seq=seq))
            seq += 1
        delta_f = next((f for f in all_facts if f.fact_type == "delta"), None)
        if delta_f:
            context_sentences.append(make_fallback_sentence(delta_f, author="company", seq=seq))
            seq += 1

        answer_block = AnswerBlockDTO(
            type="answer",
            value_fact_id=val_fact.fact_id,
            sentences=context_sentences,
        )
        return ReportSpecDTO(kind="answer_card", note_label="Tra cứu chỉ tiêu", blocks=[answer_block])

    # 2. Company Profile
    if question_type == "company_profile":
        blocks: list[Any] = []
        target = signals[0].fact_ids[0].split(":")[2] if (signals and signals[0].fact_ids) else "Ngân hàng"
        anchor_period = period_vi(all_facts[0].period) if all_facts else "kỳ phân tích"

        # Headline
        first_val = next((f for f in all_facts if f.fact_type == "value"), None)
        if first_val:
            hl_sent = make_fallback_sentence(first_val, author="orchestrator", seq=seq)
        else:
            hl_sent = SentenceDTO(
                sentence_id="sent-fb-hl",
                text=f"Báo cáo tổng quan vị thế tài chính trong {anchor_period}.",
                fact_ids=[all_facts[0].fact_id] if all_facts else [],
                author="orchestrator",
                source="deterministic_fallback",
            )
        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Key points from signals
        kp_items: list[KeyPointItemDTO] = []
        for sig in signals[:4]:
            sig_facts = [facts_by_id[fid] for fid in sig.fact_ids if fid in facts_by_id]
            if sig_facts:
                s_sent = make_fallback_sentence(sig_facts[0], author="sector", seq=seq)
                seq += 1
                kp_items.append(KeyPointItemDTO(title=f"{sig.label}: {sig.verdict.replace('_', ' ').capitalize()}", sentences=[s_sent]))
        if kp_items:
            blocks.append(KeyPointsBlockDTO(type="key_points", items=kp_items))

        # Figures: scatter, rank_heatmap, small_multiples (or line_trend)
        fig_no = 1
        for ds_id, ds in datasets_by_id.items():
            if ds.shape in ("paired", "peer_table", "series_multi", "series"):
                chart_type = ds.allowed_charts[0] if ds.allowed_charts else "rank_heatmap"
                takeaway_fact = next((f for f in all_facts if f.metric_id in ds.metric_ids and f.value is not None), None)
                if takeaway_fact:
                    t_sent = make_fallback_sentence(takeaway_fact, author="orchestrator", seq=seq)
                    seq += 1
                else:
                    t_sent = SentenceDTO(
                        sentence_id=f"sent-fb-t-{fig_no}",
                        text=f"Biểu đồ thể hiện {ds.title}.",
                        fact_ids=[all_facts[0].fact_id] if all_facts else [],
                        author="orchestrator",
                        source="deterministic_fallback",
                    )
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
                c_sents = [make_fallback_sentence(fnd_facts[0], author="critic", seq=seq)] if fnd_facts else []
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

        return ReportSpecDTO(kind="note", note_label="Hồ sơ doanh nghiệp", blocks=blocks)

    # 3. Ranking
    if question_type == "ranking":
        blocks = []
        top_rank = next((f for f in all_facts if f.fact_type == "peer_rank" and f.rank_better == 1), None)
        if top_rank:
            hl_sent = make_fallback_sentence(top_rank, author="orchestrator", seq=seq)
        else:
            hl_sent = make_fallback_sentence(all_facts[0], author="orchestrator", seq=seq) if all_facts else SentenceDTO(sentence_id="sent-fb-1", text="Xếp hạng chỉ tiêu tài chính.", fact_ids=[], author="orchestrator", source="deterministic_fallback")
        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Figure ranked_bar
        ranked_ds = next((ds for ds in datasets_by_id.values() if ds.shape == "ranked_list"), None)
        if ranked_ds:
            rf_f = next((f for f in all_facts if f.fact_type == "spread"), all_facts[0] if all_facts else None)
            t_sent = make_fallback_sentence(rf_f, author="sector", seq=seq) if rf_f else SentenceDTO(sentence_id="sent-fb-t1", text="Biểu đồ xếp hạng toàn nhóm.", fact_ids=[], author="sector", source="deterministic_fallback")
            seq += 1
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

        return ReportSpecDTO(kind="note", note_label="Xếp hạng nhóm ngân hàng", blocks=blocks)

    # 4. Trend
    if question_type == "trend":
        blocks = []
        delta_f = next((f for f in all_facts if f.fact_type == "delta"), None)
        if delta_f:
            hl_sent = make_fallback_sentence(delta_f, author="orchestrator", seq=seq)
        else:
            hl_sent = make_fallback_sentence(all_facts[0], author="orchestrator", seq=seq) if all_facts else SentenceDTO(sentence_id="sent-fb-1", text="Diễn biến chỉ tiêu tài chính.", fact_ids=[], author="orchestrator", source="deterministic_fallback")
        blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
        seq += 1

        # Figure line_trend
        series_ds = next((ds for ds in datasets_by_id.values() if ds.shape in ("series", "series_multi")), None)
        if series_ds:
            blocks.append(
                FigureBlockDTO(
                    type="figure",
                    figure_no=1,
                    chart="line_trend" if series_ds.shape == "series" else "small_multiples",
                    dataset_id=series_ds.dataset_id,
                    title=series_ds.title,
                    takeaway=hl_sent,
                )
            )

        # Key points (deltas, gaps)
        kp_items = []
        for df in [f for f in all_facts if f.fact_type == "delta"][:3]:
            kp_items.append(KeyPointItemDTO(title=f"Biến động {period_vi(df.period)}", sentences=[make_fallback_sentence(df, author="company", seq=seq)]))
            seq += 1
        if kp_items:
            blocks.append(KeyPointsBlockDTO(type="key_points", items=kp_items))

        return ReportSpecDTO(kind="note", note_label="Diễn biến theo chuỗi thời gian", blocks=blocks)

    # 5. Head-to-Head
    blocks = []
    lead_f = next((f for f in all_facts if f.fact_type == "lead_count"), None)
    if lead_f:
        hl_sent = make_fallback_sentence(lead_f, author="orchestrator", seq=seq)
    else:
        hl_sent = make_fallback_sentence(all_facts[0], author="orchestrator", seq=seq) if all_facts else SentenceDTO(sentence_id="sent-fb-1", text="So sánh đối đầu.", fact_ids=[], author="orchestrator", source="deterministic_fallback")
    blocks.append(HeadlineBlockDTO(type="headline", sentence=hl_sent))
    seq += 1

    # Figure comparison_table
    cmp_ds = next((ds for ds in datasets_by_id.values() if ds.shape in ("comparison_table", "peer_table")), None)
    if cmp_ds:
        blocks.append(
            FigureBlockDTO(
                type="figure",
                figure_no=1,
                chart="comparison_table",
                dataset_id=cmp_ds.dataset_id,
                title=cmp_ds.title,
                takeaway=hl_sent,
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

    return ReportSpecDTO(kind="note", note_label="So sánh đối đầu", blocks=blocks)
