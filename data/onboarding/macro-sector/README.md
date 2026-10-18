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
2. An independent check re-opened 28 randomly drawn URLs: 21 matched, none contradicted the number,
   7 had a wrong link or a page without the number.
3. Three curation workers re-opened EVERY row, checked that the number is on the page and that its
   basis fits the metric (for example a 9-month average is not a quarter value), and computed a
   SHA-256 of the page content. Rows that failed any step were dropped (not estimated).

## Rules

- `source_tier=primary` becomes `valid`; `secondary` is loaded as `pending_validation` and is not
  used in reports.
- No interpolation and no estimates: a quarter without a verified source stays empty.
- Policy rates for 2024_Q4 to 2026_Q2 rest on decision 1123/QĐ-NHNN remaining in force; the source
  confirming no replacing decision was accessed on 2026-10-18 (stated in `source_locator`).
- GDP for the latest quarters may be preliminary ("ước đạt") in the NSO release.
- Not included: interbank exchange rates and interbank overnight rate (no primary quarterly series),
  USD/VND central rate (no stable primary permalink), core inflation for quarters where NSO only
  publishes cumulative figures.
