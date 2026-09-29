"""Deterministic report facts and exhibits calculation.

Core pure mathematical module:
- No sqlite3, openai, or langgraph imports.
- No hard-coded issuer literals.
- No presentation-specific Vietnamese strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .dataset_contract import CanonicalObservation, QualityStatus

FORMULA: dict[str, str] = {
    "value": "fact-value-v1",
    "peer_median": "peer-median-v1",
    "peer_rank": "peer-rank-competition-v1",
    "gap_to_median": "gap-to-median-pp-v1",
    "delta": "delta-pp-v1",
    "median_delta": "median-delta-pp-v1",
    "pairwise_gap": "pairwise-gap-pp-v1",
    "spread": "spread-pp-v1",
    "ratio_to_median": "ratio-to-median-v1",
    "lead_count": "lead-count-v1",
}


@dataclass
class Fact:
    """Atomic deterministic fact computed by analysis tools."""

    fact_id: str
    fact_type: str
    entity_id: str | None = None
    other_entity_id: str | None = None
    universe_id: str | None = None
    metric_id: str = ""
    period: str = ""
    from_period: str | None = None
    value: float | None = None
    unit: str = ""
    rank_better: int | None = None
    rank_desc: int | None = None
    denominator: int | None = None
    formula_version: str = ""
    input_observation_ids: list[str] = field(default_factory=list)
    input_fact_ids: list[str] = field(default_factory=list)


@dataclass
class SignalResult:
    """Classified signal outcome for a metric dimension."""

    group: str
    label: str
    verdict: str  # 'above_peers' | 'in_line' | 'below_peers' | 'mixed' | 'insufficient_data'
    metric_ids: list[str]
    fact_ids: list[str]


@dataclass
class CrossLevelCandidate:
    """Candidate cross-level insight identified from facts and signals."""

    finding_id: str
    kind: str  # 'divergent_signals' | 'counter_trend' | 'cross_metric_extreme'
    severity: str  # 'notice' | 'warning'
    text: str
    fact_ids: list[str]
    status: str = "confirmed"
    pattern: str | None = None


def value_fact(obs: CanonicalObservation) -> Fact | None:
    """Create a point-in-time value fact from a validated observation."""
    if obs.validation_status is not QualityStatus.VALID or obs.value is None:
        return None
    fact_id = f"fact:value:{obs.entity_id}:{obs.period_id}:{obs.metric_id}"
    return Fact(
        fact_id=fact_id,
        fact_type="value",
        entity_id=obs.entity_id,
        metric_id=obs.metric_id,
        period=obs.period_id,
        value=float(obs.value),
        unit=obs.unit or "%",
        formula_version=FORMULA["value"],
        input_observation_ids=[obs.observation_id],
    )


def median_fact(
    median_obs: CanonicalObservation,
    universe_id: str,
    valid_obs_list: Sequence[CanonicalObservation] | None = None,
) -> Fact | None:
    """Create a peer median fact from an aggregated benchmark observation."""
    if median_obs.validation_status is not QualityStatus.VALID or median_obs.value is None:
        return None
    metadata = median_obs.metadata or {}
    eligible_denom = metadata.get("eligible_denominator")
    denom = int(eligible_denom if eligible_denom is not None else (len(valid_obs_list) if valid_obs_list else 0))
    if valid_obs_list:
        obs_ids = [obs.observation_id for obs in valid_obs_list]
    else:
        member_obs = metadata.get("peer_member_observations")
        if member_obs:
            obs_ids = [r["observation_id"] for r in member_obs if r.get("accepted") and r.get("observation_id")]
        else:
            obs_ids = list(metadata.get("member_observation_ids") or [])
    fact_id = f"fact:peer_median:{universe_id}:{median_obs.period_id}:{median_obs.metric_id}"
    return Fact(
        fact_id=fact_id,
        fact_type="peer_median",
        universe_id=universe_id,
        metric_id=median_obs.metric_id,
        period=median_obs.period_id,
        value=float(median_obs.value),
        unit=median_obs.unit or "%",
        denominator=denom,
        formula_version=FORMULA["peer_median"],
        input_observation_ids=obs_ids,
    )


def rank_facts(
    obs_list: Sequence[CanonicalObservation],
    universe_id: str,
    direction: str,
) -> list[Fact]:
    """Compute competition ranking facts (1-2-2-4) over valid observations."""
    valid_obs = [
        obs for obs in obs_list
        if obs.validation_status is QualityStatus.VALID and obs.value is not None
    ]
    if not valid_obs:
        return []
    denom = len(valid_obs)
    all_obs_ids = [obs.observation_id for obs in valid_obs]
    result: list[Fact] = []
    for obs in valid_obs:
        val = float(obs.value)  # type: ignore
        rank_desc = 1 + sum(1 for other in valid_obs if float(other.value) > val)  # type: ignore
        if direction == "lower_is_better":
            rank_better: int | None = 1 + sum(1 for other in valid_obs if float(other.value) < val)  # type: ignore
        elif direction == "higher_is_better":
            rank_better = rank_desc
        else:
            rank_better = None
        fact_val = float(rank_better if rank_better is not None else rank_desc)
        fact_id = f"fact:peer_rank:{obs.entity_id}:{universe_id}:{obs.period_id}:{obs.metric_id}"
        result.append(
            Fact(
                fact_id=fact_id,
                fact_type="peer_rank",
                entity_id=obs.entity_id,
                universe_id=universe_id,
                metric_id=obs.metric_id,
                period=obs.period_id,
                value=fact_val,
                unit="rank",
                rank_better=rank_better,
                rank_desc=rank_desc,
                denominator=denom,
                formula_version=FORMULA["peer_rank"],
                input_observation_ids=list(all_obs_ids),
            )
        )
    return result


def gap_fact(value: Fact | None, median: Fact | None) -> Fact | None:
    """Compute gap to peer median in percentage points."""
    if value is None or median is None or value.value is None or median.value is None:
        return None
    diff = float(value.value) - float(median.value)
    fact_id = f"fact:gap_to_median:{value.entity_id}:{median.universe_id}:{value.period}:{value.metric_id}"
    input_obs = list(dict.fromkeys(value.input_observation_ids + median.input_observation_ids))
    return Fact(
        fact_id=fact_id,
        fact_type="gap_to_median",
        entity_id=value.entity_id,
        universe_id=median.universe_id,
        metric_id=value.metric_id,
        period=value.period,
        value=diff,
        unit="pp",
        formula_version=FORMULA["gap_to_median"],
        input_observation_ids=input_obs,
        input_fact_ids=[value.fact_id, median.fact_id],
    )


def delta_fact(
    from_obs: CanonicalObservation | None,
    to_obs: CanonicalObservation | None,
) -> Fact | None:
    """Compute sequential or multi-period delta between two observations."""
    if from_obs is None or to_obs is None:
        return None
    if from_obs.validation_status is not QualityStatus.VALID or from_obs.value is None:
        return None
    if to_obs.validation_status is not QualityStatus.VALID or to_obs.value is None:
        return None
    diff = float(to_obs.value) - float(from_obs.value)
    fact_id = f"fact:delta:{to_obs.entity_id}:{from_obs.period_id}_to_{to_obs.period_id}:{to_obs.metric_id}"
    return Fact(
        fact_id=fact_id,
        fact_type="delta",
        entity_id=to_obs.entity_id,
        metric_id=to_obs.metric_id,
        period=to_obs.period_id,
        from_period=from_obs.period_id,
        value=diff,
        unit="pp",
        formula_version=FORMULA["delta"],
        input_observation_ids=[from_obs.observation_id, to_obs.observation_id],
    )


def median_delta_fact(
    m_from: CanonicalObservation | Fact | None,
    m_to: CanonicalObservation | Fact | None,
    universe_id: str | None = None,
) -> Fact | None:
    """Compute sequential delta between two peer median benchmarks."""
    if m_from is None or m_to is None or m_from.value is None or m_to.value is None:
        return None
    v_from = float(m_from.value)
    v_to = float(m_to.value)
    p_from = getattr(m_from, "period_id", getattr(m_from, "period", ""))
    p_to = getattr(m_to, "period_id", getattr(m_to, "period", ""))
    metric_id = getattr(m_to, "metric_id", "")
    univ_id = universe_id or getattr(m_to, "universe_id", "")
    diff = v_to - v_from
    obs_ids: list[str] = []
    for m in (m_from, m_to):
        if hasattr(m, "observation_id") and getattr(m, "observation_id"):
            obs_ids.append(getattr(m, "observation_id"))
        elif hasattr(m, "input_observation_ids"):
            obs_ids.extend(getattr(m, "input_observation_ids"))
    fact_id = f"fact:median_delta:{univ_id}:{p_from}_to_{p_to}:{metric_id}"
    den = getattr(m_to, "denominator", None) or getattr(m_from, "denominator", None)
    return Fact(
        fact_id=fact_id,
        fact_type="median_delta",
        universe_id=univ_id,
        metric_id=metric_id,
        period=p_to,
        from_period=p_from,
        value=diff,
        unit="pp",
        denominator=den,
        formula_version=FORMULA["median_delta"],
        input_observation_ids=list(dict.fromkeys(obs_ids)),
    )


def pairwise_gap_fact(
    a_obs: CanonicalObservation | Fact | None,
    b_obs: CanonicalObservation | Fact | None,
) -> Fact | None:
    """Compute pairwise difference between two entities for a metric."""
    if a_obs is None or b_obs is None or a_obs.value is None or b_obs.value is None:
        return None
    a_val = float(a_obs.value)
    b_val = float(b_obs.value)
    a_entity = getattr(a_obs, "entity_id", "")
    b_entity = getattr(b_obs, "entity_id", "")
    period = getattr(a_obs, "period_id", getattr(a_obs, "period", ""))
    metric_id = getattr(a_obs, "metric_id", "")
    diff = a_val - b_val
    fact_id = f"fact:pairwise_gap:{a_entity}:vs:{b_entity}:{period}:{metric_id}"
    obs_ids: list[str] = []
    fact_ids: list[str] = []
    for item in (a_obs, b_obs):
        if hasattr(item, "observation_id") and getattr(item, "observation_id"):
            obs_ids.append(getattr(item, "observation_id"))
        elif hasattr(item, "input_observation_ids"):
            obs_ids.extend(getattr(item, "input_observation_ids"))
        if hasattr(item, "fact_id") and getattr(item, "fact_id"):
            fact_ids.append(getattr(item, "fact_id"))
    return Fact(
        fact_id=fact_id,
        fact_type="pairwise_gap",
        entity_id=a_entity,
        other_entity_id=b_entity,
        metric_id=metric_id,
        period=period,
        value=diff,
        unit="pp",
        formula_version=FORMULA["pairwise_gap"],
        input_observation_ids=list(dict.fromkeys(obs_ids)),
        input_fact_ids=fact_ids,
    )


def spread_fact(
    obs_list: Sequence[CanonicalObservation],
    universe_id: str,
) -> Fact | None:
    """Compute range spread (max - min) across peer universe members."""
    valid_obs = [
        obs for obs in obs_list
        if obs.validation_status is QualityStatus.VALID and obs.value is not None
    ]
    if len(valid_obs) < 2:
        return None
    sorted_obs = sorted(valid_obs, key=lambda x: float(x.value))  # type: ignore
    min_obs = sorted_obs[0]
    max_obs = sorted_obs[-1]
    diff = float(max_obs.value) - float(min_obs.value)  # type: ignore
    period = max_obs.period_id
    metric_id = max_obs.metric_id
    fact_id = f"fact:spread:{universe_id}:{period}:{metric_id}"
    return Fact(
        fact_id=fact_id,
        fact_type="spread",
        universe_id=universe_id,
        metric_id=metric_id,
        period=period,
        value=diff,
        unit="pp",
        denominator=len(valid_obs),
        formula_version=FORMULA["spread"],
        input_observation_ids=[max_obs.observation_id, min_obs.observation_id],
    )


def ratio_to_median_fact(value: Fact | None, median: Fact | None) -> Fact | None:
    """Compute ratio of an entity's value to the peer median."""
    if value is None or median is None or value.value is None or median.value is None:
        return None
    m_val = float(median.value)
    if m_val == 0.0:
        return None
    ratio = float(value.value) / m_val
    fact_id = f"fact:ratio_to_median:{value.entity_id}:{median.universe_id}:{value.period}:{value.metric_id}"
    input_obs = list(dict.fromkeys(value.input_observation_ids + median.input_observation_ids))
    return Fact(
        fact_id=fact_id,
        fact_type="ratio_to_median",
        entity_id=value.entity_id,
        universe_id=median.universe_id,
        metric_id=value.metric_id,
        period=value.period,
        value=ratio,
        unit="x",
        formula_version=FORMULA["ratio_to_median"],
        input_observation_ids=input_obs,
        input_fact_ids=[value.fact_id, median.fact_id],
    )


