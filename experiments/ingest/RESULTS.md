# INGEST Evaluation Results: Full-file OCR & LLM Row Selection

**Run date**: 2026-10-16 23:27 SE Asia Standard Time  
**Dataset**: 10 audited FY2025 consolidated annual bank filings  
**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  
**LlamaParse tier**: `cost_effective` (version: `latest`)  
**Active run**: scope=`full`, llm_assist=`True`  

## Comparative Benchmark across Evaluation Phases

| Metric | Tesseract Baseline (INGEST-1) | LlamaParse Selected (INGEST-4) | LlamaParse Full (INGEST-6a) | LlamaParse Full + LLM Assist (INGEST-6b) |
|--------|-------------------------------|-----------------------|-----------------------------|-------------------------------------------|
| Cells evaluated in ground truth | 150 | 150 | 150 | 150 |
| **Correct (within ±0.01 tỷ)** | **62** | **84** | **93** | **93** |
| **Overall Accuracy** | **41.3%** | **56.0%** | **62.0%** | **62.0%** |
| Missing rows (`row_not_found`) | 47 (31.3%) | 23 (15.3%) | 8 | 8 |
| Unselected note pages (`value_not_on_any_selected_page`) | 36 (24.0%) | 31 (20.7%) | 10 | 10 |
| Wrong row / subtotal | 4 (2.7%) | 12 (8.0%) | 39 | 39 |
| Wrong column period | 0 (0.0%) | 0 (0.0%) | 0 | 0 |
| Total Pages Sent to OCR/Cloud | 868 pages (local OCR) | 148 pages | 897 pages | 897 pages |
| Total OCR Wall Time | ~1.5s (cached) | 179.8s | 381.6s | 12.8s |
| Estimated API Credits | 0 credits | 148 credits | 897 credits | 897 credits |
| OpenAI Tokens Used | 0 tokens | 0 tokens | 0 tokens | 0 tokens |

## Current Run Error Cause Breakdown (scope=full, llm_assist=True)

| Cause | Count | % of Evaluated | Description |
|-------|-------|----------------|-------------|
| `correct` | 93 | 62.0% | Extracted value matches ground truth within ±0.01 tỷ VND |
| `row_not_found` | 8 | 5.3% | Target row label was not matched on classified statement pages (`status == 'missing'`) |
| `value_not_on_any_selected_page` | 10 | 6.7% | Ground truth number not on classified pages (e.g. NPL breakdown notes located beyond classified pages) |
| `wrong_row_or_subtotal` | 39 | 26.0% | Row matched an adjacent label or subtotal rather than the exact target item |
| `right_row_wrong_unit` | 0 | 0.0% | Row matched but scaled by incorrect unit multiplier |
| `right_row_wrong_column` | 0 | 0.0% | Row matched but extracted opposite period column |

## Current Run Per-Bank Results (scope=full, llm_assist=True)

| Bank | Total Pages | Pages Sent to OCR | OCR Time | Unit | Tokens | Correct | Wrong | Missing | Accuracy |
|------|-------------|-------------------|----------|------|--------|---------|-------|---------|----------|
| ACB | 100 | 100 | 1.4s | million_vnd | 0 | 8 | 7 | 0 | 53% |
| BID | 74 | 74 | 1.1s | million_vnd | 0 | 4 | 11 | 0 | 27% |
| CTG | 85 | 85 | 1.4s | million_vnd | 0 | 11 | 4 | 0 | 73% |
| HDB | 71 | 71 | 1.0s | million_vnd | 0 | 13 | 2 | 0 | 87% |
| MBB | 103 | 103 | 1.3s | million_vnd | 0 | 11 | 4 | 0 | 73% |
| SHB | 68 | 68 | 1.0s | million_vnd | 0 | 8 | 5 | 2 | 53% |
| STB | 108 | 108 | 1.4s | million_vnd | 0 | 5 | 4 | 6 | 33% |
| TCB | 104 | 104 | 1.2s | million_vnd | 0 | 10 | 5 | 0 | 67% |
| VCB | 84 | 84 | 2.0s | million_vnd | 0 | 12 | 3 | 0 | 80% |
| VPB | 100 | 100 | 1.2s | million_vnd | 0 | 11 | 4 | 0 | 73% |

## Current Run Error Analysis (by issue code)

| Issue Code | Occurrences |
|-----------|------------|
| `period_mismatch` | 21 |
| `target_column_unconfirmed` | 5 |
| `column_missing` | 4 |
| `row_not_found` | 4 |
| `low_confidence_match` | 2 |

## Key Findings & Architecture Impact

- **Full-file OCR Impact (INGEST-6a)**: Running LlamaParse across all document pages allows page classification to discover loan footnote breakdown tables located deep in notes (30-60 pages in), reducing `value_not_on_any_selected_page` errors.
- **LLM Row Selection Discipline (D-086)**: The LLM acts solely as a discriminator among numbered printed lines; code deterministically extracts numbers, applies unit multiplier, and verifies text inclusion (`value_in_page_text`).
- **Budget & Cost Tracking**: LlamaParse usage is bounded by `llama_max_pages_per_filing` (default 300) and disk caching by `(sha256, chunk_range, tier)` prevents re-billing on identical filings.
- Full row details are saved in `experiments/ingest/rows_llamaparse_full_llm.json`.
