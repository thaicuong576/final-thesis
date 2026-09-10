"""Read-only progress and throughput summaries for the pilot review workflow."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from scripts.build_review_ledger import audit_review_rows


@dataclass(frozen=True)
class CheckerProgress:
    """Progress for one reviewer slot in a blind copy or merged ledger."""

    label: str
    row_count: int
    completed_count: int
    completion_rate: float
    decision_counts: dict[str, int]
    completed_by_ticker: dict[str, int]
    completed_by_metric: dict[str, int]
    first_checked_at: str | None
    last_checked_at: str | None
    elapsed_hours: float | None
    throughput_rows_per_hour: float | None
    invalid_timestamp_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "row_count": self.row_count,
            "completed_count": self.completed_count,
            "completion_rate": self.completion_rate,
            "decision_counts": self.decision_counts,
            "completed_by_ticker": self.completed_by_ticker,
            "completed_by_metric": self.completed_by_metric,
            "first_checked_at": self.first_checked_at,
            "last_checked_at": self.last_checked_at,
            "elapsed_hours": self.elapsed_hours,
            "throughput_rows_per_hour": self.throughput_rows_per_hour,
            "invalid_timestamp_count": self.invalid_timestamp_count,
        }


@dataclass(frozen=True)
class ReviewProgressReport:
    path: str
    row_count: int
    checkers: tuple[CheckerProgress, ...]
    both_checkers_completed: int
    disagreement_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "row_count": self.row_count,
            "checkers": [checker.as_dict() for checker in self.checkers],
            "both_checkers_completed": self.both_checkers_completed,
            "disagreement_count": self.disagreement_count,
        }


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("review file must contain a header")
        return list(reader), list(reader.fieldnames)


def _key(prefix: str, suffix: str) -> str:
    return f"{prefix}_{suffix}" if prefix else suffix


def _parse_checked_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _checker_progress(
    rows: Sequence[dict[str, str]],
    *,
    label: str,
    prefix: str,
) -> CheckerProgress:
    decision_counts: Counter[str] = Counter()
    tickers: Counter[str] = Counter()
    metrics: Counter[str] = Counter()
    timestamps: list[datetime] = []
    invalid_timestamp_count = 0
    completed_count = 0

    decision_field = _key(prefix, "decision")
    checked_at_field = _key(prefix, "checked_at")
    for row in rows:
        decision = row.get(decision_field, "").strip()
        if not decision:
            continue
        completed_count += 1
        decision_counts[decision] += 1
        ticker = row.get("ticker", "").strip()
        metric = row.get("metric", "").strip()
        if ticker:
            tickers[ticker] += 1
        if metric:
            metrics[metric] += 1
        checked_at = row.get(checked_at_field, "").strip()
        parsed = _parse_checked_at(checked_at)
        if parsed is None:
            if checked_at:
                invalid_timestamp_count += 1
        else:
            timestamps.append(parsed)

    first = min(timestamps) if timestamps else None
    last = max(timestamps) if timestamps else None
    elapsed_hours = None
    throughput = None
    if first is not None and last is not None:
        elapsed_seconds = (last - first).total_seconds()
        if elapsed_seconds > 0:
            elapsed_hours = elapsed_seconds / 3600.0
            throughput = completed_count / elapsed_hours

    row_count = len(rows)
    return CheckerProgress(
        label=label,
        row_count=row_count,
        completed_count=completed_count,
        completion_rate=completed_count / row_count if row_count else 0.0,
        decision_counts=dict(sorted(decision_counts.items())),
        completed_by_ticker=dict(sorted(tickers.items())),
        completed_by_metric=dict(sorted(metrics.items())),
        first_checked_at=first.isoformat() if first else None,
        last_checked_at=last.isoformat() if last else None,
        elapsed_hours=elapsed_hours,
        throughput_rows_per_hour=throughput,
        invalid_timestamp_count=invalid_timestamp_count,
    )


def summarize_review_file(path: Path) -> ReviewProgressReport:
    """Summarize a blind reviewer copy or a merged two-checker ledger.

    This function never changes the input file and deliberately reports
    incomplete work instead of treating blank cells as missing decisions.
    Throughput is left null when timestamps do not span a positive interval.
    """

    rows, fieldnames = _read_rows(path)
    is_merged = "checker_a_decision" in fieldnames and "checker_b_decision" in fieldnames
    if is_merged:
        checkers = (
            _checker_progress(rows, label="checker_a", prefix="checker_a"),
            _checker_progress(rows, label="checker_b", prefix="checker_b"),
        )
        both_completed = sum(
            bool(row.get("checker_a_decision", "").strip())
            and bool(row.get("checker_b_decision", "").strip())
            for row in rows
        )
        disagreement_count = audit_review_rows(rows).disagreement_count
    else:
        required = {"target_id", "ticker", "metric", "period", "decision"}
        if not required.issubset(fieldnames):
            raise ValueError(
                "review file must be a blind copy or merged ledger with required fields"
            )
        checkers = (_checker_progress(rows, label="checker", prefix=""),)
        both_completed = 0
        disagreement_count = 0

    return ReviewProgressReport(
        path=str(path),
        row_count=len(rows),
        checkers=checkers,
        both_checkers_completed=both_completed,
        disagreement_count=disagreement_count,
    )
