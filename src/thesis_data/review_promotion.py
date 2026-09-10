"""Promote an independently reviewed candidate snapshot into a gold snapshot.

The candidate database, merged review ledger, and exported label artifact are
all read-only inputs.  Promotion first materializes a temporary
``reviewed_candidate`` database, then delegates the existing fail-closed gold
promotion checks to :func:`create_gold_snapshot`.  The candidate database is
never updated in place.
"""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Mapping, Sequence

from scripts.build_review_ledger import (
    accepted_reviewer_prefix,
    audit_review_rows,
    final_review_decision,
)

from .review_import import (
    _accepted_candidate_matches,
    _split_source_references,
    build_gold_label_rows,
)
from .schema import GoldConfig, GoldLabel, GoldPromotionResult
from .storage import create_gold_snapshot, create_gold_snapshot_schema


def _target_id(row: Mapping[str, str]) -> str:
    return f"{row.get('ticker', '').strip()}:{row.get('period', '').strip()}:{row.get('metric', '').strip()}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_register(path: Path) -> set[str]:
    rows = _read_csv(path)
    targets = {_target_id(row) if not row.get("target_id", "").strip() else row["target_id"].strip() for row in rows}
    if not rows or any(not target for target in targets):
        raise ValueError("review register must contain non-empty target IDs")
    if len(targets) != len(rows):
        raise ValueError("review register must not contain duplicate target IDs")
    return targets


def _read_gold_labels(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"gold label artifact does not exist: {path}")
    labels: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                label = GoldLabel.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"invalid gold label at line {line_number}") from exc
            labels.append(label.model_dump(mode="json"))
    if not labels:
        raise ValueError("gold label artifact is empty")
    return labels


def _canonical_counter(rows: Sequence[Mapping[str, Any]]) -> Counter[str]:
    return Counter(
        json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    )


def _load_candidate_data(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"candidate database does not exist: {path}")
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required = {"metric_observations", "source_records", "evidence_snippets"}
        missing = required - tables
        if missing:
            raise ValueError(f"candidate database missing tables: {sorted(missing)}")

        observation_rows = connection.execute(
            """
            SELECT observation_id, ticker, sector, metric, value, unit, period,
                   as_of_date, period_basis, source_id, source_locator,
                   quality_status, reason
            FROM metric_observations ORDER BY observation_id
            """
        ).fetchall()
        source_rows = connection.execute(
            """
            SELECT source_id, source_type, source_tier, source_url, retrieved_at,
                   local_path, content_hash, publisher, license_note,
                   quality_status, notes
            FROM source_records ORDER BY source_id
            """
        ).fetchall()
        evidence_rows = connection.execute(
            """
            SELECT evidence_id, source_id, source_document, page_number,
                   section_name, period, ticker, quote, retrieval_score,
                   parser_status, is_paginated
            FROM evidence_snippets ORDER BY evidence_id
            """
        ).fetchall()
    finally:
        connection.close()

    by_cell: dict[str, list[dict[str, Any]]] = {}
    by_observation: dict[str, tuple[Any, ...]] = {}
    for row in observation_rows:
        ref = {
            "observation_id": row[0],
            "ticker": row[1],
            "sector": row[2],
            "metric": row[3],
            "value": row[4],
            "unit": row[5],
            "period": row[6],
            "as_of_date": row[7],
            "period_basis": row[8],
            "source_id": row[9],
            "source_locator": row[10],
        }
        by_cell.setdefault(f"{row[1]}:{row[6]}:{row[3]}", []).append(ref)
        by_observation[row[0]] = row

    return {
        "observations_by_cell": by_cell,
        "observations_by_id": by_observation,
        "source_rows": source_rows,
        "evidence_rows": evidence_rows,
    }


