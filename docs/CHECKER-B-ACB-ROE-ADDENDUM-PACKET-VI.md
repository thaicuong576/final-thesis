# Checker B - ACB ROE addendum

## Purpose

The official consolidated ACB filings contain enough statement inputs to test a
new, explicit ROE candidate route for Q2--Q4 2024. This is an addendum to the
completed 48-cell review. It does not rewrite the original Checker-B file or
change any Gold status.

## Cells

- ACB, 2024_Q2, `bank.roe`
- ACB, 2024_Q3, `bank.roe`
- ACB, 2024_Q4, `bank.roe`

## Permitted evidence

- `data/raw/official/gold-bank-2025-pilot-v1/ACB_2024_Q2_consolidated.pdf`
- `data/raw/official/gold-bank-2025-pilot-v1/ACB_2024_Q3_consolidated.pdf`
- `data/raw/official/gold-bank-2025-pilot-v1/ACB_2024_Q4_consolidated.pdf`
- The issuer's official source URL recorded in the source manifest.

Inspect the consolidated statement pages for total equity and profit after tax,
and the note listing subsidiary ownership. The candidate route uses the frozen
ROE TTM formula `prior_fy - prior_ytd + current_ytd`, divided by beginning/end
average total equity. Confirm independently whether the filing supports using
consolidated profit after tax as the shareholder-profit numerator, including
whether the 100% subsidiary ownership and absence of a separate non-controlling
interest line are sufficient for this convention.

## Do not use

- Checker A, Checker B's original 48-cell file, the merged ledger, or the
  adjudication overlay.
- Vendor values or the candidate JSONL/SQLite files, which would reveal the
  proposed calculation and create anchoring.

## Required output

Fill only:

`data/reconciliation/gold-bank-2025-pilot-v1/private-review-ai/checker-b-acb-roe-addendum-v1.csv`

For each row, provide a decision, numeric value and `%` unit if accepted,
`ttm` period basis if accepted, official source ID/URL/locator, consolidation
basis, `definition_match=yes`, timestamp, and a short note. If the convention
is not justified, use `missing` with a concrete reason. Do not guess or use an
unapproved fallback.

After filling, verify that all three rows have non-empty decision, checker ID,
timestamp, and notes, and that accepted rows have complete source mapping.
