# Quarterly operational inputs — top-10 listed banks, 2024 Q1 to 2026 Q2 (D-079)

`inputs.csv` is the sole input of `scripts/build_quarterly_snapshot.py`. It produces
`data/processed/bank-quarterly-top10-operational-v1.sqlite` (dataset
`bank-quarterly-top10-operational-v1`). This is an operational product snapshot.
It is not the Gold evaluation benchmark.

```bash
PYTHONPATH=src python scripts/build_quarterly_snapshot.py \
  --inputs data/onboarding/quarterly-top10/inputs.csv \
  --out data/processed/bank-quarterly-top10-operational-v1.sqlite \
  --names data/onboarding/top10-2025/banks.json
```

## Coverage (NPL, LLR coverage, ROA, ROE per bank-quarter)

| Bank | 2024 Q1 | 2024 Q2 | 2024 Q3 | 2024 Q4 | 2025 Q1 | 2025 Q2 | 2025 Q3 | 2025 Q4 | 2026 Q1 | 2026 Q2 |
|---|---|---|---|---|---|---|---|---|---|---|
| ACB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BID | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CTG | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HDB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MBB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SHB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| STB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| TCB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| VCB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| VPB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

That is 100 of 100 bank-quarters and 400 ratio values (revision r3, 2026-10-02).
Revisions r1 and r2 had 92 bank-quarters: eight consolidated filings were missing from
the usual Vietstock path. They were found elsewhere (see Sources) and added in r3.
The 368 ratio values of r2 are unchanged in r3. No value is imputed anywhere; if a
quarter is ever missing, medians and ranks use fewer banks and the reports say so
(for example, "hạng 2/7").

## Sources

- Quarterly consolidated interim statements are listed in
  `data/raw/official/bank-quarterly-v1/SOURCES.txt`.
  - Most come from the Vietstock mirror; VPB 2025 Q3 comes from VPBank IR.
  - ACB 2024 Q2 comes from ACB IR (the same file is used by Gold v5).
  - Every row carries the SHA-256 of the exact PDF.
- The eight quarters added in r3 come from these places:
  - ACB 2026 Q1: ACB investor relations (acb.com.vn).
  - BID 2024 Q3: BIDV investor relations (bidv.com.vn).
  - CTG 2024 Q3 and 2025 Q3: VietinBank investor site (investor.vietinbank.vn).
  - HDB 2024 Q3: HDBank investor relations (cdn.hdbank.com.vn).
  - VPB 2026 Q1: CafeF document mirror of the VPBank consolidated Q1 filing.
  - SHB 2024 Q2 and VPB 2026 Q2: the **reviewed semi-annual** consolidated statements on
    Vietstock (`..._6T_<year>_Soatxet_Hopnhat.pdf`). Their locators carry
    `filing=báo cáo bán niên đã soát xét`. The other quarters use unreviewed quarterly
    statements, so these two cells rest on a stronger filing than their neighbours.
- 2025 Q4 values, and the 2024 Q4 values that FY2025 needs, are the audited FY2025 rows
  of `data/onboarding/top10-2025` (D-078). They take precedence over interim readings.
- The file Vietstock publishes at `TCB_..._Q4_2024_Hopnhat.pdf` actually contains the
  2023 Q4 report.
  - It is stored as `TCB_2023Q4.pdf` and used only for 2023 comparatives.
  - The real 2024 Q4 report is `..._Hopnhat_1.pdf`.

## How values were read

1. Every page was text-extracted, using the PDF text layer where one exists and
   otherwise Tesseract 5 (200 dpi and 300 dpi passes).
2. An extractor accepted a value automatically only when an arithmetic check held. For
   example, the five loan groups must add to the printed total, or two OCR passes must
   agree (`reading=confirmed` or `confirmed_ocr_twice`).
3. Every other cell was read visually from a rendered crop of the page (`reading=visual`).
   - Each visual reading was checked against the statement's own identity: assets equal
     liabilities plus equity, groups add to the total, YTD profit equals the
     before-tax figure minus tax.
4. `reading=single` (29 cells) means one OCR pass with no second confirmation. These
   values were accepted because they agree with Gold or move consistently with
   neighbouring quarters.
5. `comparative_only` (26 cells) were taken from the prior-period column of a later
   filing, mainly for 2023 profits needed by TTM.

Locators use Vietnamese statement/row labels (since revision r2). The current revision is r3,
snapshot `snapshot-ee70ddd78d8068a1ae86adeb7baa260841138fa4a3ff4dbde8896863d6989395`.
In r3 the 80 input cells of the eight added quarters are `reading=confirmed`: each was read from
the page text (text layer for ACB, Tesseract otherwise) and accepted only because an identity
held. The five loan groups add to the printed total, liabilities plus equity equal total assets,
the equity components add to total equity, gross loans minus provision equal the net loan line,
and profit after tax minus the non-controlling share equals parent profit. Balance-sheet and
income-statement comparatives in the new filings also equal the values already held for the
prior period. Each `source_locator` states the PDF page, the statement or note, the row, the column
(current or comparative) and the reading status.

## Definitions

These are the same as Gold v5 and D-078:

- NPL is groups 3 to 5 divided by gross loans.
  - Gross loans are the total of the loan-quality table.
  - Margin lending is excluded wherever it is reported outside the classification:
    ACB, TCB, and VPB (aligned to the FY2025 audited convention).
  - For ACB 2026 Q1 and VPB 2026 Q1/Q2 the provision is general plus specific provision,
    without the separate margin-lending provision, as in the audited FY2025 rows.
- LLR coverage is the balance-sheet loan-loss provision divided by NPL balance.
- ROA and ROE are trailing-twelve-month values:
  - Q1 to Q3 use `YTD(t) − YTD(t−4) + FY(y−1)` over the average of the period-end
    balance and the prior year-end balance (`roa-ttm-interim-v1`, `roe-ttm-interim-v1`).
  - Q4 uses the annual figure over the average of year-end balances
    (`*-ttm-annual-ytd-v1`).
  - ROE uses profit attributable to the parent over parent equity, which is total equity
    minus minority interests.

## Verification

- 76 quarterly ratio values overlap with Gold v5 (ACB, MBB, TCB, VCB, VPB, 2024); 66 agree.
  - VPB 2024 NPL is 0.05 to 0.08 points higher because margin lending is excluded here.
  - TCB 2024 Q1 to Q3 ROA/ROE in Gold are the bank's own rounded ratios computed on a
    different averaging basis. The input values match the filings.
  - VCB 2024 Q4 ROE (18.74 vs 18.60) uses audited restated 2024 equity.
- All 40 ratio values for 2025 Q4 equal the production FY2025 snapshot (D-078) exactly.
- The reviewer of record is `claude-orchestrator-filing-transcription`. The readings were
  made by an AI agent and have not had an independent human review.
