"""Export an eligible review ledger as provenance-preserving gold labels.

This module deliberately creates a JSONL label artifact rather than mutating
the candidate SQLite database. Candidate observations remain pending until a
separate, explicit promotion step updates the observation/source statuses.
"""

from __future__ import annotations

import csv
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping, Sequence

from scripts.build_review_ledger import (
    accepted_reviewer_prefix,
    audit_review_rows,
)

from .schema import GoldLabel


CandidateReference = dict[str, Any]


def _target_cell(row: Mapping[str, str]) -> str:
    return f"{row.get('ticker', '').strip()}:{row.get('period', '').strip()}:{row.get('metric', '').strip()}"


def _read_ledger(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_expected_target_ids(register_path: Path) -> set[str]:
    if not register_path.exists():
        raise FileNotFoundError(f"review register does not exist: {register_path}")
    with register_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "target_id" not in reader.fieldnames:
            raise ValueError("review register must contain a target_id column")
        target_ids = [row.get("target_id", "").strip() for row in reader]
    if not target_ids or any(not target_id for target_id in target_ids):
        raise ValueError("review register must contain non-empty target IDs")
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("review register must not contain duplicate target IDs")
    return set(target_ids)


def _accepted_value(row: Mapping[str, str], prefix: str) -> float:
    raw = row.get(f"{prefix}_value", "").strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"accepted review has non-numeric value: {prefix}") from exc


def _value_matches(candidate_value: float | None, reviewed_value: float) -> bool:
    if candidate_value is None or not math.isfinite(candidate_value):
        return False
    # Official tables are often reviewed at a displayed precision different
    # from the stored derived candidate. Allow only rounding-scale drift: a
    # broad percentage-point tolerance can collapse nearby competing variants
    # (for example, parent-equity and total-equity ROE) into one mapping.
    return math.isclose(
        float(candidate_value),
        reviewed_value,
        rel_tol=1e-6,
        abs_tol=max(0.0001, abs(reviewed_value) * 1e-6),
    )


def _split_source_references(raw: str) -> tuple[str, ...]:
    """Return source IDs/URLs from a review field that cites multiple sources.

    The review contract names a singular ``source_id`` field, but a derived
    TTM value can legitimately depend on both the quarter filing and the prior
    fiscal-year filing. Reviewers may therefore enter a pipe- or semicolon-
    separated list. This parser is intentionally limited to the two
    delimiters used by the review packet and leaves source locators untouched.
    """
    return tuple(
        part.strip()
        for part in re.split(r"\s*(?:\||;)\s*", raw.strip())
        if part.strip()
    )


def _accepted_candidate_matches(
    row: Mapping[str, str], prefix: str, candidates: Sequence[CandidateReference]
) -> list[CandidateReference]:
    reviewed_value = _accepted_value(row, prefix)
    reviewed_unit = row[f"{prefix}_unit"].strip().lower()
    reviewed_basis = row[f"{prefix}_period_basis"].strip().lower()
    reviewed_source_id = row[f"{prefix}_source_id"].strip()
    reviewed_source_ids = set(_split_source_references(reviewed_source_id))
    matches = [
        candidate
        for candidate in candidates
        if candidate["source_id"] in reviewed_source_ids
        and str(candidate["unit"]).strip().lower() == reviewed_unit
        and str(candidate["period_basis"]).strip().lower() == reviewed_basis
        and _value_matches(candidate["value"], reviewed_value)
    ]
    exact_locator = [
        candidate
        for candidate in matches
        if candidate["source_locator"] == row[f"{prefix}_source_locator"].strip()
    ]
    return exact_locator or matches


def _review_label(
    row: Mapping[str, str],
    prefix: str,
    observation_id: str,
    *,
    target_id: str,
    label_type: str = "value_check",
    decision: str | None = None,
    adjudicator: bool = False,
) -> dict[str, Any]:
    decision = decision or row[f"{prefix}_decision"].strip()
    value = _accepted_value(row, prefix) if decision == "accepted" else None
    checker_id = (
        row["adjudicator_id"].strip()
        if adjudicator
        else row[f"{prefix}_id"].strip()
    )
    checked_at = (
        row["adjudicated_at"].strip()
        if adjudicator
        else row[f"{prefix}_checked_at"].strip()
    )
    source_locator = (
        row[f"{prefix}_source_locator"].strip()
        if decision == "accepted" and not adjudicator
        else None
    )
    source_id = (
        row[f"{prefix}_source_id"].strip()
        if decision == "accepted" and not adjudicator
        else ""
    )
    source_url = (
        row[f"{prefix}_source_url"].strip()
        if decision == "accepted" and not adjudicator
        else ""
    )
    notes = (
        row["adjudication_reason"].strip()
        if adjudicator
        else row[f"{prefix}_notes"].strip()
    )
    resolution_note = (
        f"review_target_id={target_id}; decision={decision}; "
        f"source_id={source_id}; source_url={source_url}; notes={notes}"
    )
    label = GoldLabel(
        label_id=f"review:{target_id}:{observation_id}:{checker_id}:{label_type}",
        target_id=observation_id,
        label_type=label_type,
        expected_value=value,
        expected_judgment=decision,
        checker_id=checker_id,
        checked_at=datetime.fromisoformat(checked_at.replace("Z", "+00:00")),
        source_locator=source_locator,
        resolution_note=resolution_note,
    )
    return label.model_dump(mode="json")


