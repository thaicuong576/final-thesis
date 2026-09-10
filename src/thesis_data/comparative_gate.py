"""Fail-closed semantic preflight for cross-issuer comparative runs."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import json
from pathlib import Path
import sqlite3

from .schema import GoldConfig


@dataclass(frozen=True)
class ComparativeDefinitionAudit:
    """Result of checking the declared cross-issuer metric convention."""

    eligible: bool
    blockers: tuple[str, ...]
    snapshot_id: str | None
    checked_cells: int
    valid_cells: int
    missing_cells: int


def audit_comparative_definition_gate(
    db_path: Path,
    manifest_path: Path,
    config: GoldConfig,
) -> ComparativeDefinitionAudit:
    """Verify that valid observations use the frozen comparative convention.

    The metric database intentionally keeps raw/derived observations immutable;
    semantic decisions live in a versioned sidecar manifest with evidence
    references. Missing cells are allowed here and remain governed by the
    ordinary Gold coverage gate. A valid cell whose issuer rule is not
    comparative-compatible blocks before provider setup.
    """

    blockers: list[str] = []
    if not manifest_path.exists():
        return ComparativeDefinitionAudit(
            False, ("comparative_definition_manifest_missing",), None, 0, 0, 0
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ComparativeDefinitionAudit(
            False, ("comparative_definition_manifest_invalid",), None, 0, 0, 0
        )

    if manifest.get("schema_version") != 1:
        blockers.append("comparative_definition_manifest_schema_invalid")
    if manifest.get("working_convention") != "parent_attributable_equity":
        blockers.append("comparative_definition_convention_mismatch")
    if manifest.get("scope") != {
        "tickers": list(config.tickers),
        "periods": list(config.periods),
        "required_metrics": list(config.required_metrics),
    }:
        blockers.append("comparative_definition_scope_mismatch")

    issuer_rules = manifest.get("issuer_rules")
    if not isinstance(issuer_rules, dict):
        blockers.append("comparative_definition_issuer_rules_missing")
        issuer_rules = {}

    if not db_path.exists():
        blockers.append("database_missing")
        return ComparativeDefinitionAudit(
            False, tuple(dict.fromkeys(blockers)), None, 0, 0, 0
        )

    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "snapshot_metadata" not in tables or "metric_observations" not in tables:
            blockers.append("comparative_definition_required_tables_missing")
            return ComparativeDefinitionAudit(
                False, tuple(dict.fromkeys(blockers)), None, 0, 0, 0
            )
        metadata = connection.execute(
            "SELECT snapshot_id, status FROM snapshot_metadata ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
        snapshot_id = str(metadata[0]) if metadata else None
        if metadata is None:
            blockers.append("comparative_definition_snapshot_metadata_missing")
        elif metadata[1] != "gold":
            blockers.append("comparative_definition_snapshot_not_gold")
        if snapshot_id != manifest.get("snapshot_id"):
            blockers.append("comparative_definition_snapshot_id_mismatch")

        checked_cells = valid_cells = missing_cells = 0
        placeholders_ticker = ",".join("?" for _ in config.tickers)
        placeholders_period = ",".join("?" for _ in config.periods)
        placeholders_metric = ",".join("?" for _ in config.required_metrics)
        rows = connection.execute(
            f"""
            SELECT ticker, period, metric, value, quality_status
            FROM metric_observations
            WHERE ticker IN ({placeholders_ticker})
              AND period IN ({placeholders_period})
              AND metric IN ({placeholders_metric})
            """,
            (*config.tickers, *config.periods, *config.required_metrics),
        ).fetchall()
        cell_counts = Counter((row[0], row[1], row[2]) for row in rows)
        for cell, count in sorted(cell_counts.items()):
            if count > 1:
                blockers.append(
                    f"comparative_definition_duplicate_cell:{cell[0]}:{cell[1]}:{cell[2]}"
                )
        by_cell = {(row[0], row[1], row[2]): row for row in rows}
        for ticker in config.tickers:
            rule = issuer_rules.get(ticker)
            if not isinstance(rule, dict):
                blockers.append(f"comparative_definition_issuer_rule_missing:{ticker}")
                continue
            if not rule.get("comparative_compatible", False):
                blockers.append(
                    f"comparative_definition_incompatible:{ticker}:{rule.get('basis', 'unknown')}"
                )
            for period in config.periods:
                for metric in config.required_metrics:
                    checked_cells += 1
                    row = by_cell.get((ticker, period, metric))
                    if row is None:
                        blockers.append(f"comparative_definition_cell_missing:{ticker}:{period}:{metric}")
                        continue
                    if row[4] == "valid" and row[3] is not None:
                        valid_cells += 1
                    elif row[4] == "missing":
                        missing_cells += 1
    finally:
        connection.close()

    return ComparativeDefinitionAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        snapshot_id=snapshot_id,
        checked_cells=checked_cells,
        valid_cells=valid_cells,
        missing_cells=missing_cells,
    )
