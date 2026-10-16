import json
import os
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

OUT_DIR = r"C:\Users\ASUS\AppData\Local\Temp\orch\ingest3\shots"
os.makedirs(OUT_DIR, exist_ok=True)

TINY_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'

CAP_DATA = {
    "snapshotId": "gold-v5",
    "datasetId": "finance-vietnam-banks",
    "datasetSnapshotId": "gold-v5",
    "dataset_snapshot_id": "gold-v5",
    "goldVersion": "v5",
    "entities": [{"id": "ACB", "ticker": "ACB", "name": "ACB", "type": "company"}],
    "periods": [{"id": "2024_Q4", "label": "Q4 2024", "year": 2024, "quarter": 4}],
    "metrics": [{
        "id": "bank.npl_g35",
        "acronym": "NPL_G35",
        "label": "Tỷ lệ nợ xấu (nhóm 3–5)",
        "shortLabel": "Nợ xấu",
        "topicId": "company",
        "unit": "%",
        "direction": "lower_is_better",
        "decimals": 2,
        "group": "asset_quality",
        "groupLabel": "Chất lượng nợ"
    }],
    "topics": [],
    "peerUniverses": [],
    "analysis_available": True,
    "coverage": [{"entity_id": "ACB", "period_id": "2024_Q4", "metrics": ["bank.npl_g35"]}]
}

PROCESSING_FILING_DATA = {
    "filing_id": "fl-acb2025proc003",
    "entity_id": "ACB",
    "fiscal_year": 2025,
    "reporting_scope": "consolidated",
    "display_name": "Ngân hàng Á Châu (ACB)",
    "status": "processing",
    "ocr_provider": "tesseract",
    "rows": [],
    "progress": {"pages_done": 37, "page_count": 120},
    "statement_pages": {"balance_sheet": [], "income_statement": [], "loan_quality_note": []},
    "validation": {
        "status": "fail",
        "ready_to_confirm": False,
        "blocking_reasons_vi": ["Đang đọc báo cáo tài chính..."],
        "checks": []
    },
    "limitations_vi": []
}

CONFIRM_RESULT = {
    "upload_id": "up-acb2025q4-01",
    "entity_id": "ACB",
    "display_name": "Ngân hàng Á Châu",
    "status": "accepted",
    "period_id": "2025_Q4",
    "metrics": [
        {"metric_id": "bank.npl_g35", "computed_value": 0.99, "reported_value": 0.99, "status": "matched"},
        {"metric_id": "bank.llr_coverage", "computed_value": 112.5, "reported_value": 112.5, "status": "matched"},
        {"metric_id": "bank.roa", "computed_value": 1.65, "reported_value": 1.65, "status": "matched"},
        {"metric_id": "bank.roe", "computed_value": 17.58, "reported_value": 17.58, "status": "matched"}
    ],
    "row_issues": [],
    "limitations_vi": "Dữ liệu vận hành mới tạo từ báo cáo tài chính PDF. Độc lập với snapshot Gold v5."
}

def route_handler(route):
    url = route.request.url
    if "capabilities" in url:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(CAP_DATA))
    elif "confirm" in url:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(CONFIRM_RESULT))
    elif "filings" in url and ("fl-acb2025proc003" in url or route.request.method == "POST"):
        route.fulfill(status=201 if route.request.method == "POST" else 200, content_type="application/json", body=json.dumps(PROCESSING_FILING_DATA))
    elif "onboarding" in url:
        route.fulfill(status=404, content_type="application/json", body="{}")
    elif "/pages/" in url and url.endswith(".png"):
        route.fulfill(status=200, content_type="image/png", body=TINY_PNG)
    else:
        route.continue_()

def capture_element(page, locator, path, label, name):
    # Hide sticky header during element screenshot so it doesn't blur or overlap
    page.evaluate("document.querySelectorAll('header.sticky, header').forEach(el => el.style.display = 'none')")
    locator.scroll_into_view_if_needed()
    time.sleep(0.4)
    locator.screenshot(path=path)
    # Restore header
    page.evaluate("document.querySelectorAll('header.sticky, header').forEach(el => el.style.display = '')")
    if label == "390":
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        inner_w = page.evaluate("window.innerWidth")
        assert scroll_w <= inner_w, f"Horizontal overflow on {label}px shot {name}: scrollWidth={scroll_w} > innerWidth={inner_w}"
    print(f"Captured {name}-{label}.png (scrollWidth check passed)")

