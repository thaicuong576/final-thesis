"""Build non-Gold MBB ROA/ROE candidates from visually transcribed statements.

The facts below are deliberately explicit and page-bound.  The script does not
read vendor ratios, does not promote a snapshot, and preserves an alternative
ROE denominator so an independent reviewer can resolve the convention.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


FACTS = (
    {
        "period": "2024_Q1", "as_of_date": "2024-03-31", "source_id": "official-MBB-2024-Q1-consolidated",
        "balance_page": 3, "equity_page": 4, "income_page": 6,
        "current_ytd_pat": 4624216, "prior_ytd_pat": 5205556, "prior_fy_pat": 21053792,
        "current_ytd_parent_profit": 4532698, "prior_ytd_parent_profit": 5023662, "prior_fy_parent_profit": 20676788,
        "beginning_assets": 944953640, "ending_assets": 900647141,
        "beginning_total_equity": 96711159, "ending_total_equity": 101341424,
        "beginning_nci": 3973110, "ending_nci": 4066862,
    },
    {
        "period": "2024_Q2", "as_of_date": "2024-06-30", "source_id": "official-MBB-2024-Q2-consolidated",
        "balance_page": 3, "equity_page": 4, "income_page": 6,
        "current_ytd_pat": 10726199, "prior_ytd_pat": 10187996, "prior_fy_pat": 21053792,
        "current_ytd_parent_profit": 10559447, "prior_ytd_parent_profit": 9917157, "prior_fy_parent_profit": 20676788,
        "beginning_assets": 944953640, "ending_assets": 988604894,
        "beginning_total_equity": 96711159, "ending_total_equity": 104213948,
        "beginning_nci": 3973110, "ending_nci": 4065509,
    },
    {
        "period": "2024_Q3", "as_of_date": "2024-09-30", "source_id": "official-MBB-2024-Q3-consolidated",
        "balance_page": 3, "equity_page": 4, "income_page": 6,
        "current_ytd_pat": 16569642, "prior_ytd_pat": 16008704, "prior_fy_pat": 21053792,
        "current_ytd_parent_profit": 16349603, "prior_ytd_parent_profit": 15690422, "prior_fy_parent_profit": 20676788,
        "beginning_assets": 944953640, "ending_assets": 1028819208,
        "beginning_total_equity": 96711159, "ending_total_equity": 110023198,
        "beginning_nci": 3973110, "ending_nci": 4221301,
    },
    {
        "period": "2024_Q4", "as_of_date": "2024-12-31", "source_id": "official-MBB-2024-Q4-consolidated",
        "balance_page": 3, "equity_page": 4, "income_page": 6,
        "current_ytd_pat": 22951264, "prior_ytd_pat": None, "prior_fy_pat": 21053792,
        "current_ytd_parent_profit": 22633757, "prior_ytd_parent_profit": None, "prior_fy_parent_profit": 20676788,
        "beginning_assets": 944953640, "ending_assets": 1128801062,
        "beginning_total_equity": 96711159, "ending_total_equity": 117059581,
        "beginning_nci": 3973110, "ending_nci": 4910880,
    },
)


def _ratio(numerator: int, denominator: Decimal) -> float:
    value = (Decimal(numerator) / denominator * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return float(value)


def _ttm(current: int, prior_ytd: int | None, prior_fy: int) -> int:
    return current if prior_ytd is None else prior_fy - prior_ytd + current


def _candidate(fact: dict, metric: str, value: float, *, locator: str, formula: str, input_facts: dict, variant: str | None = None) -> dict:
    observation_id = f"{fact['source_id']}:{fact['period']}:{metric}"
    if variant:
        observation_id += f":{variant}"
    return {
        "observation_id": observation_id,
        "ticker": "MBB",
        "sector": "bank",
        "metric": metric,
        "value": value,
        "unit": "%",
        "period": fact["period"],
        "as_of_date": fact["as_of_date"],
        "period_basis": "ttm",
        "source_id": fact["source_id"],
        "source_locator": locator,
        "quality_status": "pending_validation",
        "reason": "Visually transcribed official consolidated statements; independent checker must verify every input, reporting basis, period convention, and rounding before Gold promotion.",
        "formula_version": "roa-ttm-v1" if metric == "bank.roa" else "roe-ttm-v1",
        "input_facts": input_facts,
        "variant": variant,
        "extraction_status": "visual_candidate_not_gold",
    }


def build(output: Path) -> list[dict]:
    rows: list[dict] = []
    for fact in FACTS:
        roa_ttm = _ttm(fact["current_ytd_pat"], fact["prior_ytd_pat"], fact["prior_fy_pat"])
        parent_ttm = _ttm(fact["current_ytd_parent_profit"], fact["prior_ytd_parent_profit"], fact["prior_fy_parent_profit"])
        avg_assets = (Decimal(fact["beginning_assets"]) + Decimal(fact["ending_assets"])) / Decimal("2")
        total_avg_equity = (Decimal(fact["beginning_total_equity"]) + Decimal(fact["ending_total_equity"])) / Decimal("2")
        parent_avg_equity = (
            Decimal(fact["beginning_total_equity"] - fact["beginning_nci"])
            + Decimal(fact["ending_total_equity"] - fact["ending_nci"])
        ) / Decimal("2")
        locator = (
            f"pdf_pages:{fact['balance_page']},{fact['equity_page']},{fact['income_page']};"
            "sections:consolidated_balance_sheet|consolidated_income_statement;extraction:visual_transcription"
        )
        rows.append(_candidate(
            fact, "bank.roa", _ratio(roa_ttm, avg_assets), locator=locator,
            formula="prior_fy_pat-prior_ytd_pat+current_ytd_pat over average_total_assets",
            input_facts={
                "current_ytd_pat": fact["current_ytd_pat"], "prior_ytd_pat": fact["prior_ytd_pat"],
                "prior_fy_pat": fact["prior_fy_pat"], "pat_ttm": roa_ttm,
                "beginning_total_assets": fact["beginning_assets"], "ending_total_assets": fact["ending_assets"],
                "average_total_assets": float(avg_assets), "unit": "million_vnd",
                "profit_convention": "consolidated_net_profit_after_tax",
            },
        ))
        rows.append(_candidate(
            fact, "bank.roe", _ratio(parent_ttm, parent_avg_equity), locator=locator,
            formula="prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit over average_parent_equity",
            input_facts={
                "current_ytd_parent_profit": fact["current_ytd_parent_profit"], "prior_ytd_parent_profit": fact["prior_ytd_parent_profit"],
                "prior_fy_parent_profit": fact["prior_fy_parent_profit"], "parent_profit_ttm": parent_ttm,
                "beginning_parent_equity": fact["beginning_total_equity"] - fact["beginning_nci"],
                "ending_parent_equity": fact["ending_total_equity"] - fact["ending_nci"],
                "average_parent_equity": float(parent_avg_equity), "unit": "million_vnd",
                "profit_convention": "profit_attributable_to_bank_shareholders",
            },
            variant="parent_attributable_equity",
        ))
        rows.append(_candidate(
            fact, "bank.roe", _ratio(parent_ttm, total_avg_equity), locator=locator,
            formula="prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit over average_total_equity",
            input_facts={
                "parent_profit_ttm": parent_ttm, "beginning_total_equity": fact["beginning_total_equity"],
                "ending_total_equity": fact["ending_total_equity"], "average_total_equity": float(total_avg_equity),
                "unit": "million_vnd", "profit_convention": "profit_attributable_to_bank_shareholders",
            },
            variant="total_consolidated_equity",
        ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build(args.output)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
