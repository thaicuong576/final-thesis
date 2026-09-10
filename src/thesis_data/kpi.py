"""Extract explicitly source-disclosed KPI rows from text-layer PDF tables."""

from __future__ import annotations

from datetime import date
import re
from pathlib import Path

import fitz

from .periods import validate_period_bounds
from .schema import EvidenceSnippet, MetricObservation, PeriodBasis, QualityStatus


_PERIODS = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
_SOURCE_HEADERS = ("4Q23", "1Q24", "2Q24", "3Q24", "4Q24")
_LABELS = {
    "NPL": ("bank.npl_g35", PeriodBasis.POINT_IN_TIME),
    "Coverage ratio": ("bank.llr_coverage", PeriodBasis.POINT_IN_TIME),
    "CIR": ("bank.cir", PeriodBasis.QUARTER_ONLY),
    "ROA (LTM)": ("bank.roa", PeriodBasis.TTM),
    "ROE (LTM)": ("bank.roe", PeriodBasis.TTM),
}
_PERCENT = re.compile(r"^(?:\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?)%$")


def _find_financial_highlights_page(document: fitz.Document) -> tuple[int, list[str]]:
    for index, page in enumerate(document):
        lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
        joined = " ".join(lines)
        if (
            "4Q24 Financial Highlights" in joined
            and "Coverage ratio" in lines
            and "ROA (LTM)" in lines
        ):
            return index, lines
    raise ValueError("financial highlights table page was not found")


def _extract_percent_row(lines: list[str], label: str) -> list[float]:
    for index, line in enumerate(lines):
        if line != label:
            continue
        position = index + 1
        while position < len(lines) and not lines[position]:
            position += 1
        if position >= len(lines) or lines[position] != "%":
            continue
        values: list[float] = []
        for candidate in lines[position + 1 : position + 32]:
            if _PERCENT.fullmatch(candidate):
                values.append(float(candidate.rstrip("% ").replace(",", "")))
                if len(values) == len(_SOURCE_HEADERS):
                    return values
            elif values:
                break
    raise ValueError(f"could not extract five percentage values for row: {label}")


def extract_tcb_fy24_kpis(pdf_path: Path, source_id: str) -> list[MetricObservation]:
    """Extract 1Q24–4Q24 KPI candidates from TCB's FY24 presentation.

    The first value in the table is 4Q23 and is intentionally excluded. All
    returned observations remain pending until definition, cutoff, and an
    independent checker are recorded.
    """
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"expected an existing PDF path: {pdf_path}")
    document = fitz.open(pdf_path)
    try:
        page_index, lines = _find_financial_highlights_page(document)
        observations: list[MetricObservation] = []
        for label, (metric, period_basis) in _LABELS.items():
            values = _extract_percent_row(lines, label)[1:]
            for period, value in zip(_PERIODS, values):
                reason = "pending independent checker and source-cutoff verification"
                if metric == "bank.npl_g35":
                    reason = (
                        "pending reconciliation: issuer NPL label must be verified as "
                        "group 3-5 over the thesis denominator"
                    )
                observations.append(
                    MetricObservation(
                        observation_id=f"{source_id}:{period}:{metric}",
                        ticker="TCB",
                        sector="bank",
                        metric=metric,
                        value=value,
                        unit="%",
                        period=period,
                        as_of_date=validate_period_bounds(period)[1],
                        period_basis=period_basis,
                        source_id=source_id,
                        source_locator=(
                            f"page:{page_index + 1};table:4Q24 financial highlights;"
                            f"row:{label};columns:{','.join(_SOURCE_HEADERS[1:])}"
                        ),
                        quality_status=QualityStatus.PENDING_VALIDATION,
                        reason=reason,
                    )
                )
        return observations
    finally:
        document.close()


def extract_tcb_fy24_evidence(pdf_path: Path, source_id: str) -> list[EvidenceSnippet]:
    """Create page-aware evidence rows for the KPI table rows used above."""
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"expected an existing PDF path: {pdf_path}")
    document = fitz.open(pdf_path)
    try:
        page_index, lines = _find_financial_highlights_page(document)
        snippets: list[EvidenceSnippet] = []
        for label in _LABELS:
            values = _extract_percent_row(lines, label)
            quote = (
                f"{label} | columns: {', '.join(_SOURCE_HEADERS)} | values: "
                + ", ".join(f"{value:g}%" for value in values)
            )
            snippets.append(
                EvidenceSnippet(
                    evidence_id=f"{source_id}:page:{page_index + 1}:row:{label}",
                    source_id=source_id,
                    source_document=pdf_path.name,
                    page_number=page_index + 1,
                    section_name="Appendix / 4Q24 Financial Highlights",
                    ticker="TCB",
                    quote=quote,
                    retrieval_score=1.0,
                    parser_status="text_layer_table_row",
                    is_paginated=True,
                )
            )
        return snippets
    finally:
        document.close()
