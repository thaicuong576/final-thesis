"""Build a deterministic manual-reconciliation register from a proposed scope.

The register is deliberately separate from the immutable staging databases. It
is a review worksheet: vendor candidates are copied in for comparison, while
official values and acceptance decisions remain blank until a human checks the
issuer source.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


METRIC_FIELDS = {
    "bank.npl_g35": "npl",
    "bank.llr_coverage": "loansLossReservesToNPLs",
    "bank.cir": "cir",
    "bank.roa": "roa",
    "bank.roe": "roe",
}

REGISTER_FIELDS = (
    "target_id",
    "ticker",
    "sector",
    "metric",
    "period",
    "review_status",
    "vendor_observation_ids",
    "vendor_value",
    "vendor_unit",
    "vendor_period_basis",
    "vendor_source_id",
    "vendor_source_url",
    "vendor_source_locator",
    "official_value",
    "official_unit",
    "official_period_basis",
    "official_source_id",
    "official_source_url",
    "official_source_locator",
    "consolidation_basis",
    "definition_match",
    "reconciliation_result",
    "checker_id",
    "checked_at",
    "notes",
)


def _load_scope(path: Path) -> tuple[list[str], list[str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tickers = [item["ticker"] for item in payload["issuers"]]
    periods = [item["period"] for item in payload["periods"]]
    metrics = list(payload["primary_metrics"])
    if not tickers or not periods or not metrics:
        raise ValueError("selection must contain issuers, periods, and primary_metrics")
    unknown = set(metrics) - set(METRIC_FIELDS)
    if unknown:
        raise ValueError(f"no vendor-field mapping for metrics: {sorted(unknown)}")
    return tickers, periods, metrics


def build_register(staging_db: Path, selection_path: Path) -> list[dict[str, str]]:
    """Return one row per target cell, including zero-candidate cells."""
    tickers, periods, metrics = _load_scope(selection_path)
    field_codes = [METRIC_FIELDS[metric] for metric in metrics]
    ticker_marks = ",".join("?" for _ in tickers)
    period_marks = ",".join("?" for _ in periods)
    field_marks = ",".join("?" for _ in field_codes)

    connection = sqlite3.connect(f"file:{staging_db.resolve()}?mode=ro", uri=True)
    try:
        candidates = connection.execute(
            f"""
            SELECT id, ticker, sector, period, field_code, value, unit,
                   source_id, source_locator, quality_status
            FROM ratio_observations
            WHERE ticker IN ({ticker_marks})
              AND period IN ({period_marks})
              AND ratio_type = 'RATIO_TTM'
              AND field_code IN ({field_marks})
            ORDER BY ticker, period, field_code, id
            """,
            (*tickers, *periods, *field_codes),
        ).fetchall()
        source_ids = sorted({row[7] for row in candidates})
        source_map: dict[str, tuple[str, str]] = {}
        if source_ids:
            source_marks = ",".join("?" for _ in source_ids)
            source_map = {
                row[0]: (row[1] or "", row[2] or "")
                for row in connection.execute(
                    f"SELECT source_id, source_url, quality_status FROM source_records "
                    f"WHERE source_id IN ({source_marks})",
                    tuple(source_ids),
                )
            }
    finally:
        connection.close()

    grouped: dict[tuple[str, str, str], list[tuple]] = defaultdict(list)
    for candidate in candidates:
        metric = next(metric for metric, field in METRIC_FIELDS.items() if field == candidate[4])
        grouped[(candidate[1], candidate[3], metric)].append(candidate)

    rows: list[dict[str, str]] = []
    for ticker in tickers:
        for period in periods:
            for metric in metrics:
                target_id = f"{ticker}:{period}:{metric}"
                group = grouped.get((ticker, period, metric), [])
                first = group[0] if group else None
                source_url, _source_quality = source_map.get(first[7], ("", "")) if first else ("", "")
                if first:
                    review_status = "pending_official_check"
                    notes = (
                        "Vendor candidate only; verify official filing, page/table, "
                        "consolidation, definition, unit, sign, and period basis."
                    )
                    vendor_value = "" if first[5] is None else str(first[5])
                    vendor_unit = first[6] or ""
                    vendor_source_id = first[7] or ""
                    vendor_locator = first[8] or ""
                    candidate_ids = ";".join(str(row[0]) for row in group)
                else:
                    review_status = "missing_vendor_candidate"
                    notes = "No supported vendor candidate; search official source or record a justified missing value."
                    vendor_value = vendor_unit = vendor_source_id = vendor_locator = candidate_ids = ""
                rows.append(
                    {
                        "target_id": target_id,
                        "ticker": ticker,
                        "sector": "bank",
                        "metric": metric,
                        "period": period,
                        "review_status": review_status,
                        "vendor_observation_ids": candidate_ids,
                        "vendor_value": vendor_value,
                        "vendor_unit": vendor_unit,
                        "vendor_period_basis": "TTM" if first else "",
                        "vendor_source_id": vendor_source_id,
                        "vendor_source_url": source_url,
                        "vendor_source_locator": vendor_locator,
                        "official_value": "",
                        "official_unit": "",
                        "official_period_basis": "",
                        "official_source_id": "",
                        "official_source_url": "",
                        "official_source_locator": "",
                        "consolidation_basis": "",
                        "definition_match": "",
                        "reconciliation_result": "",
                        "checker_id": "",
                        "checked_at": "",
                        "notes": notes,
                    }
                )
    return rows


def write_register(rows: list[dict[str, str]], output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing register: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_db", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = build_register(args.staging_db, args.selection)
    write_register(rows, args.output)
    candidate_rows = sum(row["review_status"] == "pending_official_check" for row in rows)
    print(f"register_rows={len(rows)} candidate_rows={candidate_rows} pending_rows={len(rows) - candidate_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
