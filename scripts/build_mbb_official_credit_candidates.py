"""Build non-Gold MBB NPL and loan-loss-coverage candidates from official pages.

The source pages are scan-only and were transcribed from the consolidated
quarterly filings. Values remain pending validation until two independent
reviewers verify the figures, denominator scope, provision scope, and period.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


FACTS = (
    {
        "period": "2024_Q1", "as_of_date": "2024-03-31", "source_id": "official-MBB-2024-Q1-consolidated",
        "npl_pdf_page": 27, "npl_printed_page": 21, "provision_pdf_page": 30, "provision_printed_page": 24,
        "gross_loans": 615316724, "stage_3": 4038993, "stage_4": 5207370, "stage_5": 6048054,
        "specific_provision": 7671576, "general_provision": 4572754,
    },
    {
        "period": "2024_Q2", "as_of_date": "2024-06-30", "source_id": "official-MBB-2024-Q2-consolidated",
        "npl_pdf_page": 29, "npl_printed_page": 21, "provision_pdf_page": 32, "provision_printed_page": 24,
        "gross_loans": 673799059, "stage_3": 3665451, "stage_4": 4816496, "stage_5": 2541101,
        "specific_provision": 6173192, "general_provision": 5041352,
    },
    {
        "period": "2024_Q3", "as_of_date": "2024-09-30", "source_id": "official-MBB-2024-Q3-consolidated",
        "npl_pdf_page": 30, "npl_printed_page": 22, "provision_pdf_page": 33, "provision_printed_page": 25,
        "gross_loans": 702019545, "stage_3": 6054806, "stage_4": 5582585, "stage_5": 4047280,
        "specific_provision": 5547364, "general_provision": 5239293,
    },
    {
        "period": "2024_Q4", "as_of_date": "2024-12-31", "source_id": "official-MBB-2024-Q4-consolidated",
        "npl_pdf_page": 29, "npl_printed_page": 21, "provision_pdf_page": 32, "provision_printed_page": 24,
        "gross_loans": 776657846, "stage_3": 3379646, "stage_4": 4599274, "stage_5": 4606512,
        "specific_provision": 5814288, "general_provision": 5795573,
    },
)


def _percent(numerator: int, denominator: int) -> float:
    return float(
        (Decimal(numerator) / Decimal(denominator) * Decimal("100")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    )


def build(output: Path) -> list[dict]:
    rows: list[dict] = []
    for fact in FACTS:
        npl_balance = fact["stage_3"] + fact["stage_4"] + fact["stage_5"]
        total_provision = fact["specific_provision"] + fact["general_provision"]
        source_id = fact["source_id"]
        npl_locator = (
            f"pdf_pages:{fact['npl_pdf_page']};printed_page:{fact['npl_printed_page']};"
            "section:note_5_customer_loans;row:loan_quality;"
            "denominator:dư_nợ_cho_vay;groups:3|4|5;extraction:visual_transcription"
        )
        coverage_locator = (
            f"pdf_pages:{fact['npl_pdf_page']},{fact['provision_pdf_page']};"
            f"printed_pages:{fact['npl_printed_page']},{fact['provision_printed_page']};"
            "sections:note_5_customer_loans|note_6_credit_risk_provision;"
            "extraction:visual_transcription"
        )
        common = {
            "ticker": "MBB",
            "sector": "bank",
            "unit": "%",
            "period": fact["period"],
            "as_of_date": fact["as_of_date"],
            "period_basis": "point_in_time",
            "source_id": source_id,
            "quality_status": "pending_validation",
            "reason": "Visually transcribed official consolidated statements; independent checker must verify every input, denominator scope, provision scope, and rounding before Gold promotion.",
            "extraction_status": "visual_candidate_not_gold",
        }
        rows.append({
            **common,
            "observation_id": f"{source_id}:{fact['period']}:bank.npl_g35",
            "metric": "bank.npl_g35",
            "value": _percent(npl_balance, fact["gross_loans"]),
            "source_locator": npl_locator,
            "formula_version": "npl-g35-v1",
            "input_facts": {
                "gross_loans": fact["gross_loans"],
                "stage_3": fact["stage_3"], "stage_4": fact["stage_4"], "stage_5": fact["stage_5"],
                "npl_g35_balance": npl_balance,
                "loan_denominator_scope": "dư nợ cho vay total including margin balance shown in note 5",
                "unit": "million_vnd",
            },
            "variant": None,
        })
        rows.append({
            **common,
            "observation_id": f"{source_id}:{fact['period']}:bank.llr_coverage",
            "metric": "bank.llr_coverage",
            "value": _percent(total_provision, npl_balance),
            "source_locator": coverage_locator,
            "formula_version": "llr-coverage-v1",
            "input_facts": {
                "stage_3": fact["stage_3"], "stage_4": fact["stage_4"], "stage_5": fact["stage_5"],
                "npl_g35_balance": npl_balance,
                "specific_provision": fact["specific_provision"],
                "general_provision": fact["general_provision"],
                "total_loan_loss_provision": total_provision,
                "provision_scope": "specific provision plus general provision from note 6",
                "unit": "million_vnd",
            },
            "variant": "total_specific_plus_general_provision",
        })
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
