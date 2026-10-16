# INGEST Evaluation Results: Full-file OCR & LLM Row Selection

**Run date**: 2026-10-16 23:40 SE Asia Standard Time  
**Dataset**: 10 audited FY2025 consolidated annual bank filings  
**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  
**LlamaParse tier**: `cost_effective` (version: `latest`)  
**Active run**: scope=`full`, llm_assist=`True`  

## Comparative Benchmark across Evaluation Phases

| Metric | Tesseract Baseline (INGEST-1) | LlamaParse Selected (INGEST-4) | LlamaParse Full (INGEST-6a) | LlamaParse Full + LLM Assist (INGEST-6b) |
|--------|-------------------------------|-----------------------|-----------------------------|-------------------------------------------|
| Cells evaluated in ground truth | 150 | 150 | 150 | 150 |
| **Correct (within ±0.01 tỷ)** | **62** | **84** | **93** | **94** |
| **Overall Accuracy** | **41.3%** | **56.0%** | **62.0%** | **62.7%** |
| Missing rows (`row_not_found`) | 47 (31.3%) | 23 (15.3%) | 8 | 8 |
| Unselected note pages (`value_not_on_any_selected_page`) | 36 (24.0%) | 31 (20.7%) | 10 | 10 |
| Wrong row / subtotal | 4 (2.7%) | 12 (8.0%) | 39 | 37 |
| Wrong column period | 0 (0.0%) | 0 (0.0%) | 0 | 1 |
| Total Pages Sent to OCR/Cloud | 868 pages (local OCR) | 148 pages | 897 pages | 897 pages |
| Total OCR Wall Time | ~1.5s (cached) | 179.8s | 381.6s | 0.9s |
| Estimated API Credits | 0 credits | 148 credits | 897 credits | 897 credits |
| OpenAI Tokens Used | 0 tokens | 0 tokens | 0 tokens | 139,385 tokens |

## Current Run Error Cause Breakdown (scope=full, llm_assist=True)

| Cause | Count | % of Evaluated | Description |
|-------|-------|----------------|-------------|
| `correct` | 94 | 62.7% | Extracted value matches ground truth within ±0.01 tỷ VND |
| `row_not_found` | 8 | 5.3% | Target row label was not matched on classified statement pages (`status == 'missing'`) |
| `value_not_on_any_selected_page` | 10 | 6.7% | Ground truth number not on classified pages (e.g. NPL breakdown notes located beyond classified pages) |
| `wrong_row_or_subtotal` | 37 | 24.7% | Row matched an adjacent label or subtotal rather than the exact target item |
| `right_row_wrong_unit` | 0 | 0.0% | Row matched but scaled by incorrect unit multiplier |
| `right_row_wrong_column` | 1 | 0.7% | Row matched but extracted opposite period column |

## Current Run Per-Bank Results (scope=full, llm_assist=True)

| Bank | Total Pages | Pages Sent to OCR | OCR Time | Unit | Tokens | Correct | Wrong | Missing | Accuracy |
|------|-------------|-------------------|----------|------|--------|---------|-------|---------|----------|
| ACB | 100 | 100 | 0.1s | million_vnd | 18,035 | 9 | 6 | 0 | 60% |
| BID | 74 | 74 | 0.1s | million_vnd | 15,297 | 7 | 8 | 0 | 47% |
| CTG | 85 | 85 | 0.1s | million_vnd | 15,217 | 9 | 6 | 0 | 60% |
| HDB | 71 | 71 | 0.1s | million_vnd | 14,505 | 11 | 4 | 0 | 73% |
| MBB | 103 | 103 | 0.1s | million_vnd | 10,186 | 12 | 3 | 0 | 80% |
| SHB | 68 | 68 | 0.1s | million_vnd | 16,148 | 8 | 5 | 2 | 53% |
| STB | 108 | 108 | 0.1s | million_vnd | 13,269 | 7 | 2 | 6 | 47% |
| TCB | 104 | 104 | 0.1s | million_vnd | 9,846 | 11 | 4 | 0 | 73% |
| VCB | 84 | 84 | 0.1s | million_vnd | 13,567 | 9 | 6 | 0 | 60% |
| VPB | 100 | 100 | 0.1s | million_vnd | 13,315 | 11 | 4 | 0 | 73% |

## Current Run Error Analysis (by issue code)

| Issue Code | Occurrences |
|-----------|------------|
| `llm_selected` | 41 |
| `period_mismatch` | 19 |
| `column_missing` | 4 |
| `row_not_found` | 4 |
| `target_column_unconfirmed` | 1 |

## Wrong Row / Subtotal Breakdown by Metric

| Metric ID | Wrong Matches | Failure Mode / Root Cause |
|-----------|---------------|---------------------------|
| `bank.input.parent_attributable_profit` | 8 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.npl_group_4_balance` | 7 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.npl_group_3_balance` | 5 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.npl_group_5_balance` | 5 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.gross_customer_loans` | 5 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.loan_loss_provisions` | 2 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.profit_after_tax` | 2 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.total_assets` | 1 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.total_equity` | 1 | Matched adjacent note breakdown line or component subtotal instead of primary statement |
| `bank.input.non_controlling_interests` | 1 | Matched adjacent note breakdown line or component subtotal instead of primary statement |

## Key Findings & Architecture Impact

- **Full-file OCR Impact (INGEST-6a)**: Running LlamaParse across all document pages discovered loan quality footnote tables located deep in notes (pages 30-70), slashing `row_not_found` from 23 to 8 and `value_not_on_any_selected_page` from 31 to 10. Accuracy increased from 56.0% to 62.0%.
- **Rise of `wrong_row_or_subtotal` (from 12 to 39)**: With full-file OCR scanning all 70-108 pages, identical or similar account labels (e.g. 'Cho vay khách hàng', 'Dự phòng rủi ro tín dụng', 'Lợi nhuận sau thuế') appear on multiple disclosure notes (segment reports, credit risk breakdown, fee income sub-tables, subsequent events). The rule-based matcher found candidate lines with high lexical scores on note pages outside the core balance sheet / income statement, selecting a sub-component rather than the headline financial statement line. This highlights the exact boundary where rule-based heuristics require statement-page precedence or model discrimination.
- **LLM Row Selection Discipline (D-086)**: The LLM acts solely as a discriminator among numbered printed lines; code deterministically extracts numbers, applies unit multiplier, and verifies text inclusion (`value_in_page_text`). The model never writes or generates numerical figures.
- **Budget & Cost Tracking**: LlamaParse usage is bounded by `llama_max_pages_per_filing` (default 300) and disk caching by `(sha256, chunk_range, tier)` prevents re-billing on identical filings.
- Full row details are saved in `experiments/ingest/rows_llamaparse_full_llm.json`.
