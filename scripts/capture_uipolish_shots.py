import argparse
import json
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

TEMP_DIR = r"C:\Users\ASUS\AppData\Local\Temp\orch\uipolish\shots"
os.makedirs(TEMP_DIR, exist_ok=True)

TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"

CAP_DATA = {
    "snapshotId": "gold-v5",
    "datasetId": "finance-vietnam-banks",
    "datasetSnapshotId": "gold-v5",
    "dataset_snapshot_id": "gold-v5",
    "goldVersion": "v5",
    "entities": [
        {"id": "ACB", "ticker": "ACB", "name": "Á Châu", "type": "company"},
        {"id": "MBB", "ticker": "MBB", "name": "Quân Đội", "type": "company"},
        {"id": "VCB", "ticker": "VCB", "name": "Vietcombank", "type": "company"},
    ],
    "periods": [
        {"id": "2024_Q4", "label": "Q4 2024", "year": 2024, "quarter": 4},
        {"id": "2025_Q4", "label": "Q4 2025", "year": 2025, "quarter": 4},
    ],
    "metrics": [
        {
            "id": "bank.npl_g35",
            "acronym": "NPL_G35",
            "label": "Tỷ lệ nợ xấu (nhóm 3–5)",
            "shortLabel": "Nợ xấu",
            "topicId": "company",
            "unit": "%",
            "direction": "lower_is_better",
            "decimals": 2,
            "group": "asset_quality",
            "groupLabel": "Chất lượng nợ",
        },
        {
            "id": "bank.llr_coverage",
            "acronym": "LLR",
            "label": "Tỷ lệ bao phủ nợ xấu",
            "shortLabel": "Bao phủ nợ",
            "topicId": "company",
            "unit": "%",
            "direction": "higher_is_better",
            "decimals": 1,
            "group": "asset_quality",
            "groupLabel": "Chất lượng nợ",
        },
        {
            "id": "bank.roa",
            "acronym": "ROA",
            "label": "Tỷ suất sinh lời trên tổng tài sản",
            "shortLabel": "ROA",
            "topicId": "company",
            "unit": "%",
            "direction": "higher_is_better",
            "decimals": 2,
            "group": "profitability",
            "groupLabel": "Hiệu quả",
        },
        {
            "id": "bank.roe",
            "acronym": "ROE",
            "label": "Tỷ suất sinh lời trên vốn chủ sở hữu",
            "shortLabel": "ROE",
            "topicId": "company",
            "unit": "%",
            "direction": "higher_is_better",
            "decimals": 2,
            "group": "profitability",
            "groupLabel": "Hiệu quả",
        },
    ],
    "topics": [],
    "peerUniverses": [],
    "analysis_available": True,
    "coverage": [{"entity_id": "ACB", "period_id": "2024_Q4", "metrics": ["bank.npl_g35"]}],
}

