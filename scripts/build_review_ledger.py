"""Build and audit a two-checker reconciliation ledger.

The main reconciliation register is a one-row-per-target worksheet. This
ledger is a separate, append-safe review surface: it has independent slots for
checker A and checker B, plus an adjudication slot for disagreements. It never
changes the candidate files, raw sources, or main register.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


DECISIONS = frozenset({"accepted", "missing", "conflicting", "invalid"})

_CONTEXT_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "register_review_status",
    "vendor_observation_ids",
    "vendor_value",
    "vendor_unit",
    "vendor_period_basis",
    "vendor_source_id",
    "vendor_source_url",
    "vendor_source_locator",
)

# A reviewer must independently inspect official evidence. Keep vendor values,
# vendor locators, and the register's status out of their private copy because
# those fields can anchor the review before the official source is checked.
_BLIND_CONTEXT_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
)

_CHECKER_SUFFIXES = (
    "id",
    "decision",
    "value",
    "unit",
    "period_basis",
    "source_id",
    "source_url",
    "source_locator",
    "consolidation_basis",
    "definition_match",
    "checked_at",
    "notes",
)

REVIEW_LEDGER_FIELDS = _CONTEXT_FIELDS + tuple(
    f"checker_{checker}_{suffix}"
    for checker in ("a", "b")
    for suffix in _CHECKER_SUFFIXES
) + (
    "adjudication_decision",
    "adjudication_source_slot",
    "adjudicator_id",
    "adjudicated_at",
    "adjudication_reason",
)

REVIEWER_COPY_FIELDS = _BLIND_CONTEXT_FIELDS + tuple(
    "checker_id" if suffix == "id" else suffix for suffix in _CHECKER_SUFFIXES
)


@dataclass(frozen=True)
class ReviewLedgerAudit:
    eligible: bool
    blockers: tuple[str, ...]
    row_count: int
    checker_a_completed: int
    checker_b_completed: int
    disagreement_count: int


def build_review_ledger(register_path: Path) -> list[dict[str, str]]:
    """Create blank independent-review slots from an existing register."""
    with register_path.open("r", encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    required = {"target_id", "ticker", "sector", "metric", "period"}
    if not source_rows or not required.issubset(source_rows[0]):
        raise ValueError("register must contain target identity columns")

    rows: list[dict[str, str]] = []
    for source in source_rows:
        row = {field: source.get(field, "") or "" for field in REVIEW_LEDGER_FIELDS}
        row["register_review_status"] = source.get("review_status", "") or ""
        for field in (
            "vendor_observation_ids",
            "vendor_value",
            "vendor_unit",
            "vendor_period_basis",
            "vendor_source_id",
            "vendor_source_url",
            "vendor_source_locator",
        ):
            row[field] = source.get(field, "") or ""
        rows.append(row)
    return rows


def write_review_ledger(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write a new ledger without overwriting an existing review file."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing review ledger: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_reviewer_copy_from_rows(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a blind single-reviewer copy from already-selected register rows."""
    required = {"target_id", "ticker", "sector", "metric", "period"}
    if not source_rows or not required.issubset(source_rows[0]):
        raise ValueError("register must contain target identity columns")

    rows: list[dict[str, str]] = []
    for source in source_rows:
        # Only target identity is copied from the register. Every reviewer-owned
        # field must start blank; copying ``notes`` (or any other fill field)
        # would leak register context and can anchor an independent decision.
        row = {field: "" for field in REVIEWER_COPY_FIELDS}
        for field in _BLIND_CONTEXT_FIELDS:
            row[field] = source.get(field, "") or ""
        rows.append(row)
    return rows


