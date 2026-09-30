"""Deterministic analysis tools producing facts and datasets.

Executes query-planned analysis tools:
- lookup
- peer_position
- ranking
- trend
- head_to_head
- decomposition
- dispersion (extended)
- relationship (extended)

All computations are deterministic and provenance-tracked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from thesis_data.dataset_contract import CanonicalObservation, QualityStatus
from thesis_data.dataset_provider import aggregate_peer_median
from thesis_data.report_facts import (
    FORMULA,
    Fact,
    classify_signals,
    delta_fact,
    derived_ratio_fact,
    detect_cross_level_candidates,
    gap_fact,
    lead_count_fact,
    median_delta_fact,
    median_fact,
    pairwise_gap_fact,
    rank_facts,
    ratio_to_median_fact,
    spread_fact,
    value_fact,
)
from .metric_presentation import get_metric_presentation
from .schemas import (
    DatasetDTO,
    DatasetRowDTO,
    FactDTO,
    ProducedByDTO,
    ReferenceLineDTO,
    SignalDTO,
    SourceNoteDTO,
)

logger = logging.getLogger(__name__)


def _format_quarter_period(period: str) -> str:
    """Format canonical period (e.g. 2024_Q4) into standard display (e.g. Q4/2024)."""
    if not period:
        return ""
    parts = period.split("_")
    if len(parts) == 2 and parts[1].startswith("Q"):
        return f"{parts[1]}/{parts[0]}"
    return period


def humanize_locator(raw: str) -> str:
    """Humanize a machine-structured source locator string into a readable string."""
    if not raw:
        return ""
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    kv: dict[str, str] = {}
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip()] = v.strip()

    tokens: list[str] = []
    # 1. Page
    if "printed_page" in kv:
        tokens.append(f"tr. {kv['printed_page']}")
    elif "printed_pages" in kv:
        p_val = kv["printed_pages"].replace("_and_", ", ").replace(",", ", ")
        p_val = ", ".join(p.strip() for p in p_val.split(","))
        tokens.append(f"tr. {p_val}")
    elif "page" in kv:
        tokens.append(f"tr. {kv['page']}")

    # 2. Section
    sec = kv.get("section") or kv.get("sections")
    if sec:
        sec_clean = sec.replace("_", " ")
        if "|" in sec_clean:
            sec_clean = " · ".join(s.strip() for s in sec_clean.split("|"))
        tokens.append(sec_clean)
    elif "statement" in kv:
        tokens.append(kv["statement"].replace("_", " "))
    elif "table" in kv:
        tokens.append(kv["table"].replace("_", " "))

    if tokens:
        return " · ".join(tokens)
    return raw


@dataclass
class ToolContext:
    """Execution context provided to analysis tools."""

    provider: Any
    dataset_ref: Any
    catalog: Any
    universe_id: str | None
    universe_members: tuple[str, ...]
    presentation: Any  # get_metric_presentation callable
    cache: dict[tuple[str, str, str], CanonicalObservation | None]


@dataclass
class MissingCell:
    """Unobserved cell record."""

    entity_id: str
    period: str
    metric_id: str
    reason: str


@dataclass
class ToolResult:
    """Outcome of a single analysis tool execution."""

    tool: str
    agent: str
    label: str
    facts: list[Fact]
    datasets: list[DatasetDTO]
    missing: list[MissingCell]


def get_cached_obs(
    ctx: ToolContext, entity_id: str, period_id: str, metric_id: str
) -> CanonicalObservation | None:
    """Retrieve an observation using the execution cache."""
    key = (entity_id, period_id, metric_id)
    if key in ctx.cache:
        return ctx.cache[key]
    obs: CanonicalObservation | None = None
    try:
        if hasattr(ctx.provider, "get_metric"):
            obs = ctx.provider.get_metric(ctx.dataset_ref, entity_id, period_id, metric_id)
    except Exception:
        obs = None
    ctx.cache[key] = obs
    return obs


def _get_universe_obs(
    ctx: ToolContext, period: str, metric: str
) -> tuple[list[CanonicalObservation], list[CanonicalObservation]]:
    """Return all observations and valid observations across universe members."""
    all_obs: list[CanonicalObservation] = []
    valid_obs: list[CanonicalObservation] = []
    for entity in ctx.universe_members:
        obs = get_cached_obs(ctx, entity, period, metric)
        if obs is not None:
            all_obs.append(obs)
            if obs.validation_status is QualityStatus.VALID and obs.value is not None:
                valid_obs.append(obs)
    return all_obs, valid_obs


def _safe_peer_median(
    ctx: ToolContext, universe_id: str, period: str, metric: str, valid_obs: list[CanonicalObservation]
) -> Fact | None:
    """Aggregate and create peer median fact safely."""
    if not valid_obs:
        return None
    try:
        if hasattr(ctx.provider, "get_peer_benchmark"):
            benchmarks = ctx.provider.get_peer_benchmark(
                ctx.dataset_ref, universe_id, period, (metric,), peer_entity_ids=ctx.universe_members
            )
            if (
                benchmarks
                and benchmarks[0].validation_status is QualityStatus.VALID
                and benchmarks[0].value is not None
            ):
                return median_fact(benchmarks[0], universe_id, valid_obs)
    except Exception:
        pass
    try:
        med_obs = aggregate_peer_median(
            dataset_ref=ctx.dataset_ref,
            peer_universe_id=universe_id,
            period_id=period,
            metric_id=metric,
            peer_entity_ids=ctx.universe_members,
            member_observations=valid_obs,
        )
        return median_fact(med_obs, universe_id, valid_obs)
    except Exception as exc:
        logger.debug("Failed aggregate_peer_median for %s %s: %s", period, metric, exc)
        return None


def run_lookup_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute lookup tool: single-point value with context."""
    entities = params.get("entities") or [params.get("entity") or params.get("target") or ""]
    period = params.get("period") or ""
    metrics = params.get("metrics") or ([params.get("metric")] if params.get("metric") else [])
    facts: list[Fact] = []
    missing: list[MissingCell] = []
    rows: list[DatasetRowDTO] = []

    universe_id = ctx.universe_id

    for entity in entities:
        if not entity:
            continue
        for metric in metrics:
            if not metric:
                continue
            obs = get_cached_obs(ctx, entity, period, metric)
            if obs is not None and obs.validation_status is QualityStatus.VALID and obs.value is not None:
                v_fact = value_fact(obs)
                if v_fact:
                    facts.append(v_fact)
                rows.append(
                    DatasetRowDTO(
                        entity_id=entity,
                        metric_id=metric,
                        period=period,
                        status="valid",
                        value=float(obs.value),
                        observation_id=obs.observation_id,
                    )
                )
            else:
                missing.append(MissingCell(entity_id=entity, period=period, metric_id=metric, reason="DATA_UNAVAILABLE"))
                rows.append(
                    DatasetRowDTO(
                        entity_id=entity,
                        metric_id=metric,
                        period=period,
                        status="missing",
                        value=None,
                        missing_reason="DATA_UNAVAILABLE",
                    )
                )

            # Peer context: median & rank if universe available
            med_fact: Fact | None = None
            if universe_id and len(ctx.universe_members) >= 2:
                _, valid_obs = _get_universe_obs(ctx, period, metric)
                med_fact = _safe_peer_median(ctx, universe_id, period, metric, valid_obs)
                if med_fact:
                    facts.append(med_fact)
                pres = ctx.presentation(metric)
                r_facts = rank_facts(valid_obs, universe_id, pres.direction)
                ent_rf = next((rf for rf in r_facts if rf.entity_id == entity), None)
                if ent_rf:
                    facts.append(ent_rf)

            # Period context: delta to previous quarter if available
            p_parts = period.split("_")
            if len(p_parts) == 2 and p_parts[1].startswith("Q"):
                try:
                    q_num = int(p_parts[1][1:])
                    year_num = int(p_parts[0])
                    if q_num > 1:
                        prev_period = f"{year_num}_Q{q_num - 1}"
                        prev_obs = get_cached_obs(ctx, entity, prev_period, metric)
                        if prev_obs is not None and prev_obs.validation_status is QualityStatus.VALID and prev_obs.value is not None:
                            pv_fact = value_fact(prev_obs)
                            if pv_fact:
                                facts.append(pv_fact)
                            curr_obs = get_cached_obs(ctx, entity, period, metric)
                            d_fact = delta_fact(prev_obs, curr_obs)
                            if d_fact:
                                facts.append(d_fact)
                except ValueError:
                    pass

    datasets: list[DatasetDTO] = []
    if rows:
        metric_slug = metrics[0].rsplit(".", 1)[-1] if metrics else "metric"
        ent_slug = entities[0].lower() if entities else "all"
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-lookup-{ent_slug}-{metric_slug}-{period.lower().replace('_', '')}",
                shape="kpi",
                title=f"Tra cứu chỉ tiêu · {entities[0]} {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="lookup", agent="company"),
                metric_ids=list(metrics),
                periods=[period],
                highlight_entity_ids=list(entities),
                rows=rows,
                allowed_charts=["kpi_strip"],
            )
        )

    label = f"Tra cứu {metrics[0].rsplit('.', 1)[-1].upper() if metrics else ''} · {entities[0] if entities else ''}"
    return ToolResult(tool="lookup", agent="company", label=label, facts=facts, datasets=datasets, missing=missing)


