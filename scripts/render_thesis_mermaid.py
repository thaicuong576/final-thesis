#!/usr/bin/env python3
"""Render docs/thesis-v2/figures/*.mmd to monochrome PNG with real Mermaid (via Playwright).

Black text and borders on a white page, no fills. Output is cropped to the SVG so the
Word builder keeps the natural aspect ratio. Requires: playwright + chromium, network access to cdnjs.

Usage: python scripts/render_thesis_mermaid.py [figures_dir]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

MERMAID_URL = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"
FONT = "Times New Roman, Times, serif"
THEME = {
    "background": "#ffffff", "fontFamily": FONT, "fontSize": "15px",
    "primaryColor": "#ffffff", "primaryTextColor": "#000000", "primaryBorderColor": "#000000",
    "secondaryColor": "#ffffff", "tertiaryColor": "#ffffff", "lineColor": "#000000",
    "textColor": "#000000", "mainBkg": "#ffffff", "nodeBorder": "#000000",
    "clusterBkg": "#ffffff", "clusterBorder": "#000000", "edgeLabelBackground": "#ffffff",
    "titleColor": "#000000", "nodeTextColor": "#000000",
}
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;padding:16px;background:#fff}} .mermaid{{display:inline-block;background:#fff}}
.cluster rect{{stroke-dasharray:5 4 !important;fill:#fff !important}}
path.flowchart-link{{stroke-width:1.2px !important}} .edgeLabel,.edgeLabel p{{background:#fff !important}}
</style></head><body><pre class="mermaid" id="m">{src}</pre>
<script src="{url}"></script>
<script>mermaid.initialize({cfg});</script></body></html>"""


async def render_all(figures: Path) -> None:
    from playwright.async_api import async_playwright

    cfg = json.dumps({
        "startOnLoad": True, "theme": "base", "themeVariables": THEME, "securityLevel": "loose",
        "flowchart": {"htmlLabels": True, "wrappingWidth": 520, "curve": "basis",
                      "nodeSpacing": 30, "rankSpacing": 38, "padding": 10},
    })
    async with async_playwright() as p:
        browser = None
        for kw in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
            try:
                browser = await p.chromium.launch(**kw)
                break
            except Exception as exc:  # noqa: BLE001 - try the next browser channel
                last = exc
        if browser is None:
            raise SystemExit(f"No usable Chromium/Chrome/Edge for Playwright: {last}")
        ctx = await browser.new_context(viewport={"width": 1400, "height": 1000}, device_scale_factor=3)
        for mmd in sorted(figures.glob("*.mmd")):
            src = mmd.read_text(encoding="utf-8").replace("&", "&amp;").replace("<b>", "&lt;b&gt;").replace("</b>", "&lt;/b&gt;").replace("<br/>", "&lt;br/&gt;")
            page = await ctx.new_page()
            await page.set_content(HTML.format(src=src, url=MERMAID_URL, cfg=cfg), wait_until="networkidle")
            await page.wait_for_selector("#m svg", timeout=20000)
            await page.evaluate("document.fonts.ready")
            svg = await page.query_selector("#m svg")
            out = mmd.with_suffix(".png")
            await svg.screenshot(path=str(out), omit_background=False)
            await page.close()
            print("rendered", out.name)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(render_all(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/thesis-v2/figures")))