def derived_ratio_fact(
    num_obs: CanonicalObservation | None,
    den_obs: CanonicalObservation | None,
    formula_id: str,
    formula_version: str,
) -> Fact | None:
    """Compute derived ratio (e.g. ROE / ROA) from two primary observations."""
    if num_obs is None or den_obs is None:
        return None
    if num_obs.validation_status is not QualityStatus.VALID or num_obs.value is None:
        return None
    if den_obs.validation_status is not QualityStatus.VALID or den_obs.value is None:
        return None
    d_val = float(den_obs.value)
    if d_val == 0.0:
        return None
    ratio = float(num_obs.value) / d_val
    period = num_obs.period_id
    entity_id = num_obs.entity_id
    fact_id = f"fact:derived_ratio:{entity_id}:{period}:{formula_id}"
    input_fact_ids = [
        f"fact:value:{entity_id}:{period}:{num_obs.metric_id}",
        f"fact:value:{entity_id}:{period}:{den_obs.metric_id}",
    ]
    return Fact(
        fact_id=fact_id,
        fact_type="derived_ratio",
        entity_id=entity_id,
        metric_id=formula_id,
        period=period,
        value=ratio,
        unit="x",
        formula_version=formula_version,
        input_observation_ids=[num_obs.observation_id, den_obs.observation_id],
        input_fact_ids=input_fact_ids,
    )