def run_peer_position_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute peer_position tool: CAMEL position vs peer group."""
    target = params.get("entity") or params.get("target") or ""
    period = params.get("period") or ""
    metrics = params.get("metrics") or []
    universe_id = ctx.universe_id

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    peer_table_rows: list[DatasetRowDTO] = []
    reference_lines: list[ReferenceLineDTO] = []

    if not universe_id or len(ctx.universe_members) < 2:
        for metric in metrics:
            missing.append(MissingCell(entity_id=target, period=period, metric_id=metric, reason="UNIVERSE_UNAVAILABLE"))
            target_obs = get_cached_obs(ctx, target, period, metric)
            if target_obs and target_obs.validation_status is QualityStatus.VALID and target_obs.value is not None:
                vf = value_fact(target_obs)
                if vf:
                    facts.append(vf)
        label = f"Vị thế so với nhóm · {target} (không có universe)"
        return ToolResult(tool="peer_position", agent="sector", label=label, facts=facts, datasets=[], missing=missing)

    for metric in metrics:
        _, valid_obs = _get_universe_obs(ctx, period, metric)
        pres = ctx.presentation(metric)
        rf_list = rank_facts(valid_obs, universe_id, pres.direction)
        rf_by_entity = {rf.entity_id: rf for rf in rf_list}

        med_fact = _safe_peer_median(ctx, universe_id, period, metric, valid_obs)
        if med_fact:
            facts.append(med_fact)
            if med_fact.value is not None:
                reference_lines.append(
                    ReferenceLineDTO(
                        kind="median",
                        metric_id=metric,
                        period=period,
                        value=float(med_fact.value),
                        fact_id=med_fact.fact_id,
                    )
                )

        target_obs = get_cached_obs(ctx, target, period, metric)
        target_val_fact: Fact | None = None
        if target_obs is not None and target_obs.validation_status is QualityStatus.VALID and target_obs.value is not None:
            target_val_fact = value_fact(target_obs)
            if target_val_fact:
                facts.append(target_val_fact)
        else:
            missing.append(MissingCell(entity_id=target, period=period, metric_id=metric, reason="DATA_UNAVAILABLE"))

        target_rf = rf_by_entity.get(target)
        if target_rf:
            facts.append(target_rf)

        if target_val_fact and med_fact:
            gap_f = gap_fact(target_val_fact, med_fact)
            if gap_f:
                facts.append(gap_f)
            rtm_f = ratio_to_median_fact(target_val_fact, med_fact)
            if rtm_f:
                facts.append(rtm_f)

        for member in ctx.universe_members:
            obs = get_cached_obs(ctx, member, period, metric)
            rf = rf_by_entity.get(member)
            if obs is not None and obs.validation_status is QualityStatus.VALID and obs.value is not None:
                peer_table_rows.append(
                    DatasetRowDTO(
                        entity_id=member,
                        metric_id=metric,
                        period=period,
                        status="valid",
                        value=float(obs.value),
                        observation_id=obs.observation_id,
                        rank_better=rf.rank_better if rf else None,
                        rank_desc=rf.rank_desc if rf else None,
                    )
                )
            else:
                peer_table_rows.append(
                    DatasetRowDTO(
                        entity_id=member,
                        metric_id=metric,
                        period=period,
                        status="missing",
                        value=None,
                        missing_reason="DATA_UNAVAILABLE",
                    )
                )

    datasets: list[DatasetDTO] = []
    if peer_table_rows:
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-peer-position-{target.lower()}-{period.lower().replace('_', '')}",
                shape="peer_table",
                title=f"Vị thế nhóm · {target} {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="peer_position", agent="sector"),
                metric_ids=list(metrics),
                periods=[period],
                highlight_entity_ids=[target] if target else [],
                rows=peer_table_rows,
                reference_lines=reference_lines,
                allowed_charts=["rank_heatmap", "comparison_table"],
            )
        )

    # If pair exists (e.g. NPL & LLR or ROA & ROE), produce paired scatter dataset
    if len(metrics) >= 2:
        scatter_metrics = metrics[:2]
        scatter_rows = [r for r in peer_table_rows if r.metric_id in scatter_metrics]
        m1_pres = ctx.presentation(scatter_metrics[0])
        m2_pres = ctx.presentation(scatter_metrics[1])
        m1_name = m1_pres.short_label or m1_pres.label or scatter_metrics[0].rsplit('.', 1)[-1]
        m2_name = m2_pres.short_label or m2_pres.label or scatter_metrics[1].rsplit('.', 1)[-1]
        # F2: add peer_median reference_lines for both axes so frontend can render median lines
        paired_ref_lines: list[ReferenceLineDTO] = []
        for sm in scatter_metrics:
            med = next(
                (f for f in facts if f.fact_type == "peer_median" and f.metric_id == sm and f.period == period),
                None,
            )
            if med is not None and med.value is not None:
                paired_ref_lines.append(
                    ReferenceLineDTO(
                        kind="median",
                        metric_id=sm,
                        period=period,
                        value=float(med.value),
                        fact_id=med.fact_id,
                    )
                )
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-paired-{target.lower()}-{period.lower().replace('_', '')}",
                shape="paired",
                title=f"Tương quan {m1_name} và {m2_name} · {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="peer_position", agent="sector"),
                metric_ids=list(scatter_metrics),
                periods=[period],
                highlight_entity_ids=[target] if target else [],
                rows=scatter_rows,
                reference_lines=paired_ref_lines,
                allowed_charts=["scatter"],
            )
        )

    label = f"Vị thế so với nhóm · {target} ({len(ctx.universe_members)} ngân hàng)"
    return ToolResult(tool="peer_position", agent="sector", label=label, facts=facts, datasets=datasets, missing=missing)


def run_ranking_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute ranking tool: universe ranking on metric with context."""
    metric = params.get("metric") or ""
    period = params.get("period") or ""
    context_metrics = params.get("context_metrics") or []
    highlights = params.get("highlight_entity_ids") or ([params.get("highlight_entity")] if params.get("highlight_entity") else [])
    universe_id = ctx.universe_id

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    ranked_rows: list[DatasetRowDTO] = []
    reference_lines: list[ReferenceLineDTO] = []

    if not universe_id or len(ctx.universe_members) < 2:
        pres = ctx.presentation(metric)
        missing.append(MissingCell(entity_id="", period=period, metric_id=metric, reason="UNIVERSE_UNAVAILABLE"))
        label = f"Xếp hạng {pres.label} (không có universe)"
        return ToolResult(tool="ranking", agent="sector", label=label, facts=[], datasets=[], missing=missing)

    # 1. Primary metric
    _, valid_obs = _get_universe_obs(ctx, period, metric)
    pres = ctx.presentation(metric)
    rf_list = rank_facts(valid_obs, universe_id, pres.direction)
    facts.extend(rf_list)

    for obs in valid_obs:
        vf = value_fact(obs)
        if vf:
            facts.append(vf)

    med_fact = _safe_peer_median(ctx, universe_id, period, metric, valid_obs)
    if med_fact:
        facts.append(med_fact)
        if med_fact.value is not None:
            reference_lines.append(
                ReferenceLineDTO(
                    kind="median",
                    metric_id=metric,
                    period=period,
                    value=float(med_fact.value),
                    fact_id=med_fact.fact_id,
                )
            )

    sp_fact = spread_fact(valid_obs, universe_id)
    if sp_fact:
        facts.append(sp_fact)

    # Top & bottom ratio to median
    top_rf = next((rf for rf in rf_list if rf.rank_better == 1), None)
    bot_rf = next((rf for rf in rf_list if rf.rank_better == rf.denominator), None)
    for target_rf in (top_rf, bot_rf):
        if target_rf and med_fact:
            v_fact = next((f for f in facts if f.fact_type == "value" and f.entity_id == target_rf.entity_id and f.metric_id == metric), None)
            if v_fact:
                rtm = ratio_to_median_fact(v_fact, med_fact)
                if rtm:
                    facts.append(rtm)

    # Sort rf_list according to rank_desc
    rf_by_entity = {rf.entity_id: rf for rf in rf_list}
    sorted_obs = sorted(valid_obs, key=lambda x: (rf_by_entity.get(x.entity_id).rank_better or 999) if rf_by_entity.get(x.entity_id) else 999)
    for obs in sorted_obs:
        rf = rf_by_entity.get(obs.entity_id)
        ranked_rows.append(
            DatasetRowDTO(
                entity_id=obs.entity_id,
                metric_id=metric,
                period=period,
                status="valid",
                value=float(obs.value),  # type: ignore
                observation_id=obs.observation_id,
                rank_better=rf.rank_better if rf else None,
                rank_desc=rf.rank_desc if rf else None,
            )
        )

    # 2. Context metrics (rank and values of top & bottom)
    for cm in context_metrics:
        _, cm_valid = _get_universe_obs(ctx, period, cm)
        cm_pres = ctx.presentation(cm)
        cm_rfs = rank_facts(cm_valid, universe_id, cm_pres.direction)
        cm_rf_by_entity = {rf.entity_id: rf for rf in cm_rfs}
        # Record facts for extreme entities
        extreme_entities = {top_rf.entity_id if top_rf else "", bot_rf.entity_id if bot_rf else ""}
        extreme_entities.discard("")
        for ent in extreme_entities:
            rf = cm_rf_by_entity.get(ent)
            if rf:
                facts.append(rf)
            obs = get_cached_obs(ctx, ent, period, cm)
            if obs and obs.validation_status is QualityStatus.VALID and obs.value is not None:
                vf = value_fact(obs)
                if vf:
                    facts.append(vf)

    datasets: list[DatasetDTO] = []
    metric_slug = metric.rsplit(".", 1)[-1]
    datasets.append(
        DatasetDTO(
            dataset_id=f"ds-ranking-{metric_slug}-{period.lower().replace('_', '')}",
            shape="ranked_list",
            title=f"Xếp hạng {pres.label} · {_format_quarter_period(period)}",
            produced_by=ProducedByDTO(tool="ranking", agent="sector"),
            metric_ids=[metric],
            periods=[period],
            highlight_entity_ids=list(highlights) if highlights else ([top_rf.entity_id] if top_rf and top_rf.entity_id else []),
            rows=ranked_rows,
            reference_lines=reference_lines,
            allowed_charts=["ranked_bar", "comparison_table"],
        )
    )

    label = f"Xếp hạng {pres.label} · {len(ctx.universe_members)} ngân hàng"
    return ToolResult(tool="ranking", agent="sector", label=label, facts=facts, datasets=datasets, missing=missing)