def make_rows(clean=True):
    def r(m, l, role, p, val, page, rl, st="candidate", is_edited=False, issues=None):
        return {
            "row_id": f"{m}:{role}",
            "metric_id": m,
            "label_vi": l,
            "period_role": role,
            "period_id": p,
            "value_billion_vnd": val,
            "extracted_value_billion_vnd": val,
            "raw_text": val if val else "",
            "row_label": rl,
            "page": page,
            "source": "ocr",
            "status": st,
            "edited": is_edited,
            "confirmed": True if clean else (st == "candidate"),
            "issues": issues or [],
            "alternatives": [],
        }

    rows = [
        r("bank.input.npl_group_3_balance", "Nợ nhóm 3", "target", "2025_Q4", "764.791", 50, "Nhóm 3 - Nợ dưới tiêu chuẩn"),
        r("bank.input.npl_group_3_balance", "Nợ nhóm 3", "prior", "2024_Q4", "700.000", 50, "Nhóm 3 - Nợ dưới tiêu chuẩn"),
        r("bank.input.npl_group_4_balance", "Nợ nhóm 4", "target", "2025_Q4", "770.229", 50, "Nhóm 4 - Nợ nghi ngờ"),
        r("bank.input.npl_group_4_balance", "Nợ nhóm 4", "prior", "2024_Q4", "680.000", 50, "Nhóm 4 - Nợ nghi ngờ"),
        r("bank.input.npl_group_5_balance", "Nợ nhóm 5", "target", "2025_Q4", "3800.000", 50, "Nhóm 5 - Nợ có khả năng mất vốn"),
        r("bank.input.npl_group_5_balance", "Nợ nhóm 5", "prior", "2024_Q4", "3200.000", 50, "Nhóm 5 - Nợ có khả năng mất vốn"),
        r("bank.input.customer_loans_gross", "Tổng dư nợ cho vay khách hàng", "target", "2025_Q4", "538461.000", 48, "Cho vay khách hàng"),
        r("bank.input.customer_loans_gross", "Tổng dư nợ cho vay khách hàng", "prior", "2024_Q4", "480000.000", 48, "Cho vay khách hàng"),
        r("bank.input.loan_loss_reserves", "Dự phòng rủi ro cho vay khách hàng", "target", "2025_Q4", "6000.000", 48, "Dự phòng rủi ro cho vay khách hàng"),
        r("bank.input.loan_loss_reserves", "Dự phòng rủi ro cho vay khách hàng", "prior", "2024_Q4", "5200.000", 48, "Dự phòng rủi ro cho vay khách hàng"),
        r("bank.input.total_assets", "Tổng tài sản", "target", "2025_Q4", "864696.000", 8, "TỔNG CỘNG TÀI SẢN"),
        r("bank.input.total_assets", "Tổng tài sản", "prior", "2024_Q4", "718794.000", 8, "TỔNG CỘNG TÀI SẢN"),
        r("bank.input.equity", "Vốn chủ sở hữu", "target", "2025_Q4", "85324.000", 9, "VỐN CHỦ SỞ HỮU"),
        r("bank.input.equity", "Vốn chủ sở hữu", "prior", "2024_Q4", "73582.000", 9, "VỐN CHỦ SỞ HỮU"),
        r("bank.input.profit_after_tax", "Lợi nhuận sau thuế", "target", "2025_Q4", "17651.000", 11, "LỢI NHUẬN SAU THUẾ"),
        r("bank.input.profit_after_tax", "Lợi nhuận sau thuế", "prior", "2024_Q4", "16043.000", 11, "LỢI NHUẬN SAU THUẾ"),
        r("bank.input.parent_attributable_profit", "Lợi nhuận công ty mẹ", "target", "2025_Q4", "17651.000", 11, "Lợi nhuận sau thuế của công ty mẹ"),
        r("bank.input.parent_attributable_profit", "Lợi nhuận công ty mẹ", "prior", "2024_Q4", "16043.000", 11, "Lợi nhuận sau thuế của công ty mẹ"),
        r(
            "bank.input.non_controlling_interests",
            "Lợi ích CĐ không kiểm soát",
            "target",
            "2025_Q4",
            "0.000",
            11,
            "Lợi ích của cổ đông không kiểm soát",
        ),
        r(
            "bank.input.non_controlling_interests",
            "Lợi ích CĐ không kiểm soát",
            "prior",
            "2024_Q4",
            None if not clean else "0.000",
            11 if clean else None,
            "Lợi ích của cổ đông không kiểm soát",
            st="missing" if not clean else "candidate",
            issues=[{"code": "missing_value", "severity": "error", "message_vi": "Không tìm thấy số liệu kỳ trước"}] if not clean else [],
        ),
    ]
    return rows