def _get_flat_pp(flat_pp: Mapping[str, float] | float, metric_id: str, default: float = 0.05) -> float:
    """Resolve flat threshold in percentage points for a given metric."""
    if isinstance(flat_pp, (int, float)):
        return float(flat_pp)
    if metric_id in flat_pp:
        return float(flat_pp[metric_id])
    short_id = metric_id.rsplit(".", 1)[-1]
    if short_id in flat_pp:
        return float(flat_pp[short_id])
    return default


def _is_consecutive_period(p_from: str, p_to: str) -> bool:
    """Check if p_to is chronologically the immediately consecutive period after p_from."""
    if "_Q" in p_from and "_Q" in p_to:
        try:
            y1, q1 = p_from.split("_Q")
            y2, q2 = p_to.split("_Q")
            return (int(y2) * 4 + int(q2)) == (int(y1) * 4 + int(q1) + 1)
        except Exception:
            pass
    if p_from.startswith("Q") and p_to.startswith("Q") and p_from[1:].isdigit() and p_to[1:].isdigit():
        try:
            return int(p_to[1:]) == int(p_from[1:]) + 1
        except Exception:
            pass
    if p_from.isdigit() and p_to.isdigit():
        try:
            return int(p_to) == int(p_from) + 1
        except Exception:
            pass
    return False


