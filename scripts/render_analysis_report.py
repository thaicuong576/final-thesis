"""Render a user-facing Markdown, HTML and JSON report from a run manifest."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.report_view import load_report_view  # noqa: E402


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(view: dict) -> str:
    run = view["run"]
    scope = view["scope"]
    summary = view["summary"]
    lines = [
        "# Bank analysis report",
        "",
        f"**Status:** `{run['status']}`  ",
        f"**Snapshot:** `{_md(run.get('snapshot_id'))}`  ",
        f"**Arm:** `{_md(run.get('arm'))}`  ",
        f"**Model:** `{_md(run.get('model_id'))}`",
        "",
        "## Scope",
        "",
        f"- Banks: `{', '.join(scope['issuers'])}`",
        f"- Periods: `{', '.join(scope['periods'])}`",
        f"- Metrics: `{', '.join(item['label'] for item in scope['metrics'])}`",
        "",
        "## Data status",
        "",
        f"- Valid cells: `{summary['valid_cells']}/{summary['total_cells']}`",
        f"- Missing/unaccepted cells: `{summary['missing_or_unaccepted_cells']}`",
        f"- Cells with stored evidence snippets: `{summary['cells_with_stored_evidence']}`",
        f"- Sources used: `{summary['source_count']}`",
        "",
        "The numeric table below is read from the Gold snapshot. The model contributes interpretation and flags; it is not the arithmetic authority.",
        "",
        "## Metric table",
        "",
        "| Bank | Period | " + " | ".join(item["label"] for item in scope["metrics"]) + " | Status |",
        "|---|---|" + "---|" * (len(scope["metrics"]) + 1),
    ]
    for row in view["matrix"]:
        values = [item["display_value"] for item in row["metrics"]]
        lines.append("| " + " | ".join([row["ticker"], row["period"], *values, row["status"]]) + " |")

    lines.extend(["", "## Agent analysis", ""])
    for heading, key in (("Findings", "findings"), ("Anomaly classifications", "anomaly_classifications"), ("Missing/conflict register", "missing_conflict_register"), ("Quality flags", "quality_flags")):
        lines.extend([f"### {heading}", ""])
        items = view["analysis"][key]
        lines.extend(f"- {_md(item)}" for item in items) if items else lines.append("- None recorded.")
        lines.append("")

    lines.extend(["## Evidence trail", "", "| Bank | Period | Metric | Value | Source | Locator | Evidence |", "|---|---|---|---:|---|---|---|"])
    for row in view["matrix"]:
        for item in row["metrics"]:
            source = item.get("source_id") or "—"
            locator = item.get("source_locator") or "—"
            evidence = ", ".join(item.get("evidence_ids", [])) or "no snippet"
            lines.append("| " + " | ".join([row["ticker"], row["period"], item["label"], item["display_value"], _md(source), _md(locator), _md(evidence)]) + " |")

    lines.extend(["", "## Missing cells", ""])
    if view["missing_cells"]:
        lines.extend(f"- `{item['ticker']} / {item['period']} / {item['metric']}`: {_md(item['reason'])}" for item in view["missing_cells"])
    else:
        lines.append("- None.")
    telemetry = run["telemetry"]
    lines.extend([
        "",
        "## Run details",
        "",
        f"- Calls: `{telemetry['call_count']}`; tool calls: `{telemetry['tool_calls']}`",
        f"- Tokens: `{telemetry['input_tokens']}` input + `{telemetry['output_tokens']}` output",
        f"- Estimated cost: `${telemetry['cost_estimate_usd']}`",
        f"- Wall-clock latency: `{telemetry['wall_clock_latency_ms']} ms`",
        "",
        "The report is `partial` when the Gold snapshot contains explicit missing cells. Missing values are not filled or guessed.",
        "",
    ])
    return "\n".join(lines)


def render_html(view: dict) -> str:
    run, scope, summary = view["run"], view["scope"], view["summary"]
    header = f"<h1>Bank analysis report</h1><p class='meta'><b>Status</b> {escape(str(run['status']))} · <b>Snapshot</b> {escape(str(run.get('snapshot_id')))} · <b>Arm</b> {escape(str(run.get('arm')))}</p>"
    cards = "".join(f"<div class='card'><b>{escape(str(label))}</b><span>{escape(str(value))}</span></div>" for label, value in (("Valid cells", f"{summary['valid_cells']}/{summary['total_cells']}"), ("Missing", summary['missing_or_unaccepted_cells']), ("Evidence snippets", summary['cells_with_stored_evidence']), ("Sources", summary['source_count'])))
    table = ["<table><thead><tr><th>Bank</th><th>Period</th>"] + [f"<th>{escape(item['label'])}</th>" for item in scope["metrics"]] + ["<th>Status</th></tr></thead><tbody>"]
    for row in view["matrix"]:
        table.append(f"<tr><td>{escape(row['ticker'])}</td><td>{escape(row['period'])}</td>" + "".join(f"<td>{escape(item['display_value'])}</td>" for item in row["metrics"]) + f"<td>{escape(row['status'])}</td></tr>")
    table.append("</tbody></table>")
    findings = "".join(f"<li>{escape(item)}</li>" for item in view["analysis"]["findings"]) or "<li>None recorded.</li>"
    missing_items = "".join(
        "<li>" + escape(f"{item['ticker']} / {item['period']} / {item['metric']}: {item['reason']}") + "</li>"
        for item in view["missing_cells"]
    ) or "<li>None.</li>"
    return """<!doctype html><html lang='vi'><meta charset='utf-8'><title>Bank analysis report</title><style>
body{font:14px system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 20px;color:#17202a;background:#f7f6f2}h1{margin-bottom:4px}.meta{color:#5b6470}.cards{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.card{background:white;border:1px solid #d9d6ce;border-radius:10px;padding:14px 18px;min-width:120px}.card span{display:block;font-size:24px;font-weight:700;margin-top:4px}table{border-collapse:collapse;width:100%;background:white}th,td{border-bottom:1px solid #e5e2db;padding:9px;text-align:left}th{background:#efede7}section{margin-top:28px}li{margin:6px 0}.note{background:#fff7dc;padding:12px;border-left:4px solid #d8a900}
</style><body>""" + header + f"<div class='cards'>{cards}</div><p class='note'>Số liệu lấy trực tiếp từ Gold snapshot. Missing không được tự điền.</p><section><h2>Metric table</h2>{''.join(table)}</section><section><h2>Agent findings</h2><ul>{findings}</ul></section><section><h2>Missing cells</h2><ul>{missing_items}</ul></section></body></html>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    view = load_report_view(args.manifest, args.db)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report-view.json").write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(render_markdown(view), encoding="utf-8")
    (args.output_dir / "report.html").write_text(render_html(view), encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "status": view["run"]["status"], "cells": view["summary"]["total_cells"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
