"""Fail-closed audit for inputs to the comparative agent experiments."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from .schema import GoldConfig


@dataclass(frozen=True)
class BaselineInputAudit:
    eligible: bool
    blockers: tuple[str, ...]
    snapshot_id: str | None
    expected_cells: int
    valid_cells: int
    covered_cells: int
    valid_source_count: int
    non_valid_source_count: int


def audit_baseline_inputs(db_path: Path, config: GoldConfig) -> BaselineInputAudit:
    """Verify that a database is a promoted, source-grounded experiment input.

    This guard deliberately permits justified missing metric cells, but never
    permits pending/estimated/conflicting observations or sources into a run.
    """
    blockers: list[str] = []
    snapshot_id: str | None = None
    expected_cells = len(config.tickers) * len(config.periods) * len(config.required_metrics)
    valid_cells = covered_cells = 0
    valid_source_count = non_valid_source_count = 0

    if not db_path.exists():
        return BaselineInputAudit(
            False,
            ("database_missing",),
            None,
            expected_cells,
            0,
            0,
            0,
            0,
        )

    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required_tables = {"snapshot_metadata", "source_records", "metric_observations", "gold_labels"}
        for table in sorted(required_tables - tables):
            blockers.append(f"missing_{table}")
        if blockers:
            return BaselineInputAudit(
                False,
                tuple(blockers),
                None,
                expected_cells,
                0,
                0,
                0,
                0,
            )

        metadata = connection.execute(
            "SELECT snapshot_id, status, config_json FROM snapshot_metadata LIMIT 1"
        ).fetchone()
        if metadata is None:
            blockers.append("missing_snapshot_metadata")
        else:
            snapshot_id, status, config_json = metadata
            if status != "gold":
                blockers.append("snapshot_not_gold")
            try:
                snapshot_config = json.loads(config_json)
            except (TypeError, json.JSONDecodeError):
                blockers.append("invalid_snapshot_config")
            else:
                for key, expected in (
                    ("tickers", list(config.tickers)),
                    ("periods", list(config.periods)),
                    ("required_metrics", list(config.required_metrics)),
                    ("min_manual_labels", config.min_manual_labels),
                    ("min_independent_checkers", config.min_independent_checkers),
                    ("min_metric_coverage", config.min_metric_coverage),
                ):
                    if snapshot_config.get(key) != expected:
                        blockers.append(f"snapshot_config_mismatch:{key}")

        valid_source_count, non_valid_source_count = connection.execute(
            """
            SELECT
              SUM(CASE WHEN quality_status = 'valid' THEN 1 ELSE 0 END),
              SUM(CASE WHEN quality_status <> 'valid' THEN 1 ELSE 0 END)
            FROM source_records
            """
        ).fetchone()
        valid_source_count = valid_source_count or 0
        non_valid_source_count = non_valid_source_count or 0
        if non_valid_source_count:
            blockers.append("non_valid_source_records")

        marks_ticker = ",".join("?" for _ in config.tickers)
        marks_period = ",".join("?" for _ in config.periods)
        marks_metric = ",".join("?" for _ in config.required_metrics)
        parameters = (*config.tickers, *config.periods, *config.required_metrics)
        valid_cells = connection.execute(
            f"""
            SELECT COUNT(DISTINCT ticker || '|' || period || '|' || metric)
            FROM metric_observations
            WHERE ticker IN ({marks_ticker}) AND period IN ({marks_period})
              AND metric IN ({marks_metric})
              AND quality_status = 'valid' AND value IS NOT NULL
            """,
            parameters,
        ).fetchone()[0]
        covered_cells = connection.execute(
            f"""
            SELECT COUNT(DISTINCT ticker || '|' || period || '|' || metric)
            FROM metric_observations
            WHERE ticker IN ({marks_ticker}) AND period IN ({marks_period})
              AND metric IN ({marks_metric})
              AND quality_status IN ('valid', 'missing')
            """,
            parameters,
        ).fetchone()[0]
        if valid_cells / expected_cells < config.min_metric_coverage:
            blockers.append("insufficient_valid_metric_coverage")
        if covered_cells < expected_cells:
            blockers.append("incomplete_target_cells")

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
                  AND observation.ticker IN ({marks_ticker})
                  AND observation.period IN ({marks_period})
                  AND observation.metric IN ({marks_metric})
                """,
                parameters,
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
                  AND observation.ticker IN ({marks_ticker})
                  AND observation.period IN ({marks_period})
                  AND observation.metric IN ({marks_metric})
                """,
                parameters,
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
                  AND observation.ticker IN ({marks_ticker})
                  AND observation.period IN ({marks_period})
                  AND observation.metric IN ({marks_metric})
                GROUP BY observation.ticker
                """,
                parameters,
            ).fetchall()
        }
        if any(period_counts.get(ticker, 0) < min_period_labels for ticker in config.tickers):
            blockers.append("insufficient_period_label_coverage")

        invalid_status_count = connection.execute(
            f"""
            SELECT COUNT(*) FROM metric_observations
            WHERE ticker IN ({marks_ticker}) AND period IN ({marks_period})
              AND metric IN ({marks_metric})
              AND quality_status NOT IN ('valid', 'missing')
            """,
            parameters,
        ).fetchone()[0]
        if invalid_status_count:
            blockers.append("non_publishable_metric_status")

        missing_reason_count = connection.execute(
            f"""
            SELECT COUNT(*) FROM metric_observations
            WHERE ticker IN ({marks_ticker}) AND period IN ({marks_period})
              AND metric IN ({marks_metric}) AND quality_status = 'missing'
              AND (reason IS NULL OR reason = '')
            """,
            parameters,
        ).fetchone()[0]
        if missing_reason_count:
            blockers.append("missing_metric_reason")

        duplicate_count = connection.execute(
            f"""
            SELECT COUNT(*) FROM (
              SELECT ticker, period, metric FROM metric_observations
              WHERE ticker IN ({marks_ticker}) AND period IN ({marks_period})
                AND metric IN ({marks_metric})
              GROUP BY ticker, period, metric HAVING COUNT(*) > 1
            )
            """,
            parameters,
        ).fetchone()[0]
        if duplicate_count:
            blockers.append("duplicate_target_cells")

        invalid_provenance_count = connection.execute(
            f"""
            SELECT COUNT(*) FROM metric_observations AS metric
            LEFT JOIN source_records AS source ON source.source_id = metric.source_id
            WHERE metric.ticker IN ({marks_ticker}) AND metric.period IN ({marks_period})
              AND metric.metric IN ({marks_metric})
              AND metric.quality_status = 'valid'
              AND (metric.value IS NULL OR metric.source_locator IS NULL
                   OR source.source_id IS NULL OR source.quality_status <> 'valid')
            """,
            parameters,
        ).fetchone()[0]
        if invalid_provenance_count:
            blockers.append("invalid_metric_provenance")
    finally:
        connection.close()

    return BaselineInputAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        snapshot_id=snapshot_id,
        expected_cells=expected_cells,
        valid_cells=valid_cells,
        covered_cells=covered_cells,
        valid_source_count=valid_source_count,
        non_valid_source_count=non_valid_source_count,
    )