def _period_key(p: str) -> tuple[int, int]:
    """Tuple sort key for period string."""
    if "_Q" in p:
        try:
            y, q = p.split("_Q")
            return (int(y), int(q))
        except Exception:
            pass
    if p.startswith("Q") and p[1:].isdigit():
        try:
            return (0, int(p[1:]))
        except Exception:
            pass
    if p.isdigit():
        return (int(p), 0)
    return (0, 0)


def lead_count_fact(
    a: str,
    b: str,
    metric_pairs: Sequence[tuple[str, Fact | None]],
    directions: Mapping[str, str],
    flat_pp: Mapping[str, float] | float = 0.0,
    period: str = "",
) -> Fact:
    """Compute number of metrics where entity a outperforms entity b."""
    eligible_pairs = [
        (m, gap) for m, gap in metric_pairs if gap is not None and gap.value is not None
    ]
    leads = 0
    input_fact_ids: list[str] = []
    input_obs_ids: list[str] = []
    for m, gap_fact in eligible_pairs:
        input_fact_ids.append(gap_fact.fact_id)  # type: ignore
        input_obs_ids.extend(gap_fact.input_observation_ids)  # type: ignore
        gap = float(gap_fact.value)  # type: ignore
        direction = directions.get(m, "higher_is_better")
        m_flat = _get_flat_pp(flat_pp, m, default=0.0)
        if direction == "higher_is_better":
            if gap > m_flat:
                leads += 1
        elif direction == "lower_is_better":
            if -gap > m_flat:
                leads += 1
    fact_id = f"fact:lead_count:{a}:vs:{b}:{period}"
    return Fact(
        fact_id=fact_id,
        fact_type="lead_count",
        entity_id=a,
        other_entity_id=b,
        metric_id="comparison.overall",
        period=period,
        value=float(leads),
        unit="count",
        denominator=len(eligible_pairs),
        formula_version=FORMULA["lead_count"],
        input_observation_ids=list(dict.fromkeys(input_obs_ids)),
        input_fact_ids=input_fact_ids,
    )