def run_trend_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute trend tool: multi-period progression and benchmark trajectory."""
    target = params.get("entity") or params.get("target") or ""
    periods = params.get("periods") or []
    metrics = params.get("metrics") or []
    universe_id = ctx.universe_id

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    series_rows: list[DatasetRowDTO] = []
    reference_lines: list[ReferenceLineDTO] = []

    for metric in metrics:
        pres = ctx.presentation(metric)
        # 1. Target values
        for p in periods:
            obs = get_cached_obs(ctx, target, p, metric)
            if obs is not None and obs.validation_status is QualityStatus.VALID and obs.value is not None:
                vf = value_fact(obs)
                if vf:
                    facts.append(vf)
                series_rows.append(
                    DatasetRowDTO(
                        entity_id=target,
                        metric_id=metric,
                        period=p,
                        status="valid",
                        value=float(obs.value),
                        observation_id=obs.observation_id,
                    )
                )
            else:
                missing.append(MissingCell(entity_id=target, period=p, metric_id=metric, reason="DATA_UNAVAILABLE"))
                series_rows.append(
                    DatasetRowDTO(
                        entity_id=target,
                        metric_id=metric,
                        period=p,
                        status="missing",
                        value=None,
                        missing_reason="DATA_UNAVAILABLE",
                    )
                )

        # 2. Sequential deltas for target
        for i in range(len(periods) - 1):
            p_from, p_to = periods[i], periods[i + 1]
            o_from = get_cached_obs(ctx, target, p_from, metric)
            o_to = get_cached_obs(ctx, target, p_to, metric)
            d_fact = delta_fact(o_from, o_to)
            if d_fact:
                facts.append(d_fact)

        # 3. Overall delta from first valid to last valid
        valid_target_obs = [
            o for p in periods
            if (o := get_cached_obs(ctx, target, p, metric)) is not None
            and o.validation_status is QualityStatus.VALID and o.value is not None
        ]
        if len(valid_target_obs) >= 2 and valid_target_obs[0].period_id != valid_target_obs[-1].period_id:
            facts.append(delta_fact(valid_target_obs[0], valid_target_obs[-1]))

        # 4. Peer medians and median deltas
        if universe_id and len(ctx.universe_members) >= 2:
            med_facts_by_period: dict[str, Fact] = {}
            for p in periods:
                _, valid_obs = _get_universe_obs(ctx, p, metric)
                mf = _safe_peer_median(ctx, universe_id, p, metric, valid_obs)
                if mf:
                    facts.append(mf)
                    med_facts_by_period[p] = mf
                    # Target gap to median at this period
                    t_obs = get_cached_obs(ctx, target, p, metric)
                    if t_obs and t_obs.validation_status is QualityStatus.VALID and t_obs.value is not None:
                        t_vf = value_fact(t_obs)
                        gf = gap_fact(t_vf, mf)
                        if gf:
                            facts.append(gf)

            # Sequential median deltas
            for i in range(len(periods) - 1):
                p_from, p_to = periods[i], periods[i + 1]
                m_from = med_facts_by_period.get(p_from)
                m_to = med_facts_by_period.get(p_to)
                if m_from and m_to:
                    m_delta = median_delta_fact(m_from, m_to, universe_id)
                    if m_delta:
                        facts.append(m_delta)

            # Rank at anchor period
            if periods:
                anchor = periods[-1]
                _, anchor_valid = _get_universe_obs(ctx, anchor, metric)
                rf_list = rank_facts(anchor_valid, universe_id, pres.direction)
                target_rf = next((rf for rf in rf_list if rf.entity_id == target), None)
                if target_rf:
                    facts.append(target_rf)

    datasets: list[DatasetDTO] = []
    if series_rows:
        if len(metrics) == 1:
            datasets.append(
                DatasetDTO(
                    dataset_id=f"ds-trend-{target.lower()}-{metrics[0].rsplit('.', 1)[-1]}",
                    shape="series",
                    title=f"Diễn biến {ctx.presentation(metrics[0]).label} · {target}",
                    produced_by=ProducedByDTO(tool="trend", agent="company"),
                    metric_ids=list(metrics),
                    periods=list(periods),
                    highlight_entity_ids=[target] if target else [],
                    rows=series_rows,
                    reference_lines=reference_lines,
                    allowed_charts=["line_trend"],
                )
            )
        else:
            datasets.append(
                DatasetDTO(
                    dataset_id=f"ds-series-multi-{target.lower()}",
                    shape="series_multi",
                    title=f"Diễn biến các chỉ tiêu tài chính · {target}",
                    produced_by=ProducedByDTO(tool="trend", agent="company"),
                    metric_ids=list(metrics),
                    periods=list(periods),
                    highlight_entity_ids=[target] if target else [],
                    rows=series_rows,
                    reference_lines=reference_lines,
                    allowed_charts=["small_multiples"],
                )
            )

    label = f"Diễn biến tài chính {target} · {len(periods)} kỳ"
    return ToolResult(tool="trend", agent="company", label=label, facts=facts, datasets=datasets, missing=missing)


def run_head_to_head_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute head_to_head tool: direct pairwise comparison and lead counts."""
    entities = params.get("entities") or []
    if not entities and params.get("target"):
        entities = [params.get("target")] + list(params.get("peers") or [])
    period = params.get("period") or ""
    metrics = params.get("metrics") or []
    universe_id = ctx.universe_id

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    comparison_rows: list[DatasetRowDTO] = []

    # 1. Values for each entity
    for entity in entities:
        for metric in metrics:
            obs = get_cached_obs(ctx, entity, period, metric)
            if obs is not None and obs.validation_status is QualityStatus.VALID and obs.value is not None:
                vf = value_fact(obs)
                if vf:
                    facts.append(vf)
                comparison_rows.append(
                    DatasetRowDTO(
                        entity_id=entity,
                        metric_id=metric,
                        period=period,
                        status="valid",
                        value=float(obs.value),
                        observation_id=obs.observation_id,
                    )
                )
            else:
                missing.append(MissingCell(entity_id=entity, period=period, metric_id=metric, reason="DATA_UNAVAILABLE"))
                comparison_rows.append(
                    DatasetRowDTO(
                        entity_id=entity,
                        metric_id=metric,
                        period=period,
                        status="missing",
                        value=None,
                        missing_reason="DATA_UNAVAILABLE",
                    )
                )

    # 2. Pairwise comparisons across each pair
    directions = {m: ctx.presentation(m).direction for m in metrics}
    if len(entities) >= 2:
        first = entities[0]
        for other in entities[1:]:
            fwd_gaps: list[tuple[str, Fact | None]] = []
            rev_gaps: list[tuple[str, Fact | None]] = []
            for metric in metrics:
                a_obs = get_cached_obs(ctx, first, period, metric)
                b_obs = get_cached_obs(ctx, other, period, metric)
                pg_fwd = pairwise_gap_fact(a_obs, b_obs)
                if pg_fwd:
                    facts.append(pg_fwd)
                fwd_gaps.append((metric, pg_fwd))
                pg_rev = pairwise_gap_fact(b_obs, a_obs)
                if pg_rev:
                    facts.append(pg_rev)
                rev_gaps.append((metric, pg_rev))

            # Lead count in BOTH directions
            facts.append(lead_count_fact(first, other, fwd_gaps, directions, flat_pp=0.0, period=period))
            facts.append(lead_count_fact(other, first, rev_gaps, directions, flat_pp=0.0, period=period))

    # 3. Median if universe available
    if universe_id and len(ctx.universe_members) >= 2:
        for metric in metrics:
            _, valid_obs = _get_universe_obs(ctx, period, metric)
            mf = _safe_peer_median(ctx, universe_id, period, metric, valid_obs)
            if mf:
                facts.append(mf)

    datasets: list[DatasetDTO] = []
    if comparison_rows:
        slug = "-".join(e.lower() for e in entities[:2])
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-h2h-{slug}-{period.lower().replace('_', '')}",
                shape="comparison_table",
                title=f"So sánh đối đầu · {' vs '.join(entities)} ({_format_quarter_period(period)})",
                produced_by=ProducedByDTO(tool="head_to_head", agent="company"),
                metric_ids=list(metrics),
                periods=[period],
                highlight_entity_ids=[entities[0]] if entities else [],
                rows=comparison_rows,
                allowed_charts=["comparison_table", "grouped_bar"],
            )
        )

    label = f"So sánh đối đầu · {' vs '.join(entities)}"
    return ToolResult(tool="head_to_head", agent="company", label=label, facts=facts, datasets=datasets, missing=missing)


