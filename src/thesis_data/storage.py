"""Versioned SQLite storage and fail-closed gold-snapshot promotion."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .schema import CoverageSummary, GoldConfig, GoldPromotionResult


_GOLD_SCHEMA = """
CREATE TABLE snapshot_metadata (
    snapshot_id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL
);
CREATE TABLE coverage_summary (
    summary_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    expected_count INTEGER NOT NULL,
    candidate_count INTEGER NOT NULL,
    valid_count INTEGER NOT NULL,
    missing_count INTEGER NOT NULL,
    coverage_ratio REAL NOT NULL
);
CREATE TABLE source_records (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    local_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    publisher TEXT NOT NULL,
    license_note TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    notes TEXT
);
CREATE TABLE metric_observations (
    observation_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    sector TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    unit TEXT,
    period TEXT NOT NULL,
    as_of_date TEXT,
    period_basis TEXT,
    source_id TEXT,
    source_locator TEXT,
    quality_status TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);
CREATE TABLE derived_metrics (
    derived_id TEXT PRIMARY KEY,
    ticker TEXT,
    sector TEXT,
    metric TEXT NOT NULL,
    value REAL,
    unit TEXT NOT NULL,
    period TEXT NOT NULL,
    period_basis TEXT NOT NULL,
    input_observation_ids_json TEXT NOT NULL,
    formula_version TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    reason TEXT
);
CREATE TABLE macro_observations (
    observation_id TEXT PRIMARY KEY,
    indicator TEXT NOT NULL,
    value REAL,
    unit TEXT NOT NULL,
    period TEXT NOT NULL,
    source_id TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);
-- Legacy macro_observations remains unchanged for compatibility.  New
-- acceptance-aware macro data is stored in this explicitly versioned table;
-- legacy rows are never silently promoted or reinterpreted as V2.
CREATE TABLE macro_observations_v2 (
    observation_id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    value REAL,
    unit TEXT,
    period TEXT NOT NULL,
    source_id TEXT,
    quality_status TEXT NOT NULL,
    reason TEXT,
    source_series_id TEXT,
    indicator_definition_version TEXT NOT NULL,
    frequency TEXT NOT NULL,
    observation_date TEXT,
    effective_from TEXT,
    as_of_date TEXT,
    period_basis TEXT NOT NULL,
    alignment_method TEXT,
    source_locator TEXT,
    transformation_version TEXT,
    input_observation_ids_json TEXT NOT NULL,
    adjudication_ref TEXT,
    review_check_ids_json TEXT NOT NULL,
    UNIQUE(indicator_id, period),
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);
CREATE TABLE macro_evidence_snippets (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    indicator_id TEXT NOT NULL,
    period TEXT NOT NULL,
    source_document TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    quote TEXT NOT NULL,
    as_of_date TEXT,
    effective_from TEXT,
    parser_status TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);