FILING_CLEAN = {
    "filing_id": "fl-acb2025clean001",
    "filename": "BCTC_ACB_2025_KiemToan.pdf",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "page_count": 120,
    "status": "ready",
    "entity_id": "ACB",
    "display_name": "Ngân hàng TMCP Á Châu (ACB)",
    "fiscal_year": 2025,
    "reporting_scope": "consolidated",
    "ocr_provider": "tesseract",
    "progress": {"pages_done": 120, "page_count": 120},
    "statement_pages": {"balance_sheet": [8, 9], "income_statement": [10, 11], "loan_quality_note": [48, 50]},
    "unit_detected": "triệu VND",
    "rows": make_rows(clean=True),
    "validation": {
        "status": "pass",
        "ready_to_confirm": True,
        "blocking_reasons_vi": [],
        "checks": [
            {"code": "npl_sum_equals_gross", "severity": "info", "message_vi": "Tổng nợ nhóm 3–5 khớp công thức."},
            {"code": "pat_equals_parent_plus_nci", "severity": "info", "message_vi": "Lợi nhuận sau thuế cân đối."},
        ],
    },
    "limitations_vi": ["Số liệu 2025 là số sau kiểm toán năm.", "Ngoại tệ quy đổi theo tỷ giá cuối năm."],
}

FILING_REJECTED = {
    "filing_id": "fl-mbb2025rej002",
    "filename": "BCTC_MBB_2025_LoiChungMinh.pdf",
    "sha256": "f4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afb",
    "page_count": 98,
    "status": "ready",
    "entity_id": "MBB",
    "display_name": "Ngân hàng TMCP Quân Đội (MBB)",
    "fiscal_year": 2025,
    "reporting_scope": "consolidated",
    "ocr_provider": "tesseract",
    "progress": {"pages_done": 98, "page_count": 98},
    "statement_pages": {"balance_sheet": [7, 8], "income_statement": [9, 10], "loan_quality_note": [45]},
    "unit_detected": "triệu VND",
    "rows": make_rows(clean=False),
    "validation": {
        "status": "fail",
        "ready_to_confirm": False,
        "blocking_reasons_vi": [
            "Còn 1 dòng thiếu cần nhập thủ công.",
            "Còn 1 dòng cần xem lại cần xác nhận.",
        ],
        "checks": [
            {
                "code": "missing_required",
                "severity": "error",
                "message_vi": "Dòng 'Lợi ích cổ đông không kiểm soát (kỳ trước)' bị thiếu.",
                "row_ids": ["bank.input.non_controlling_interests:prior"],
            },
            {
                "code": "pat_equals_parent_plus_nci",
                "severity": "warning",
                "message_vi": "Lợi nhuận sau thuế ≠ Lợi nhuận công ty mẹ + Lợi ích CĐKKS (kỳ trước).",
                "row_ids": ["bank.input.profit_after_tax:prior"],
            },
        ],
    },
    "limitations_vi": ["Tài liệu phát hiện lỗi mất cân đối bảng kết quả kinh doanh."],
}

FILING_PROCESSING = {
    "filing_id": "fl-acb2025proc003",
    "filename": "BCTC_ACB_2025_KiemToan.pdf",
    "sha256": "",
    "page_count": 120,
    "status": "processing",
    "entity_id": "ACB",
    "display_name": "Ngân hàng Á Châu (ACB)",
    "fiscal_year": 2025,
    "reporting_scope": "consolidated",
    "ocr_provider": "tesseract",
    "progress": {"pages_done": 42, "page_count": 120},
    "statement_pages": {"balance_sheet": [], "income_statement": [], "loan_quality_note": []},
    "unit_detected": None,
    "rows": [],
    "validation": {
        "status": "fail",
        "ready_to_confirm": False,
        "blocking_reasons_vi": ["Đang đọc và quét OCR 120 trang..."],
        "checks": [],
    },
    "limitations_vi": [],
}