def run_decomposition_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute decomposition tool: Du Pont derived profitability ratios."""
    entities = params.get("entities") or ([params.get("entity")] if params.get("entity") else [])
    period = params.get("period") or ""
    formula_id = params.get("formula") or "derived.roe_over_roa"
    formula_version = "roe-over-roa-v1"

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    rows: list[DatasetRowDTO] = []

    for entity in entities:
        if not entity:
            continue
        num_obs = get_cached_obs(ctx, entity, period, "bank.roe")
        den_obs = get_cached_obs(ctx, entity, period, "bank.roa")
        dr = derived_ratio_fact(num_obs, den_obs, formula_id, formula_version)
        if dr:
            facts.append(dr)
            rows.append(
                DatasetRowDTO(
                    entity_id=entity,
                    metric_id=formula_id,
                    period=period,
                    status="valid",
                    value=dr.value,
                )
            )
        else:
            missing.append(MissingCell(entity_id=entity, period=period, metric_id=formula_id, reason="DATA_UNAVAILABLE"))
            rows.append(
                DatasetRowDTO(
                    entity_id=entity,
                    metric_id=formula_id,
                    period=period,
                    status="missing",
                    value=None,
                    missing_reason="DATA_UNAVAILABLE",
                )
            )

    reference_lines: list[ReferenceLineDTO] = []
    if ctx.universe_id and len(ctx.universe_members) >= 2:
        universe_id = ctx.universe_id
        all_ratios: list[Fact] = []
        for member in ctx.universe_members:
            dr = next((f for f in facts if f.entity_id == member and f.fact_type == "derived_ratio"), None)
            if dr is None:
                m_num = get_cached_obs(ctx, member, period, "bank.roe")
                m_den = get_cached_obs(ctx, member, period, "bank.roa")
                dr = derived_ratio_fact(m_num, m_den, formula_id, formula_version)
            if dr and dr.value is not None:
                all_ratios.append(dr)
        if all_ratios:
            sorted_vals = sorted(r.value for r in all_ratios)  # type: ignore
            n = len(sorted_vals)
            med_val = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
            all_input_obs: list[str] = []
            for r in all_ratios:
                all_input_obs.extend(r.input_observation_ids)
            med_fact = Fact(
                fact_id=f"fact:peer_median:{universe_id}:{period}:{formula_id}",
                fact_type="peer_median",
                universe_id=universe_id,
                metric_id=formula_id,
                period=period,
                value=float(med_val),
                unit="x",
                denominator=len(all_ratios),
                formula_version=FORMULA["peer_median"],
                input_observation_ids=list(dict.fromkeys(all_input_obs)),
                input_fact_ids=[r.fact_id for r in all_ratios],
            )
            facts.append(med_fact)
            reference_lines.append(
                ReferenceLineDTO(
                    kind="median",
                    metric_id=formula_id,
                    period=period,
                    value=float(med_val),
                    fact_id=med_fact.fact_id,
                )
            )

    datasets: list[DatasetDTO] = []
    if rows:
        ent_slug = entities[0].lower() if entities else "all"
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-decomp-{ent_slug}-{period.lower().replace('_', '')}",
                shape="kpi",
                title=f"Phân rã đòn bẩy ROE/ROA · {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="decomposition", agent="company"),
                metric_ids=[formula_id],
                periods=[period],
                highlight_entity_ids=list(entities),
                rows=rows,
                reference_lines=reference_lines,
                allowed_charts=["kpi_strip"],
            )
        )

    label = f"Phân rã ROE/ROA · {', '.join(entities)}"
    return ToolResult(tool="decomposition", agent="company", label=label, facts=facts, datasets=datasets, missing=missing)


def run_dispersion_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute dispersion tool: distribution spread and outlier detection."""
    metric = params.get("metric") or ""
    period = params.get("period") or ""
    universe_id = ctx.universe_id
    if not universe_id or len(ctx.universe_members) < 2:
        pres = ctx.presentation(metric)
        return ToolResult(
            tool="dispersion",
            agent="sector",
            label=f"Độ phân tán {pres.label} (không có universe)",
            facts=[],
            datasets=[],
            missing=[MissingCell(entity_id="", period=period, metric_id=metric, reason="UNIVERSE_UNAVAILABLE")],
        )

    facts: list[Fact] = []
    missing: list[MissingCell] = []
    rows: list[DatasetRowDTO] = []

    _, valid_obs = _get_universe_obs(ctx, period, metric)
    med_f = _safe_peer_median(ctx, universe_id, period, metric, valid_obs)
    if med_f:
        facts.append(med_f)
    sp_f = spread_fact(valid_obs, universe_id)
    if sp_f:
        facts.append(sp_f)

    pres = ctx.presentation(metric)
    rf_list = rank_facts(valid_obs, universe_id, pres.direction)
    facts.extend(rf_list)

    for obs in valid_obs:
        vf = value_fact(obs)
        if vf:
            facts.append(vf)
        rows.append(
            DatasetRowDTO(
                entity_id=obs.entity_id,
                metric_id=metric,
                period=period,
                status="valid",
                value=float(obs.value),  # type: ignore
                observation_id=obs.observation_id,
            )
        )

    datasets: list[DatasetDTO] = []
    if rows:
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-dispersion-{metric.rsplit('.', 1)[-1]}-{period.lower().replace('_', '')}",
                shape="ranked_list",
                title=f"Độ phân tán {pres.label} · {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="dispersion", agent="sector"),
                metric_ids=[metric],
                periods=[period],
                rows=rows,
                allowed_charts=["ranked_bar", "comparison_table"],
            )
        )

    label = f"Độ phân tán {pres.label} · {_format_quarter_period(period)}"
    return ToolResult(tool="dispersion", agent="sector", label=label, facts=facts, datasets=datasets, missing=missing)