CREATE TABLE evidence_snippets (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_document TEXT NOT NULL,
    page_number INTEGER,
    section_name TEXT,
    period TEXT,
    ticker TEXT,
    quote TEXT NOT NULL,
    retrieval_score REAL,
    parser_status TEXT NOT NULL,
    is_paginated INTEGER NOT NULL,
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);
CREATE TABLE gold_labels (
    label_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    label_type TEXT NOT NULL,
    expected_value REAL,
    expected_judgment TEXT,
    checker_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    source_locator TEXT,
    resolution_note TEXT NOT NULL
);
CREATE TABLE evaluation_questions (
    question_id TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    version TEXT NOT NULL
);
"""


def create_gold_snapshot_schema(db_path: Path) -> None:
    """Create an empty gold schema at a new path without overwriting files."""
    if db_path.exists():
        raise FileExistsError(f"refusing to overwrite existing database: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(_GOLD_SCHEMA)
        connection.commit()
    finally:
        connection.close()


def create_gold_snapshot(
    staging_db: Path,
    output_db: Path,
    config: GoldConfig,
) -> GoldPromotionResult:
    """Promote a validated staging database, failing closed until ready."""
    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite existing database: {output_db}")

    blockers: list[str] = []
    coverage_summaries: list[CoverageSummary] = []
    connection = sqlite3.connect(f"file:{staging_db.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "source_records" not in tables:
            blockers.append("missing_source_records")
        else:
            valid_sources = connection.execute(
                "SELECT COUNT(*) FROM source_records WHERE quality_status = 'valid'"
            ).fetchone()[0]
            if valid_sources == 0:
                blockers.append("sources_not_accepted")

        for table in ("metric_observations", "gold_labels"):
            if table not in tables:
                blockers.append(f"missing_{table}")

        if len(config.tickers) == 0:
            blockers.append("empty_ticker_scope")
        if len(config.periods) == 0:
            blockers.append("empty_period_scope")

        if not blockers:
            placeholders_ticker = ",".join("?" for _ in config.tickers)
            placeholders_period = ",".join("?" for _ in config.periods)
            placeholders_metric = ",".join("?" for _ in config.required_metrics)
            scope_parameters = (
                *config.tickers,
                *config.periods,
                *config.required_metrics,
            )
            expected_cells = (
                len(config.tickers) * len(config.periods) * len(config.required_metrics)
            )
            valid_cells = connection.execute(
                f"""
                SELECT COUNT(DISTINCT ticker || '|' || period || '|' || metric)
                FROM metric_observations
                WHERE ticker IN ({placeholders_ticker})
                  AND period IN ({placeholders_period})
                  AND metric IN ({placeholders_metric})
                  AND quality_status = 'valid'
                  AND value IS NOT NULL
                """,
                scope_parameters,
            ).fetchone()[0]
            coverage = valid_cells / expected_cells if expected_cells else 0.0
            if coverage < config.min_metric_coverage:
                blockers.append("insufficient_metric_coverage")

            covered_cells = connection.execute(
                f"""
                SELECT COUNT(DISTINCT ticker || '|' || period || '|' || metric)
                FROM metric_observations
                WHERE ticker IN ({placeholders_ticker})
                  AND period IN ({placeholders_period})
                  AND metric IN ({placeholders_metric})
                  AND quality_status IN ('valid', 'missing')
                """,
                scope_parameters,
            ).fetchone()[0]
            if covered_cells < expected_cells:
                blockers.append("incomplete_target_cells")

            duplicate_target_cells = connection.execute(
                f"""
                SELECT COUNT(*) FROM (
                  SELECT ticker, period, metric
                  FROM metric_observations
                  WHERE ticker IN ({placeholders_ticker})
                    AND period IN ({placeholders_period})
                    AND metric IN ({placeholders_metric})
                    AND quality_status IN ('valid', 'missing')
                  GROUP BY ticker, period, metric
                  HAVING COUNT(*) > 1
                )
                """,
                scope_parameters,
            ).fetchone()[0]
            if duplicate_target_cells:
                blockers.append("duplicate_target_cells")

            invalid_valid_rows = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM metric_observations AS metric
                LEFT JOIN source_records AS source
                  ON source.source_id = metric.source_id
                WHERE metric.ticker IN ({placeholders_ticker})
                  AND metric.period IN ({placeholders_period})
                  AND metric.metric IN ({placeholders_metric})
                  AND metric.quality_status = 'valid'
                  AND (
                    metric.value IS NULL
                    OR metric.unit IS NULL
                    OR metric.unit = ''
                    OR metric.period_basis IS NULL
                    OR metric.source_locator IS NULL
                    OR source.quality_status <> 'valid'
                    OR source.source_id IS NULL
                  )
                """,
                scope_parameters,
            ).fetchone()[0]
            if invalid_valid_rows:
                blockers.append("invalid_metric_provenance")

            missing_reason_rows = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM metric_observations
                WHERE ticker IN ({placeholders_ticker})
                  AND period IN ({placeholders_period})
                  AND metric IN ({placeholders_metric})
                  AND quality_status = 'missing'
                  AND (reason IS NULL OR reason = '')
                """,
                scope_parameters,
            ).fetchone()[0]
            if missing_reason_rows:
                blockers.append("missing_metric_reasons")

            label_count = connection.execute(
                "SELECT COUNT(*) FROM gold_labels"
            ).fetchone()[0]
            if label_count < config.min_manual_labels:
                blockers.append("insufficient_manual_labels")

            checker_count = connection.execute(
                "SELECT COUNT(DISTINCT checker_id) FROM gold_labels"
            ).fetchone()[0]
            if checker_count < config.min_independent_checkers:
                blockers.append("insufficient_independent_checkers")

            value_check_pairs = {
                (ticker, metric)
                for ticker, metric in connection.execute(
                    f"""
                    SELECT DISTINCT observation.ticker, observation.metric
                    FROM gold_labels AS label
                    JOIN metric_observations AS observation
                      ON observation.observation_id = label.target_id
                    WHERE label.label_type = 'value_check'
                      AND observation.ticker IN ({placeholders_ticker})
                      AND observation.period IN ({placeholders_period})
                      AND observation.metric IN ({placeholders_metric})
                    """,
                    scope_parameters,
                ).fetchall()
            }
            expected_metric_pairs = {
                (ticker, metric)
                for ticker in config.tickers
                for metric in config.required_metrics
            }
            value_check_cells = {
                (ticker, period, metric)
                for ticker, period, metric in connection.execute(
                    f"""
                    SELECT DISTINCT observation.ticker, observation.period, observation.metric
                    FROM gold_labels AS label
                    JOIN metric_observations AS observation
                      ON observation.observation_id = label.target_id
                    WHERE label.label_type = 'value_check'
                      AND observation.ticker IN ({placeholders_ticker})
                      AND observation.period IN ({placeholders_period})
                      AND observation.metric IN ({placeholders_metric})
                    """,
                    scope_parameters,
                ).fetchall()
            }
            expected_target_cells = {
                (ticker, period, metric)
                for ticker in config.tickers
                for period in config.periods
                for metric in config.required_metrics
            }
            for ticker, period, metric in sorted(expected_target_cells - value_check_cells):
                blockers.append(
                    f"missing_value_check_for_target_cell:{ticker}:{period}:{metric}"
                )
            if not expected_metric_pairs.issubset(value_check_pairs):
                blockers.append("insufficient_metric_label_coverage")

            min_period_labels = min(2, len(config.periods))
            period_counts = {
                ticker: count
                for ticker, count in connection.execute(
                    f"""
                    SELECT observation.ticker, COUNT(DISTINCT observation.period)
                    FROM gold_labels AS label
                    JOIN metric_observations AS observation
                      ON observation.observation_id = label.target_id
                    WHERE label.label_type = 'value_check'
                      AND observation.ticker IN ({placeholders_ticker})
                      AND observation.period IN ({placeholders_period})
                      AND observation.metric IN ({placeholders_metric})
                    GROUP BY observation.ticker
                    """,
                    scope_parameters,
                ).fetchall()
            }
            if any(period_counts.get(ticker, 0) < min_period_labels for ticker in config.tickers):
                blockers.append("insufficient_period_label_coverage")

            for ticker in config.tickers:
                for metric in config.required_metrics:
                    counts = connection.execute(
                        """
                        SELECT
                          COUNT(DISTINCT CASE
                            WHEN quality_status IN ('valid', 'missing') THEN period END),
                          COUNT(DISTINCT CASE
                            WHEN quality_status = 'valid' AND value IS NOT NULL THEN period END),
                          COUNT(DISTINCT CASE
                            WHEN quality_status = 'missing' THEN period END)
                        FROM metric_observations
                        WHERE ticker = ? AND metric = ? AND period IN ({})
                        """.format(placeholders_period),
                        (ticker, metric, *config.periods),
                    ).fetchone()
                    candidate_count, valid_count, missing_count = counts
                    coverage_summaries.append(
                        CoverageSummary(
                            summary_id=f"{output_db.stem}:{ticker}:{metric}",
                            snapshot_id=output_db.stem,
                            ticker=ticker,
                            metric=metric,
                            expected_count=len(config.periods),
                            candidate_count=candidate_count,
                            valid_count=valid_count,
                            missing_count=missing_count,
                            coverage_ratio=valid_count / len(config.periods),
                        )
                    )
    finally:
        connection.close()

    if blockers:
        return GoldPromotionResult(eligible=False, blockers=blockers)

    create_gold_snapshot_schema(output_db)
    staging = sqlite3.connect(f"file:{staging_db.resolve()}?mode=ro", uri=True)
    gold = sqlite3.connect(output_db)
    try:
        gold.execute("BEGIN")
        snapshot_id = output_db.stem
        gold.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                snapshot_id,
                datetime.now(timezone.utc).isoformat(),
                "gold",
                json.dumps(config.model_dump(mode="json"), sort_keys=True),
            ),
        )
        gold.executemany(
            "INSERT INTO coverage_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    summary.summary_id,
                    summary.snapshot_id,
                    summary.ticker,
                    summary.metric,
                    summary.expected_count,
                    summary.candidate_count,
                    summary.valid_count,
                    summary.missing_count,
                    summary.coverage_ratio,
                )
                for summary in coverage_summaries
            ],
        )

        ticker_marks = ",".join("?" for _ in config.tickers)
        period_marks = ",".join("?" for _ in config.periods)
        metric_marks = ",".join("?" for _ in config.required_metrics)
        scope_params = (*config.tickers, *config.periods, *config.required_metrics)
        metric_rows = staging.execute(
            f"""
            SELECT observation_id, ticker, sector, metric, value, unit, period,
                   as_of_date, period_basis, source_id, source_locator,
                   quality_status, reason
            FROM metric_observations
            WHERE ticker IN ({ticker_marks})
              AND period IN ({period_marks})
              AND metric IN ({metric_marks})
              AND quality_status IN ('valid', 'missing')
            ORDER BY observation_id
            """,
            scope_params,
        ).fetchall()
        metric_ids = {row[0] for row in metric_rows}
        source_ids = {row[9] for row in metric_rows}

        for row in staging.execute(
            """
            SELECT source_id, source_type, source_tier, source_url, retrieved_at,
                   local_path, content_hash, publisher, license_note,
                   quality_status, notes
            FROM source_records
            WHERE quality_status = 'valid'
            ORDER BY source_id
            """
        ):
            gold.execute("INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)

        gold.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            metric_rows,
        )

        if "macro_observations" in {
            row[0]
            for row in staging.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            macro_rows = staging.execute(
                """
                SELECT observation_id, indicator, value, unit, period, source_id,
                       quality_status, reason
                FROM macro_observations
                WHERE quality_status IN ('valid', 'missing')
                ORDER BY observation_id
                """
            ).fetchall()
            gold.executemany(
                "INSERT INTO macro_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                macro_rows,
            )

        if "macro_observations_v2" in {
            row[0]
            for row in staging.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            macro_v2_rows = staging.execute(
                """
                SELECT observation_id, indicator_id, value, unit, period, source_id,
                       quality_status, reason, source_series_id,
                       indicator_definition_version, frequency, observation_date,
                       effective_from, as_of_date, period_basis, alignment_method,
                       source_locator, transformation_version,
                       input_observation_ids_json, adjudication_ref,
                       review_check_ids_json
                FROM macro_observations_v2
                WHERE quality_status IN ('valid', 'missing')
                ORDER BY observation_id
                """
            ).fetchall()
            gold.executemany(
                """
                INSERT INTO macro_observations_v2
                (observation_id, indicator_id, value, unit, period, source_id,
                 quality_status, reason, source_series_id,
                 indicator_definition_version, frequency, observation_date,
                 effective_from, as_of_date, period_basis, alignment_method,
                 source_locator, transformation_version,
                 input_observation_ids_json, adjudication_ref,
                 review_check_ids_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                macro_v2_rows,
            )

        if "macro_evidence_snippets" in {
            row[0]
            for row in staging.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            macro_evidence_rows = staging.execute(
                """
                SELECT evidence_id, source_id, indicator_id, period,
                       source_document, source_locator, quote, as_of_date,
                       effective_from, parser_status
                FROM macro_evidence_snippets
                ORDER BY evidence_id
                """
            ).fetchall()
            gold.executemany(
                """
                INSERT INTO macro_evidence_snippets
                (evidence_id, source_id, indicator_id, period, source_document,
                 source_locator, quote, as_of_date, effective_from, parser_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                macro_evidence_rows,
            )

        if "derived_metrics" in {row[0] for row in staging.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            derived_rows = staging.execute(
                f"""
                SELECT derived_id, ticker, sector, metric, value, unit, period,
                       period_basis, input_observation_ids_json, formula_version,
                       quality_status, reason
                FROM derived_metrics
                WHERE (ticker IN ({ticker_marks}) OR ticker IS NULL)
                  AND period IN ({period_marks})
                  AND quality_status IN ('valid', 'missing')
                ORDER BY derived_id
                """,
                (*config.tickers, *config.periods),
            ).fetchall()
            gold.executemany(
                "INSERT INTO derived_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                derived_rows,
            )

        source_marks = ",".join("?" for _ in source_ids)
        if source_ids and "evidence_snippets" in {row[0] for row in staging.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            evidence_rows = staging.execute(
                f"""
                SELECT evidence_id, source_id, source_document, page_number,
                       section_name, period, ticker, quote, retrieval_score,
                       parser_status, is_paginated
                FROM evidence_snippets
                WHERE source_id IN ({source_marks})
                ORDER BY evidence_id
                """,
                tuple(source_ids),
            ).fetchall()
            gold.executemany(
                "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                evidence_rows,
            )

        label_target_ids = set(metric_ids)
        if source_ids and "evidence_snippets" in {
            row[0]
            for row in staging.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            evidence_marks = ",".join("?" for _ in source_ids)
            evidence_ids = {
                row[0]
                for row in staging.execute(
                    f"""
                    SELECT evidence_id
                    FROM evidence_snippets
                    WHERE source_id IN ({evidence_marks})
                    """,
                    tuple(source_ids),
                ).fetchall()
            }
            label_target_ids.update(evidence_ids)

        if label_target_ids:
            label_rows = staging.execute(
                """
                SELECT label_id, target_id, label_type, expected_value,
                       expected_judgment, checker_id, checked_at, source_locator,
                       resolution_note
                FROM gold_labels
                WHERE target_id IN ({})
                ORDER BY label_id
                """.format(
                    ",".join("?" for _ in label_target_ids)
                ),
                tuple(label_target_ids),
            ).fetchall()
            gold.executemany(
                "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                label_rows,
            )

        if "evaluation_questions" in {row[0] for row in staging.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            question_rows = staging.execute(
                """
                SELECT question_id, question_text, question_type, version
                FROM evaluation_questions ORDER BY question_id
                """
            ).fetchall()
            gold.executemany(
                "INSERT INTO evaluation_questions VALUES (?, ?, ?, ?)",
                question_rows,
            )
        gold.commit()
    except Exception:
        gold.rollback()
        raise
    finally:
        staging.close()
        gold.close()
    return GoldPromotionResult(
        eligible=True,
        blockers=[],
        output_path=str(output_db),
        snapshot_id=output_db.stem,
    )