def classify_signals(
    target: str,
    facts: Sequence[Fact],
    metric_groups: Mapping[str, Sequence[str]],
    directions: Mapping[str, str],
    flat_pp: Mapping[str, float] | float = 0.05,
    group_labels: Mapping[str, str] | None = None,
) -> list[SignalResult]:
    """Classify target entity standing across financial dimensions."""
    gaps_by_metric: dict[str, Fact] = {}
    ranks_by_metric: dict[str, Fact] = {}
    for f in facts:
        if f.entity_id == target:
            if f.fact_type == "gap_to_median":
                gaps_by_metric[f.metric_id] = f
            elif f.fact_type == "peer_rank":
                ranks_by_metric[f.metric_id] = f

    results: list[SignalResult] = []
    labels = group_labels or {}
    for group, metrics in metric_groups.items():
        better_count = 0
        worse_count = 0
        in_line_count = 0
        insufficient_count = 0
        fact_ids: list[str] = []
        evaluated_metrics: list[str] = []

        for m in metrics:
            evaluated_metrics.append(m)
            gap = gaps_by_metric.get(m)
            rank = ranks_by_metric.get(m)
            if gap is not None:
                fact_ids.append(gap.fact_id)
            if rank is not None:
                fact_ids.append(rank.fact_id)

            if gap is None or gap.value is None:
                insufficient_count += 1
                continue

            gap_val = float(gap.value)
            direction = directions.get(m, "higher_is_better")
            if direction == "lower_is_better":
                adj_gap = -gap_val
            elif direction == "higher_is_better":
                adj_gap = gap_val
            else:
                adj_gap = 0.0

            m_flat = _get_flat_pp(flat_pp, m, default=0.05)
            if adj_gap > m_flat:
                better_count += 1
            elif adj_gap < -m_flat:
                worse_count += 1
            else:
                in_line_count += 1

        total = len(metrics)
        if total == 0 or insufficient_count == total:
            verdict = "insufficient_data"
        elif better_count >= 1 and worse_count == 0:
            verdict = "above_peers"
        elif worse_count >= 1 and better_count == 0:
            verdict = "below_peers"
        elif better_count >= 1 and worse_count >= 1:
            verdict = "mixed"
        else:
            verdict = "in_line"

        results.append(
            SignalResult(
                group=group,
                label=labels.get(group, group),
                verdict=verdict,
                metric_ids=evaluated_metrics,
                fact_ids=list(dict.fromkeys(fact_ids)),
            )
        )
    return results