def build_gold_label_rows(
    review_rows: Sequence[Mapping[str, str]],
    candidate_db: Path,
    expected_target_ids: set[str],
) -> list[dict[str, Any]]:
    """Convert eligible review rows to validated labels without writing files."""
    review_rows = [dict(row) for row in review_rows]
    audit = audit_review_rows(review_rows, expected_target_ids)
    if not audit.eligible:
        raise ValueError(f"review ledger is not eligible: {list(audit.blockers)}")

    if not candidate_db.exists():
        raise FileNotFoundError(f"candidate database does not exist: {candidate_db}")

    connection = sqlite3.connect(f"file:{candidate_db.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing_tables = {"metric_observations", "source_records"} - tables
        if missing_tables:
            raise ValueError(f"candidate database missing tables: {sorted(missing_tables)}")

        candidate_rows = connection.execute(
            """
            SELECT observation_id, ticker, metric, period, value, unit,
                   period_basis, source_id, source_locator
            FROM metric_observations
            ORDER BY observation_id
            """
        ).fetchall()
        candidates_by_cell: dict[str, list[CandidateReference]] = {}
        for (
            observation_id,
            ticker,
            metric,
            period,
            value,
            unit,
            period_basis,
            source_id,
            source_locator,
        ) in candidate_rows:
            cell = f"{ticker}:{period}:{metric}"
            candidates_by_cell.setdefault(cell, []).append(
                {
                    "observation_id": observation_id,
                    "value": value,
                    "unit": unit,
                    "period_basis": period_basis,
                    "source_id": source_id,
                    "source_locator": source_locator,
                }
            )
        source_urls = {
            source_id: source_url
            for source_id, source_url in connection.execute(
                "SELECT source_id, source_url FROM source_records"
            ).fetchall()
        }
    finally:
        connection.close()

    labels: list[dict[str, Any]] = []
    blockers: list[str] = []
    for row in review_rows:
        target_id = row.get("target_id", "").strip()
        computed_target_id = _target_cell(row)
        if target_id != computed_target_id:
            blockers.append(f"target_identity_mismatch:{target_id}")
            continue
        candidates = candidates_by_cell.get(target_id, [])
        if not candidates:
            blockers.append(f"missing_candidate_observation:{target_id}")
            continue

        accepted_prefix = accepted_reviewer_prefix(row)
        selected_candidates: list[CandidateReference]
        if accepted_prefix:
            selected_candidates = _accepted_candidate_matches(
                row, accepted_prefix, candidates
            )
            if len(selected_candidates) == 0:
                blockers.append(f"accepted_candidate_mapping_missing:{target_id}")
                continue
            if len(selected_candidates) != 1:
                blockers.append(f"ambiguous_candidate_observation:{target_id}")
                continue
        else:
            # A missing/conflicting/invalid judgment applies to the cell, not
            # to one silently selected variant. Preserve the label on every
            # candidate observation so later adjudication can exclude the
            # unresolved alternatives explicitly.
            selected_candidates = candidates

        for prefix in ("checker_a", "checker_b"):
            if row[f"{prefix}_decision"].strip() == "accepted":
                source_ids = _split_source_references(row[f"{prefix}_source_id"])
                source_urls_reviewed = set(
                    _split_source_references(row[f"{prefix}_source_url"])
                )
                if not source_ids:
                    blockers.append(f"accepted_source_not_in_candidate_db:{target_id}:")
                for source_id in source_ids:
                    if source_id not in source_urls:
                        blockers.append(
                            f"accepted_source_not_in_candidate_db:{target_id}:{source_id}"
                        )
                    elif source_urls[source_id] not in source_urls_reviewed:
                        blockers.append(
                            f"accepted_source_url_mismatch:{target_id}:{source_id}"
                        )
                # A label may validate a candidate against another source,
                # but the candidate's own provenance must remain visible in
                # the resolution note and never be replaced implicitly.
                if not any(candidate["source_id"] for candidate in selected_candidates):
                    blockers.append(f"candidate_missing_source:{target_id}")

        if blockers:
            continue
        for candidate in selected_candidates:
            observation_id = candidate["observation_id"]
            labels.append(
                _review_label(
                    row,
                    "checker_a",
                    observation_id,
                    target_id=target_id,
                )
            )
            labels.append(
                _review_label(
                    row,
                    "checker_b",
                    observation_id,
                    target_id=target_id,
                )
            )

            if (
                row["checker_a_decision"].strip()
                != row["checker_b_decision"].strip()
                or row["adjudication_decision"].strip()
            ):
                adjudication = row["adjudication_decision"].strip()
                if adjudication == "accepted":
                    accepted_prefix = accepted_reviewer_prefix(row)
                    if accepted_prefix is None:
                        raise ValueError(
                            f"accepted adjudication has no accepted source slot: {target_id}"
                        )
                    labels.append(
                        _review_label(
                            row,
                            accepted_prefix,
                            observation_id,
                            target_id=target_id,
                            label_type="adjudication",
                            decision=adjudication,
                            adjudicator=True,
                        )
                    )
                else:
                    labels.append(
                        _review_label(
                            row,
                            "checker_a",
                            observation_id,
                            target_id=target_id,
                            label_type="adjudication",
                            decision=adjudication,
                            adjudicator=True,
                        )
                    )

    if blockers:
        raise ValueError(f"review ledger cannot be imported: {list(dict.fromkeys(blockers))}")
    return labels


def import_review_ledger(
    review_path: Path,
    candidate_db: Path,
    output_path: Path,
    register_path: Path,
) -> int:
    """Export an eligible ledger to a new JSONL gold-label candidate file."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing label export: {output_path}")
    expected_target_ids = _read_expected_target_ids(register_path)
    labels = build_gold_label_rows(
        _read_ledger(review_path), candidate_db, expected_target_ids
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        for label in labels:
            handle.write(json.dumps(label, ensure_ascii=False, sort_keys=True) + "\n")
    return len(labels)
