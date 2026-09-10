"""Merge disjoint, independently reviewed ledgers into one target-scoped ledger.

This utility is intentionally narrow: it carries forward an already
adjudicated ledger (for example, MBB ROA/ROE) and appends a separately
reviewed ledger (for example, MBB NPL/coverage). It never overwrites a target,
selects a checker, or promotes a candidate. Every input must already be
eligible under the two-checker review contract, and their union must exactly
match the supplied register.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    REVIEW_LEDGER_FIELDS,
    audit_review_rows,
    write_review_ledger,
)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"review artifact does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def _register_targets(register_path: Path) -> list[str]:
    fields, rows = _read_csv(register_path)
    if "target_id" not in fields or not rows:
        raise ValueError("review register must contain target_id and at least one row")
    targets = [row.get("target_id", "").strip() for row in rows]
    if any(not target for target in targets):
        raise ValueError("review register contains an empty target_id")
    if len(set(targets)) != len(targets):
        raise ValueError("review register contains duplicate target_id values")
    return targets


def _validate_target_identity(row: dict[str, str]) -> None:
    target_id = row.get("target_id", "").strip()
    expected = ":".join(
        (
            row.get("ticker", "").strip(),
            row.get("period", "").strip(),
            row.get("metric", "").strip(),
        )
    )
    if not target_id or expected != target_id:
        raise ValueError(
            f"target identity mismatch: target_id={target_id!r} computed={expected!r}"
        )


def _load_eligible_ledger(
    path: Path, expected_targets: set[str]
) -> tuple[set[str], list[dict[str, str]]]:
    fields, rows = _read_csv(path)
    missing_fields = sorted(set(REVIEW_LEDGER_FIELDS) - set(fields))
    if missing_fields:
        raise ValueError(f"ledger {path} is missing fields: {missing_fields}")
    if not rows:
        raise ValueError(f"ledger {path} is empty")

    for row in rows:
        _validate_target_identity(row)
    target_ids = [row["target_id"].strip() for row in rows]
    if not set(target_ids).issubset(expected_targets):
        unexpected = sorted(set(target_ids) - expected_targets)
        raise ValueError(f"ledger {path} has targets outside register: {unexpected}")

    audit = audit_review_rows(rows, set(target_ids))
    if not audit.eligible:
        raise ValueError(
            f"ledger {path} is not eligible: {list(audit.blockers)}"
        )
    return set(target_ids), rows


def merge_disjoint_review_ledgers(
    prior_ledger_path: Path,
    incremental_ledger_path: Path,
    register_path: Path,
) -> list[dict[str, str]]:
    """Merge two eligible ledgers whose target sets are disjoint.

    The output follows the target order in ``register_path``. The register is
    used only as a completeness and ordering contract; reviewer-owned fields
    are copied from the two ledgers without reinterpretation.
    """

    return merge_disjoint_review_ledgers_many(
        (prior_ledger_path, incremental_ledger_path), register_path
    )


def merge_disjoint_review_ledgers_many(
    ledger_paths: Sequence[Path],
    register_path: Path,
) -> list[dict[str, str]]:
    """Merge two or more eligible ledgers with pairwise-disjoint targets.

    Each input may cover only a subset of the register. The union must cover
    the register exactly, so a chain such as base Gold -> MBB -> VCB can be
    checked atomically without creating a partially merged intermediate file.
    """
    if len(ledger_paths) < 2:
        raise ValueError("at least two ledgers are required")
    register_order = _register_targets(register_path)
    expected_targets = set(register_order)
    combined_targets: set[str] = set()
    all_rows: list[dict[str, str]] = []
    for ledger_path in ledger_paths:
        targets, rows = _load_eligible_ledger(ledger_path, expected_targets)
        overlap = sorted(combined_targets & targets)
        if overlap:
            raise ValueError(
                f"ledger target sets overlap; refusing overwrite: {overlap}"
            )
        combined_targets.update(targets)
        all_rows.extend(rows)
    if combined_targets != expected_targets:
        missing = sorted(expected_targets - combined_targets)
        extra = sorted(combined_targets - expected_targets)
        raise ValueError(
            f"ledger union does not equal register: missing={missing} extra={extra}"
        )

    by_target = {row["target_id"].strip(): row for row in all_rows}
    if len(by_target) != len(register_order):
        raise ValueError("merged ledger would contain duplicate target IDs")
    return [by_target[target_id] for target_id in register_order]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledgers", type=Path, nargs="+")
    parser.add_argument("register", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows = merge_disjoint_review_ledgers_many(args.ledgers, args.register)
    write_review_ledger(rows, args.output)
    print(f"merged_rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
