"""Namespace reviewer source IDs for an expansion candidate snapshot.

Reviewers inspect standalone candidate sources.  The expansion builder
prefixes copied source IDs (for example ``expansion:official-VCB-...``) to
keep the combined snapshot collision-safe.  This utility creates a new
promotion-bound ledger with that explicit namespace while preserving the
original reviewer ledger unchanged.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


SOURCE_ID_FIELDS = (
    "vendor_source_id",
    "checker_a_source_id",
    "checker_b_source_id",
)


def _namespace_source_ids(raw: str, prefix: str) -> str:
    if not raw.strip():
        return ""
    parts = [part.strip() for part in re.split(r"\s*(?:\||;)\s*", raw) if part.strip()]
    return "|".join(
        part if part.startswith(prefix) else f"{prefix}{part}"
        for part in parts
    )


def namespace_review_ledger(
    input_path: Path,
    output_path: Path,
    *,
    prefix: str = "expansion:",
    tickers: set[str] | None = None,
) -> int:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows or "target_id" not in fields:
        raise ValueError("review ledger must contain target_id and at least one row")
    for row in rows:
        if tickers is not None and row.get("ticker", "").strip() not in tickers:
            continue
        for field in SOURCE_ID_FIELDS:
            if field in row:
                row[field] = _namespace_source_ids(row.get(field, ""), prefix)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix", default="expansion:")
    parser.add_argument("--ticker", action="append", dest="tickers")
    args = parser.parse_args()
    count = namespace_review_ledger(
        args.input,
        args.output,
        prefix=args.prefix,
        tickers=set(args.tickers) if args.tickers else None,
    )
    print(f"namespaced_rows={count} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
