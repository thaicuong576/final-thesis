from decimal import Decimal
import unittest

from thesis_data.metrics import (
    QualityStatus,
    calculate_cir_operating_expense,
    calculate_llr,
    calculate_npl,
    calculate_peer_median,
    calculate_roa,
    calculate_roa_from_ytd,
    calculate_roa_ttm,
    calculate_roe_ttm,
    normalize_percent,
    normalize_vnd_billion,
)


class MetricTests(unittest.TestCase):
    def test_npl_uses_group_three_to_five_over_gross_loans(self):
        result = calculate_npl(Decimal("10"), Decimal("20"), Decimal("30"), Decimal("1000"))
        self.assertEqual(result.value, Decimal("6"))
        self.assertEqual(result.unit, "%")
        self.assertEqual(result.quality_status, QualityStatus.VALID)

    def test_llr_returns_null_for_zero_npl_balance(self):
        result = calculate_llr(Decimal("25"), Decimal("0"))
        self.assertIsNone(result.value)
        self.assertEqual(result.quality_status, QualityStatus.MISSING)
        self.assertEqual(result.reason, "zero_denominator")

    def test_cir_returns_null_when_an_input_is_missing(self):
        result = calculate_cir_operating_expense(None, Decimal("100"))
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "missing_input")

    def test_roa_uses_average_assets(self):
        result = calculate_roa(Decimal("12"), Decimal("400"))
        self.assertEqual(result.value, Decimal("3"))

    def test_roa_from_ytd_subtracts_prior_quarter_within_fiscal_year(self):
        result = calculate_roa_from_ytd(
            Decimal("30"),
            Decimal("18"),
            Decimal("400"),
            current_fiscal_year=2024,
            prior_fiscal_year=2024,
        )
        self.assertEqual(result.value, Decimal("3"))
        self.assertEqual(result.period_basis, "quarter_only")

    def test_roa_from_ytd_rejects_cross_fiscal_year_subtraction(self):
        result = calculate_roa_from_ytd(
            Decimal("30"),
            Decimal("18"),
            Decimal("400"),
            current_fiscal_year=2025,
            prior_fiscal_year=2024,
        )
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "cross_fiscal_year_subtraction")

    def test_roa_ttm_uses_prior_fy_minus_prior_ytd_plus_current_ytd(self):
        result = calculate_roa_ttm(
            Decimal("6774568"),
            Decimal("4101950"),
            Decimal("8494171"),
            Decimal("840979451.5"),
        )
        self.assertEqual(result.value, Decimal("1.3278"))
        self.assertEqual(result.period_basis, "ttm")
        self.assertEqual(result.formula_version, "roa-ttm-v1")

    def test_roe_ttm_uses_parent_attributable_profit_and_average_equity(self):
        result = calculate_roe_ttm(
            Decimal("7125083"),
            Decimal("5597747"),
            Decimal("9973939"),
            Decimal("138931332.5"),
        )
        self.assertEqual(result.value, Decimal("8.2784"))
        self.assertEqual(result.period_basis, "ttm")
        self.assertEqual(result.formula_version, "roe-ttm-v1")

    def test_ttm_ratios_return_missing_when_a_flow_input_is_missing(self):
        result = calculate_roa_ttm(None, Decimal("1"), Decimal("2"), Decimal("100"))
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "missing_input")

    def test_normalize_percent_converts_decimal_to_percentage(self):
        self.assertEqual(normalize_percent(Decimal("0.125"), "decimal"), Decimal("12.5"))
        self.assertEqual(normalize_percent(Decimal("12.5"), "%"), Decimal("12.5"))

    def test_normalize_vnd_billion_converts_millions(self):
        self.assertEqual(
            normalize_vnd_billion(Decimal("1250"), "million_vnd"),
            Decimal("1.25"),
        )

    def test_peer_median_ignores_missing_values(self):
        result = calculate_peer_median(
            [Decimal("1"), None, Decimal("3"), Decimal("2"), Decimal("4")]
        )
        self.assertEqual(result.value, Decimal("2.5"))