def run_relationship_tool(ctx: ToolContext, params: dict[str, Any]) -> ToolResult:
    """Execute relationship tool: paired correlation scatter."""
    metrics = params.get("metrics") or []
    period = params.get("period") or ""
    universe_id = ctx.universe_id
    facts: list[Fact] = []
    missing: list[MissingCell] = []
    rows: list[DatasetRowDTO] = []

    for m in metrics:
        _, valid_obs = _get_universe_obs(ctx, period, m)
        pres = ctx.presentation(m)
        if universe_id and len(ctx.universe_members) >= 2:
            rf_list = rank_facts(valid_obs, universe_id, pres.direction)
            facts.extend(rf_list)
        for obs in valid_obs:
            vf = value_fact(obs)
            if vf:
                facts.append(vf)
            rows.append(
                DatasetRowDTO(
                    entity_id=obs.entity_id,
                    metric_id=m,
                    period=period,
                    status="valid",
                    value=float(obs.value),  # type: ignore
                    observation_id=obs.observation_id,
                )
            )

    datasets: list[DatasetDTO] = []
    if rows:
        datasets.append(
            DatasetDTO(
                dataset_id=f"ds-relationship-{period.lower().replace('_', '')}",
                shape="paired",
                title=f"Mối tương quan chỉ tiêu · {_format_quarter_period(period)}",
                produced_by=ProducedByDTO(tool="relationship", agent="sector"),
                metric_ids=list(metrics),
                periods=[period],
                rows=rows,
                allowed_charts=["scatter"],
            )
        )

    label = f"Tương quan chỉ tiêu · {_format_quarter_period(period)}"
    return ToolResult(tool="relationship", agent="sector", label=label, facts=facts, datasets=datasets, missing=missing)