def _reviewed_plans(
    rows: Sequence[Mapping[str, str]],
    observations_by_cell: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    plans: list[dict[str, Any]] = []
    accepted_source_ids: set[str] = set()
    blockers: list[str] = []
    for row in rows:
        cell = _target_id(row)
        candidates = list(observations_by_cell.get(cell, ()))
        decision = final_review_decision(row)
        if decision == "accepted":
            prefix = accepted_reviewer_prefix(row)
            if prefix is None:
                blockers.append(f"accepted_without_reviewer_mapping:{cell}")
                continue
            matches = _accepted_candidate_matches(row, prefix, candidates)
            if len(matches) != 1:
                blockers.append(f"accepted_candidate_mapping_not_unique:{cell}")
                continue
            selected = matches[0]
            if not selected.get("source_id"):
                blockers.append(f"accepted_candidate_missing_source:{cell}")
                continue
            # The selected candidate owns the canonical observation FK. Keep
            # every source explicitly cited by the accepted review valid too,
            # because TTM derivations may depend on a quarter filing plus a
            # prior fiscal-year filing. The candidate observation itself is
            # never rewritten to a composite source ID.
            accepted_source_ids.add(str(selected["source_id"]))
            accepted_source_ids.update(
                _split_source_references(row[f"{prefix}_source_id"])
            )
            plans.append({"kind": "valid", "cell": cell, "candidate": selected})
        elif decision == "missing":
            plans.append(
                {
                    "kind": "missing",
                    "cell": cell,
                    "observation_id": f"missing:{cell}",
                    "reason": (
                        row.get("adjudication_reason", "").strip()
                        or row.get("checker_a_notes", "").strip()
                        or row.get("checker_b_notes", "").strip()
                        or "no comparable accepted official observation"
                    ),
                }
            )
        else:
            blockers.append(f"unresolved_review_decision:{cell}:{decision or 'blank'}")
    return plans, accepted_source_ids, blockers


def _write_reviewed_staging(
    output: Path,
    candidate_data: Mapping[str, Any],
    plans: Sequence[Mapping[str, Any]],
    accepted_source_ids: set[str],
    labels: Sequence[Mapping[str, Any]],
) -> None:
    create_gold_snapshot_schema(output)
    connection = sqlite3.connect(output)
    try:
        config_json = json.dumps(
            {"source": "reviewed_candidate", "created_by": "review_promotion"},
            sort_keys=True,
        )
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                output.stem,
                datetime.now(timezone.utc).isoformat(),
                "reviewed_candidate",
                config_json,
            ),
        )

        source_rows = []
        for source in candidate_data["source_rows"]:
            source = list(source)
            if source[0] in accepted_source_ids:
                prior_status = source[9]
                source[9] = "valid"
                source[10] = f"review accepted source; prior_status={prior_status}"
            source_rows.append(tuple(source))
        connection.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            source_rows,
        )

        observation_rows: list[tuple[Any, ...]] = []
        for plan in plans:
            if plan["kind"] == "valid":
                candidate = plan["candidate"]
                source_row = candidate_data["observations_by_id"][candidate["observation_id"]]
                row = list(source_row)
                row[11] = "valid"
                row[12] = None
                observation_rows.append(tuple(row))
            else:
                ticker, period, metric = plan["cell"].split(":", 2)
                observation_rows.append(
                    (
                        plan["observation_id"],
                        ticker,
                        "bank",
                        metric,
                        None,
                        None,
                        period,
                        None,
                        None,
                        None,
                        None,
                        "missing",
                        plan["reason"],
                    )
                )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            observation_rows,
        )

        evidence_rows = [
            row
            for row in candidate_data["evidence_rows"]
            if row[1] in accepted_source_ids
        ]
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            evidence_rows,
        )

        label_rows = [
            (
                label["label_id"],
                label["target_id"],
                label["label_type"],
                label["expected_value"],
                label["expected_judgment"],
                label["checker_id"],
                label["checked_at"],
                label["source_locator"],
                label["resolution_note"],
            )
            for label in labels
        ]
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            label_rows,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def promote_reviewed_snapshot(
    candidate_db: Path,
    review_ledger_path: Path,
    gold_labels_path: Path,
    register_path: Path,
    output_db: Path,
    config: GoldConfig,
) -> GoldPromotionResult:
    """Create a gold snapshot from a completed reviewed candidate workflow."""

    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite existing database: {output_db}")

    try:
        review_rows = _read_csv(review_ledger_path)
        expected_targets = _read_register(register_path)
    except (OSError, ValueError) as exc:
        return GoldPromotionResult(eligible=False, blockers=[f"review_input_invalid:{exc}"])

    audit = audit_review_rows(review_rows, expected_targets)
    blockers = list(audit.blockers)
    config_targets = {
        f"{ticker}:{period}:{metric}"
        for ticker in config.tickers
        for period in config.periods
        for metric in config.required_metrics
    }
    if expected_targets != config_targets:
        blockers.append("review_scope_mismatch")
    if blockers:
        return GoldPromotionResult(
            eligible=False,
            blockers=list(dict.fromkeys(blockers)),
        )

    try:
        candidate_data = _load_candidate_data(candidate_db)
    except (OSError, ValueError) as exc:
        return GoldPromotionResult(
            eligible=False,
            blockers=[f"candidate_database_invalid:{exc}"],
        )

    plans, accepted_source_ids, plan_blockers = _reviewed_plans(
        review_rows,
        candidate_data["observations_by_cell"],
    )
    if plan_blockers:
        return GoldPromotionResult(
            eligible=False,
            blockers=list(dict.fromkeys(plan_blockers)),
        )

    try:
        expected_labels = build_gold_label_rows(
            review_rows,
            candidate_db,
            expected_targets,
        )
        supplied_labels = _read_gold_labels(gold_labels_path)
    except (OSError, ValueError) as exc:
        return GoldPromotionResult(
            eligible=False,
            blockers=[f"gold_label_artifact_invalid:{exc}"],
        )

    if _canonical_counter(expected_labels) != _canonical_counter(supplied_labels):
        return GoldPromotionResult(
            eligible=False,
            blockers=["gold_label_artifact_mismatch"],
        )

    plan_by_cell = {plan["cell"]: plan for plan in plans}
    final_labels: list[dict[str, Any]] = []
    for label in supplied_labels:
        observation_id = label["target_id"]
        candidate_row = candidate_data["observations_by_id"].get(observation_id)
        if candidate_row is None:
            continue
        cell = f"{candidate_row[1]}:{candidate_row[6]}:{candidate_row[3]}"
        plan = plan_by_cell.get(cell)
        if plan is None:
            continue
        if plan["kind"] == "valid":
            if observation_id == plan["candidate"]["observation_id"]:
                final_labels.append(dict(label))
        else:
            remapped = dict(label)
            remapped["target_id"] = plan["observation_id"]
            remapped["label_id"] = (
                f"promotion:{cell}:{label['checker_id']}:{label['label_type']}"
            )
            final_labels.append(remapped)

    # Multiple candidate variants may receive the same missing judgment.  The
    # final synthetic missing observation needs one label per checker/type.
    deduplicated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for label in final_labels:
        key = (label["target_id"], label["checker_id"], label["label_type"])
        deduplicated.setdefault(key, label)
    final_labels = sorted(deduplicated.values(), key=lambda row: row["label_id"])

    with tempfile.TemporaryDirectory(prefix="reviewed-candidate-") as temp_dir:
        reviewed_db = Path(temp_dir) / "reviewed.sqlite"
        _write_reviewed_staging(
            reviewed_db,
            candidate_data,
            plans,
            accepted_source_ids,
            final_labels,
        )
        return create_gold_snapshot(reviewed_db, output_db, config)
