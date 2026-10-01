"""Deterministic, unit-aware financial metric calculations."""

from dataclasses import replace, dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Literal, Sequence

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


@dataclass(frozen=True)
class OperationalDerivedFormulaSpec:
    """Versioned formula contract used before operational snapshot acceptance."""

    metric_id: str
    formula_version: str
    input_metric_ids: tuple[str, ...]
    input_units: tuple[str, ...]
    input_period_bases: tuple[str, ...]
    output_unit: str
    output_period_basis: str
    tolerance: Decimal
    period_rule: Literal["same_period", "q4_ttm", "interim_ttm", "annual_ytd"]
    calculate: Callable[[tuple[Number, ...]], MetricResult]


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


def calculate_npl_g35_balance(
    group_3_balance: Number,
    group_4_balance: Number,
    group_5_balance: Number,
) -> MetricResult:
    """Sum accepted group 3–5 balances in normalized VND billion."""

    values = tuple(_decimal(value) for value in (
        group_3_balance,
        group_4_balance,
        group_5_balance,
    ))
    if any(value is None for value in values):
        return MetricResult(
            value=None,
            unit="billion_vnd",
            quality_status=QualityStatus.MISSING,
            reason="missing_input",
            formula_version="npl-g35-balance-v1",
            period_basis="point_in_time",
        )
    return MetricResult(
        value=sum(values, Decimal("0")),
        unit="billion_vnd",
        quality_status=QualityStatus.VALID,
        reason=None,
        formula_version="npl-g35-balance-v1",
        period_basis="point_in_time",
    )


def calculate_parent_attributable_equity(
    total_equity: Number,
    non_controlling_interests: Number,
) -> MetricResult:
    """Derive parent-attributable equity from total equity less NCI."""

    total_decimal = _decimal(total_equity)
    nci_decimal = _decimal(non_controlling_interests)
    if total_decimal is None or nci_decimal is None:
        return MetricResult(
            value=None,
            unit="billion_vnd",
            quality_status=QualityStatus.MISSING,
            reason="missing_input",
            formula_version="parent-attributable-equity-v1",
            period_basis="point_in_time",
        )
    return MetricResult(
        value=total_decimal - nci_decimal,
        unit="billion_vnd",
        quality_status=QualityStatus.VALID,
        reason=None,
        formula_version="parent-attributable-equity-v1",
        period_basis="point_in_time",
    )


def _q4_ttm_average(left: Number, right: Number) -> Decimal | None:
    left_decimal = _decimal(left)
    right_decimal = _decimal(right)
    if left_decimal is None or right_decimal is None:
        return None
    return (left_decimal + right_decimal) / Decimal("2")


def _calculate_q4_roa_ttm(inputs: tuple[Number, ...]) -> MetricResult:
    average_assets = _q4_ttm_average(inputs[2], inputs[3])
    return calculate_roa_ttm(inputs[0], inputs[1], inputs[1], average_assets)


def _calculate_q4_roe_ttm(inputs: tuple[Number, ...]) -> MetricResult:
    average_equity = _q4_ttm_average(inputs[2], inputs[3])
    return calculate_roe_ttm(inputs[0], inputs[1], inputs[1], average_equity)


def _calculate_interim_roa_ttm(inputs: tuple[Number, ...]) -> MetricResult:
    """Inputs: YTD profit (t), YTD profit (same quarter, prior year), FY profit (prior year),
    total assets (t), total assets (prior year-end). Average = opening/closing of the year."""
    result = calculate_roa_ttm(inputs[0], inputs[1], inputs[2], _q4_ttm_average(inputs[3], inputs[4]))
    return replace(result, formula_version="roa-ttm-interim-v1")


def _calculate_interim_roe_ttm(inputs: tuple[Number, ...]) -> MetricResult:
    result = calculate_roe_ttm(inputs[0], inputs[1], inputs[2], _q4_ttm_average(inputs[3], inputs[4]))
    return replace(result, formula_version="roe-ttm-interim-v1")


def _calculate_annual_ytd_roa(inputs: tuple[Number, ...]) -> MetricResult:
    """Q4: the full-year YTD profit is already trailing twelve months."""
    result = calculate_roa_ttm(inputs[0], 0, 0, _q4_ttm_average(inputs[1], inputs[2]))
    return replace(result, formula_version="roa-ttm-annual-ytd-v1")


def _calculate_annual_ytd_roe(inputs: tuple[Number, ...]) -> MetricResult:
    result = calculate_roe_ttm(inputs[0], 0, 0, _q4_ttm_average(inputs[1], inputs[2]))
    return replace(result, formula_version="roe-ttm-annual-ytd-v1")


