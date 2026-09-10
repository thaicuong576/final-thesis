"""Read-only audits for staging and gold SQLite snapshots."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Sequence

from .periods import validate_period_bounds


_GOLD_TABLES = (
    "coverage_summary",
    "metric_observations",
    "derived_metrics",
    "evidence_snippets",
    "gold_labels",
    "evaluation_questions",
)

_DUPLICATE_KEYS = {
    "financial_observations": (
        "ticker",
        "statement_type",
        "period",
        "field_code",
        "source_id",
    ),
    "ratio_observations": (
        "ticker",
        "period",
        "ratio_type",
        "field_code",
        "source_id",
    ),
    "market_daily": ("ticker", "trade_date", "source_family"),
}


@dataclass(frozen=True)
class SnapshotAudit:
    """Machine-readable result of a snapshot audit."""

    snapshot_id: str
    findings: tuple[dict[str, Any], ...]
    summary: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "summary": self.summary,
            "findings": list(self.findings),
        }


def _finding(
    code: str,
    severity: str,
    message: str,
    **context: Any,
) -> dict[str, Any]:
    result = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    result.update(context)
    return result


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    }


def _duplicate_group_count(
    connection: sqlite3.Connection,
    table: str,
    columns: Iterable[str],
) -> int:
    names = tuple(columns)
    available = _column_names(connection, table)
    if any(column not in available for column in names):
        return 0
    selected = ", ".join(f'"{column}"' for column in names)
    query = (
        f'SELECT COUNT(*) FROM (SELECT {selected}, COUNT(*) AS n '
        f'FROM "{table}" GROUP BY {selected} HAVING n > 1)'
    )
    return int(connection.execute(query).fetchone()[0])


def _open_read_only(db_path: Path) -> sqlite3.Connection:
    resolved = db_path.resolve()
    return sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)


def audit_snapshot(
    db_path: Path,
    expected_tickers: Sequence[str],
    expected_periods: Sequence[str],
) -> SnapshotAudit:
    """Audit a SQLite snapshot without changing it."""
    connection = _open_read_only(db_path)
    findings: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "expected_tickers": list(expected_tickers),
        "expected_periods": list(expected_periods),
        "duplicate_groups": 0,
        "missing_tables": [],
    }

    try:
        tables = _table_names(connection)
        snapshot_id = db_path.stem
        metric_snapshot = "metric_observations" in tables and "snapshot_metadata" in tables
        summary["snapshot_kind"] = "metric_snapshot" if metric_snapshot else "legacy_staging"

        if "dataset_run" in tables:
            row = connection.execute(
                "SELECT run_id FROM dataset_run ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                snapshot_id = row[0]

        if metric_snapshot and "snapshot_metadata" in tables:
            metadata_row = connection.execute(
                "SELECT status FROM snapshot_metadata ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if metadata_row and metadata_row[0]:
                summary["snapshot_status"] = metadata_row[0]

        required_tables = (
            ("source_records", "metric_observations")
            if metric_snapshot
            else ("benchmark_periods", "source_records")
        )
        for required_table in required_tables:
            if required_table not in tables:
                summary["missing_tables"].append(required_table)
                findings.append(
                    _finding(
                        "missing_required_table",
                        "error",
                        f"Required table is absent: {required_table}",
                        table=required_table,
                    )
                )

        if "benchmark_periods" in tables and not metric_snapshot:
            rows = connection.execute(
                "SELECT period, period_start, period_end FROM benchmark_periods"
            ).fetchall()
            by_period = {row[0]: row for row in rows}
            for period in expected_periods:
                row = by_period.get(period)
                if row is None:
                    findings.append(
                        _finding(
                            "missing_period",
                            "error",
                            f"Expected benchmark period is absent: {period}",
                            period=period,
                        )
                    )
                    continue
                try:
                    expected_start, expected_end = validate_period_bounds(period)
                    actual_start = date_from_iso(row[1])
                    actual_end = date_from_iso(row[2])
                except (TypeError, ValueError):
                    findings.append(
                        _finding(
                            "invalid_period_boundary",
                            "error",
                            f"Benchmark period has an invalid date: {period}",
                            period=period,
                            period_start=row[1],
                            period_end=row[2],
                        )
                    )
                    continue
                if (actual_start, actual_end) != (expected_start, expected_end):
                    findings.append(
                        _finding(
                            "period_boundary_mismatch",
                            "error",
                            f"Benchmark period boundaries do not match calendar rules: {period}",
                            period=period,
                            expected_start=expected_start.isoformat(),
                            expected_end=expected_end.isoformat(),
                            actual_start=actual_start.isoformat(),
                            actual_end=actual_end.isoformat(),
                        )
                    )

        if "financial_observations" in tables and not metric_snapshot:
            ticker_rows = connection.execute(
                "SELECT DISTINCT ticker FROM financial_observations"
            ).fetchall()
            period_rows = connection.execute(
                "SELECT DISTINCT period FROM financial_observations"
            ).fetchall()
            actual_tickers = {row[0] for row in ticker_rows}
            actual_periods = {row[0] for row in period_rows}
            summary["financial_tickers"] = sorted(actual_tickers)
            summary["financial_periods"] = sorted(actual_periods)
            for ticker in expected_tickers:
                if ticker not in actual_tickers:
                    findings.append(
                        _finding(
                            "missing_ticker",
                            "error",
                            f"Expected ticker is absent from financial observations: {ticker}",
                            ticker=ticker,
                        )
                    )
            for period in expected_periods:
                if period not in actual_periods:
                    findings.append(
                        _finding(
                            "missing_period",
                            "error",
                            f"Expected period is absent from financial observations: {period}",
                            period=period,
                        )
                    )
        elif not metric_snapshot:
            findings.append(
                _finding(
                    "missing_required_table",
                    "error",
                    "Required table is absent: financial_observations",
                    table="financial_observations",
                )
            )
        elif "metric_observations" in tables:
            ticker_rows = connection.execute(
                "SELECT DISTINCT ticker FROM metric_observations"
            ).fetchall()
            period_rows = connection.execute(
                "SELECT DISTINCT period FROM metric_observations"
            ).fetchall()
            actual_tickers = {row[0] for row in ticker_rows}
            actual_periods = {row[0] for row in period_rows}
            summary["metric_tickers"] = sorted(actual_tickers)
            summary["metric_periods"] = sorted(actual_periods)
            summary["metric_quality_statuses"] = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT quality_status, COUNT(*) "
                    "FROM metric_observations GROUP BY quality_status"
                ).fetchall()
            }
            for ticker in expected_tickers:
                if ticker not in actual_tickers:
                    findings.append(
                        _finding(
                            "missing_ticker",
                            "error",
                            f"Expected ticker is absent from metric observations: {ticker}",
                            ticker=ticker,
                        )
                    )
            for period in expected_periods:
                if period not in actual_periods:
                    findings.append(
                        _finding(
                            "missing_period",
                            "error",
                            f"Expected period is absent from metric observations: {period}",
                            period=period,
                        )
                    )

        if "source_records" in tables:
            statuses = connection.execute(
                "SELECT quality_status, COUNT(*) FROM source_records GROUP BY quality_status"
            ).fetchall()
            status_counts = {row[0]: row[1] for row in statuses}
            summary["source_quality_statuses"] = status_counts
            if status_counts and status_counts.get("valid", 0) == 0:
                findings.append(
                    _finding(
                        "sources_not_accepted",
                        "error",
                        "No source record is accepted as valid.",
                        statuses=status_counts,
                    )
                )

        for gold_table in _GOLD_TABLES:
            if gold_table not in tables:
                summary["missing_tables"].append(gold_table)
                findings.append(
                    _finding(
                        "missing_gold_table",
                        "error",
                        f"Gold-supporting table is absent: {gold_table}",
                        table=gold_table,
                    )
                )

        duplicate_counts = {}
        for table, columns in _DUPLICATE_KEYS.items():
            if table in tables:
                count = _duplicate_group_count(connection, table, columns)
                duplicate_counts[table] = count
                summary["duplicate_groups"] += count
                if count:
                    findings.append(
                        _finding(
                            "duplicate_observation_key",
                            "error",
                            f"Duplicate observation groups found in {table}: {count}",
                            table=table,
                            count=count,
                        )
                    )
        summary["duplicate_groups_by_table"] = duplicate_counts
        summary["finding_count"] = len(findings)
        return SnapshotAudit(snapshot_id, tuple(findings), summary)
    finally:
        connection.close()


def date_from_iso(value: str):
    """Parse an ISO date while keeping the helper local to the audit module."""
    from datetime import date

    return date.fromisoformat(value)