TOOLS: dict[str, Callable[[ToolContext, dict[str, Any]], ToolResult]] = {
    "lookup": run_lookup_tool,
    "peer_position": run_peer_position_tool,
    "ranking": run_ranking_tool,
    "trend": run_trend_tool,
    "head_to_head": run_head_to_head_tool,
    "decomposition": run_decomposition_tool,
    "dispersion": run_dispersion_tool,
    "relationship": run_relationship_tool,
}


def verify_fact_inputs(
    provider: Any,
    dataset_ref: Any,
    facts: Sequence[Fact],
) -> tuple[list[Fact], list[Fact], list[str]]:
    """Verify observation inputs and cascade invalidations for dependent facts."""
    valid_facts: list[Fact] = []
    dropped_facts: list[Fact] = []
    dropped_fact_ids: set[str] = set()
    limitations: list[str] = []

    # First pass: check direct input observation IDs
    for f in facts:
        is_valid = True
        for obs_id in f.input_observation_ids:
            try:
                obs = None
                if hasattr(provider, "resolve_observation"):
                    obs = provider.resolve_observation(dataset_ref, obs_id)
                elif hasattr(provider, "get_observation"):
                    obs = provider.get_observation(dataset_ref, obs_id)

                if obs is not None:
                    if obs.validation_status is not QualityStatus.VALID or obs.value is None:
                        is_valid = False
                        break
                    if f.fact_type == "value":
                        if f.entity_id and obs.entity_id != f.entity_id:
                            is_valid = False
                            break
                        if f.period and obs.period_id != f.period:
                            is_valid = False
                            break
                        if f.metric_id and obs.metric_id != f.metric_id:
                            is_valid = False
                            break
                elif hasattr(provider, "resolve_observation") or hasattr(provider, "get_observation"):
                    is_valid = False
                    break
            except Exception:
                is_valid = False
                break
        if is_valid:
            valid_facts.append(f)
        else:
            dropped_facts.append(f)
            dropped_fact_ids.add(f.fact_id)
            limitations.append(f"Loại bỏ dữ liệu {f.fact_id} do thiếu dữ liệu gốc kiểm định.")

    # Second pass: cascade drop any facts whose input_fact_ids include dropped facts
    changed = True
    while changed:
        changed = False
        remaining: list[Fact] = []
        for f in valid_facts:
            if any(dep_id in dropped_fact_ids for dep_id in f.input_fact_ids):
                dropped_facts.append(f)
                dropped_fact_ids.add(f.fact_id)
                limitations.append(f"Loại bỏ dữ liệu dẫn xuất {f.fact_id} do phụ thuộc fact bị loại.")
                changed = True
            else:
                remaining.append(f)
        valid_facts = remaining

    return valid_facts, dropped_facts, limitations


