# Metric Dictionary

Status: Working definition for the scoped applied-thesis benchmark. A metric becomes accepted only after its inputs, source meaning, units, period basis, and manual example pass validation.

## Scope

The default first baseline uses the 48-cell pilot: ACB, TCB, and VPB across
`2024_Q1` through `2024_Q4`. The five-bank/eight-quarter design is a
conditional expansion, not a prerequisite for the first result. Metrics are
computed by code from normalized observations. Vendor-provided ratios are
retained as source observations and are not silently promoted to canonical
values.

## Common rules

- Ratio units are percentage points in stored display values unless the observation explicitly records a decimal representation; conversion is explicit and tested.
- Monetary amounts use VND billion in normalized storage.
- A balance-sheet metric is point-in-time and uses the statement reporting date.
- An income-statement metric is a flow. Vietnamese interim statements are YTD by default; quarter-only flow is `current_fiscal_year_ytd - prior_quarter_fiscal_year_ytd` within the same fiscal year.
- Annual values are not substituted for quarterly values without a labeled annual-basis rule.
- A missing value remains null with a reason. A zero denominator produces null with `zero_denominator` status.
- Conflicting source variants are retained as separate observations and resolved through reconciliation; they are not overwritten.
- Every accepted metric includes source ID, source locator, period, unit, quality status, and formula version.
- The TTM profitability implementation uses `roa-ttm-v1` and `roe-ttm-v1`:
  `prior_fy - prior_ytd + current_ytd`, divided by the beginning/end average
  balance-sheet denominator, then rounded to four percentage points for the
  pilot candidate snapshot.
- For the comparative bank ROE benchmark, the working convention is
  `parent_attributable_equity`: profit attributable to bank shareholders
  divided by average equity attributable to the parent, calculated as total
  consolidated equity minus non-controlling interest at each endpoint. A
  source-disclosed or total-equity ROE variant is not interchangeable with
  this convention and must remain outside a comparative Gold run until
  explicitly reconciled.

## Primary metrics

| Metric ID | Meaning | Formula | Basis | Unit | Primary source | Acceptance note |
|---|---|---|---|---|---|---|
| `bank.npl_g35` | Share of loans in groups 3–5 | `(stage_3 + stage_4 + stage_5) / gross_loans` | Point-in-time | `%` | Audited/interim issuer statement or notes | Stage mapping and loan denominator must be recorded. |
| `bank.llr_coverage` | Provision coverage of group 3–5 NPL | `loan_loss_provisions / npl_g35_balance` | Point-in-time | `%` | Issuer statement/notes | Provision scope must match the NPL numerator. |
| `bank.cir` | Operating efficiency | `operating_expense / total_operating_income` | Quarter-only or source-disclosed period | `%` | Issuer income statement | Numerator and TOI mapping must be documented. |
| `bank.roa` | Profitability relative to assets | `net_profit / average_total_assets` | Quarter-only or source-disclosed period | `%` | Issuer statement plus balance sheet | Profit convention and average-balance convention are recorded. For the VPB pilot TTM variant, `ttm_profit = prior_fy_profit - prior_ytd_profit + current_ytd_profit`, then divide by beginning/end average assets. |
| `bank.roe` | Profitability relative to equity | `parent_attributable_profit / average_parent_attributable_equity` | Quarter-only or source-disclosed period | `%` | Issuer statement plus balance sheet | Comparative benchmark convention: parent-attributable profit over average `(total consolidated equity - NCI)`. For TTM, use `prior_fy - prior_ytd + current_ytd`; for Q4 use FY2024. |

## Conditional and extension metrics

These metrics are not part of the primary gate until their definitions and coverage are demonstrated.

| Metric ID | Formula or source rule | Why conditional |
|---|---|---|
| `bank.nim` | `net_interest_income / average_earning_assets` | Earning-asset categories are not uniformly exposed by the tested sources. |
| `bank.casa` | `demand_deposits / customer_deposits` | Deposit category mapping varies by source and note presentation. |
| `bank.ldr_simple` | `gross_loans / customer_deposits` | This is a simple analytical ratio, not automatically the regulatory LDR definition. |
| `bank.car_disclosed` | Use source-disclosed regulatory CAR | CAR should not be reconstructed from ordinary statements for the MVP. |
| `sector.peer_median` | Median of accepted issuer observations for one metric, period, and peer set | Peer membership and missing-value policy must be frozen. |
| `sector.percentile` | Deterministic percentile rank within the frozen peer set | Rank direction and interpolation rule must be fixed. |
| `macro.policy_rate` | Official SBV rate level and change | Rate type and effective date must be explicit. |
| `macro.credit_growth` | Official source-disclosed system credit-growth value | Publication date and period basis must be aligned. |

## Period and source handling

For every derived flow metric, store both the source YTD inputs and the derived quarter-only observation. If only an annual or TTM vendor ratio is available, retain it as a non-equivalent variant and do not mix it with quarter-only values in peer statistics.

Source tiers are `primary`, `accelerator`, `cross_check`, and `context`. Only primary or explicitly reconciled cross-check observations may enter the gold benchmark. Fallback macro data can remain in the staging store but cannot be presented as official SBV/GSO evidence.

## Required formula tests

Each implementation must test:

- normal positive values;
- missing numerator or denominator;
- zero denominator;
- percent-to-decimal and VND-million/billion conversions;
- YTD-to-quarter subtraction within a fiscal year;
- rejection of cross-fiscal-year subtraction;
- conflicting source variants;
- peer median with null values and an all-null peer set.
