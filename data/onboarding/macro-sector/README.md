# Macro and sector inputs (MACRO-DATA v1)

`inputs.csv` is the optional second input of `scripts/build_quarterly_snapshot.py --macro-inputs`.
It adds the entity `VN` (macro) with period-aligned observations for 2022_Q4 to 2026_Q2.
It is an operational product input, not the Gold evaluation benchmark. The A/B/C experiments
ran on bank data only and are not affected.

```bash
PYTHONPATH=src python scripts/build_quarterly_snapshot.py \
  --inputs data/onboarding/quarterly-top10/inputs.csv \
  --macro-inputs data/onboarding/macro-sector/inputs.csv \
  --out data/processed/bank-quarterly-top10-macro-v1.sqlite \
  --names data/onboarding/top10-2025/banks.json
```

## How the rows were produced

1. Four research workers collected candidate series from official publishers (SBV, National
   Statistics Office, Government portal), each with URL, publication date and a verbatim quote.
2. An independent check re-opened 28 randomly drawn URLs from the candidate files: 21 matched, none contradicted the number,
   7 had a wrong link or a page without the number. A second independent check of 25 random rows of this final CSV:
   20 matched, 0 differed, 0 wrong basis, 5 could not be confirmed (one page rendered blank, which row was then dropped;
   four policy-rate rows for 2025-2026, see below).
3. Three curation workers re-opened EVERY row, checked that the number is on the page and that its
   basis fits the metric (for example a 9-month average is not a quarter value), and computed a
   SHA-256 of the page content. Rows that failed any step were dropped (not estimated).

## Rules

- `source_tier=primary` becomes `valid`; `secondary` is loaded as `pending_validation` and is not
  used in reports.
- No interpolation and no estimates: a quarter without a verified source stays empty.
- Policy rates (refinancing, rediscount) for 2024_Q4 to 2026_Q2 are carried forward: decision 1123/QĐ-NHNN
  (4.5% / 3.0%) remains in force and an official Government-portal article says the policy rates are kept
  unchanged. The article does not repeat the numbers, so these 14 rows are qualitative confirmations, stated in `source_locator`.
- Sector rows: only official, system-wide figures. NPL ratios that exclude special-control banks use the separate metric
  `sector.system_npl_ratio_excl_special_control` and must not be compared with `sector.system_npl_ratio`.
- GDP for the latest quarters may be preliminary ("ước đạt") in the NSO release.
- Not included: interbank exchange rates and interbank overnight rate (no primary quarterly series),
  USD/VND central rate (no stable primary permalink), core inflation for quarters where NSO only
  publishes cumulative figures.
