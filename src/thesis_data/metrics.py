"""Deterministic, unit-aware financial metric calculations."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Sequence

from .schema import QualityStatus


Number = Decimal | int | float | None


@dataclass(frozen=True)
class MetricResult:
    value: Decimal | None
    unit: str
    quality_status: QualityStatus
    reason: str | None
    formula_version: str
    period_basis: str


def _decimal(value: Number) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _ratio(
    numerator: Number,
    denominator: Number,
    *,
    formula_version: str,
    period_basis: str,
) -> MetricResult:
    numerator_decimal = _decimal(numerator)
    denominator_decimal = _decimal(denominator)
    if numerator_decimal is None or denominator_decimal is None:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="missing_input",
            formula_version=formula_version,
            period_basis=period_basis,
        )
    if denominator_decimal == 0:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="zero_denominator",
            formula_version=formula_version,
            period_basis=period_basis,
        )
    return MetricResult(
        value=numerator_decimal / denominator_decimal * Decimal("100"),
        unit="%",
        quality_status=QualityStatus.VALID,
        reason=None,
        formula_version=formula_version,
        period_basis=period_basis,
    )


def calculate_npl(
    stage_3: Number,
    stage_4: Number,
    stage_5: Number,
    gross_loans: Number,
) -> MetricResult:
    values = [_decimal(value) for value in (stage_3, stage_4, stage_5)]
    if any(value is None for value in values):
        return _ratio(
            None,
            gross_loans,
            formula_version="npl-g35-v1",
            period_basis="point_in_time",
        )
    return _ratio(
        sum(values, Decimal("0")),
        gross_loans,
        formula_version="npl-g35-v1",
        period_basis="point_in_time",
    )


def calculate_llr(provision_balance: Number, npl_balance: Number) -> MetricResult:
    return _ratio(
        provision_balance,
        npl_balance,
        formula_version="llr-coverage-v1",
        period_basis="point_in_time",
    )


def calculate_cir_operating_expense(
    operating_expense: Number,
    operating_income: Number,
) -> MetricResult:
    return _ratio(
        operating_expense,
        operating_income,
        formula_version="cir-v1",
        period_basis="source_period",
    )


def calculate_roa(net_profit: Number, average_assets: Number) -> MetricResult:
    return _ratio(
        net_profit,
        average_assets,
        formula_version="roa-v1",
        period_basis="source_period",
    )


def calculate_roa_from_ytd(
    current_ytd: Number,
    prior_ytd: Number,
    average_assets: Number,
    *,
    current_fiscal_year: int,
    prior_fiscal_year: int,
) -> MetricResult:
    if current_fiscal_year != prior_fiscal_year:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="cross_fiscal_year_subtraction",
            formula_version="roa-v1-ytd-quarter",
            period_basis="quarter_only",
        )
    current_decimal = _decimal(current_ytd)
    prior_decimal = _decimal(prior_ytd)
    if current_decimal is None or prior_decimal is None:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="missing_input",
            formula_version="roa-v1-ytd-quarter",
            period_basis="quarter_only",
        )
    return _ratio(
        current_decimal - prior_decimal,
        average_assets,
        formula_version="roa-v1-ytd-quarter",
        period_basis="quarter_only",
    )


def _ttm_flow(current_ytd: Number, prior_ytd: Number, prior_fy: Number) -> Decimal | None:
    current_decimal = _decimal(current_ytd)
    prior_decimal = _decimal(prior_ytd)
    prior_fy_decimal = _decimal(prior_fy)
    if current_decimal is None or prior_decimal is None or prior_fy_decimal is None:
        return None
    return prior_fy_decimal - prior_decimal + current_decimal


def _rounded_ratio(
    numerator: Number,
    denominator: Number,
    *,
    formula_version: str,
    period_basis: str,
) -> MetricResult:
    result = _ratio(
        numerator,
        denominator,
        formula_version=formula_version,
        period_basis=period_basis,
    )
    if result.value is None:
        return result
    return MetricResult(
        value=result.value.quantize(Decimal("0.0001")),
        unit=result.unit,
        quality_status=result.quality_status,
        reason=result.reason,
        formula_version=result.formula_version,
        period_basis=result.period_basis,
    )


def calculate_roa_ttm(
    current_ytd: Number,
    prior_ytd: Number,
    prior_fy: Number,
    average_assets: Number,
) -> MetricResult:
    """Calculate TTM ROA from current/prior YTD profit and prior FY profit."""
    return _rounded_ratio(
        _ttm_flow(current_ytd, prior_ytd, prior_fy),
        average_assets,
        formula_version="roa-ttm-v1",
        period_basis="ttm",
    )


def calculate_roe_ttm(
    current_ytd: Number,
    prior_ytd: Number,
    prior_fy: Number,
    average_equity: Number,
) -> MetricResult:
    """Calculate TTM ROE using profit attributable to bank shareholders."""
    return _rounded_ratio(
        _ttm_flow(current_ytd, prior_ytd, prior_fy),
        average_equity,
        formula_version="roe-ttm-v1",
        period_basis="ttm",
    )


def normalize_percent(value: Number, source_unit: str) -> Decimal:
    decimal_value = _decimal(value)
    if decimal_value is None:
        raise ValueError("percent value must be numeric")
    if source_unit in {"%", "percent", "percentage_points"}:
        return decimal_value
    if source_unit == "decimal":
        return decimal_value * Decimal("100")
    raise ValueError(f"unsupported percent unit: {source_unit}")


def normalize_vnd_billion(value: Number, source_unit: str) -> Decimal:
    decimal_value = _decimal(value)
    if decimal_value is None:
        raise ValueError("VND amount must be numeric")
    if source_unit == "billion_vnd":
        return decimal_value
    if source_unit == "million_vnd":
        return decimal_value / Decimal("1000")
    if source_unit == "vnd":
        return decimal_value / Decimal("1000000000")
    raise ValueError(f"unsupported VND unit: {source_unit}")


def calculate_peer_median(values: Sequence[Number]) -> MetricResult:
    present = sorted(
        decimal_value
        for decimal_value in (_decimal(value) for value in values)
        if decimal_value is not None
    )
    if not present:
        return MetricResult(
            value=None,
            unit="same_as_input",
            quality_status=QualityStatus.MISSING,
            reason="all_values_missing",
            formula_version="peer-median-v1",
            period_basis="same_period",
        )
    middle = len(present) // 2
    if len(present) % 2:
        median = present[middle]
    else:
        median = (present[middle - 1] + present[middle]) / Decimal("2")
    return MetricResult(
        value=median,
        unit="same_as_input",
        quality_status=QualityStatus.VALID,
        reason=None,
        formula_version="peer-median-v1",
        period_basis="same_period",
    )
