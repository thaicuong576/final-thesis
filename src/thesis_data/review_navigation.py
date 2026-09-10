"""Build a blind, source-only navigation index for independent review."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterable, Mapping


# Keep this schema deliberately separate from the reconciliation and candidate
# schemas. In particular, it has no value, observation_id, quote, or vendor
# fields that could anchor an independent checker.
NAVIGATION_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "navigation_status",
    "source_id",
    "source_type",
    "source_tier",
    "publisher",
    "source_url",
    "local_path",
    "source_quality_status",
    "source_locator",
    "evidence_id",
    "source_document",
    "page_number",
    "section_name",
    "evidence_period",
    "evidence_ticker",
    "parser_status",
    "evidence_status",
)

_SAFE_LOCATOR_KEYS = frozenset(
    {
        "columns",
        "html",
        "page",
        "pages",
        "pdf_page",
        "pdf_pages",
        "printed_page",
        "row",
        "section",
        "statement",
        "table",
    }
)


@dataclass(frozen=True)
class ReviewNavigationResult:
    output_path: str
    target_count: int
    row_count: int
    source_gap_count: int


def _read_register(register_path: Path) -> list[dict[str, str]]:
    with register_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"target_id", "ticker", "sector", "metric", "period"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("register must contain target identity columns")
    target_ids = [row.get("target_id", "").strip() for row in rows]
    if any(not target_id for target_id in target_ids):
        raise ValueError("register contains an empty target_id")
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("register contains duplicate target_id")
    return rows


def _connect_read_only(snapshot_db: Path) -> sqlite3.Connection:
    if not snapshot_db.exists():
        raise FileNotFoundError(snapshot_db)
    return sqlite3.connect(f"file:{snapshot_db.resolve()}?mode=ro", uri=True)


def _base_row(target: Mapping[str, str], *, status: str) -> dict[str, str]:
    return {
        "target_id": target.get("target_id", "").strip(),
        "ticker": target.get("ticker", "").strip(),
        "sector": target.get("sector", "").strip(),
        "metric": target.get("metric", "").strip(),
        "period": target.get("period", "").strip(),
        "navigation_status": status,
        "source_id": "",
        "source_type": "",
        "source_tier": "",
        "publisher": "",
        "source_url": "",
        "local_path": "",
        "source_quality_status": "",
        "source_locator": "",
        "evidence_id": "",
        "source_document": "",
        "page_number": "",
        "section_name": "",
        "evidence_period": "",
        "evidence_ticker": "",
        "parser_status": "",
        "evidence_status": "",
    }


def _blind_locator(raw_locator: str | None) -> str:
    """Keep physical navigation tokens while dropping semantic hints."""
    if not raw_locator:
        return ""
    safe_tokens: list[str] = []
    for token in raw_locator.split(";"):
        key, separator, _ = token.partition(":")
        if separator and key.strip().lower() in _SAFE_LOCATOR_KEYS:
            safe_tokens.append(token.strip())
    return ";".join(safe_tokens)


def _source_rows(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    rows = connection.execute(
        "SELECT source_id, source_type, source_tier, publisher, source_url, "
        "local_path, quality_status FROM source_records "
        "WHERE source_tier = 'primary' ORDER BY source_id"
    ).fetchall()
    return {
        row[0]: {
            "source_id": row[0],
            "source_type": row[1],
            "source_tier": row[2],
            "publisher": row[3],
            "source_url": row[4],
            "local_path": row[5],
            "source_quality_status": row[6],
        }
        for row in rows
    }


def _evidence_rows(
    connection: sqlite3.Connection,
    source_id: str,
    *,
    ticker: str,
    period: str,
) -> list[dict[str, str]]:
    rows = connection.execute(
        "SELECT evidence_id, source_document, page_number, section_name, "
        "period, ticker, parser_status FROM evidence_snippets "
        "WHERE source_id = ? ORDER BY page_number, evidence_id",
        (source_id,),
    ).fetchall()
    matching = [
        row
        for row in rows
        if (row[4] is None or row[4] == period)
        and (row[5] is None or row[5] == ticker)
    ]
    return [
        {
            "evidence_id": row[0],
            "source_document": row[1],
            "page_number": "" if row[2] is None else str(row[2]),
            "section_name": row[3] or "",
            "evidence_period": row[4] or "",
            "evidence_ticker": row[5] or "",
            "parser_status": row[6],
            "evidence_status": "matching_evidence_record",
        }
        for row in matching
    ]


def _target_source_pairs(
    connection: sqlite3.Connection,
    target: Mapping[str, str],
    source_records: Mapping[str, Mapping[str, str]],
) -> list[tuple[dict[str, str], str]]:
    rows = connection.execute(
        "SELECT DISTINCT source_id, source_locator FROM metric_observations "
        "WHERE ticker = ? AND metric = ? AND period = ? AND source_id IS NOT NULL "
        "ORDER BY source_id, source_locator",
        (target.get("ticker", ""), target.get("metric", ""), target.get("period", "")),
    ).fetchall()
    return [
        (dict(source_records[source_id]), source_locator or "")
        for source_id, source_locator in rows
        if source_id in source_records
    ]


def build_blind_source_navigation_index(
    register_path: Path,
    snapshot_db: Path,
) -> list[dict[str, str]]:
    """Return source locators for register targets without candidate context.

    Only primary-tier source records are exposed. Candidate values, observation
    IDs, candidate metadata, source notes, and evidence quotes are intentionally
    never selected from SQLite.
    """
    targets = _read_register(register_path)
    connection = _connect_read_only(snapshot_db)
    try:
        source_records = _source_rows(connection)
        rows: list[dict[str, str]] = []
        for target in targets:
            pairs = _target_source_pairs(connection, target, source_records)
            if not pairs:
                row = _base_row(target, status="source_gap")
                row["evidence_status"] = "no_primary_source_route"
                rows.append(row)
                continue

            for source, source_locator in pairs:
                evidence = _evidence_rows(
                    connection,
                    source["source_id"],
                    ticker=target.get("ticker", ""),
                    period=target.get("period", ""),
                )
                if not evidence:
                    evidence = [{"evidence_status": "no_matching_evidence_record"}]
                for evidence_row in evidence:
                    row = _base_row(target, status="source_route_available")
                    row.update(source)
                    row["source_locator"] = _blind_locator(source_locator)
                    row.update(evidence_row)
                    rows.append(row)
        return rows
    finally:
        connection.close()


def write_blind_source_navigation_index(
    rows: Iterable[Mapping[str, str]],
    output_path: Path,
) -> ReviewNavigationResult:
    """Write a navigation index without overwriting an existing artifact."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite navigation index: {output_path}")
    materialized = [dict(row) for row in rows]
    for row in materialized:
        if set(row) != set(NAVIGATION_FIELDS):
            raise ValueError("navigation row fields do not match the contract")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NAVIGATION_FIELDS)
        writer.writeheader()
        writer.writerows(materialized)
    target_ids = {row["target_id"] for row in materialized}
    source_gap_count = sum(
        1 for row in materialized if row["navigation_status"] == "source_gap"
    )
    return ReviewNavigationResult(
        output_path=str(output_path),
        target_count=len(target_ids),
        row_count=len(materialized),
        source_gap_count=source_gap_count,
    )
