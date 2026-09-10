"""Materialize blank blind-review copies for a proposed explicit scope."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.build_review_ledger import (  # noqa: E402
    build_reviewer_copy_from_rows,
    write_reviewer_copy,
)


PENDING_ADVISOR_STATUS = "proposed_metric_reduction_pending_advisor_confirmation"


def _target_id(row: dict[str, str]) -> str:
    explicit = row.get("target_id", "").strip()
    if explicit:
        return explicit
    return ":".join(
        row.get(field, "").strip() for field in ("ticker", "period", "metric")
    )


def _load_scope(scope_path: Path) -> tuple[dict[str, Any], set[str]]:
    try:
        data = json.loads(scope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid scope manifest: {scope_path}") from exc

    if data.get("status") != PENDING_ADVISOR_STATUS:
        raise ValueError("scoped review copies require advisor-pending fallback status")
    scope_id = str(data.get("scope_id", "")).strip()
    if not scope_id:
        raise ValueError("scope manifest must contain scope_id")

    issuers = tuple(str(value).strip() for value in data.get("issuers", ()))
    periods = tuple(
        str(item.get("period", "")).strip()
        if isinstance(item, dict)
        else str(item).strip()
        for item in data.get("periods", ())
    )
    metrics = tuple(str(value).strip() for value in data.get("primary_metrics", ()))
    if not issuers or not periods or not metrics or any(not value for value in (*issuers, *periods, *metrics)):
        raise ValueError("scope manifest must contain non-empty issuers, periods, and primary_metrics")

    expected = {
        f"{ticker}:{period}:{metric}"
        for ticker in issuers
        for period in periods
        for metric in metrics
    }
    if data.get("target_cell_count") != len(expected):
        raise ValueError("scope target_cell_count does not match scope dimensions")
    return data, expected


def build_scoped_reviewer_copies(
    register_path: Path, scope_path: Path, output_dir: Path
) -> dict[str, Any]:
    """Write two blank blind copies containing exactly the proposed scope."""
    scope, expected_targets = _load_scope(scope_path)
    with register_path.open("r", encoding="utf-8", newline="") as handle:
        register_rows = list(csv.DictReader(handle))
    if not register_rows:
        raise ValueError("register is empty")

    register_targets = [_target_id(row) for row in register_rows]
    if any(not target for target in register_targets):
        raise ValueError("register contains an empty target ID")
    if len(set(register_targets)) != len(register_targets):
        raise ValueError("register contains duplicate target IDs")
    missing = sorted(expected_targets - set(register_targets))
    if missing:
        raise ValueError(f"register is missing scope targets: {missing}")

    selected_rows = [row for row in register_rows if _target_id(row) in expected_targets]
    copies = build_reviewer_copy_from_rows(selected_rows)
    outputs = {
        "checker_a": output_dir / "review-checker-a-blind-template-v1.csv",
        "checker_b": output_dir / "review-checker-b-blind-template-v1.csv",
    }
    manifest_path = output_dir / "scope-review-manifest.json"
    if any(path.exists() for path in (*outputs.values(), manifest_path)):
        raise FileExistsError(f"refusing to overwrite scoped review output under {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for path in outputs.values():
        write_reviewer_copy(copies, path)
    manifest = {
        "schema_version": 1,
        "scope_id": scope["scope_id"],
        "status": scope["status"],
        "target_cell_count": len(selected_rows),
        "source_register": str(register_path),
        "reviewer_files": {key: str(path) for key, path in outputs.items()},
        "candidate_values_included": False,
        "canonical_scope_changed": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    parser.add_argument("scope", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    try:
        result = build_scoped_reviewer_copies(args.register, args.scope, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