def build_source_notes(
    provider: Any,
    dataset_ref: Any,
    facts: Sequence[Fact],
) -> list[SourceNoteDTO]:
    """Aggregate primary source notes from verified facts."""
    obs_to_facts: dict[str, list[str]] = {}
    for f in facts:
        for obs_id in f.input_observation_ids:
            obs_to_facts.setdefault(obs_id, []).append(f.fact_id)

    source_notes: list[SourceNoteDTO] = []
    note_no = 1
    seen_sources: set[str] = set()

    for obs_id, f_ids in obs_to_facts.items():
        try:
            obs = (
                provider.resolve_observation(dataset_ref, obs_id)
                if hasattr(provider, "resolve_observation")
                else (provider.get_observation(dataset_ref, obs_id) if hasattr(provider, "get_observation") else None)
            )
            if obs is None:
                continue
            src_ref = obs.source_ref
            # F1: when source_ref is None, derive source_id from obs_id convention:
            # obs_id = "<source_id>:<period>:<metric_id>:<variant>"
            if not src_ref:
                src_ref = obs_id.split(":")[0]
            if src_ref in seen_sources:
                continue
            src = provider.get_source(dataset_ref, src_ref) if hasattr(provider, "get_source") else None
            # Even if get_source fails, produce a minimal note so source_notes is non-empty
            seen_sources.add(src_ref)

            raw_locator = getattr(obs, "source_locator", None) or (obs.metadata or {}).get("source_locator") or ""
            locator = humanize_locator(raw_locator)

            # Title formatted per D-073 and PR-3 §2
            entity = obs.entity_id
            period_id = obs.period_id
            p_parts = period_id.split("_")
            q_str = p_parts[1].replace("Q", "") if len(p_parts) == 2 else ""
            y_str = p_parts[0] if len(p_parts) == 2 else period_id
            scope = getattr(obs, "reporting_scope", None)
            scope_vi = "hợp nhất" if scope == "consolidated" else ("riêng lẻ" if scope == "parent_only" else "")
            if scope_vi:
                title = f"{entity} · BCTC {scope_vi} Q{q_str}/{y_str}"
            else:
                title = f"{entity} · BCTC Q{q_str}/{y_str}"

            if src is not None:
                source_id_val = src.source_id if hasattr(src, "source_id") else src_ref
                url_val = getattr(src, "source_url", None)
            else:
                source_id_val = src_ref
                url_val = None

            source_notes.append(
                SourceNoteDTO(
                    note_no=note_no,
                    source_id=source_id_val,
                    title=title,
                    url=url_val,
                    locator=locator or None,
                    fact_ids=list(dict.fromkeys(f_ids)),
                )
            )
            note_no += 1
        except Exception:
            continue

    return source_notes
