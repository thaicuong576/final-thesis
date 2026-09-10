"""Replace previously unresolved target reviews with a fresh independent review.

This is intentionally narrower than a generic ledger merge: it only replaces
targets whose current final decision is missing/conflicting/blank, verifies the
fresh two-checker ledger is eligible, preserves the surrounding ledger, and
writes a new version without mutating prior review evidence.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_review_ledger import (  # noqa: E402
    ADJUDICATION_FIELDS,
    REVIEW_LEDGER_FIELDS,
    _CHECKER_SUFFIXES,
    audit_review_rows,
    final_review_decision,
    write_review_ledger,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _replace_targets(
    base_rows: list[dict[str, str]],
    fresh_rows: list[dict[str, str]],
    *,
    allow_resolved: bool,
    semantic_reason: str | None = None,
) -> list[dict[str, str]]:
    """Replace target review slots with explicit safety mode controls."""
    base_audit = audit_review_rows(base_rows)
    if not base_audit.eligible:
        raise ValueError(f"base ledger is not eligible: {list(base_audit.blockers)}")
    fresh_audit = audit_review_rows(fresh_rows)
    if not fresh_audit.eligible:
        raise ValueError(f"fresh ledger is not eligible: {list(fresh_audit.blockers)}")

    base_by_target = {row.get("target_id", "").strip(): row for row in base_rows}
    fresh_by_target = {row.get("target_id", "").strip(): row for row in fresh_rows}
    if len(base_by_target) != len(base_rows) or "" in base_by_target:
        raise ValueError("base ledger must contain unique non-empty target IDs")
    if len(fresh_by_target) != len(fresh_rows) or "" in fresh_by_target:
        raise ValueError("fresh ledger must contain unique non-empty target IDs")

    result = [{field: value for field, value in row.items()} for row in base_rows]
    result_by_target = {row["target_id"].strip(): row for row in result}
    for target_id, fresh in fresh_by_target.items():
        if target_id not in result_by_target:
            raise ValueError(f"fresh target is not in base ledger: {target_id}")
        base = result_by_target[target_id]
        identity_fields = ("ticker", "sector", "metric", "period")
        for field in identity_fields:
            if base.get(field, "").strip() != fresh.get(field, "").strip():
                raise ValueError(f"target identity mismatch for {target_id}: {field}")
        prior_final = final_review_decision(base)
        if prior_final not in {"", "missing", "conflicting"} and not allow_resolved:
            raise ValueError(
                f"refusing to replace an already-resolved target {target_id}: {prior_final}"
            )
        if allow_resolved and not semantic_reason:
            raise ValueError("semantic replacement requires an explicit reason")
        for prefix in ("checker_a", "checker_b"):
            for suffix in _CHECKER_SUFFIXES:
                base[f"{prefix}_{suffix}"] = fresh.get(f"{prefix}_{suffix}", "") or ""
        for field in ADJUDICATION_FIELDS:
            base[field] = fresh.get(field, "") or ""
        if allow_resolved:
            fresh_reason = fresh.get("adjudication_reason", "").strip()
            reason_parts = [f"semantic_correction:{semantic_reason}"]
            if prior_final:
                reason_parts.append(f"replaced_prior_decision:{prior_final}")
            if fresh_reason:
                reason_parts.append(f"fresh_adjudication:{fresh_reason}")
            base["adjudication_reason"] = " | ".join(reason_parts)
    return result


def replace_review_targets(
    base_rows: list[dict[str, str]],
    fresh_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Replace only unresolved base targets with an eligible fresh ledger."""
    return _replace_targets(base_rows, fresh_rows, allow_resolved=False)


def replace_semantic_targets(
    base_rows: list[dict[str, str]],
    fresh_rows: list[dict[str, str]],
    *,
    reason: str,
) -> list[dict[str, str]]:
    """Apply a fresh reviewed semantic correction to previously accepted cells.

    This is deliberately separate from ordinary gap replacement. It requires a
    non-empty reason and emits a new ledger version with an explicit reason in
    every corrected row; the prior ledger remains untouched.
    """
    return _replace_targets(
        base_rows,
        fresh_rows,
        allow_resolved=True,
        semantic_reason=reason.strip(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_ledger", type=Path)
    parser.add_argument("fresh_ledger", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--semantic-reason",
        default=None,
        help="explicit reason required when correcting already-resolved semantic targets",
    )
    args = parser.parse_args()

    base_rows = _read_csv(args.base_ledger)
    fresh_rows = _read_csv(args.fresh_ledger)
    if args.semantic_reason is None:
        result = replace_review_targets(base_rows, fresh_rows)
    else:
        result = replace_semantic_targets(
            base_rows,
            fresh_rows,
            reason=args.semantic_reason,
        )
    write_review_ledger(result, args.output)
    print(f"base_rows={len(base_rows)} replaced_rows={len(fresh_rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
