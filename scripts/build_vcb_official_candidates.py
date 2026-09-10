"""Build non-Gold VCB candidates from visually transcribed official filings.

The quarterly VCB PDFs are scan/mixed-layer documents. Facts are therefore
kept explicit and page-bound, while every emitted observation remains
``pending_validation``. The ROE denominator alternatives are preserved until
the project convention is explicitly frozen for this issuer.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


FACTS = (
    {
        "period": "2024_Q1",
        "as_of_date": "2024-03-31",
        "source_id": "official-VCB-2024-Q1-consolidated",
        "balance_page": 4,
        "equity_page": 5,
        "income_page": 7,
        "income_continuation_page": 8,
        "npl_pdf_page": 30,
        "npl_printed_page": 29,
        "provision_pdf_page": 31,
        "provision_printed_page": 30,
        "current_ytd_pat": 8585993,
        "prior_ytd_pat": 8991901,
        "prior_fy_pat": 33122272,
        "current_ytd_parent_profit": 8579996,
        "prior_ytd_parent_profit": 8986435,
        "prior_fy_parent_profit": 33101027,
        "beginning_assets": 1839724560,
        "ending_assets": 1773713584,
        "beginning_total_equity": 165080490,
        "ending_total_equity": 173614126,
        "beginning_nci": 93990,
        "ending_nci": 100556,
        "gross_loans": 1266477925,
        "stage_3": 2557445,
        "stage_4": 3484199,
        # Both independent official-source reviewers transcribed the Q1
        # group-5 balance as 9,417,792.  The prior candidate used 9,411,792,
        # which made the derived Q1 NPL and coverage values inconsistent with
        # the reviewed source facts.
        "stage_5": 9417792,
        "specific_provision": 21566712,
        "general_provision": 9323973,
    },
    {
        "period": "2024_Q2",
        "as_of_date": "2024-06-30",
        "source_id": "official-VCB-2024-Q2-consolidated",
        "balance_page": 4,
        "equity_page": 5,
        "income_page": 7,
        "income_continuation_page": 8,
        "npl_pdf_page": 30,
        "npl_printed_page": 29,
        "provision_pdf_page": 31,
        "provision_printed_page": 30,
        "current_ytd_pat": 16710702,
        "prior_ytd_pat": 16419859,
        "prior_fy_pat": 33122272,
        "current_ytd_parent_profit": 16699410,
        "prior_ytd_parent_profit": 16409258,
        "prior_fy_parent_profit": 33101027,
        "beginning_assets": 1839724560,
        "ending_assets": 1905638845,
        "beginning_total_equity": 165080490,
        "ending_total_equity": 181702789,
        "beginning_nci": 93990,
        "ending_nci": 105738,
        "gross_loans": 1369645310,
        "stage_3": 3048320,
        "stage_4": 3379968,
        "stage_5": 10017770,
        "specific_provision": 24785227,
        "general_provision": 10098320,
    },
    {
        "period": "2024_Q3",
        "as_of_date": "2024-09-30",
        "source_id": "official-VCB-2024-Q3-consolidated",
        "balance_page": 4,
        "equity_page": 5,
        "income_page": 7,
        "income_continuation_page": 8,
        "npl_pdf_page": 28,
        "npl_printed_page": 27,
        "provision_pdf_page": 29,
        "provision_printed_page": 28,
        "current_ytd_pat": 25283196,
        "prior_ytd_pat": 23694415,
        "prior_fy_pat": 33122272,
        "current_ytd_parent_profit": 25266008,
        "prior_ytd_parent_profit": 23678177,
        "prior_fy_parent_profit": 33101027,
        "beginning_assets": 1839724560,
        "ending_assets": 1932361908,
        "beginning_total_equity": 165080490,
        "ending_total_equity": 190297001,
        "beginning_nci": 93990,
        "ending_nci": 110763,
        "gross_loans": 1401151675,
        "stage_3": 2696789,
        "stage_4": 3344332,
        "stage_5": 11092294,
        "specific_provision": 24735379,
        "general_provision": 10328062,
    },
    {
        "period": "2024_Q4",
        "as_of_date": "2024-12-31",
        "source_id": "official-VCB-2024-Q4-consolidated-quarterly",
        "balance_page": 4,
        "equity_page": 5,
        "income_page": 7,
        "income_continuation_page": 8,
        "npl_pdf_page": 31,
        "npl_printed_page": 30,
        "provision_pdf_page": 32,
        "provision_printed_page": 31,
        "current_ytd_pat": 33853127,
        "prior_ytd_pat": None,
        "prior_fy_pat": 33122272,
        "current_ytd_parent_profit": 33831396,
        "prior_ytd_parent_profit": None,
        "prior_fy_parent_profit": 33101027,
        "beginning_assets": 1839724560,
        "ending_assets": 2085397244,
        "beginning_total_equity": 165080490,
        "ending_total_equity": 198956110,
        "beginning_nci": 93990,
        "ending_nci": 96261,
        "gross_loans": 1449219780,
        "stage_3": 2153039,
        "stage_4": 1518558,
        "stage_5": 10292417,
        "specific_provision": 20495176,
        "general_provision": 10687999,
    },
)


def _percent(numerator: int, denominator: int | Decimal) -> float:
    return float(
        (Decimal(numerator) / Decimal(denominator) * Decimal("100")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    )


def _ttm(current: int, prior_ytd: int | None, prior_fy: int) -> int:
    return current if prior_ytd is None else prior_fy - prior_ytd + current


def _candidate(
    fact: dict,
    metric: str,
    value: float,
    *,
    locator: str,
    formula: str,
    input_facts: dict,
    period_basis: str,
    variant: str | None = None,
) -> dict:
    observation_id = f"{fact['source_id']}:{fact['period']}:{metric}"
    if variant:
        observation_id += f":{variant}"
    return {
        "observation_id": observation_id,
        "ticker": "VCB",
        "sector": "bank",
        "metric": metric,
        "value": value,
        "unit": "%",
        "period": fact["period"],
        "as_of_date": fact["as_of_date"],
        "period_basis": period_basis,
        "source_id": fact["source_id"],
        "source_locator": locator,
        "quality_status": "pending_validation",
        "reason": (
            "Visually transcribed official VCB consolidated statements; "
            "independent checker must verify every input, restatement basis, "
            "period convention, scope, and rounding before Gold promotion."
        ),
        "formula_version": formula,
        "input_facts": input_facts,
        "variant": variant,
        "extraction_status": "visual_candidate_not_gold",
    }


def build(output: Path) -> list[dict]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    rows: list[dict] = []
    for fact in FACTS:
        pat_ttm = _ttm(
            fact["current_ytd_pat"], fact["prior_ytd_pat"], fact["prior_fy_pat"]
        )
        parent_ttm = _ttm(
            fact["current_ytd_parent_profit"],
            fact["prior_ytd_parent_profit"],
            fact["prior_fy_parent_profit"],
        )
        average_assets = (
            Decimal(fact["beginning_assets"]) + Decimal(fact["ending_assets"])
        ) / Decimal("2")
        average_total_equity = (
            Decimal(fact["beginning_total_equity"])
            + Decimal(fact["ending_total_equity"])
        ) / Decimal("2")
        average_parent_equity = (
            Decimal(fact["beginning_total_equity"] - fact["beginning_nci"])
            + Decimal(fact["ending_total_equity"] - fact["ending_nci"])
        ) / Decimal("2")
        statement_locator = (
            f"pdf_pages:{fact['balance_page']},{fact['equity_page']},"
            f"{fact['income_page']},{fact['income_continuation_page']};"
            "sections:consolidated_balance_sheet|consolidated_income_statement;"
            "prior_fy_basis:Q4_2024_restated_comparative_for_common_beginning_basis;"
            "extraction:visual_transcription"
        )
        rows.append(
            _candidate(
                fact,
                "bank.roa",
                _percent(pat_ttm, average_assets),
                locator=statement_locator,
                formula="prior_fy_pat-prior_ytd_pat+current_ytd_pat over average_total_assets",
                period_basis="ttm",
                input_facts={
                    "current_ytd_pat": fact["current_ytd_pat"],
                    "prior_ytd_pat": fact["prior_ytd_pat"],
                    "prior_fy_pat": fact["prior_fy_pat"],
                    "pat_ttm": pat_ttm,
                    "beginning_total_assets": fact["beginning_assets"],
                    "ending_total_assets": fact["ending_assets"],
                    "average_total_assets": float(average_assets),
                    "unit": "million_vnd",
                    "profit_convention": "consolidated_net_profit_after_tax",
                    "beginning_basis": "Q4_2024_restated_comparative",
                },
            )
        )
        rows.append(
            _candidate(
                fact,
                "bank.roe",
                _percent(parent_ttm, average_parent_equity),
                locator=statement_locator,
                formula="prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit over average_parent_equity",
                period_basis="ttm",
                variant="parent_attributable_equity",
                input_facts={
                    "current_ytd_parent_profit": fact["current_ytd_parent_profit"],
                    "prior_ytd_parent_profit": fact["prior_ytd_parent_profit"],
                    "prior_fy_parent_profit": fact["prior_fy_parent_profit"],
                    "parent_profit_ttm": parent_ttm,
                    "beginning_parent_equity": fact["beginning_total_equity"]
                    - fact["beginning_nci"],
                    "ending_parent_equity": fact["ending_total_equity"]
                    - fact["ending_nci"],
                    "average_parent_equity": float(average_parent_equity),
                    "unit": "million_vnd",
                    "profit_convention": "profit_attributable_to_bank_shareholders",
                    "beginning_basis": "Q4_2024_restated_comparative",
                },
            )
        )
        rows.append(
            _candidate(
                fact,
                "bank.roe",
                _percent(parent_ttm, average_total_equity),
                locator=statement_locator,
                formula="prior_fy_parent_profit-prior_ytd_parent_profit+current_ytd_parent_profit over average_total_equity",
                period_basis="ttm",
                variant="total_consolidated_equity",
                input_facts={
                    "parent_profit_ttm": parent_ttm,
                    "beginning_total_equity": fact["beginning_total_equity"],
                    "ending_total_equity": fact["ending_total_equity"],
                    "average_total_equity": float(average_total_equity),
                    "unit": "million_vnd",
                    "profit_convention": "profit_attributable_to_bank_shareholders",
                    "beginning_basis": "Q4_2024_restated_comparative",
                },
            )
        )

        npl_balance = fact["stage_3"] + fact["stage_4"] + fact["stage_5"]
        total_provision = fact["specific_provision"] + fact["general_provision"]
        npl_locator = (
            f"pdf_pages:{fact['npl_pdf_page']};printed_page:{fact['npl_printed_page']};"
            "section:note_customer_loans;row:loan_quality;groups:3|4|5;"
            "denominator:total_customer_loans;extraction:visual_transcription"
        )
        coverage_locator = (
            f"pdf_pages:{fact['npl_pdf_page']},{fact['provision_pdf_page']};"
            f"printed_pages:{fact['npl_printed_page']},{fact['provision_printed_page']};"
            "sections:note_customer_loans|note_loan_loss_provision;"
            "extraction:visual_transcription"
        )
        common_credit = {
            "period_basis": "point_in_time",
            "npl_g35_balance": npl_balance,
            "gross_loans": fact["gross_loans"],
            "stage_3": fact["stage_3"],
            "stage_4": fact["stage_4"],
            "stage_5": fact["stage_5"],
            "unit": "million_vnd",
        }
        rows.append(
            _candidate(
                fact,
                "bank.npl_g35",
                _percent(npl_balance, fact["gross_loans"]),
                locator=npl_locator,
                formula="(stage_3+stage_4+stage_5) over total_customer_loans",
                period_basis="point_in_time",
                input_facts={
                    **common_credit,
                    "loan_denominator_scope": "total customer loans reported in the loan-quality note",
                },
            )
        )
        rows.append(
            _candidate(
                fact,
                "bank.llr_coverage",
                _percent(total_provision, npl_balance),
                locator=coverage_locator,
                formula="(specific_provision+general_provision) over npl_g35_balance",
                period_basis="point_in_time",
                variant="total_specific_plus_general_provision",
                input_facts={
                    **common_credit,
                    "specific_provision": fact["specific_provision"],
                    "general_provision": fact["general_provision"],
                    "total_loan_loss_provision": total_provision,
                    "provision_scope": "specific provision plus general provision from the customer-loan provision note",
                },
            )
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
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