def run():
    url = "http://localhost:4173/data"
    dummy_pdf_path = os.path.abspath(r"D:\eddie-projects\personal-projects\final-thesis\scripts\dummy.pdf")
    viewports = [
        ("1440", 1440, 900),
        ("390", 390, 844)
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        for label, width, height in viewports:
            print(f"=== Capturing for {label}px ({width}x{height}) ===")
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.route("**/*", route_handler)

            # 1. Upload step
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector("[data-testid='filing-wizard-section']", timeout=15000)
            time.sleep(1)
            wizard = page.locator("[data-testid='filing-wizard-section']")
            capture_element(page, wizard, os.path.join(OUT_DIR, f"01-upload-step-{label}.png"), label, "01-upload-step")

            # 2. Processing step (upload dummy file)
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(dummy_pdf_path)
            time.sleep(0.3)
            # Fill mandatory bank entity ID
            page.locator("#input-entity-id").fill("ACB")
            time.sleep(0.3)
            # Select mandatory reporting scope
            page.locator("input[value='consolidated']").check()
            time.sleep(0.3)
            # Submit upload
            submit_btn = page.locator("button:has-text('Bắt đầu đọc và trích xuất PDF')")
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()
            page.wait_for_selector("[data-testid='processing-step']", timeout=5000)
            time.sleep(2.2)
            capture_element(page, wizard, os.path.join(OUT_DIR, f"02-processing-step-{label}.png"), label, "02-processing-step")

            # 3. Extracted table with issues
            # Click "Làm lại từ đầu"
            reset_btn = page.locator("button:has-text('Làm lại từ đầu')").first
            reset_btn.click()
            time.sleep(0.5)
            sample_btn = page.locator("button:has-text('Dùng bộ mẫu dựng sẵn')").first
            sample_btn.click()
            page.wait_for_selector("[data-testid='sample-selector-modal']", timeout=5000)
            time.sleep(0.5)
            # Click 2nd button (issues sample)
            modal = page.locator("[data-testid='sample-selector-modal']")
            open_btns = modal.locator("button:has-text('Mở mẫu')")
            open_btns.nth(1).click()
            page.wait_for_selector("[data-testid='extracted-rows-section']", timeout=5000)
            time.sleep(1)
            table_sec = page.locator("[data-testid='extracted-rows-section']")
            capture_element(page, table_sec, os.path.join(OUT_DIR, f"03-extracted-issues-{label}.png"), label, "03-extracted-issues")

            # 4. Validation panel with errors
            val_panel = page.locator("[data-testid='validation-panel']")
            capture_element(page, val_panel, os.path.join(OUT_DIR, f"04-validation-errors-{label}.png"), label, "04-validation-errors")

            # 5. Ready to confirm (clean sample)
            reset_btn = page.locator("button:has-text('Làm lại từ đầu')").first
            reset_btn.click()
            time.sleep(0.5)
            sample_btn = page.locator("button:has-text('Dùng bộ mẫu dựng sẵn')").first
            sample_btn.click()
            page.wait_for_selector("[data-testid='sample-selector-modal']", timeout=5000)
            time.sleep(0.5)
            modal = page.locator("[data-testid='sample-selector-modal']")
            open_btns = modal.locator("button:has-text('Mở mẫu')")
            # 1st button is clean
            open_btns.nth(0).click()
            page.wait_for_selector("[data-testid='ready-to-confirm-box']", timeout=5000)
            time.sleep(1)
            confirm_box = page.locator("[data-testid='ready-to-confirm-box']")
            capture_element(page, confirm_box, os.path.join(OUT_DIR, f"05-ready-to-confirm-{label}.png"), label, "05-ready-to-confirm")

            # 6. Confirmed result
            confirm_btn = page.locator("[data-testid='confirm-filing-button']").first
            confirm_btn.click()
            page.wait_for_selector("[data-testid='confirmation-result-card']", timeout=5000)
            time.sleep(1)
            res_card = page.locator("[data-testid='confirmation-result-card']")
            capture_element(page, res_card, os.path.join(OUT_DIR, f"06-confirmed-result-{label}.png"), label, "06-confirmed-result")

            context.close()

        browser.close()
    print("ALL_INGEST_SCREENSHOTS_DONE")

if __name__ == "__main__":
    run()
