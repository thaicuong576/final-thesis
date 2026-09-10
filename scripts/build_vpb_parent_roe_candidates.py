"""Build deterministic VPB ROE candidates using parent-attributable equity."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


FACTS = (
    {
        "period": "2024_Q1",
        "source_id": "official-VPB-2024-Q1-consolidated-lookup",
        "source_locator": "pdf_pages:6,8;equity_scope:total_equity_minus_nci;formula:prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit_over_average_parent_attributable_equity",
        "current_ytd_parent_profit": 3566697,
        "prior_ytd_parent_profit": 2535954,
        "prior_fy_parent_profit": 9973939,
        "current_total_equity": 142937410,
        "current_nci": 4739680,
        "prior_total_equity": 139795527,
        "prior_nci": 5164494,
    },
    {
        "period": "2024_Q2",
        "source_id": "official-VPB-2024-Q2-consolidated-lookup",
        "source_locator": "pdf_pages:6,8;equity_scope:total_equity_minus_nci;formula:prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit_over_average_parent_attributable_equity",
        "current_ytd_parent_profit": 7125083,
        "prior_ytd_parent_profit": 5597747,
        "prior_fy_parent_profit": 9973939,
        "current_total_equity": 138067138,
        "current_nci": 4811741,
        "prior_total_equity": 139795527,
        "prior_nci": 5164494,
    },
    {
        "period": "2024_Q3",
        "source_id": "official-VPB-2024-Q3-consolidated-lookup",
        "source_locator": "pdf_pages:6,8;equity_scope:total_equity_minus_nci;formula:prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit_over_average_parent_attributable_equity",
        "current_ytd_parent_profit": 11161375,
        "prior_ytd_parent_profit": 8022493,
        "prior_fy_parent_profit": 9973939,
        "current_total_equity": 142239874,
        "current_nci": 4948185,
        "prior_total_equity": 139795527,
        "prior_nci": 5164494,
    },
    {
        "period": "2024_Q4",
        "source_id": "official-VPB-2024-Q4-consolidated-lookup",
        "source_locator": "pdf_pages:6,8;equity_scope:total_equity_minus_nci;formula:fy2024_parent_profit_over_average_parent_attributable_equity",
        "current_ytd_parent_profit": 15778795,
        "prior_ytd_parent_profit": None,
        "prior_fy_parent_profit": 15778795,
        "current_total_equity": 147275262,
        "current_nci": 5370287,
        "prior_total_equity": 139795527,
        "prior_nci": 5164494,
    },
)


def _round4(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def build_candidates() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fact in FACTS:
        current_parent_equity = fact["current_total_equity"] - fact["current_nci"]
        prior_parent_equity = fact["prior_total_equity"] - fact["prior_nci"]
        average_parent_equity = (
            Decimal(current_parent_equity) + Decimal(prior_parent_equity)
        ) / Decimal(2)
        if fact["period"] == "2024_Q4":
            parent_profit_ttm = fact["prior_fy_parent_profit"]
        else:
            parent_profit_ttm = (
                fact["prior_fy_parent_profit"]
                - fact["prior_ytd_parent_profit"]
                + fact["current_ytd_parent_profit"]
            )
        value = _round4(Decimal(parent_profit_ttm) / average_parent_equity * Decimal(100))
        rows.append(
            {
                "observation_id": f"official-VPB-2024-consolidated-lookup:{fact['period']}:bank.roe:parent_attributable_equity",
                "ticker": "VPB",
                "sector": "bank",
                "metric": "bank.roe",
                "value": value,
                "unit": "%",
                "period": fact["period"],
                "as_of_date": {
                    "2024_Q1": "2024-03-31",
                    "2024_Q2": "2024-06-30",
                    "2024_Q3": "2024-09-30",
                    "2024_Q4": "2024-12-31",
                }[fact["period"]],
                "period_basis": "ttm",
                "source_id": fact["source_id"],
                "source_locator": fact["source_locator"],
                "quality_status": "pending_validation",
                "reason": "derived parent-attributable-equity candidate from official consolidated statements; requires fresh independent review after denominator convention freeze",
                "formula_version": "roe_ttm_parent_equity.v1",
                "variant": "parent_attributable_equity",
                "input_facts": {
                    "prior_fy_parent_profit": fact["prior_fy_parent_profit"],
                    "prior_ytd_parent_profit": fact["prior_ytd_parent_profit"],
                    "current_ytd_parent_profit": fact["current_ytd_parent_profit"],
                    "parent_profit_ttm": parent_profit_ttm,
                    "current_total_equity": fact["current_total_equity"],
                    "current_nci": fact["current_nci"],
                    "current_parent_attributable_equity": current_parent_equity,
                    "prior_total_equity": fact["prior_total_equity"],
                    "prior_nci": fact["prior_nci"],
                    "prior_parent_attributable_equity": prior_parent_equity,
                    "average_parent_attributable_equity": float(average_parent_equity),
                    "unit": "million_vnd",
                    "profit_convention": "profit attributable to bank shareholders",
                    "equity_convention": "total consolidated equity minus non-controlling interest",
                },
            }
        )
    return rows


def write_candidates(output: Path) -> int:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = build_candidates()
    with output.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps({"candidate_rows": write_candidates(args.output), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
