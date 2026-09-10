// Capture the real local app without changing its source or visible content.
const { chromium } = require('C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'docs/assets/thesis-visuals-20260910');
(async () => {
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1120, height: 920}, deviceScaleFactor: 2});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:8765/', {waitUntil: 'networkidle'});
    await page.getByRole('heading', {name: 'Ngân hàng Việt Nam Quý 4 năm 2024'}).waitFor();
    const stats = await page.locator('.stat-line').boundingBox();
    await page.screenshot({path: path.join(out, 'figure-5-1-overview.png'), clip: {x:0,y:0,width:1120,height:Math.ceil(stats.y + stats.height + 12)}});
    await page.setViewportSize({width:800,height:1100});
    const claim = page.locator('#evidence details').first();
    await claim.locator('summary').click();
    await claim.scrollIntoViewIfNeeded();
    await claim.screenshot({path: path.join(out, 'figure-5-2-evidence.png')});
    const report = await (await page.request.get('http://127.0.0.1:8765/data/analysis-report.json')).json();
    const series = await (await page.request.get('http://127.0.0.1:8765/data/analysis-series.json')).json();
    if (report.run.snapshot_id !== series.snapshot_id) throw new Error('Snapshot mismatch');
    if (errors.length) throw new Error(errors.join('\n'));
    const result = {url: page.url(), captured_at_utc: new Date().toISOString(),
      viewport: {overview:{width:1120,height:920},evidence:{width:800,height:1100}}, device_scale_factor:2, snapshot:report.run.snapshot_id,
      report_run:report.run.run_id, readonly:true, source_modified:false,
      screenshot_region:['top through data coverage summary','first expanded evidence claim'], page_errors:errors};
    fs.writeFileSync(path.join(out, 'capture-manifest.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