FILING_FAILED = {
    "filing_id": "fl-fail004",
    "filename": "BCTC_Loi_2025.pdf",
    "sha256": "",
    "page_count": 0,
    "status": "failed",
    "error_code": "ocr_unavailable",
    "message_vi": "Máy chủ chưa cài công cụ OCR (Tesseract). Liên hệ quản trị viên hoặc dùng bộ mẫu để trình diễn.",
    "entity_id": "ACB",
    "display_name": "Ngân hàng Á Châu (ACB)",
    "fiscal_year": 2025,
    "reporting_scope": "consolidated",
    "ocr_provider": "tesseract",
    "progress": {"pages_done": 0, "page_count": 0},
    "statement_pages": {"balance_sheet": [], "income_statement": [], "loan_quality_note": []},
    "unit_detected": None,
    "rows": [],
    "validation": {"status": "fail", "ready_to_confirm": False, "blocking_reasons_vi": [], "checks": []},
    "limitations_vi": [],
}

CONFIRM_RESULT = {
    "upload_id": "up-acb2025q4-01",
    "entity_id": "ACB",
    "display_name": "Ngân hàng TMCP Á Châu",
    "status": "accepted",
    "period_id": "2025_Q4",
    "metrics": [
        {"metric_id": "bank.npl_g35", "computed_value": 0.99, "reported_value": 0.99, "status": "matched"},
        {"metric_id": "bank.llr_coverage", "computed_value": 112.5, "reported_value": 112.5, "status": "matched"},
        {"metric_id": "bank.roa", "computed_value": 1.65, "reported_value": 1.65, "status": "matched"},
        {"metric_id": "bank.roe", "computed_value": 17.58, "reported_value": 17.58, "status": "matched"},
    ],
    "row_issues": [],
    "limitations_vi": "Dữ liệu vận hành mới tạo từ báo cáo tài chính PDF. Độc lập với snapshot Gold v5.",
}

SAMPLES = [
    {
        "sample_id": "acb-2025-clean",
        "title_vi": "ACB 2025 — đọc sạch (mẫu)",
        "entity_id": "ACB",
        "fiscal_year": 2025,
        "page_count": 120,
        "note_vi": "Tất cả 20 dòng đều đọc thành công, 0 dòng cần xem lại.",
    },
    {
        "sample_id": "mbb-2025-rejected",
        "title_vi": "MBB 2025 — có lỗi mất cân đối (mẫu)",
        "entity_id": "MBB",
        "fiscal_year": 2025,
        "page_count": 98,
        "note_vi": "1 dòng cần xem lại, 1 dòng thiếu, 1 lỗi kiểm tra.",
    },
    {
        "sample_id": "acb-2025-processing",
        "title_vi": "ACB 2025 — đang đọc báo cáo (mẫu)",
        "entity_id": "ACB",
        "fiscal_year": 2025,
        "page_count": 120,
        "note_vi": "Trình diễn thanh tiến độ và thông tin công cụ OCR.",
    },
]

def make_route_handler(current_state):
    def route_handler(route):
        url = route.request.url
        method = route.request.method

        if "auth/status" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"required": False}))
        elif "capabilities" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(CAP_DATA))
        elif "filing-samples" in url and "open" in url:
            if "mbb" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_REJECTED))
            elif "processing" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_PROCESSING))
            else:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_CLEAN))
        elif "filing-samples" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(SAMPLES))
        elif "confirm" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(CONFIRM_RESULT))
        elif "rows" in url and method == "PUT":
            payload = json.loads(route.request.post_data or "{}")
            resp_row = dict(FILING_CLEAN["rows"][0])
            resp_row["value_billion_vnd"] = payload.get("value_billion_vnd")
            resp_row["confirmed"] = payload.get("confirmed", True)
            resp_row["edited"] = True
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"row": resp_row, "validation": FILING_CLEAN["validation"]}),
            )
        elif "filings" in url and method == "POST":
            route.fulfill(
                status=201,
                content_type="application/json",
                body=json.dumps({"filing_id": current_state.get("post_filing_id", "fl-acb2025proc003"), "status": "processing"}),
            )
        elif "fl-fail004" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_FAILED))
        elif "fl-acb2025proc003" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_PROCESSING))
        elif "fl-mbb2025rej002" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(FILING_REJECTED))
        elif "/pages/" in url and url.endswith(".png"):
            route.fulfill(status=200, content_type="image/png", body=TINY_PNG)
        elif "/api/" in url and "onboarding" in url:
            route.fulfill(status=404, content_type="application/json", body="{}")
        else:
            route.continue_()

    return route_handler