_AMOUNT = "billion_vnd"
_POINT_IN_TIME = "point_in_time"
_AMOUNT_INPUTS_3 = (_AMOUNT, _AMOUNT, _AMOUNT)
_AMOUNT_INPUTS_2 = (_AMOUNT, _AMOUNT)
_AMOUNT_INPUTS_4 = (_AMOUNT, _AMOUNT, _AMOUNT, _AMOUNT)
_POINT_INPUTS_3 = (_POINT_IN_TIME, _POINT_IN_TIME, _POINT_IN_TIME)
_POINT_INPUTS_2 = (_POINT_IN_TIME, _POINT_IN_TIME)
_Q4_TTM_INPUT_BASES = ("annual", "annual", _POINT_IN_TIME, _POINT_IN_TIME)
_OPERATIONAL_DERIVED_FORMULAS = {
    ("bank.input.npl_g35_balance", "npl-g35-balance-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.input.npl_g35_balance",
        formula_version="npl-g35-balance-v1",
        input_metric_ids=(
            "bank.input.npl_group_3_balance",
            "bank.input.npl_group_4_balance",
            "bank.input.npl_group_5_balance",
        ),
        input_units=_AMOUNT_INPUTS_3,
        input_period_bases=_POINT_INPUTS_3,
        output_unit=_AMOUNT,
        output_period_basis=_POINT_IN_TIME,
        tolerance=Decimal("0.0000001"),
        period_rule="same_period",
        calculate=lambda inputs: calculate_npl_g35_balance(*inputs),
    ),
    ("bank.input.parent_attributable_equity", "parent-attributable-equity-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.input.parent_attributable_equity",
        formula_version="parent-attributable-equity-v1",
        input_metric_ids=(
            "bank.input.total_equity",
            "bank.input.non_controlling_interests",
        ),
        input_units=_AMOUNT_INPUTS_2,
        input_period_bases=_POINT_INPUTS_2,
        output_unit=_AMOUNT,
        output_period_basis=_POINT_IN_TIME,
        tolerance=Decimal("0.0000001"),
        period_rule="same_period",
        calculate=lambda inputs: calculate_parent_attributable_equity(*inputs),
    ),
    ("bank.npl_g35", "npl-g35-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.npl_g35",
        formula_version="npl-g35-v1",
        input_metric_ids=(
            "bank.input.npl_group_3_balance",
            "bank.input.npl_group_4_balance",
            "bank.input.npl_group_5_balance",
            "bank.input.gross_customer_loans",
        ),
        input_units=_AMOUNT_INPUTS_4,
        input_period_bases=(_POINT_IN_TIME,) * 4,
        output_unit="percent",
        output_period_basis=_POINT_IN_TIME,
        tolerance=Decimal("0.00005"),
        period_rule="same_period",
        calculate=lambda inputs: calculate_npl(*inputs),
    ),
    ("bank.llr_coverage", "llr-coverage-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.llr_coverage",
        formula_version="llr-coverage-v1",
        input_metric_ids=(
            "bank.input.loan_loss_provisions",
            "bank.input.npl_g35_balance",
        ),
        input_units=_AMOUNT_INPUTS_2,
        input_period_bases=_POINT_INPUTS_2,
        output_unit="percent",
        output_period_basis=_POINT_IN_TIME,
        tolerance=Decimal("0.00005"),
        period_rule="same_period",
        calculate=lambda inputs: calculate_llr(*inputs),
    ),
    ("bank.roa", "roa-ttm-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roa",
        formula_version="roa-ttm-v1",
        input_metric_ids=(
            "bank.input.profit_after_tax",
            "bank.input.profit_after_tax",
            "bank.input.total_assets",
            "bank.input.total_assets",
        ),
        input_units=_AMOUNT_INPUTS_4,
        input_period_bases=_Q4_TTM_INPUT_BASES,
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="q4_ttm",
        calculate=_calculate_q4_roa_ttm,
    ),
    ("bank.roe", "roe-ttm-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roe",
        formula_version="roe-ttm-v1",
        input_metric_ids=(
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_equity",
            "bank.input.parent_attributable_equity",
        ),
        input_units=_AMOUNT_INPUTS_4,
        input_period_bases=_Q4_TTM_INPUT_BASES,
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="q4_ttm",
        calculate=_calculate_q4_roe_ttm,
    ),
    ("bank.roa", "roa-ttm-interim-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roa",
        formula_version="roa-ttm-interim-v1",
        input_metric_ids=(
            "bank.input.profit_after_tax",
            "bank.input.profit_after_tax",
            "bank.input.profit_after_tax",
            "bank.input.total_assets",
            "bank.input.total_assets",
        ),
        input_units=(_AMOUNT,) * 5,
        input_period_bases=("ytd", "ytd", "ytd", _POINT_IN_TIME, _POINT_IN_TIME),
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="interim_ttm",
        calculate=_calculate_interim_roa_ttm,
    ),
    ("bank.roe", "roe-ttm-interim-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roe",
        formula_version="roe-ttm-interim-v1",
        input_metric_ids=(
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_equity",
            "bank.input.parent_attributable_equity",
        ),
        input_units=(_AMOUNT,) * 5,
        input_period_bases=("ytd", "ytd", "ytd", _POINT_IN_TIME, _POINT_IN_TIME),
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="interim_ttm",
        calculate=_calculate_interim_roe_ttm,
    ),
    ("bank.roa", "roa-ttm-annual-ytd-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roa",
        formula_version="roa-ttm-annual-ytd-v1",
        input_metric_ids=("bank.input.profit_after_tax", "bank.input.total_assets", "bank.input.total_assets"),
        input_units=(_AMOUNT,) * 3,
        input_period_bases=("ytd", _POINT_IN_TIME, _POINT_IN_TIME),
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="annual_ytd",
        calculate=_calculate_annual_ytd_roa,
    ),
    ("bank.roe", "roe-ttm-annual-ytd-v1"): OperationalDerivedFormulaSpec(
        metric_id="bank.roe",
        formula_version="roe-ttm-annual-ytd-v1",
        input_metric_ids=(
            "bank.input.parent_attributable_profit",
            "bank.input.parent_attributable_equity",
            "bank.input.parent_attributable_equity",
        ),
        input_units=(_AMOUNT,) * 3,
        input_period_bases=("ytd", _POINT_IN_TIME, _POINT_IN_TIME),
        output_unit="percent",
        output_period_basis="ttm",
        tolerance=Decimal("0.00005"),
        period_rule="annual_ytd",
        calculate=_calculate_annual_ytd_roe,
    ),
}


def operational_derived_formula(
    metric_id: str,
    formula_version: str,
) -> OperationalDerivedFormulaSpec | None:
    """Return one explicit formula contract for operational snapshot promotion."""

    return _OPERATIONAL_DERIVED_FORMULAS.get((metric_id, formula_version))
