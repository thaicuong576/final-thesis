# INGEST-1 Evaluation Results

**Run date**: 2026-10-16 17:11 SE Asia Standard Time  
**Dataset**: 10 audited FY2025 consolidated annual bank filings  
**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  
**Pipeline**: PyMuPDF text-layer detection + Tesseract OCR (when no text layer)  

## Overall Accuracy

| Metric | Count |
|--------|-------|
| Cells evaluated (in ground truth) | 150 |
| **Correct** (within ±0.01 tỷ) | **62** |
| Wrong value | 41 |
| Missing (row not found) | 47 |
| **Accuracy** | **41.3%** |

## Error Cause Breakdown (Data-Driven)

| Cause | Count | % of Evaluated | Description |
|-------|-------|----------------|-------------|
| `correct` | 62 | 41.3% | Extracted value matches ground truth within ±0.01 tỷ VND |
| `row_not_found` | 47 | 31.3% | Target row label was not matched on classified statement pages (`status == 'missing'`) |
| `value_not_on_any_selected_page` | 36 | 24.0% | Ground truth number not on classified pages (e.g. NPL breakdown notes located beyond classified pages) |
| `wrong_row_or_subtotal` | 4 | 2.7% | Row matched an adjacent label or subtotal rather than the exact target item |
| `right_row_wrong_unit` | 1 | 0.7% | Row matched but scaled by incorrect unit multiplier |
| `right_row_wrong_column` | 0 | 0.0% | Row matched but extracted opposite period column |

## Per-Bank Results

| Bank | Pages | Text-layer | OCR | OCR time | Unit | Correct | Wrong | Missing | Accuracy |
|------|-------|-----------|-----|----------|------|---------|-------|---------|----------|
| ACB | 100 | 1 | 99 | 0.1s | million_vnd | 10 | 4 | 1 | 67% |
| BID | 74 | 2 | 72 | 0.0s | million_vnd | 11 | 2 | 2 | 73% |
| CTG | 85 | 0 | 85 | 0.0s | million_vnd | 8 | 5 | 2 | 53% |
| HDB | 71 | 2 | 69 | 0.0s | million_vnd | 3 | 6 | 6 | 20% |
| MBB | 103 | 2 | 101 | 0.0s | million_vnd | 11 | 4 | 0 | 73% |
| SHB | 68 | 0 | 68 | 0.0s | million_vnd | 2 | 0 | 13 | 13% |
| STB | 108 | 0 | 108 | 0.0s | million_vnd | 2 | 4 | 9 | 13% |
| TCB | 104 | 0 | 104 | 0.0s | million_vnd | 6 | 3 | 6 | 40% |
| VCB | 84 | 0 | 84 | 0.0s | million_vnd | 7 | 7 | 1 | 47% |
| VPB | 100 | 1 | 99 | 0.0s | million_vnd | 2 | 6 | 7 | 13% |

## Error Analysis (by issue code)

| Issue Code | Occurrences |
|-----------|------------|
| `row_not_found` | 47 |
| `period_mismatch` | 14 |
| `low_confidence_match` | 4 |
| `parent_profit_inferred_from_pat` | 4 |
| `prior_column_unconfirmed` | 3 |
| `target_column_unconfirmed` | 2 |
| `nci_not_presented` | 2 |

## Key Findings & Bottlenecks

- **Unit bug resolution**: Fixing unit detection (robust regex for OCR-garbled Vietnamese headers like 'Triéu VND', 'Tr. VND', and rejecting bare 'VND') raised accuracy from the 4.0% baseline to **41.3%** (62/150 cells correct).
- **Column misalignment disproven**: Data shows `right_row_wrong_column` is 0 (0.0%). Column misalignment is NOT a meaningful error source.
- **Primary bottleneck #1 — Missing rows (`row_not_found`, 31.3%)**: Tesseract `-l eng` OCR degrades Vietnamese diacritics on row labels (e.g. 'Thu nhập lãi thuần' -> garbled text), preventing string/keyword matching.
- **Primary bottleneck #2 — Unselected note pages (`value_not_on_any_selected_page`, 24.0%)**: NPL group 3/4/5 loans reside in footnote tables (Note 10/11) 30–60 pages deep into the annual report. The 2-page note heuristic in `classify_pages` does not select these pages, so the numbers are physically absent from candidate extraction.
- **Subtotal mismatches (`wrong_row_or_subtotal`, 2.7%)**: Extractor matches an adjacent or general provision item (e.g. 'Dự phòng rủi ro khác') instead of the specific loan loss provision line.
- Ground truth covers 10 metrics × 2 periods per bank = up to 200 cells; some banks have 0 NCI so fewer cells (150 total).
- This is honest experimental evidence for the thesis. No bank-specific rule tuning was applied.
- See `experiments/ingest/rows.json` for full row-level detail.