def capture_element(page, locator, path, label, name):
    page.evaluate("document.querySelectorAll('header.sticky, header').forEach(el => el.style.display = 'none')")
    locator.scroll_into_view_if_needed()
    time.sleep(0.4)
    locator.screenshot(path=path)
    page.evaluate("document.querySelectorAll('header.sticky, header').forEach(el => el.style.display = '')")
    if label == "390":
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        inner_w = page.evaluate("window.innerWidth")
        assert scroll_w <= inner_w, f"Horizontal overflow on {label}px shot {name}: scrollWidth={scroll_w} > innerWidth={inner_w}"
    print(f"Captured {os.path.basename(path)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="before", choices=["before", "after"])
    parser.add_argument("--repo-copy-dir", default=r"docs\plans\2026-10-16-filing-ingest\before-shots")
    args = parser.parse_args()

    mode = args.mode
    prefix = f"{mode}_"
    os.makedirs(TEMP_DIR, exist_ok=True)
    if args.repo_copy_dir:
        os.makedirs(args.repo_copy_dir, exist_ok=True)

    url = "http://localhost:5173/data"
    dummy_pdf = os.path.abspath("scripts/dummy.pdf")

    viewports = [("1440", 1440, 900), ("390", 390, 844)]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        for label, width, height in viewports:
            print(f"\n--- Walking {mode} on {label}px ---")
            state = {"post_filing_id": "fl-acb2025proc003"}
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.route("**/*", make_route_handler(state))

            # 1. Upload step
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(1)
            wizard = page.locator("[data-testid='filing-wizard-section']")
            p1 = os.path.join(TEMP_DIR, f"{prefix}01_upload_step_{label}.png")
            capture_element(page, wizard, p1, label, "01_upload_step")

            # 2. Upload processing state
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(dummy_pdf)
            time.sleep(0.3)
            page.locator("#input-entity-id").fill("ACB")
            time.sleep(0.3)
            # Find and select consolidated scope
            radio = page.locator("input[value='consolidated']")
            if radio.count() > 0:
                radio.first.check(force=True)
            time.sleep(0.3)
            submit_btn = page.locator("button:has-text('Bắt đầu đọc và trích xuất PDF'), button:has-text('Trích xuất PDF')").first
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()
            page.wait_for_selector("[data-testid='processing-step']", timeout=5000)
            time.sleep(1.5)
            p2 = os.path.join(TEMP_DIR, f"{prefix}02_processing_{label}.png")
            capture_element(page, wizard, p2, label, "02_processing")

            # 3. Clean sample (Extracted rows table)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(0.5)
            # Open sample modal
            sample_trigger = page.locator("button:has-text('Dùng bộ mẫu dựng sẵn'), button:has-text('hoặc dùng bộ mẫu'), a:has-text('hoặc dùng bộ mẫu')").first
            sample_trigger.click()
            page.wait_for_selector("[data-testid='sample-selector-modal']", timeout=5000)
            time.sleep(0.5)
            # Open first sample (clean)
            modal = page.locator("[data-testid='sample-selector-modal']")
            modal.locator("button:has-text('Mở mẫu')").first.click()
            page.wait_for_selector("[data-testid='extracted-rows-section']", timeout=5000)
            time.sleep(1)
            p3 = os.path.join(TEMP_DIR, f"{prefix}03_extracted_clean_{label}.png")
            capture_element(page, wizard, p3, label, "03_extracted_clean")

            # 4. Editing a value
            edit_btn = page.locator("button[title*='sửa' i]:visible, button:has-text('Sửa'):visible").first
            if edit_btn.count() > 0 and edit_btn.is_visible():
                edit_btn.scroll_into_view_if_needed()
                edit_btn.click()
                time.sleep(0.5)
                p4 = os.path.join(TEMP_DIR, f"{prefix}04_editing_row_{label}.png")
                capture_element(page, wizard, p4, label, "04_editing_row")
                # Save edit
                save_btn = page.locator("button:has-text('Lưu'):visible").first
                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click()
                    time.sleep(0.5)

            # 5. Rejected sample with validation errors (MBB)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(0.5)
            sample_trigger = page.locator("button:has-text('Dùng bộ mẫu dựng sẵn'), button:has-text('hoặc dùng bộ mẫu'), a:has-text('hoặc dùng bộ mẫu')").first
            sample_trigger.click()
            page.wait_for_selector("[data-testid='sample-selector-modal']", timeout=5000)
            time.sleep(0.5)
            modal = page.locator("[data-testid='sample-selector-modal']")
            # Click MBB sample (index 1)
            modal.locator("button:has-text('Mở mẫu')").nth(1).click()
            page.wait_for_selector("[data-testid='validation-panel']", timeout=5000)
            time.sleep(1)
            val_panel = page.locator("[data-testid='filing-wizard-section']")
            p5 = os.path.join(TEMP_DIR, f"{prefix}05_rejected_errors_{label}.png")
            capture_element(page, val_panel, p5, label, "05_rejected_errors")

            # 6. Confirmed result (Import -> Ask)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(0.5)
            sample_trigger = page.locator("button:has-text('Dùng bộ mẫu dựng sẵn'), button:has-text('hoặc dùng bộ mẫu'), a:has-text('hoặc dùng bộ mẫu')").first
            sample_trigger.click()
            page.wait_for_selector("[data-testid='sample-selector-modal']", timeout=5000)
            time.sleep(0.5)
            modal = page.locator("[data-testid='sample-selector-modal']")
            modal.locator("button:has-text('Mở mẫu')").first.click()
            page.wait_for_selector("[data-testid='confirm-filing-button']", timeout=5000)
            time.sleep(0.5)
            confirm_btn = page.locator("[data-testid='confirm-filing-button']").first
            confirm_btn.scroll_into_view_if_needed()
            confirm_btn.click()
            page.wait_for_selector("[data-testid='confirmation-result-card']", timeout=5000)
            time.sleep(1)
            p6 = os.path.join(TEMP_DIR, f"{prefix}06_confirmed_result_{label}.png")
            capture_element(page, wizard, p6, label, "06_confirmed_result")

            # 7. Failed OCR state
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(0.3)
            state["post_filing_id"] = "fl-fail004"
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(dummy_pdf)
            time.sleep(0.3)
            page.locator("#input-entity-id").fill("ACB")
            time.sleep(0.3)
            radio = page.locator("input[value='consolidated']")
            if radio.count() > 0:
                radio.first.check(force=True)
            time.sleep(0.3)
            submit_btn = page.locator("button:has-text('Bắt đầu đọc và trích xuất PDF'), button:has-text('Trích xuất PDF')").first
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()
            time.sleep(2.5)
            p7 = os.path.join(TEMP_DIR, f"{prefix}07_failed_ocr_{label}.png")
            capture_element(page, wizard, p7, label, "07_failed_ocr")

            context.close()

        browser.close()

    if args.repo_copy_dir:
        for f in os.listdir(TEMP_DIR):
            if f.startswith(prefix):
                shutil.copy2(os.path.join(TEMP_DIR, f), os.path.join(args.repo_copy_dir, f))
        print(f"Copied all {mode} screenshots to {args.repo_copy_dir}")

    print("ALL_SHOTS_SUCCESS")

if __name__ == "__main__":
    main()
