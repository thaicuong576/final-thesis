"""Capture visual verification screenshots for Task MKT-1.

Runs local FastAPI backend with FakeSSIMarketDataClient (recorded fixtures)
and operational snapshot bank-quarterly-top10-operational-v1-r4.sqlite.
Serves frontend via vite preview on 127.0.0.1:5173.
Uses Playwright (msedge channel) to capture desktop (1440px) and mobile (390px) screenshots.
Injects 'DỮ LIỆU MẪU' banner in harness page only.
Saves screenshots to C:/Users/ASUS/AppData/Local/Temp/orch/mkt1/shots/.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

from fastapi import FastAPI
import uvicorn
from playwright.sync_api import sync_playwright

from thesis_api.main import create_app
from thesis_api.settings import Settings
import thesis_api.market_data as mkt


SHOTS_DIR = Path("C:/Users/ASUS/AppData/Local/Temp/orch/mkt1/shots")
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

operational_db = Path("data/processed/bank-quarterly-top10-operational-v1-r4.sqlite")
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
            mkt._quotes_timestamp = datetime.now(timezone.utc) - timedelta(seconds=60)
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient(fail_daily=True))
        elif mode == "empty_down":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(mkt.FakeSSIMarketDataClient(fail_daily=True))
        elif mode == "unconfigured":
            mkt.clear_market_data_cache()
            mkt.set_market_data_client(None)
        return {"status": "ok", "mode": mode}

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


def main():
    server = setup_api_server()
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    frontend_dir = Path("frontend").resolve()
    if not (frontend_dir / "dist" / "index.html").exists():
        print("Building frontend...")
        subprocess.run(["npm.cmd", "run", "build"], cwd=frontend_dir, check=True, shell=True)

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
            # 1. Configured state (1440px & 390px)
            # -----------------------------------------------------------------
            print("1. Capturing configured state...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=configured", method="POST")
            )

            # Desktop 1440
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=BID")
            # Wait for data to render
            page.wait_for_selector("text=17.87%")
            page.wait_for_selector("text=33.950")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_configured_1440.png"))
            page.close()

            # Mobile 390
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=BID")
            page.wait_for_selector("text=17.87%")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_configured_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 2. Scatter chart expanded (1440px & 390px)
            # -----------------------------------------------------------------
            print("2. Capturing scatter chart expanded...")
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=BID")
            expand_btn = page.locator("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn.scroll_into_view_if_needed()
            expand_btn.click()
            page.wait_for_selector("text=Công thức: P/B = Giá đóng cửa")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "02_scatter_chart_expanded_1440.png"))
            page.close()

            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=BID")
            expand_btn = page.locator("button:has-text('Bối cảnh thị trường: Định giá P/B so với ROE')")
            expand_btn.scroll_into_view_if_needed()
            expand_btn.click()
            page.wait_for_selector("text=Công thức: P/B = Giá đóng cửa")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "02_scatter_chart_expanded_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 3. Stale state (1440px & 390px)
            # -----------------------------------------------------------------
            print("3. Capturing stale state...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=stale", method="POST")
            )
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=dữ liệu trễ")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_stale_1440.png"))
            page.close()

            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=dữ liệu trễ")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_stale_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 4. SSI down + empty cache state (1440px & 390px)
            # -----------------------------------------------------------------
            print("4. Capturing SSI down + empty cache state...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=empty_down", method="POST")
            )
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=Dữ liệu thị trường tạm thời không khả dụng")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "03_price_strip_empty_ssi_down_1440.png"))
            page.close()

            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_selector("text=Dữ liệu thị trường tạm thời không khả dụng")
            page.wait_for_timeout(1000)
            inject_harness_banner(page)
            page.screenshot(path=str(SHOTS_DIR / "03_price_strip_empty_ssi_down_390.png"))
            page.close()

            # -----------------------------------------------------------------
            # 5. Unconfigured state (1440px & 390px)
            # -----------------------------------------------------------------
            print("5. Capturing unconfigured state...")
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8000/test-control/mode?mode=unconfigured", method="POST")
            )
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_unconfigured_1440.png"))
            page.close()

            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/reports/er9-t01")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS_DIR / "01_report_price_strip_and_focal_unconfigured_390.png"))
            page.close()

            browser.close()
            print("All screenshots successfully captured!")

    finally:
        print("Stopping servers...")
        server.should_exit = True
        try:
            vite_proc.terminate()
            vite_proc.wait(timeout=5)
        except Exception:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(vite_proc.pid)], shell=True)


if __name__ == "__main__":
    main()
