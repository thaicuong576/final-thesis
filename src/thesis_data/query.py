"""Read-only query boundary exposed to later agents."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Sequence

from .metrics import calculate_peer_median
from .schema import AgentPayload, AgentStatus, EvidenceSnippet


@dataclass(frozen=True)
class EvidenceQuery:
    source_id: str | None = None
    ticker: str | None = None
    period: str | None = None
    text: str | None = None


def _connection(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)


def _base_payload(
    agent_id: str,
    status: AgentStatus,
    period: str,
    *,
    ticker: str | None = None,
    findings: list[str] | None = None,
    observation_ids: set[str] | None = None,
    source_ids: set[str] | None = None,
) -> AgentPayload:
    return AgentPayload(
        agent_id=agent_id,
        status=status,
        ticker=ticker,
        period=period,
        findings=findings or [],
        observation_ids=sorted(observation_ids or set()),
        source_ids=sorted(source_ids or set()),
    )


def _require_metric_ids(metric_ids: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(metric_ids)
    if not normalized:
        raise ValueError("metric_ids must not be empty")
    if any(not metric for metric in normalized):
        raise ValueError("metric_ids must contain non-empty identifiers")
    return normalized


def _require_indicator_ids(indicator_ids: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(indicator_ids)
    if not normalized:
        raise ValueError("indicator_ids must not be empty")
    if any(not indicator for indicator in normalized):
        raise ValueError("indicator_ids must contain non-empty identifiers")
    return normalized


def _require_tickers(tickers: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(tickers)
    if not normalized:
        raise ValueError("tickers must not be empty")
    if any(not ticker for ticker in normalized):
        raise ValueError("tickers must contain non-empty identifiers")
    return normalized


def _source_tier_filter(
    source_tiers: Sequence[str] | None,
) -> tuple[str, tuple[str, ...]]:
    if source_tiers is None:
        return "", ()
    normalized = tuple(source_tiers)
    if not normalized:
        raise ValueError("source_tiers must not be empty")
    if any(not tier for tier in normalized):
        raise ValueError("source_tiers must contain non-empty identifiers")
    return (
        " AND source.source_tier IN ({})".format(
            ",".join("?" for _ in normalized)
        ),
        normalized,
    )


def get_company_metrics(
    db: Path,
    ticker: str,
    period: str,
    metric_ids: Sequence[str],
    *,
    source_tiers: Sequence[str] | None = None,
) -> AgentPayload:
    """Return valid company metrics from a gold snapshot only."""
    metric_ids = _require_metric_ids(metric_ids)
    source_tier_clause, source_tier_parameters = _source_tier_filter(source_tiers)
    connection = _connection(db)
    try:
        rows = connection.execute(
            """
            SELECT metric.observation_id, metric.metric, metric.value, metric.unit,
                   metric.period, metric.source_id, metric.source_locator,
                   metric.quality_status
            FROM metric_observations AS metric
            JOIN source_records AS source ON source.source_id = metric.source_id
            WHERE metric.ticker = ? AND metric.period = ? AND metric.metric IN ({})
              AND metric.quality_status = 'valid'
              AND source.quality_status = 'valid'
              {}
            ORDER BY metric.metric, metric.observation_id
            """.format(",".join("?" for _ in metric_ids), source_tier_clause),
            (ticker, period, *metric_ids, *source_tier_parameters),
        ).fetchall()
    finally:
        connection.close()

    metrics: dict[str, float | None] = {metric: None for metric in metric_ids}
    units: dict[str, str] = {metric: "unknown" for metric in metric_ids}
    periods: dict[str, str] = {metric: period for metric in metric_ids}
    observation_ids: set[str] = set()
    source_ids: set[str] = set()
    findings: list[str] = []
    for observation_id, metric, value, unit, row_period, source_id, locator, _status in rows:
        if metrics[metric] is not None:
            continue
        observation_ids.add(observation_id)
        metrics[metric] = float(value) if value is not None else None
        units[metric] = unit
        periods[metric] = row_period
        source_ids.add(source_id)
        if locator is None:
            findings.append(f"missing_locator:{metric}")

    missing = [metric for metric, value in metrics.items() if value is None]
    if missing:
        findings.extend(f"missing_or_unaccepted:{metric}" for metric in missing)
    status = AgentStatus.SUCCESS if not missing else AgentStatus.PARTIAL
    payload = _base_payload(
        "company",
        status,
        period,
        ticker=ticker,
        findings=findings,
        observation_ids=observation_ids,
        source_ids=source_ids,
    )
    return payload.model_copy(
        update={
            "metrics": metrics,
            "metric_units": units,
            "metric_periods": periods,
        }
    )


def get_sector_benchmarks(
    db: Path,
    sector: str,
    period: str,
    metric_ids: Sequence[str],
    *,
    tickers: Sequence[str] | None = None,
    source_tiers: Sequence[str] | None = None,
) -> AgentPayload:
    """Calculate peer medians from valid observations in one period.

    When ``tickers`` is supplied, only that frozen peer set participates in the
    benchmark. Omitting it preserves exploratory all-sector query behavior;
    experiment runtime supplies an explicit set.
    """
    metric_ids = _require_metric_ids(metric_ids)
    normalized_tickers = (
        _require_tickers(tickers) if tickers is not None else None
    )
    source_tier_clause, source_tier_parameters = _source_tier_filter(source_tiers)
    connection = _connection(db)
    try:
        ticker_clause = ""
        ticker_parameters: tuple[str, ...] = ()
        if normalized_tickers is not None:
            ticker_clause = " AND ticker IN ({})".format(
                ",".join("?" for _ in normalized_tickers)
            )
            ticker_parameters = normalized_tickers
        rows = connection.execute(
            """
            SELECT metric.observation_id, metric.metric, metric.value,
                   metric.unit, metric.source_id
            FROM metric_observations AS metric
            JOIN source_records AS source ON source.source_id = metric.source_id
            WHERE metric.sector = ? AND metric.period = ? AND metric.metric IN ({})
              AND metric.quality_status = 'valid' AND metric.value IS NOT NULL
              AND source.quality_status = 'valid'
              {}
              {}
            ORDER BY metric.metric, metric.ticker, metric.observation_id
            """.format(
                ",".join("?" for _ in metric_ids),
                ticker_clause,
                source_tier_clause,
            ),
            (sector, period, *metric_ids, *ticker_parameters, *source_tier_parameters),
        ).fetchall()
    finally:
        connection.close()

    values: dict[str, list[float]] = {metric: [] for metric in metric_ids}
    units: dict[str, str] = {metric: "unknown" for metric in metric_ids}
    observation_ids: set[str] = set()
    source_ids: set[str] = set()
    for observation_id, metric, value, unit, source_id in rows:
        values[metric].append(value)
        units[metric] = unit
        observation_ids.add(observation_id)
        source_ids.add(source_id)

    benchmarks: dict[str, float | None] = {}
    findings: list[str] = []
    for metric in metric_ids:
        result = calculate_peer_median(values[metric])
        benchmarks[metric] = float(result.value) if result.value is not None else None
        if result.value is None:
            findings.append(f"missing_or_unaccepted:{metric}")
    status = AgentStatus.SUCCESS if not findings else AgentStatus.PARTIAL
    payload = _base_payload(
        "sector",
        status,
        period,
        findings=findings,
        observation_ids=observation_ids,
        source_ids=source_ids,
    )
    return payload.model_copy(
        update={
            "sector_benchmarks": benchmarks,
            "metric_units": units,
            "metric_periods": {metric: period for metric in metric_ids},
        }
    )


def get_macro_context(
    db: Path,
    period: str,
    indicator_ids: Sequence[str],
    *,
    source_tiers: Sequence[str] | None = None,
) -> AgentPayload:
    """Return accepted V2 macro observations and explicit accepted missingness.

    A database created before MacroObservationV2 may still be queried by the
    legacy company/runtime tests.  In that compatibility path this function
    reads the unchanged ``macro_observations`` table only when no V2 row exists
    for the requested cell.  Acceptance-aware macro references never use that
    fallback; they route exclusively to ``macro_observations_v2``.
    """
    indicator_ids = _require_indicator_ids(indicator_ids)
    source_tier_clause, source_tier_parameters = _source_tier_filter(source_tiers)
    connection = _connection(db)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        v2_rows = []
        if "macro_observations_v2" in tables:
            v2_rows = connection.execute(
                """
                SELECT macro.observation_id, macro.indicator_id, macro.value,
                       macro.unit, macro.period, macro.source_id,
                       macro.quality_status, macro.reason, macro.adjudication_ref,
                       source.quality_status AS source_quality_status,
                       source.source_tier
                FROM macro_observations_v2 AS macro
                LEFT JOIN source_records AS source ON source.source_id = macro.source_id
                WHERE macro.period = ? AND macro.indicator_id IN ({})
                ORDER BY macro.indicator_id, macro.observation_id
                """.format(",".join("?" for _ in indicator_ids)),
                (period, *indicator_ids),
            ).fetchall()
        v2_keys = {(row[1], row[4]) for row in v2_rows}
        rows = [
            row
            for row in v2_rows
            if (
                row[6] == "valid"
                and row[2] is not None
                and row[9] == "valid"
                and (not source_tiers or row[10] in source_tiers)
            )
            or (
                row[6] == "missing"
                and row[7] == "DATA_UNAVAILABLE"
                and bool(row[8])
            )
        ]
        legacy_indicators = tuple(
            indicator for indicator in indicator_ids if (indicator, period) not in v2_keys
        )
        if legacy_indicators and "macro_observations" in tables:
            rows.extend(
                (
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    "valid", None, None, row[6], row[7],
                )
                for row in connection.execute(
                    """
                    SELECT macro.observation_id, macro.indicator, macro.value,
                           macro.unit, macro.period, macro.source_id,
                           source.quality_status, source.source_tier
                    FROM macro_observations AS macro
                    JOIN source_records AS source ON source.source_id = macro.source_id
                    WHERE macro.period = ? AND macro.indicator IN ({})
                      AND macro.quality_status = 'valid'
                      AND source.quality_status = 'valid'
                      AND macro.value IS NOT NULL
                      {}
                    ORDER BY macro.indicator, macro.observation_id
                    """.format(
                        ",".join("?" for _ in legacy_indicators), source_tier_clause
                    ),
                    (period, *legacy_indicators, *source_tier_parameters),
                ).fetchall()
            )
    finally:
        connection.close()

    metrics: dict[str, float | None] = {indicator: None for indicator in indicator_ids}
    units: dict[str, str] = {indicator: "unknown" for indicator in indicator_ids}
    periods: dict[str, str] = {indicator: period for indicator in indicator_ids}
    observation_ids: set[str] = set()
    source_ids: set[str] = set()
    missing_reasons: dict[str, str] = {}
    quality_flags: list[str] = []
    for observation_id, indicator, value, unit, row_period, source_id, status, reason, _adjudication_ref, _source_quality, _source_tier in rows:
        if status == "missing":
            observation_ids.add(observation_id)
            units[indicator] = unit or "unknown"
            periods[indicator] = row_period
            missing_reasons[indicator] = reason or "missing"
            quality_flags.append(f"accepted_missing:{indicator}:{reason or 'missing'}")
            continue
        metrics[indicator] = float(value)
        units[indicator] = unit or "unknown"
        periods[indicator] = row_period
        observation_ids.add(observation_id)
        if source_id:
            source_ids.add(source_id)

    missing = [indicator for indicator, value in metrics.items() if value is None]
    findings = [
        f"missing:{indicator}:{missing_reasons[indicator]}"
        if indicator in missing_reasons
        else f"missing_or_unaccepted:{indicator}"
        for indicator in missing
    ]
    status = AgentStatus.SUCCESS if not missing else AgentStatus.PARTIAL
    payload = _base_payload(
        "macro",
        status,
        period,
        findings=findings,
        observation_ids=observation_ids,
        source_ids=source_ids,
    )
    return payload.model_copy(
        update={
            "metrics": metrics,
            "metric_units": units,
            "metric_periods": periods,
            "quality_flags": quality_flags,
            "missing_reasons": missing_reasons,
        }
    )


def get_macro_evidence(
    db: Path,
    source_ids: Sequence[str],
    indicator_id: str,
    period: str,
    *,
    source_tiers: Sequence[str] | None = None,
) -> list[EvidenceSnippet]:
    """Return typed, ticker-less evidence for one macro indicator-period."""

    if not source_ids or not indicator_id or not period:
        return []
    source_tier_clause, source_tier_parameters = _source_tier_filter(source_tiers)
    connection = _connection(db)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "macro_evidence_snippets" not in tables:
            return []
        rows = connection.execute(
            """
            SELECT evidence.evidence_id, evidence.source_id, evidence.indicator_id,
                   evidence.period, evidence.source_document,
                   evidence.source_locator, evidence.quote, evidence.as_of_date,
                   evidence.effective_from, evidence.parser_status,
                   source.quality_status, source.source_tier
            FROM macro_evidence_snippets AS evidence
            JOIN source_records AS source ON source.source_id = evidence.source_id
            WHERE evidence.source_id IN ({})
              AND evidence.indicator_id = ?
              AND evidence.period = ?
              AND source.quality_status = 'valid'
              {}
            ORDER BY evidence.evidence_id
            """.format(
                ",".join("?" for _ in source_ids), source_tier_clause
            ),
            (*source_ids, indicator_id, period, *source_tier_parameters),
        ).fetchall()
    finally:
        connection.close()

    return [
        EvidenceSnippet(
            evidence_id=row[0],
            source_id=row[1],
            source_document=row[4],
            period=row[3],
            ticker=None,
            indicator_id=row[2],
            source_locator=row[5],
            as_of_date=row[7],
            effective_from=row[8],
            quote=row[6],
            parser_status=row[9],
            is_paginated=False,
        )
        for row in rows
    ]


def get_evidence(
    db: Path,
    source_ids: Sequence[str],
    query: EvidenceQuery,
    *,
    source_tiers: Sequence[str] | None = None,
) -> list[EvidenceSnippet]:
    """Return deterministic, page-aware evidence snippets."""
    if not source_ids:
        return []
    clauses = [f"evidence.source_id IN ({','.join('?' for _ in source_ids)})"]
    parameters: list[str] = list(source_ids)
    source_tier_clause, source_tier_parameters = _source_tier_filter(source_tiers)
    if source_tier_clause:
        clauses.append(source_tier_clause.removeprefix(" AND "))
        parameters.extend(source_tier_parameters)
    if query.ticker is not None:
        clauses.append("evidence.ticker = ?")
        parameters.append(query.ticker)
    if query.period is not None:
        clauses.append("evidence.period = ?")
        parameters.append(query.period)
    if query.text is not None:
        clauses.append("LOWER(evidence.quote) LIKE ?")
        parameters.append(f"%{query.text.lower()}%")

    connection = _connection(db)
    try:
        rows = connection.execute(
            """
            SELECT evidence.evidence_id, evidence.source_id,
                   evidence.source_document, evidence.page_number,
                   section_name, period, ticker, quote, retrieval_score,
                   parser_status, is_paginated
            FROM evidence_snippets AS evidence
            JOIN source_records AS source ON source.source_id = evidence.source_id
            WHERE source.quality_status = 'valid' AND """
            + " AND ".join(clauses)
            + " ORDER BY evidence.source_id, evidence.page_number, evidence.evidence_id",
            parameters,
        ).fetchall()
    finally:
        connection.close()

    return [
        EvidenceSnippet(
            evidence_id=row[0],
            source_id=row[1],
            source_document=row[2],
            page_number=row[3],
            section_name=row[4],
            period=row[5],
            ticker=row[6],
            quote=row[7],
            retrieval_score=row[8],
            parser_status=row[9],
            is_paginated=bool(row[10]),
        )
        for row in rows
    ]
