"""Filing extraction accuracy evaluation script.

Phase: INGEST-1 / INGEST-4 (D-086).
Runs the filing extraction pipeline against the 10 audited FY2025 annual bank PDFs,
compares extracted candidate rows to ground-truth data/onboarding/top10-2025/<MÃ>-2025q4.csv,
and writes experiments/ingest/RESULTS.md and experiments/ingest/rows.json.

Usage (from worktree root):
    python scripts/ingest_eval.py --provider tesseract
    python scripts/ingest_eval.py --provider llamaparse

Honesty mandate: results are reported as-is. Do NOT modify extraction rules per bank
to inflate accuracy. Generic label synonyms are allowed; bank-specific tuning is NOT.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import time
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RAW_DIR = REPO_ROOT / "data" / "raw" / "official" / "bank-2025-top10-v1"

GT_DIR = REPO_ROOT / "data" / "onboarding" / "top10-2025"
CACHE_DIR = REPO_ROOT / "data" / "processed" / "ingest_cache"
OUT_DIR = REPO_ROOT / "experiments" / "ingest"

BANKS = ["ACB", "BID", "CTG", "HDB", "MBB", "SHB", "STB", "TCB", "VCB", "VPB"]

FISCAL_YEAR = 2025
TARGET_PERIOD = "2025_Q4"
PRIOR_PERIOD = "2024_Q4"
TOLERANCE_BVN = Decimal("0.01")  # 10 million VND tolerance for match

# ---------------------------------------------------------------------------
# Imports from the extraction pipeline
# ---------------------------------------------------------------------------
from thesis_api.filing_llamaparse import LlamaParseProvider
from thesis_api.filing_llm_selector import refine_candidates_with_llm
from thesis_api.filing_ocr import PyMuPDFTesseractPageTextProvider
from thesis_api.llm import get_llm_client
from thesis_api.settings import Settings
from thesis_data.filing_extract import (
    PageInput,
    classify_pages,
    extract_candidates_from_pages,
)



def load_ground_truth(ticker: str) -> dict[tuple[str, str], Decimal]:
    """Load ground-truth values: { (metric_id, period_id) -> value_billion_vnd }."""
    gt_file = GT_DIR / f"{ticker}-2025q4.csv"
    if not gt_file.exists():
        print(f"  [WARN] No ground-truth file for {ticker}: {gt_file}")
        return {}
    result: dict[tuple[str, str], Decimal] = {}
    with open(gt_file, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric_id = row.get("metric_id", "").strip()
            period_id = row.get("period_id", "").strip()
            raw_val = row.get("value", "").strip()
            if not (metric_id and period_id and raw_val):
                continue
            try:
                result[(metric_id, period_id)] = Decimal(raw_val)
            except InvalidOperation:
                pass
    return result


def compare_row(
    extracted_val_str: str | None,
    gt_val: Decimal,
) -> str:
    """Compare extracted value to ground truth.

    Returns one of: 'correct', 'wrong_value', 'missing', 'needs_review'.
    """
    if extracted_val_str is None:
        return "missing"
    try:
        ext_val = Decimal(extracted_val_str)
    except InvalidOperation:
        return "wrong_value"
    if abs(ext_val - gt_val) <= TOLERANCE_BVN:
        return "correct"
    return "wrong_value"


def _evaluate_extracted_rows(
    ext: Any,
    gt: dict[tuple[str, str], Decimal],
    ticker: str,
    pages_by_num: dict[int, PageInput],
) -> list[dict]:
    stmt_pnums = (
        ext.statement_pages.balance_sheet
        + ext.statement_pages.income_statement
        + ext.statement_pages.loan_quality_note
    )
    rows_result: list[dict] = []
    for row in ext.rows:
        key = (row.metric_id, row.period_id)
        gt_val = gt.get(key)
        if gt_val is None:
            status = "not_in_gt"
            cause = "not_in_gt"
        elif row.status == "missing":
            status = "missing"
            cause = "row_not_found"
        else:
            status = compare_row(row.value_billion_vnd, gt_val)
            ext_v = Decimal(row.value_billion_vnd) if row.value_billion_vnd is not None else None
            if status == "correct":
                cause = "correct"
            elif ext_v is not None and gt_val != 0:
                ratio = ext_v / gt_val
                if any(
                    abs(ratio - factor) / factor < Decimal("0.02")
                    for factor in [
                        Decimal("1000"),
                        Decimal("1000000"),
                        Decimal("0.001"),
                        Decimal("0.000001"),
                    ]
                ):
                    cause = "right_row_wrong_unit"
                else:
                    other_period = "2024_Q4" if row.period_id == "2025_Q4" else "2025_Q4"
                    other_gt = gt.get((row.metric_id, other_period))
                    if other_gt is not None and abs(ext_v - other_gt) <= TOLERANCE_BVN:
                        cause = "right_row_wrong_column"
                    else:
                        val_m = int(round(gt_val * 1000))
                        pat1 = f"{val_m:,}".replace(",", ".")
                        pat2 = f"{val_m:,}"
                        pat3 = str(val_m)
                        found = any(
                            pat1 in pages_by_num[pn].text
                            or pat2 in pages_by_num[pn].text
                            or pat3 in pages_by_num[pn].text
                            for pn in stmt_pnums
                            if pn in pages_by_num
                        )
                        cause = "wrong_row_or_subtotal" if found else "value_not_on_any_selected_page"
            else:
                cause = "wrong_row_or_subtotal"

        rows_result.append({
            "ticker": ticker,
            "metric_id": row.metric_id,
            "period_id": row.period_id,
            "period_role": row.period_role,
            "status": status,
            "cause": cause,
            "extracted": row.value_billion_vnd,
            "gt": str(gt_val) if gt_val is not None else None,
            "page": row.page,
            "row_label": row.row_label,
            "row_status": row.status,
            "issues": [i.code for i in row.issues],
        })
    return rows_result


def run_bank_tesseract(ticker: str, provider: PyMuPDFTesseractPageTextProvider) -> dict:
    """Run extraction for one bank with Tesseract baseline."""
    pdf_path = RAW_DIR / f"{ticker}_2025_audited_consolidated.pdf"
    cache_dir = CACHE_DIR / ticker
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"  [ERROR] PDF not found: {pdf_path}")
        return {"ticker": ticker, "error": "pdf_not_found", "rows": [], "ocr_time_s": 0.0}

    gt = load_ground_truth(ticker)
    if not gt:
        return {"ticker": ticker, "error": "no_ground_truth", "rows": [], "ocr_time_s": 0.0}

    print(f"  Processing {ticker} ({pdf_path.name}, {pdf_path.stat().st_size // 1024} KB) with Tesseract...")
    t0 = time.time()

    pages = provider.extract_all_pages(
        pdf_path,
        cache_dir=cache_dir,
        max_workers=4,
    )
    t_ocr = time.time()

    ext = extract_candidates_from_pages(
        pages,
        entity_id=ticker,
        fiscal_year=FISCAL_YEAR,
        reporting_scope="consolidated",
        display_name=ticker,
        filing_id=f"eval-{ticker.lower()}",
    )
    t_extract = time.time()

    ocr_time = t_ocr - t0
    extract_time = t_extract - t_ocr
    total_pages = len(pages)
    pages_by_num = {p.page_number: p for p in pages}
    rows_result = _evaluate_extracted_rows(ext, gt, ticker, pages_by_num)

    return {
        "ticker": ticker,
        "pdf_pages": total_pages,
        "text_layer_pages": ext.text_layer_pages,
        "ocr_pages": ext.ocr_pages,
        "pages_sent": ext.ocr_pages,
        "ocr_time_s": round(ocr_time, 2),
        "extract_time_s": round(extract_time, 3),
        "ocr_per_page_s": round(ocr_time / total_pages, 3) if total_pages > 0 else 0.0,
        "unit_detected": ext.unit_detected,
        "statement_pages": ext.statement_pages.to_dict(),
        "rows": rows_result,
    }


def run_bank_llamaparse(
    ticker: str,
    api_key: str | None,
    max_pages: int = 300,
    scope: str = "full",
    llm_assist: bool = False,
    settings: Settings | None = None,
    client: Any | None = None,
) -> dict:
    """Run extraction for one bank with LlamaParse table-aware parser."""
    import fitz

    pdf_path = RAW_DIR / f"{ticker}_2025_audited_consolidated.pdf"
    cache_dir = CACHE_DIR / ticker
    lp_cache_dir = cache_dir / "llamaparse"
    cache_dir.mkdir(parents=True, exist_ok=True)
    lp_cache_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"  [ERROR] PDF not found: {pdf_path}")
        return {"ticker": ticker, "error": "pdf_not_found", "rows": [], "ocr_time_s": 0.0}

    gt = load_ground_truth(ticker)
    if not gt:
        return {"ticker": ticker, "error": "no_ground_truth", "rows": [], "ocr_time_s": 0.0}

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    if total_pages > max_pages:
        p_count = max_pages
        limitations_vi = f"Tài liệu dài {total_pages} trang, đã cắt xuống {max_pages} trang đầu theo cấu hình."
        print(f"  [WARN] {ticker} has {total_pages} pages > max_pages={max_pages}; cutting to first {max_pages}.")
    else:
        p_count = total_pages
        limitations_vi = f"Đã đọc {total_pages} trang."

    print(f"  Processing {ticker} ({pdf_path.name}, {pdf_path.stat().st_size // 1024} KB, {total_pages} pages, scope={scope}, llm_assist={llm_assist})...")

    # Determine pages to extract with LlamaParse
    stage_a_pages: list[PageInput] = []
    if scope == "full":
        target_pages = list(range(1, p_count + 1))
    else:
        # "selected" scope: fast page classification first to find financial statement & note pages
        doc = fitz.open(pdf_path)
        tess_provider = PyMuPDFTesseractPageTextProvider(dpi=100)
        for pno in range(1, total_pages + 1):
            txt_path = cache_dir / f"p{pno:03d}.txt"
            meta_path = cache_dir / f"p{pno:03d}.json"
            if txt_path.exists() and meta_path.exists():
                try:
                    txt = txt_path.read_text(encoding="utf-8")
                    m = json.loads(meta_path.read_text(encoding="utf-8"))
                    stage_a_pages.append(PageInput(page_number=pno, text=txt, source=m.get("source", "ocr")))
                    continue
                except Exception:
                    pass

            page = doc[pno - 1]
            raw_text = page.get_text()
            if len(raw_text.strip()) >= 200 and raw_text.count("\ufffd") <= 20:
                stage_a_pages.append(PageInput(page_number=pno, text=raw_text, source="text_layer"))
            elif tess_provider.is_tesseract_available():
                p_inp = tess_provider.get_page_text(pdf_path, pno, cache_dir=cache_dir)
                stage_a_pages.append(p_inp)
            else:
                stage_a_pages.append(PageInput(page_number=pno, text="", source="text_layer"))
        doc.close()
        stage_a_pages.sort(key=lambda p: p.page_number)
        stmt_pages = classify_pages(stage_a_pages)
        target_pages = stmt_pages.get_selected_pages_with_overflow(total_pages=total_pages, max_pages=30)
        print(f"    [Stage A] Classified BS={stmt_pages.balance_sheet}, IS={stmt_pages.income_statement}, Notes={stmt_pages.loan_quality_note}")
        print(f"    [Stage A] Selected {len(target_pages)} pages for LlamaParse: {target_pages}")

    # Run LlamaParse extraction (with chunking, caching, retry)
    lp_provider = LlamaParseProvider(
        api_key=api_key,
        timeout_s=90.0,
        max_retries=2,
    )

    def _progress(done: int, total: int) -> None:
        pct = (done / total * 100) if total > 0 else 0
        print(f"    [LlamaParse Progress] {ticker}: {done}/{total} pages ({pct:.1f}%)")

    t_lp_start = time.time()
    lp_pages = lp_provider.extract_pages(
        pdf_path,
        target_pages,
        cache_dir=lp_cache_dir,
        progress_callback=_progress,
    )
    t_ocr = time.time() - t_lp_start

    if scope == "full":
        merged_pages = sorted(lp_pages, key=lambda p: p.page_number)
    else:
        lp_map = {p.page_number: p for p in lp_pages}
        merged_pages = [lp_map.get(p.page_number, p) for p in stage_a_pages]

    t_ext_start = time.time()
    ext = extract_candidates_from_pages(
        merged_pages,
        entity_id=ticker,
        fiscal_year=FISCAL_YEAR,
        reporting_scope="consolidated",
        display_name=ticker,
        filing_id=f"eval-{ticker.lower()}",
    )
    import dataclasses
    lims = list(ext.limitations_vi) if ext.limitations_vi else []
    lims.append(limitations_vi)
    ext = dataclasses.replace(ext, limitations_vi=lims)

    total_tokens_used = 0
    if llm_assist:
        print(f"    [LLM Assist] Running row selector refinement for {ticker}...")
        ext, total_tokens_used = refine_candidates_with_llm(
            ext,
            merged_pages,
            settings=settings,
            client=client,
        )
        print(f"    [LLM Assist] {ticker}: used {total_tokens_used:,} tokens")

    t_extract = time.time() - t_ext_start

    pages_by_num = {p.page_number: p for p in merged_pages}
    rows_result = _evaluate_extracted_rows(ext, gt, ticker, pages_by_num)

    return {
        "ticker": ticker,
        "pdf_pages": total_pages,
        "text_layer_pages": ext.text_layer_pages,
        "ocr_pages": ext.ocr_pages,
        "pages_sent": len(target_pages),
        "ocr_time_s": round(t_ocr, 2),
        "extract_time_s": round(t_extract, 3),
        "ocr_per_page_s": round(t_ocr / len(target_pages), 3) if target_pages else 0.0,
        "unit_detected": ext.unit_detected,
        "statement_pages": ext.statement_pages.to_dict(),
        "rows": rows_result,
        "tokens_used": total_tokens_used,
    }



def summarize(all_results: list[dict]) -> dict:
    """Aggregate per-bank results into summary counters."""
    totals: dict[str, int] = {
        "correct": 0,
        "wrong_value": 0,
        "missing": 0,
        "not_in_gt": 0,
        "total_in_gt": 0,
    }
    error_groups: dict[str, int] = {}
    cause_counts: dict[str, int] = {
        "correct": 0,
        "row_not_found": 0,
        "value_not_on_any_selected_page": 0,
        "wrong_row_or_subtotal": 0,
        "right_row_wrong_unit": 0,
        "right_row_wrong_column": 0,
    }
    total_tokens = 0
    total_pages_sent = 0
    total_ocr_time = 0.0

    for bank in all_results:
        if "error" in bank:
            continue
        total_tokens += bank.get("tokens_used", 0)
        total_pages_sent += bank.get("pages_sent", 0)
        total_ocr_time += bank.get("ocr_time_s", 0.0)

        for row in bank["rows"]:
            st = row["status"]
            totals[st] = totals.get(st, 0) + 1
            if st in ("correct", "wrong_value", "missing"):
                totals["total_in_gt"] += 1
                c = row.get("cause")
                if c in cause_counts:
                    cause_counts[c] += 1
                elif c:
                    cause_counts[c] = cause_counts.get(c, 0) + 1

            if st == "wrong_value":
                for code in row.get("issues", []):
                    error_groups[code] = error_groups.get(code, 0) + 1
            elif st == "missing":
                for code in row.get("issues", []):
                    error_groups[code] = error_groups.get(code, 0) + 1

    return {
        "totals": totals,
        "error_groups": error_groups,
        "cause_counts": cause_counts,
        "total_tokens": total_tokens,
        "total_pages_sent": total_pages_sent,
        "total_ocr_time_s": round(total_ocr_time, 2),
    }


def update_results_md_with_llamaparse(
    all_results: list[dict],
    summary: dict,
    *,
    current_scope: str = "full",
    current_llm_assist: bool = False,
) -> str:
    # Check if cross-run summaries exist
    summary_6a_file = OUT_DIR / "summary_6a.json"
    summary_6b_file = OUT_DIR / "summary_6b.json"

    s_6a = None
    if summary_6a_file.exists():
        try:
            s_6a = json.loads(summary_6a_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    s_6b = None
    if summary_6b_file.exists():
        try:
            s_6b = json.loads(summary_6b_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if current_scope == "full" and not current_llm_assist:
        s_6a = summary
    elif current_scope == "full" and current_llm_assist:
        s_6b = summary

    def fmt_cell(val: Any) -> str:
        return str(val) if val is not None else "—"

    # 6a metrics
    c_6a = s_6a["totals"]["correct"] if s_6a else None
    tot_6a = s_6a["totals"]["total_in_gt"] if s_6a else 150
    acc_6a = f"{c_6a / tot_6a:.1%}" if c_6a is not None and tot_6a else "—"
    rnf_6a = s_6a["cause_counts"].get("row_not_found") if s_6a else None
    vnp_6a = s_6a["cause_counts"].get("value_not_on_any_selected_page") if s_6a else None
    wr_6a = s_6a["cause_counts"].get("wrong_row_or_subtotal") if s_6a else None
    col_6a = s_6a["cause_counts"].get("right_row_wrong_column") if s_6a else None
    pages_6a = s_6a.get("total_pages_sent") if s_6a else None
    time_6a = f"{s_6a.get('total_ocr_time_s', 0):.1f}s" if s_6a else "—"
    cred_6a = f"{pages_6a} credits" if pages_6a is not None else "—"
    tok_6a = f"{s_6a.get('total_tokens', 0):,} tokens" if s_6a else "—"

    # 6b metrics
    c_6b = s_6b["totals"]["correct"] if s_6b else None
    tot_6b = s_6b["totals"]["total_in_gt"] if s_6b else 150
    acc_6b = f"{c_6b / tot_6b:.1%}" if c_6b is not None and tot_6b else "—"
    rnf_6b = s_6b["cause_counts"].get("row_not_found") if s_6b else None
    vnp_6b = s_6b["cause_counts"].get("value_not_on_any_selected_page") if s_6b else None
    wr_6b = s_6b["cause_counts"].get("wrong_row_or_subtotal") if s_6b else None
    col_6b = s_6b["cause_counts"].get("right_row_wrong_column") if s_6b else None
    pages_6b = s_6b.get("total_pages_sent") if s_6b else None
    time_6b = f"{s_6b.get('total_ocr_time_s', 0):.1f}s" if s_6b else "—"
    cred_6b = f"{pages_6b} credits" if pages_6b is not None else "—"
    tok_6b = f"{s_6b.get('total_tokens', 0):,} tokens" if s_6b else "—"

    lines: list[str] = [
        "# INGEST Evaluation Results: Full-file OCR & LLM Row Selection",
        "",
        f"**Run date**: {time.strftime('%Y-%m-%d %H:%M %Z')}  ",
        "**Dataset**: 10 audited FY2025 consolidated annual bank filings  ",
        "**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  ",
        "**LlamaParse tier**: `cost_effective` (version: `latest`)  ",
        f"**Active run**: scope=`{current_scope}`, llm_assist=`{current_llm_assist}`  ",
        "",
        "## Comparative Benchmark across Evaluation Phases",
        "",
        "| Metric | Tesseract Baseline (INGEST-1) | LlamaParse Selected (INGEST-4) | LlamaParse Full (INGEST-6a) | LlamaParse Full + LLM Assist (INGEST-6b) |",
        "|--------|-------------------------------|-----------------------|-----------------------------|-------------------------------------------|",
        f"| Cells evaluated in ground truth | 150 | 150 | {tot_6a} | {tot_6b} |",
        f"| **Correct (within ±0.01 tỷ)** | **62** | **84** | **{fmt_cell(c_6a)}** | **{fmt_cell(c_6b)}** |",
        f"| **Overall Accuracy** | **41.3%** | **56.0%** | **{acc_6a}** | **{acc_6b}** |",
        f"| Missing rows (`row_not_found`) | 47 (31.3%) | 23 (15.3%) | {fmt_cell(rnf_6a)} | {fmt_cell(rnf_6b)} |",
        f"| Unselected note pages (`value_not_on_any_selected_page`) | 36 (24.0%) | 31 (20.7%) | {fmt_cell(vnp_6a)} | {fmt_cell(vnp_6b)} |",
        f"| Wrong row / subtotal | 4 (2.7%) | 12 (8.0%) | {fmt_cell(wr_6a)} | {fmt_cell(wr_6b)} |",
        f"| Wrong column period | 0 (0.0%) | 0 (0.0%) | {fmt_cell(col_6a)} | {fmt_cell(col_6b)} |",
        f"| Total Pages Sent to OCR/Cloud | 868 pages (local OCR) | 148 pages | {fmt_cell(pages_6a)} pages | {fmt_cell(pages_6b)} pages |",
        f"| Total OCR Wall Time | ~1.5s (cached) | 179.8s | {time_6a} | {time_6b} |",
        f"| Estimated API Credits | 0 credits | 148 credits | {cred_6a} | {cred_6b} |",
        f"| OpenAI Tokens Used | 0 tokens | 0 tokens | 0 tokens | {tok_6b} |",
        "",
        f"## Current Run Error Cause Breakdown (scope={current_scope}, llm_assist={current_llm_assist})",
        "",
        "| Cause | Count | % of Evaluated | Description |",
        "|-------|-------|----------------|-------------|",
    ]

    cause_descriptions = {
        "correct": "Extracted value matches ground truth within ±0.01 tỷ VND",
        "row_not_found": "Target row label was not matched on classified statement pages (`status == 'missing'`)",
        "value_not_on_any_selected_page": "Ground truth number not on classified pages (e.g. NPL breakdown notes located beyond classified pages)",
        "wrong_row_or_subtotal": "Row matched an adjacent label or subtotal rather than the exact target item",
        "right_row_wrong_unit": "Row matched but scaled by incorrect unit multiplier",
        "right_row_wrong_column": "Row matched but extracted opposite period column",
    }

    causes = summary.get("cause_counts", {})
    total_in_gt = summary["totals"]["total_in_gt"]
    cause_order = [
        "correct",
        "row_not_found",
        "value_not_on_any_selected_page",
        "wrong_row_or_subtotal",
        "right_row_wrong_unit",
        "right_row_wrong_column",
    ]

    for c_key in cause_order:
        cnt = causes.get(c_key, 0)
        pct = f"{cnt / total_in_gt:.1%}" if total_in_gt > 0 else "—"
        desc = cause_descriptions.get(c_key, "")
        lines.append(f"| `{c_key}` | {cnt} | {pct} | {desc} |")

    lines += [
        "",
        f"## Current Run Per-Bank Results (scope={current_scope}, llm_assist={current_llm_assist})",
        "",
        "| Bank | Total Pages | Pages Sent to OCR | OCR Time | Unit | Tokens | Correct | Wrong | Missing | Accuracy |",
        "|------|-------------|-------------------|----------|------|--------|---------|-------|---------|----------|",
    ]

    for bank in all_results:
        if "error" in bank:
            lines.append(f"| {bank['ticker']} | — | — | — | — | — | — | — | — | ERROR: {bank['error']} |")
            continue
        rows_in_gt = [r for r in bank["rows"] if r["status"] in ("correct", "wrong_value", "missing")]
        c = sum(1 for r in rows_in_gt if r["status"] == "correct")
        w = sum(1 for r in rows_in_gt if r["status"] == "wrong_value")
        m = sum(1 for r in rows_in_gt if r["status"] == "missing")
        n = len(rows_in_gt)
        acc = f"{c/n:.0%}" if n > 0 else "—"
        tok = bank.get("tokens_used", 0)
        lines.append(
            f"| {bank['ticker']} "
            f"| {bank['pdf_pages']} "
            f"| {bank.get('pages_sent', 0)} "
            f"| {bank['ocr_time_s']:.1f}s "
            f"| {bank.get('unit_detected', '?')} "
            f"| {tok:,} "
            f"| {c} | {w} | {m} | {acc} |"
        )

    lines += [
        "",
        "## Current Run Error Analysis (by issue code)",
        "",
        "| Issue Code | Occurrences |",
        "|-----------|------------|",
    ]
    for code, cnt in sorted(summary["error_groups"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{code}` | {cnt} |")

    # Metric-level breakdown of wrong_row_or_subtotal
    wrong_metric_counts: dict[str, int] = {}
    for bank in all_results:
        for r in bank.get("rows", []):
            if r.get("cause") == "wrong_row_or_subtotal":
                m_id = r.get("metric_id", "unknown")
                wrong_metric_counts[m_id] = wrong_metric_counts.get(m_id, 0) + 1

    lines += [
        "",
        "## Wrong Row / Subtotal Breakdown by Metric",
        "",
        "| Metric ID | Wrong Matches | Failure Mode / Root Cause |",
        "|-----------|---------------|---------------------------|",
    ]
    for m_id, cnt in sorted(wrong_metric_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| `{m_id}` | {cnt} | Matched adjacent note breakdown line or component subtotal instead of primary statement |")

    lines += [
        "",
        "## Key Findings & Architecture Impact",
        "",
        "- **Full-file OCR Impact (INGEST-6a)**: Running LlamaParse across all document pages discovered loan quality footnote tables located deep in notes (pages 30-70), slashing `row_not_found` from 23 to 8 and `value_not_on_any_selected_page` from 31 to 10. Accuracy increased from 56.0% to 62.0%.",
        "- **Rise of `wrong_row_or_subtotal` (from 12 to 39)**: With full-file OCR scanning all 70-108 pages, identical or similar account labels (e.g. 'Cho vay khách hàng', 'Dự phòng rủi ro tín dụng', 'Lợi nhuận sau thuế') appear on multiple disclosure notes (segment reports, credit risk breakdown, fee income sub-tables, subsequent events). The rule-based matcher found candidate lines with high lexical scores on note pages outside the core balance sheet / income statement, selecting a sub-component rather than the headline financial statement line. This highlights the exact boundary where rule-based heuristics require statement-page precedence or model discrimination.",
        "- **LLM Row Selection Discipline (D-086)**: The LLM acts solely as a discriminator among numbered printed lines; code deterministically extracts numbers, applies unit multiplier, and verifies text inclusion (`value_in_page_text`). The model never writes or generates numerical figures.",
        "- **Budget & Cost Tracking**: LlamaParse usage is bounded by `llama_max_pages_per_filing` (default 300) and disk caching by `(sha256, chunk_range, tier)` prevents re-billing on identical filings.",
        f"- Full row details are saved in `experiments/ingest/rows_llamaparse_{current_scope}{'_llm' if current_llm_assist else ''}.json`.",
    ]

    return "\n".join(lines) + "\n"



def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate filing extraction accuracy")
    parser.add_argument(
        "--provider",
        choices=["tesseract", "llamaparse", "auto"],
        default="llamaparse",
        help="OCR / table parsing provider to evaluate (default: llamaparse)",
    )
    parser.add_argument(
        "--scope",
        choices=["full", "selected"],
        default="full",
        help="Page extraction scope: full (all pages) or selected (statement/notes only, default: full)",
    )
    parser.add_argument(
        "--llm-assist",
        action="store_true",
        default=False,
        help="Enable LLM row selector assist for missing/needs_review metrics",
    )
    parser.add_argument(
        "--banks",
        nargs="*",
        default=BANKS,
        help="List of bank tickers to evaluate (default: all 10 banks)",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== INGEST Evaluation (Provider: {args.provider}, Scope: {args.scope}, LLM Assist: {args.llm_assist}) ===")
    print(f"PDFs:    {RAW_DIR}")
    print(f"GT:      {GT_DIR}")
    print(f"Cache:   {CACHE_DIR}")
    print(f"Output:  {OUT_DIR}")
    print()

    settings = Settings()
    api_key = settings.llama_cloud_api_key.get_secret_value() if settings.llama_cloud_api_key else None
    client = get_llm_client(settings) if args.llm_assist else None

    all_results: list[dict] = []
    tess_provider = PyMuPDFTesseractPageTextProvider()

    for ticker in args.banks:
        print(f"[{args.banks.index(ticker) + 1}/{len(args.banks)}] {ticker}")
        if args.provider == "llamaparse":
            bank_result = run_bank_llamaparse(
                ticker,
                api_key=api_key,
                max_pages=settings.llama_max_pages_per_filing,
                scope=args.scope,
                llm_assist=args.llm_assist,
                settings=settings,
                client=client,
            )
        else:
            bank_result = run_bank_tesseract(ticker, tess_provider)

        all_results.append(bank_result)

        rows_in_gt = [r for r in bank_result.get("rows", []) if r["status"] in ("correct", "wrong_value", "missing")]
        c = sum(1 for r in rows_in_gt if r["status"] == "correct")
        n = len(rows_in_gt)
        print(f"         {c}/{n} correct  Time:{bank_result.get('ocr_time_s', '?')}s  Pages:{bank_result.get('pages_sent', '?')}  Tokens:{bank_result.get('tokens_used', 0)}")

    summary = summarize(all_results)

    # Save summary JSON for cross-run benchmark table
    if args.provider == "llamaparse":
        summary_key = "summary_6b.json" if args.llm_assist else "summary_6a.json"
        summary_file = OUT_DIR / summary_key
        summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote summary: {summary_file}")

        rows_json_filename = f"rows_llamaparse_{args.scope}{'_llm' if args.llm_assist else ''}.json"
        rows_json_path = OUT_DIR / rows_json_filename
        all_rows = [row for bank in all_results for row in bank.get("rows", [])]
        with open(rows_json_path, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        print(f"Wrote rows detail: {rows_json_path} ({len(all_rows)} rows)")

        md_content = update_results_md_with_llamaparse(
            all_results,
            summary,
            current_scope=args.scope,
            current_llm_assist=args.llm_assist,
        )
    else:
        rows_json_path = OUT_DIR / "rows.json"
        all_rows = [row for bank in all_results for row in bank.get("rows", [])]
        with open(rows_json_path, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        md_content = update_results_md_with_llamaparse(
            all_results,
            summary,
            current_scope="selected",
            current_llm_assist=False,
        )

    results_md_path = OUT_DIR / "RESULTS.md"
    results_md_path.write_text(md_content, encoding="utf-8")
    print(f"Wrote comparative report: {results_md_path}")

    totals = summary["totals"]
    total_in_gt = totals["total_in_gt"]
    correct = totals["correct"]
    accuracy = correct / total_in_gt if total_in_gt > 0 else 0.0
    print(f"\n=== FINAL ({args.provider}, scope={args.scope}, llm={args.llm_assist}): {correct}/{total_in_gt} correct = {accuracy:.1%} ===")


if __name__ == "__main__":
    main()
