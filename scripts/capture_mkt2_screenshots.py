"""Capture visual verification screenshots for Task MKT-2.

Runs local FastAPI backend with FakeSSIMarketDataClient (recorded fixtures)
and operational snapshot bank-quarterly-top10-operational-v1-r4.sqlite.
Serves frontend via vite preview on 127.0.0.1:5173.
Uses Playwright (msedge channel) to capture desktop (1440px) and mobile (390px) screenshots.
Injects 'DỮ LIỆU MẪU' banner in harness page only.
Saves 12 screenshots to C:/Users/ASUS/AppData/Local/Temp/orch/mkt2/shots/.
Verifies strictly that there is NO horizontal scroll at 390px.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
from playwright.sync_api import sync_playwright

src_dir = Path(__file__).resolve().parent.parent / "src"
if not (src_dir / "thesis_api").exists():
    src_dir = Path("D:/eddie-projects/personal-projects/final-thesis/src")
sys.path.insert(0, str(src_dir))

from thesis_api.main import create_app
from thesis_api.settings import Settings
import thesis_api.market_data as mkt


SHOTS_DIR = Path("C:/Users/ASUS/AppData/Local/Temp/orch/mkt2/shots")
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

operational_db = Path("data/processed/bank-quarterly-top10-operational-v1-r4.sqlite")
if not operational_db.exists():
    # If in worktree, resolve from parent workspace
    operational_db = Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1-r4.sqlite")
if not operational_db.exists():
    raise FileNotFoundError(f"Operational snapshot not found: {operational_db}")


def setup_api_server():
    settings = Settings(
        _env_file=None,
        sqlite_db_path=str(operational_db.resolve()),
        app_env="development",
    )
    app = create_app(settings)

    @app.post("/test-control/mode")
    async def set_mode(mode: str):
        if mode == "configured":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient())
        elif mode == "stale":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient())
            # prime cache
            await mkt.get_or_refresh_quotes(mkt.FakeSSIMarketDataClient())
            mkt._quotes_timestamp = datetime.now(timezone.utc) - timedelta(seconds=7200)
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient(fail_daily=True))
        elif mode == "empty_down":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient(fail_daily=True))
        elif mode == "unconfigured":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(None)
        return {"status": "ok", "mode": mode}

    # Override /api/analyze/stream for fast deterministic execution in harness
    @app.post("/api/analyze/stream")
    async def analyze_stream(req: Request):
        async def event_generator():
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's1', 'seq': 1, 't_ms': 100, 'kind': 'plan', 'actor': 'orchestrator', 'recipient': None, 'summary': 'Lập kế hoạch phân tích cho VCB'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's2', 'seq': 2, 't_ms': 200, 'kind': 'assign', 'actor': 'orchestrator', 'recipient': 'company', 'summary': 'Giao chuyên viên doanh nghiệp tính chỉ số VCB'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's3', 'seq': 3, 't_ms': 350, 'kind': 'tool_result', 'actor': 'company', 'recipient': None, 'summary': 'Tính toán số liệu P/B và ROE hoàn tất', 'detail': {'numbers_checked': 4, 'numbers_matched': 4}})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's4', 'seq': 4, 't_ms': 500, 'kind': 'compose', 'actor': 'company', 'recipient': 'orchestrator', 'summary': 'Tổng hợp báo cáo phân tích VCB'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's5', 'seq': 5, 't_ms': 600, 'kind': 'verify', 'actor': 'verifier', 'recipient': 'orchestrator', 'summary': 'Kiểm tra đối soát số liệu gốc: 100% khớp', 'detail': {'numbers_checked': 4, 'numbers_matched': 4}})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: TRACE_STEP\ndata: {json.dumps({'step_id': 's6', 'seq': 6, 't_ms': 750, 'kind': 'accept', 'actor': 'orchestrator', 'recipient': None, 'summary': 'Duyệt báo cáo đạt chuẩn'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"event: REPORT_READY\ndata: {json.dumps({'reportId': 'er9-t01', 'status': 'completed'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    return server


def wait_for_url(url: str, timeout: float = 20.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}")


def inject_harness_banner(page):
    page.evaluate("""() => {
        if (!document.getElementById('sample-data-harness-banner')) {
            const banner = document.createElement('div');
            banner.id = 'sample-data-harness-banner';
            banner.style.cssText = 'width: 100%; background: #DC2626; color: #FFFFFF; text-align: center; font-weight: 800; font-size: 13px; line-height: 28px; letter-spacing: 0.1em; text-transform: uppercase; z-index: 99999; box-shadow: 0 1px 3px rgba(0,0,0,0.3);';
            banner.innerText = 'DỮ LIỆU MẪU';
            document.body.insertBefore(banner, document.body.firstChild);
        }
    }""")


def assert_no_horizontal_scroll(page, label: str):
    info = page.evaluate("""() => {
        const docScroll = document.documentElement.scrollWidth;
        const docClient = document.documentElement.clientWidth;
        const bodyScroll = document.body.scrollWidth;
        const winWidth = window.innerWidth;
        const maxScroll = Math.max(docScroll, bodyScroll);
        return { docScroll, docClient, bodyScroll, winWidth, maxScroll, hasScroll: maxScroll > docClient };
    }""")
    if info["hasScroll"]:
        raise AssertionError(
            f"HORIZONTAL SCROLL DETECTED on {label}: maxScroll={info['maxScroll']} (doc={info['docScroll']}, body={info['bodyScroll']}) > clientWidth={info['docClient']} (win={info['winWidth']})"
        )


def main():
    server = setup_api_server()
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    frontend_dir = Path("frontend").resolve()
    print("Starting vite preview...")
    vite_proc = subprocess.Popen(
        ["npx.cmd", "vite", "preview", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
        cwd=frontend_dir,
        shell=True,
    )

    try:
        wait_for_url("http://127.0.0.1:8000/api/version")
        wait_for_url("http://127.0.0.1:5173/")
        print("Servers are ready.")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="msedge")
            print("Edge browser launched.")

            # -----------------------------------------------------------------
            # 1. Library report with new row (1440px & 390px)
            # -----------------------------------------------------------------
            print("1. Capturing 01_library_report_with_new_row...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=configured", method="POST")
            )

            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=Thị trường")
            page.wait_for_selector("text=Giá đóng cửa")
            page.wait_for_selector("text=P/B (Định giá)")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "01_library_report_with_new_row_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_library_report_with_new_row_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=Thị trường")
            page.wait_for_selector("text=Giá đóng cửa")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "01_library_report_with_new_row_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_library_report_with_new_row_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 2. Freshly generated result view (1440px & 390px)
            # -----------------------------------------------------------------
            print("2. Capturing 02_freshly_generated_result_view...")
            def mock_analyze_stream(route):
                sse_body = (
                    'event: TRACE_STEP\ndata: {"step_id":"s1","seq":1,"t_ms":100,"kind":"plan","actor":"orchestrator","recipient":null,"summary":"Lập kế hoạch phân tích cho VCB"}\n\n'
                    'event: TRACE_STEP\ndata: {"step_id":"s2","seq":2,"t_ms":200,"kind":"assign","actor":"orchestrator","recipient":"company","summary":"Giao chuyên viên doanh nghiệp tính chỉ số VCB"}\n\n'
                    'event: TRACE_STEP\ndata: {"step_id":"s3","seq":3,"t_ms":350,"kind":"tool_result","actor":"company","recipient":null,"summary":"Tính toán số liệu P/B và ROE hoàn tất","detail":{"numbers_checked":4,"numbers_matched":4}}\n\n'
                    'event: TRACE_STEP\ndata: {"step_id":"s4","seq":4,"t_ms":500,"kind":"compose","actor":"company","recipient":"orchestrator","summary":"Tổng hợp báo cáo phân tích VCB"}\n\n'
                    'event: TRACE_STEP\ndata: {"step_id":"s5","seq":5,"t_ms":600,"kind":"verify","actor":"verifier","recipient":"orchestrator","summary":"Kiểm tra đối soát số liệu gốc: 100% khớp","detail":{"numbers_checked":4,"numbers_matched":4}}\n\n'
                    'event: TRACE_STEP\ndata: {"step_id":"s6","seq":6,"t_ms":750,"kind":"accept","actor":"orchestrator","recipient":null,"summary":"Duyệt báo cáo đạt chuẩn"}\n\n'
                    'event: REPORT_READY\ndata: {"reportId":"er9-t01","status":"completed"}\n\n'
                )
                route.fulfill(
                    status=200,
                    headers={"content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache", "connection": "keep-alive"},
                    body=sse_body.encode("utf-8")
                )

            # Desktop 1440 - Capture real state at top of page (item 3)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.route("**/api/analyze/stream", mock_analyze_stream)
            page.goto("http://127.0.0.1:5173/analysis")
            page.wait_for_selector("textarea[aria-label='Câu hỏi phân tích']")
            page.fill("textarea[aria-label='Câu hỏi phân tích']", "Phân tích ROE của VCB")
            page.click("button:has-text('Phân tích')")
            page.wait_for_selector("text=Báo cáo đã sẵn sàng")
            page.wait_for_selector("text=Thị trường")
            page.wait_for_selector("text=Giá đóng cửa")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "02_freshly_generated_result_view_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "02_freshly_generated_result_view_1440.png"))
            page.close()

            # Mobile 390 - Capture real state at top of page (item 3)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.route("**/api/analyze/stream", mock_analyze_stream)
            page.goto("http://127.0.0.1:5173/analysis")
            page.wait_for_selector("textarea[aria-label='Câu hỏi phân tích']")
            page.fill("textarea[aria-label='Câu hỏi phân tích']", "Phân tích ROE của VCB")
            page.click("button:has-text('Phân tích')")
            page.wait_for_selector("text=Báo cáo đã sẵn sàng")
            page.wait_for_selector("text=Thị trường")
            page.wait_for_selector("text=Giá đóng cửa")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "02_freshly_generated_result_view_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "02_freshly_generated_result_view_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 3. Sector report with chips (1440px & 390px)
            # -----------------------------------------------------------------
            print("3. Capturing 03_sector_report_with_chips...")
            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t07")
            page.wait_for_selector("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn = page.locator("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn.scroll_into_view_if_needed()
            expand_btn.click()
            page.wait_for_selector("text=Bảng giá & định giá 10 ngân hàng HOSE")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "03_sector_report_with_chips_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "03_sector_report_with_chips_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t07")
            page.wait_for_selector("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn = page.locator("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn.scroll_into_view_if_needed()
            expand_btn.click()
            page.wait_for_selector("text=Bảng giá & định giá 10 ngân hàng HOSE")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "03_sector_report_with_chips_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "03_sector_report_with_chips_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 4. Stale state (1440px & 390px)
            # -----------------------------------------------------------------
            print("4. Capturing 04_stale...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=stale", method="POST")
            )

            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.locator(".report-sheet").get_by_text("dữ liệu trễ").wait_for(state="visible")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "04_stale_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "04_stale_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.locator(".report-sheet").get_by_text("dữ liệu trễ").wait_for(state="visible")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "04_stale_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "04_stale_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 5. Unconfigured state (1440px & 390px)
            # -----------------------------------------------------------------
            print("5. Capturing 05_unconfigured...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=unconfigured", method="POST")
            )

            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_timeout(1500)
            assert_no_horizontal_scroll(page, "05_unconfigured_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "05_unconfigured_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_timeout(1500)
            assert_no_horizontal_scroll(page, "05_unconfigured_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "05_unconfigured_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 6. Shell ticker alone (1440px & 390px)
            # -----------------------------------------------------------------
            print("6. Capturing 06_shell_ticker_alone...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=configured", method="POST")
            )

            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/data")
            page.wait_for_selector("text=HOSE")
            page.wait_for_selector("text=VCB")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "06_shell_ticker_alone_1440")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "06_shell_ticker_alone_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/data")
            page.wait_for_timeout(1000)
            assert_no_horizontal_scroll(page, "06_shell_ticker_alone_390")
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "06_shell_ticker_alone_390.png"))
            page.close()

            browser.close()
            print("All 12 screenshots successfully captured in C:/Users/ASUS/AppData/Local/Temp/orch/mkt2/shots/!")

    finally:
        print("Stopping servers...")
        server.should_exit = True
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(vite_proc.pid)], shell=True, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