def detect_cross_level_candidates(
    facts: Sequence[Fact],
    signals: Sequence[SignalResult],
    flat_pp: Mapping[str, float] | float = 0.05,
    directions: Mapping[str, str] | None = None,
    metric_to_group: Mapping[str, str] | None = None,
) -> list[CrossLevelCandidate]:
    """Detect cross-level candidate tensions, trade-offs, and counter-trends."""
    candidates: list[CrossLevelCandidate] = []
    cid = 1

    # 1. Divergent signals (above_peers in one group and below_peers in another)
    above_signals = [s for s in signals if s.verdict == "above_peers"]
    below_signals = [s for s in signals if s.verdict == "below_peers"]
    if above_signals and below_signals:
        f_ids: list[str] = []
        for s in above_signals:
            f_ids.extend(s.fact_ids)
        for s in below_signals:
            f_ids.extend(s.fact_ids)
        candidates.append(
            CrossLevelCandidate(
                finding_id=f"f-divergent-{cid}",
                kind="divergent_signals",
                severity="notice",
                text="Performance signals diverge across evaluated financial dimensions.",
                fact_ids=list(dict.fromkeys(f_ids)),
                pattern="divergent",
            )
        )
        cid += 1

    # 2. Counter-trend: xét cặp kỳ liên tiếp CUỐI CÙNG có đủ delta và median_delta
    delta_facts: dict[tuple[str, str, str, str], Fact] = {}
    median_delta_facts: dict[tuple[str, str, str], Fact] = {}
    for f in facts:
        if f.fact_type == "delta" and f.from_period and f.value is not None:
            delta_facts[(f.entity_id or "", f.from_period, f.period, f.metric_id)] = f
        elif f.fact_type == "median_delta" and f.from_period and f.value is not None:
            median_delta_facts[(f.from_period, f.period, f.metric_id)] = f

    # Group valid consecutive pairs by (entity, metric)
    consecutive_pairs_by_entity_metric: dict[tuple[str, str], list[tuple[str, str, Fact, Fact]]] = {}
    for (entity, from_p, to_p, metric), d_fact in delta_facts.items():
        if not _is_consecutive_period(from_p, to_p):
            continue
        m_fact = median_delta_facts.get((from_p, to_p, metric))
        if m_fact is not None and m_fact.value is not None and d_fact.value is not None:
            consecutive_pairs_by_entity_metric.setdefault((entity, metric), []).append(
                (from_p, to_p, d_fact, m_fact)
            )

    for (entity, metric), pairs in consecutive_pairs_by_entity_metric.items():
        sorted_pairs = sorted(pairs, key=lambda item: (_period_key(item[0]), _period_key(item[1])))
        from_p, to_p, d_fact, m_fact = sorted_pairs[-1]

        d_val = float(d_fact.value)  # type: ignore
        m_val = float(m_fact.value)  # type: ignore
        threshold = _get_flat_pp(flat_pp, metric, default=0.05)

        if (d_val * m_val < 0) and abs(d_val) > threshold and abs(m_val) > threshold:
            candidates.append(
                CrossLevelCandidate(
                    finding_id=f"f-counter-trend-{cid}",
                    kind="counter_trend",
                    severity="warning",
                    text="Target entity metric trend opposes peer median trajectory.",
                    fact_ids=[d_fact.fact_id, m_fact.fact_id],
                    pattern="counter_trend",
                )
            )
            cid += 1

    # 3. Cross-metric extreme (entity occupies rank 1 or rank denominator across >= 2 metrics in different groups)
    ranks_by_entity: dict[str, list[Fact]] = {}
    for f in facts:
        if f.fact_type == "peer_rank" and f.entity_id and f.rank_better is not None and f.denominator is not None:
            if f.rank_better == 1 or f.rank_better == f.denominator:
                ranks_by_entity.setdefault(f.entity_id, []).append(f)

    m2g = metric_to_group or {}
    for entity, extreme_ranks in ranks_by_entity.items():
        groups = {m2g.get(r.metric_id, r.metric_id) for r in extreme_ranks}
        if len(groups) >= 2:
            all_top = all(r.rank_better == 1 for r in extreme_ranks)
            all_bottom = all(r.rank_better == r.denominator for r in extreme_ranks)
            pattern = "consistent" if (all_top or all_bottom) else "tradeoff"
            cand_fact_ids = list(dict.fromkeys(r.fact_id for r in extreme_ranks))
            candidates.append(
                CrossLevelCandidate(
                    finding_id=f"f-extreme-{cid}",
                    kind="cross_metric_extreme",
                    severity="notice",
                    text="Entity exhibits extreme peer rank positions across different analytical dimensions.",
                    fact_ids=cand_fact_ids,
                    pattern=pattern,
                )
            )
            cid += 1

    return candidates