def build_reviewer_copy(register_path: Path) -> list[dict[str, str]]:
    """Create a blind single-reviewer copy from the main register."""
    with register_path.open("r", encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    return build_reviewer_copy_from_rows(source_rows)


def write_reviewer_copy(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write one blind reviewer's copy without overwriting an existing file."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite reviewer copy: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEWER_COPY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


@dataclass(frozen=True)
class ReviewerCopyAudit:
    eligible: bool
    blockers: tuple[str, ...]
    row_count: int
    completed_count: int


def _copy_field(suffix: str) -> str:
    return "checker_id" if suffix == "id" else suffix


ADJUDICATION_FIELDS = (
    "adjudication_decision",
    "adjudication_source_slot",
    "adjudicator_id",
    "adjudicated_at",
    "adjudication_reason",
)


def final_review_decision(row: dict[str, str]) -> str:
    """Return the explicit final decision, if an adjudicator supplied one."""
    adjudication = row.get("adjudication_decision", "").strip()
    if adjudication:
        return adjudication
    decision_a = row.get("checker_a_decision", "").strip()
    decision_b = row.get("checker_b_decision", "").strip()
    if decision_a == decision_b:
        return decision_a
    return ""


def accepted_reviewer_prefix(row: dict[str, str]) -> str | None:
    """Return the reviewer slot whose accepted mapping is canonical."""
    if final_review_decision(row) != "accepted":
        return None
    source_slot = row.get("adjudication_source_slot", "").strip()
    if source_slot:
        return source_slot
    if row.get("checker_a_decision", "").strip() == "accepted":
        return "checker_a"
    if row.get("checker_b_decision", "").strip() == "accepted":
        return "checker_b"
    return None


def apply_adjudication_overlay(
    ledger_rows: list[dict[str, str]],
    adjudication_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Apply explicit adjudication fields without changing either review copy."""
    if not ledger_rows:
        raise ValueError("review ledger must contain rows")
    ledger_by_target = {row.get("target_id", "").strip(): row for row in ledger_rows}
    if len(ledger_by_target) != len(ledger_rows) or "" in ledger_by_target:
        raise ValueError("review ledger must contain unique non-empty target IDs")

    overlay_by_target: dict[str, dict[str, str]] = {}
    for overlay in adjudication_rows:
        target_id = overlay.get("target_id", "").strip()
        if not target_id or target_id in overlay_by_target:
            raise ValueError("adjudication overlay must contain unique non-empty target IDs")
        if target_id not in ledger_by_target:
            raise ValueError(f"adjudication target is not in review ledger: {target_id}")
        missing = [field for field in ADJUDICATION_FIELDS if field not in overlay]
        if missing:
            raise ValueError(
                f"adjudication overlay is missing fields for {target_id}: {missing}"
            )
        overlay_by_target[target_id] = overlay

    result = [{field: value for field, value in row.items()} for row in ledger_rows]
    for row in result:
        overlay = overlay_by_target.get(row["target_id"].strip())
        if overlay is None:
            continue
        for field in ADJUDICATION_FIELDS:
            row[field] = overlay.get(field, "") or ""
    return result


def apply_reviewer_addendum(
    ledger_rows: list[dict[str, str]],
    addendum_rows: list[dict[str, str]],
    *,
    adjudicator_id: str,
    adjudicated_at: str,
    adjudication_reason: str,
) -> list[dict[str, str]]:
    """Add a fresh Checker-B review to a versioned ledger and adjudicate it.

    This is for newly discovered candidate routes whose original review was a
    reasoned ``missing`` decision.  The prior ledger remains untouched; the
    returned ledger is a new version in which only the addendum targets receive
    the new Checker-B slot and explicit adjudication fields.
    """
    if not adjudicator_id.strip() or not adjudicated_at.strip() or not adjudication_reason.strip():
        raise ValueError("addendum adjudication identity, timestamp, and reason are required")
    if not ledger_rows or not addendum_rows:
        raise ValueError("ledger and addendum must contain rows")

    ledger_by_target = {row.get("target_id", "").strip(): row for row in ledger_rows}
    if len(ledger_by_target) != len(ledger_rows) or "" in ledger_by_target:
        raise ValueError("review ledger must contain unique non-empty target IDs")

    addendum_audit = audit_reviewer_copy_rows(addendum_rows)
    if not addendum_audit.eligible:
        raise ValueError(
            f"reviewer addendum is not eligible: {list(addendum_audit.blockers)}"
        )

    addendum_by_target = {row["target_id"].strip(): row for row in addendum_rows}
    for target_id in addendum_by_target:
        if target_id not in ledger_by_target:
            raise ValueError(f"addendum target is not in review ledger: {target_id}")

    result = [{field: value for field, value in row.items()} for row in ledger_rows]
    for row in result:
        target_id = row["target_id"].strip()
        addendum = addendum_by_target.get(target_id)
        if addendum is None:
            continue
        prior_decision = row.get("checker_b_decision", "").strip()
        if prior_decision not in {"", "missing"}:
            raise ValueError(
                f"addendum would overwrite a non-missing checker B decision: {target_id}"
            )
        for suffix in _CHECKER_SUFFIXES:
            row[f"checker_b_{suffix}"] = addendum.get(_copy_field(suffix), "") or ""

        decision = addendum["decision"].strip()
        row["adjudication_decision"] = decision
        row["adjudication_source_slot"] = "checker_b" if decision == "accepted" else ""
        row["adjudicator_id"] = adjudicator_id.strip()
        row["adjudicated_at"] = adjudicated_at.strip()
        row["adjudication_reason"] = (
            f"{adjudication_reason.strip()} prior_checker_b_decision={prior_decision or 'blank'}"
        )
    return result


def audit_reviewer_copy_rows(rows: list[dict[str, str]]) -> ReviewerCopyAudit:
    """Validate a single reviewer's copy without inspecting another copy."""
    blockers: list[str] = []
    target_ids = [row.get("target_id", "").strip() for row in rows]
    if any(not target_id for target_id in target_ids):
        blockers.append("missing_target_id")
    if len(set(target_ids)) != len(target_ids):
        blockers.append("duplicate_target_id")

    completed_count = 0
    for row in rows:
        decision = row.get("decision", "").strip()
        populated = any(row.get(_copy_field(suffix), "").strip() for suffix in _CHECKER_SUFFIXES)
        if not decision:
            blockers.append("review_incomplete")
            continue
        completed_count += 1
        if decision not in DECISIONS:
            blockers.append("invalid_decision")
        if not row.get("checker_id", "").strip():
            blockers.append("missing_checker_id")
        for suffix in ("checked_at", "notes"):
            if not row.get(suffix, "").strip():
                blockers.append(f"missing_{suffix}")
        if decision == "accepted":
            for suffix in (
                "value",
                "unit",
                "period_basis",
                "source_id",
                "source_url",
                "source_locator",
                "consolidation_basis",
            ):
                if not row.get(suffix, "").strip():
                    blockers.append(f"accepted_missing_source_mapping:{suffix}")
            if row.get("definition_match", "").strip().lower() != "yes":
                blockers.append("accepted_definition_not_yes")
        if not populated:
            blockers.append("empty_review_slot")

    return ReviewerCopyAudit(
        eligible=not blockers and bool(rows),
        blockers=tuple(dict.fromkeys(blockers)),
        row_count=len(rows),
        completed_count=completed_count,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def merge_reviewer_copies(
    checker_a_path: Path, checker_b_path: Path
) -> list[dict[str, str]]:
    """Merge two independently completed copies into the two-checker ledger.

    The function refuses incomplete or malformed copies and refuses the same
    checker identity in both slots. It intentionally allows disagreements to
    pass through for adjudication rather than selecting a winner silently.
    """
    checker_a = _read_csv_rows(checker_a_path)
    checker_b = _read_csv_rows(checker_b_path)
    audit_a = audit_reviewer_copy_rows(checker_a)
    audit_b = audit_reviewer_copy_rows(checker_b)
    if not audit_a.eligible or not audit_b.eligible:
        raise ValueError(
            f"reviewer copy is not eligible: A={audit_a.blockers} B={audit_b.blockers}"
        )

    by_a = {row["target_id"].strip(): row for row in checker_a}
    by_b = {row["target_id"].strip(): row for row in checker_b}
    if set(by_a) != set(by_b):
        raise ValueError("reviewer copies have different target sets")

    merged: list[dict[str, str]] = []
    for target_id in sorted(by_a):
        row_a = by_a[target_id]
        row_b = by_b[target_id]
        if row_a["checker_id"].strip() == row_b["checker_id"].strip():
            raise ValueError(f"same checker identity for target {target_id}")
        row = {field: row_a.get(field, "") or "" for field in REVIEW_LEDGER_FIELDS}
        for field in _CONTEXT_FIELDS:
            row[field] = row_a.get(field, "") or ""
        for prefix, source in (("checker_a", row_a), ("checker_b", row_b)):
            for suffix in _CHECKER_SUFFIXES:
                row[f"{prefix}_{suffix}"] = source.get(_copy_field(suffix), "") or ""
        merged.append(row)
    return merged


def _checker_complete(row: dict[str, str], prefix: str) -> bool:
    return bool(row.get(f"{prefix}_decision", "").strip())


def _validate_checker(row: dict[str, str], prefix: str, blockers: list[str]) -> bool:
    decision = row.get(f"{prefix}_decision", "").strip()
    populated = any(row.get(f"{prefix}_{suffix}", "").strip() for suffix in _CHECKER_SUFFIXES)
    if not decision:
        # A blank slot is still incomplete: eligibility requires both checkers
        # to make an explicit decision for every target cell.
        blockers.append(f"{prefix}_incomplete")
        return False

    if decision not in DECISIONS:
        blockers.append(f"{prefix}_invalid_decision")
        return False
    for suffix in ("id", "checked_at", "notes"):
        if not row.get(f"{prefix}_{suffix}", "").strip():
            blockers.append(f"{prefix}_missing_{suffix}")

    if decision == "accepted":
        for suffix in (
            "value",
            "unit",
            "period_basis",
            "source_id",
            "source_url",
            "source_locator",
            "consolidation_basis",
        ):
            if not row.get(f"{prefix}_{suffix}", "").strip():
                blockers.append(f"accepted_missing_source_mapping:{prefix}:{suffix}")
        if row.get(f"{prefix}_definition_match", "").strip().lower() != "yes":
            blockers.append(f"accepted_definition_not_yes:{prefix}")
    return True


def _accepted_mapping_differs(
    row: dict[str, str], prefix_a: str, prefix_b: str
) -> bool:
    """Return whether two accepted reviews select different source/value mappings."""
    comparable_suffixes = (
        "value",
        "unit",
        "period_basis",
        "source_id",
        "source_url",
        "source_locator",
        "consolidation_basis",
        "definition_match",
    )
    for suffix in comparable_suffixes:
        left = row.get(f"{prefix_a}_{suffix}", "").strip()
        right = row.get(f"{prefix_b}_{suffix}", "").strip()
        if suffix == "value":
            try:
                if float(left) != float(right):
                    return True
                continue
            except ValueError:
                # The checker validator will report malformed values during
                # import. Treat non-numeric values as different here so the
                # audit cannot accidentally accept an unresolved mapping.
                pass
        if left != right:
            return True
    return False


def audit_review_rows(
    rows: list[dict[str, str]], expected_target_ids: set[str] | None = None
) -> ReviewLedgerAudit:
    """Validate two-checker completeness, independence, and adjudication."""
    blockers: list[str] = []
    target_ids = [row.get("target_id", "").strip() for row in rows]
    if any(not target_id for target_id in target_ids):
        blockers.append("missing_target_id")
    duplicates = sorted({target_id for target_id in target_ids if target_ids.count(target_id) > 1})
    if duplicates:
        blockers.append("duplicate_target_id")
    if expected_target_ids is not None:
        actual = set(target_ids)
        if actual != expected_target_ids:
            blockers.append("target_set_mismatch")

    checker_a_completed = 0
    checker_b_completed = 0
    disagreement_count = 0
    for row in rows:
        a_complete = _validate_checker(row, "checker_a", blockers)
        b_complete = _validate_checker(row, "checker_b", blockers)
        checker_a_completed += int(a_complete)
        checker_b_completed += int(b_complete)

        if a_complete and b_complete:
            checker_a_id = row.get("checker_a_id", "").strip()
            checker_b_id = row.get("checker_b_id", "").strip()
            if checker_a_id == checker_b_id:
                blockers.append("same_checker_id")
            decision_a = row["checker_a_decision"].strip()
            decision_b = row["checker_b_decision"].strip()
            mapping_disagreement = (
                decision_a == "accepted"
                and decision_b == "accepted"
                and _accepted_mapping_differs(row, "checker_a", "checker_b")
            )
            adjudication = row.get("adjudication_decision", "").strip()
            adjudication_populated = any(
                row.get(field, "").strip()
                for field in ADJUDICATION_FIELDS
                if field != "adjudication_decision"
            )
            if mapping_disagreement or decision_a != decision_b:
                disagreement_count += 1

            if mapping_disagreement and not adjudication:
                # Do not let an adjudicator silently choose one of two
                # accepted mappings; the row needs an explicit final decision
                # and, for an accepted result, an explicit source slot.
                blockers.append("accepted_mapping_disagreement")
            elif decision_a != decision_b and not adjudication:
                blockers.append("unadjudicated_disagreement")
            elif adjudication_populated and not adjudication:
                blockers.append("incomplete_adjudication")

            if adjudication:
                required_adjudication = (
                    "adjudicator_id",
                    "adjudicated_at",
                    "adjudication_reason",
                )
                if any(not row.get(field, "").strip() for field in required_adjudication):
                    blockers.append("incomplete_adjudication")
                if adjudication not in DECISIONS:
                    blockers.append("invalid_adjudication_decision")

                source_slot = row.get("adjudication_source_slot", "").strip()
                if source_slot and source_slot not in {"checker_a", "checker_b"}:
                    blockers.append("invalid_adjudication_source_slot")
                if adjudication == "accepted":
                    if mapping_disagreement and not source_slot:
                        blockers.append("missing_adjudication_source_slot")
                    if source_slot and row.get(f"{source_slot}_decision", "").strip() != "accepted":
                        blockers.append("adjudication_source_slot_not_accepted")
                elif source_slot:
                    blockers.append("adjudication_source_slot_without_accepted_decision")

    return ReviewLedgerAudit(
        eligible=not blockers and bool(rows),
        blockers=tuple(dict.fromkeys(blockers)),
        row_count=len(rows),
        checker_a_completed=checker_a_completed,
        checker_b_completed=checker_b_completed,
        disagreement_count=disagreement_count,
    )


def audit_review_ledger(review_path: Path, register_path: Path | None = None) -> ReviewLedgerAudit:
    """Audit a CSV ledger, optionally against the target set in the register."""
    with review_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = None
    if register_path is not None:
        with register_path.open("r", encoding="utf-8", newline="") as handle:
            expected = {row.get("target_id", "").strip() for row in csv.DictReader(handle)}
    return audit_review_rows(rows, expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path, help="main reconciliation register")
    parser.add_argument("output", type=Path, help="new output path, or existing ledger with --audit")
    parser.add_argument("--audit", action="store_true", help="audit an existing two-checker ledger")
    parser.add_argument("--reviewer-copy", action="store_true", help="create a blind single-reviewer copy")
    parser.add_argument("--merge-a", type=Path, help="checker-A copy to merge")
    parser.add_argument("--merge-b", type=Path, help="checker-B copy to merge")
    args = parser.parse_args()

    if args.audit:
        audit = audit_review_ledger(args.output, args.register)
        print(
            f"eligible={audit.eligible} rows={audit.row_count} "
            f"checker_a={audit.checker_a_completed} "
            f"checker_b={audit.checker_b_completed} "
            f"disagreements={audit.disagreement_count} blockers={list(audit.blockers)}"
        )
        return 0 if audit.eligible else 1

    if bool(args.merge_a) != bool(args.merge_b):
        parser.error("--merge-a and --merge-b must be provided together")

    if args.merge_a and args.merge_b:
        merged = merge_reviewer_copies(args.merge_a, args.merge_b)
        write_review_ledger(merged, args.output)
        print(f"merged_rows={len(merged)} output={args.output}")
        return 0

    if args.reviewer_copy:
        rows = build_reviewer_copy(args.register)
        write_reviewer_copy(rows, args.output)
        print(f"reviewer_copy_rows={len(rows)} output={args.output}")
        return 0

    rows = build_review_ledger(args.register)
    write_review_ledger(rows, args.output)
    print(f"ledger_rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
