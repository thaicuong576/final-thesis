"""Render the claim-driven Vietnamese analysis report contract."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.analysis_report import build_analysis_report  # noqa: E402
from thesis_data.analysis_report_validation import validate_analysis_report  # noqa: E402
from thesis_data.report_view import load_report_view  # noqa: E402


METRIC_LABELS = {
    "bank.npl_g35": "NPL nhóm 3–5",
    "bank.llr_coverage": "Tỷ lệ bao phủ nợ xấu",
    "bank.roa": "ROA",
    "bank.roe": "ROE",
}

STATUS_LABELS = {"partial": "một phần", "success": "thành công", "failed": "thất bại"}
ARM_LABELS = {
    "single_agent": "một tác tử",
    "hierarchical_no_critique": "phân cấp không phản biện",
    "hierarchical_bounded_critique": "phân cấp có phản biện giới hạn",
}
SUPPORT_LABELS = {
    "evidence_backed": "có bằng chứng",
    "partially_supported": "hỗ trợ một phần",
    "source_locator_only": "chỉ có vị trí nguồn",
    "unlabelled": "chưa gắn nhãn",
}

# The report renderer localizes the current reviewed claims while preserving
# the contract's stable claim IDs and the original evidence/provenance fields.
CLAIM_TRANSLATIONS = {
    "claim-001": {
        "title": "VPB có NPL cao nhất ở quý 4 năm 2024",
        "claim": "Tại quý 4 năm 2024, NPL nhóm 3–5 của VPB là 4,1956%, cao hơn ACB 1,5122%, TCB 1,17%, MBB 1,6205% và VCB 0,9636%.",
        "interpretation": "VPB có tỷ lệ khoản vay thuộc nhóm nợ xấu 3–5 được báo cáo cao nhất trong năm ngân hàng ở quý 4 năm 2024.",
        "limitation": "Đây là mô tả tại một thời điểm, không xác định nguyên nhân và không dự báo rủi ro tương lai.",
    },
    "claim-002": {
        "title": "Khả năng sinh lời của VPB cải thiện trong năm 2024",
        "claim": "ROA của VPB tăng từ 1,2179% ở quý 1 năm 2024 lên 1,8361% ở quý 4; ROE tăng từ 8,0671% lên 11,4117%.",
        "interpretation": "Các chỉ số sinh lời tại hai đầu kỳ được báo cáo của VPB cao hơn ở quý 4 so với quý 1.",
        "limitation": "So sánh hai đầu kỳ không chứng minh xu hướng liên tục hoặc quan hệ nhân quả; cần xem xét quy ước tính ROA và ROE.",
    },
    "claim-003": {
        "title": "VCB dẫn đầu về tỷ lệ bao phủ nợ xấu",
        "claim": "Tỷ lệ bao phủ của VCB cao hơn trung vị nhóm so sánh trong cả bốn quý: 199,8177% so với 92,97875% ở quý 1; 212,1089% so với 101,0% ở quý 2; 204,6495% so với 79,0721% ở quý 3; và 223,311% so với 92,2484% ở quý 4.",
        "interpretation": "Trong năm 2024, VCB có tỷ lệ bao phủ được báo cáo mạnh nhất so với trung vị của năm ngân hàng đã được chấp nhận.",
        "limitation": "Định nghĩa tỷ lệ bao phủ phụ thuộc quy ước của từng nguồn; đây không phải bằng chứng nhân quả về chất lượng tín dụng tương lai.",
    },
    "claim-004": {
        "title": "Chưa có số liệu hợp lệ cho các chỉ số của ACB ở quý 1 năm 2024",
        "claim": "Lô dữ liệu Gold xếp cả bốn chỉ số của ACB ở quý 1 năm 2024 vào trạng thái thiếu hoặc chưa được chấp nhận, trong khi dữ liệu chuẩn ngành tương ứng vẫn có sẵn.",
        "interpretation": "Không thể dùng quý 1 năm 2024 của ACB cho các so sánh số liệu cấp ngân hàng đã được kiểm chứng trong báo cáo này.",
        "limitation": "Trạng thái thiếu hoặc chưa được chấp nhận không phản ánh giá trị kinh tế thực tế; hệ thống không nội suy.",
    },
    "claim-005": {
        "title": "NPL của MBB biến động không đơn điệu",
        "claim": "NPL nhóm 3–5 của MBB giảm từ 2,4856% ở quý 1 xuống 1,6360% ở quý 2, tăng lên 2,2342% ở quý 3 rồi giảm xuống 1,6205% ở quý 4.",
        "interpretation": "NPL được báo cáo của MBB tăng ở quý 3 rồi giảm ở quý 4.",
        "limitation": "Đây là mô tả biến động, không suy ra nguyên nhân.",
    },
}

PROFILE_ASSESSMENTS = {
    "ACB": "Chưa có kết luận nổi bật trong phạm vi này.",
    "TCB": "Dẫn đầu ROA; ROA và ROE cùng giảm ở hai đầu kỳ.",
    "VPB": "Quý 4 là điểm bất thường về rủi ro tín dụng trong nhóm; NPL giảm và tỷ lệ bao phủ tăng từ đầu kỳ đến cuối kỳ.",
    "MBB": "Dẫn đầu ROE; NPL giảm và tỷ lệ bao phủ tăng từ đầu kỳ đến cuối kỳ.",
    "VCB": "Quý 4 có hồ sơ NPL/tỷ lệ bao phủ nổi bật nhất về chất lượng tín dụng; NPL giảm và tỷ lệ bao phủ tăng từ đầu kỳ đến cuối kỳ; ROA và ROE cùng giảm ở hai đầu kỳ.",
}
PROFILE_WATCH_POINTS = {
    "ACB": "Thiếu kỳ đầu hoặc kỳ cuối nên chưa thể kết luận xu hướng đầy đủ.",
    "TCB": "Không có cờ dữ liệu riêng trong phạm vi này.",
    "VPB": "NPL cao nhất và tỷ lệ bao phủ thấp nhất trong nhóm ở kỳ cuối.",
    "MBB": "Không có cờ dữ liệu riêng trong phạm vi này.",
    "VCB": "NPL thấp nhất và tỷ lệ bao phủ cao nhất trong nhóm ở kỳ cuối.",
}


def _localized_claim(claim: dict[str, Any]) -> dict[str, Any]:
    localized = dict(claim)
    localized.update(CLAIM_TRANSLATIONS.get(str(claim.get("claim_id")), {}))
    return localized


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _claim_evidence(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for row in report["matrix"]:
        for metric in row["metrics"]:
            for evidence in metric.get("evidence") or []:
                catalog.setdefault(evidence["evidence_id"], evidence)
    return catalog


def _profile_by_ticker(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {profile["ticker"]: profile for profile in report["profiles"]}


def _delta_text(item: dict[str, Any]) -> str:
    delta = item.get("delta")
    if delta is None:
        return "—"
    return f"{delta:+.4f} điểm %"


def render_markdown(report: dict[str, Any]) -> str:
    validate_analysis_report(report)
    run = report["run"]
    scope = report["scope"]
    quality = report["data_quality"]
    profiles = _profile_by_ticker(report)
    evidence_catalog = _claim_evidence(report)
    metric_ids = [item["metric_id"] for item in scope["metrics"]]
    support_text = ", ".join(
        f"{SUPPORT_LABELS.get(key, key)}={value}"
        for key, value in sorted(quality["claim_support_counts"].items())
    )
    localized_takeaways = [_localized_claim(item) for item in report["executive_summary"]["takeaways"]]
    lines = [
        f"# {report['title']}",
        "",
        f"**Trạng thái:** `{run['status']}`  ",
        f"**Bản chụp:** `{_md(run.get('snapshot_id'))}`  ",
        f"**Nhánh xử lý:** `{_md(ARM_LABELS.get(run.get('arm'), run.get('arm')))}`  ",
        f"**Mô hình:** `{_md(run.get('model_id'))}`",
        "",
        "## Kết luận nhanh",
        "",
        f"**{_md(report['executive_summary']['headline'])}**",
        "",
    ]
    for takeaway in localized_takeaways:
        lines.append(f"- **{_md(takeaway['title'])}:** {_md(takeaway['text'])} {takeaway['interpretation']}")
    if not report["executive_summary"]["takeaways"]:
        lines.append("- Chưa đủ dữ liệu để tạo kết luận so sánh.")

    lines.extend(
        [
            "",
            "## Phạm vi và chất lượng dữ liệu",
            "",
            f"- Ngân hàng: `{', '.join(scope['issuers'])}`",
            f"- Kỳ: `{', '.join(scope['periods'])}`",
            f"- Chỉ số: `{', '.join(item['label'] for item in scope['metrics'])}`",
            f"- Ô hợp lệ: `{quality['valid_cells']}/{quality['total_cells']}`; ô thiếu hoặc chưa được chấp nhận: `{quality['missing_or_unaccepted_cells']}`",
            f"- Số nhận định: `{quality['claim_count']}`; phân loại hỗ trợ: `{_md(support_text)}`",
            "",
            "Các con số trong báo cáo lấy từ bản chụp Gold. Một nhận định chỉ được coi là có bằng chứng khi mọi tham chiếu dữ liệu đều có đoạn bằng chứng; vị trí nguồn đơn thuần được đánh dấu riêng.",
            "",
            "## So sánh tại kỳ cuối",
            "",
        ]
    )
    last_period = report["profiles"][0]["period"] if report["profiles"] else "—"
    lines.append("| Ngân hàng | " + " | ".join(METRIC_LABELS.get(metric_id, metric_id) for metric_id in metric_ids) + " |")
    lines.append("|---|" + "---|" * len(metric_ids))
    for ticker in scope["issuers"]:
        profile = profiles[ticker]
        values = [profile["metrics"].get(metric_id, {}).get("display_value", "—") for metric_id in metric_ids]
        lines.append("| " + " | ".join([ticker, *values]) + " |")

    lines.extend(["", "## Xu hướng từ kỳ đầu đến kỳ cuối", ""])
    lines.append("| Ngân hàng | " + " | ".join(METRIC_LABELS.get(metric_id, metric_id) + " Δ" for metric_id in metric_ids) + " |")
    lines.append("|---|" + "---|" * len(metric_ids))
    for ticker in scope["issuers"]:
        trend = profiles[ticker]["trend"]
        values = [_delta_text(trend.get(metric_id, {})) for metric_id in metric_ids]
        lines.append("| " + " | ".join([ticker, *values]) + " |")
    lines.append("")
    lines.append("Δ là thay đổi điểm phần trăm giữa kỳ đầu và kỳ cuối; không phải tốc độ tăng trưởng tương đối.")

    lines.extend(["", "## Phân tích theo ngân hàng", ""])
    claim_map = {claim["claim_id"]: claim for claim in report["claims"]}
    for ticker in scope["issuers"]:
        profile = profiles[ticker]
        lines.extend([f"### {ticker}", "", f"**Bản chụp {last_period}:** "])
        lines.append(", ".join(f"{METRIC_LABELS.get(metric_id, metric_id)} {profile['metrics'].get(metric_id, {}).get('display_value', '—')}" for metric_id in metric_ids) + ".")
        trend_parts = []
        for metric_id in metric_ids:
            trend = profile["trend"].get(metric_id, {})
            if trend.get("delta") is not None:
                trend_parts.append(f"{METRIC_LABELS.get(metric_id, metric_id)} {_delta_text(trend)}")
        lines.append(f"**Xu hướng:** {', '.join(trend_parts) + '.' if trend_parts else 'Chưa đủ điểm đầu-cuối hợp lệ để tính.'}")
        lines.append(f"**Đánh giá:** {_md(PROFILE_ASSESSMENTS.get(ticker, profile['assessment']))}")
        if profile["watch_points"]:
            lines.append("**Cần theo dõi:** " + _md(PROFILE_WATCH_POINTS.get(ticker, "; ".join(profile["watch_points"]))) + ".")
        else:
            lines.append("**Cần theo dõi:** Không có cờ dữ liệu riêng trong phạm vi này.")
        profile_claims = [claim_map[claim_id] for claim_id in profile["claim_ids"] if claim_id in claim_map]
        if profile_claims:
            lines.append("**Nhận định liên quan:** " + ", ".join(f"`{claim['claim_id']}`" for claim in profile_claims) + ".")
        lines.append("")

    lines.extend(["## Nhận định và bằng chứng", ""])
    lines.append("Mỗi nhận định dưới đây có diễn giải và giới hạn. Mã bằng chứng là mã truy vết trong cơ sở dữ liệu; nội dung bằng chứng được liệt kê ở phần sau.")
    lines.append("")
    for claim in report["claims"]:
        localized_claim = _localized_claim(claim)
        lines.extend(
            [
                f"### `{claim['claim_id']}` — {localized_claim['title']}",
                "",
                f"**Nhận định:** {_md(localized_claim['claim'])}",
                "",
                f"**Diễn giải:** {_md(localized_claim['interpretation'])}",
                "",
                f"**Hỗ trợ:** `{_md(SUPPORT_LABELS.get(claim['support'], claim['support']))}`; **Mã bằng chứng:** `{', '.join(claim['evidence_ids']) or 'không có'}`; **Mã nguồn:** `{', '.join(claim['source_ids']) or 'không có'}`",
                "",
                f"**Giới hạn:** {_md(localized_claim['limitation'])}",
                "",
                "| Tham chiếu dữ liệu | Giá trị | Vị trí trích dẫn | Bằng chứng |",
                "|---|---:|---|---|",
            ]
        )
        for ref in claim["data_refs"]:
            lines.append(
                f"| `{ref['ticker']} / {ref['period']} / {ref['metric_id']}` | {ref['display_value']} | `{_md(ref.get('source_locator') or '—')}` | `{', '.join(ref.get('evidence_ids') or []) or 'không có đoạn bằng chứng'}` |"
            )
        lines.append("")

    lines.extend(["## Evidence snippets", ""])
    if evidence_catalog:
        lines.extend(["| Mã bằng chứng | Tài liệu | Trang | Mục | Trích dẫn |", "|---|---|---:|---|---|"])
        for evidence_id, evidence in evidence_catalog.items():
            lines.append(
                f"| `{evidence_id}` | `{_md(evidence.get('source_document'))}` | {evidence.get('page_number') or '—'} | `{_md(evidence.get('section_name') or '—')}` | {_md(evidence.get('quote') or '—')} |"
            )
    else:
        lines.append("Chưa có đoạn bằng chứng được lưu cho các nhận định trong phạm vi này; vị trí nguồn vẫn được giữ để rà soát tiếp.")

    lines.extend(["", "## Giới hạn và dữ liệu thiếu", ""])
    lines.extend(f"- {_md(item)}" for item in report["limitations"])
    lines.extend(["", "## Thông tin lần chạy", ""])
    telemetry = run["telemetry"]
    lines.extend(
        [
            f"- Số lần gọi: `{telemetry['call_count']}`; số lần gọi công cụ: `{telemetry['tool_calls']}`",
            f"- Token: `{telemetry['input_tokens']}` đầu vào + `{telemetry['output_tokens']}` đầu ra",
            f"- Chi phí ước tính: `${telemetry['cost_estimate_usd']}`",
            f"- Độ trễ: `{telemetry['wall_clock_latency_ms']} ms`",
            "",
            "Báo cáo không tự đưa ra khuyến nghị đầu tư. Báo cáo cung cấp kết luận có phạm vi, bằng chứng và giới hạn để người đọc tiếp tục đánh giá.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    validate_analysis_report(report)
    quality = report["data_quality"]
    run = report["run"]
    scope = report["scope"]
    profiles = _profile_by_ticker(report)
    metric_ids = [item["metric_id"] for item in scope["metrics"]]

    def li(items: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>" if items else "<p class='muted'>Không có.</p>"

    takeaway_html = "".join(
        f"<li><b>{escape(item['title'])}:</b> {escape(item['claim'])} {escape(item['interpretation'])}</li>"
        for item in [_localized_claim(item) for item in report["executive_summary"]["takeaways"]]
    )
    table = ["<table><thead><tr><th>Ngân hàng</th>"] + [f"<th>{escape(METRIC_LABELS.get(metric_id, metric_id))}</th>" for metric_id in metric_ids] + ["</tr></thead><tbody>"]
    for ticker in scope["issuers"]:
        profile = profiles[ticker]
        table.append("<tr><td>" + escape(ticker) + "</td>" + "".join(f"<td>{escape(profile['metrics'].get(metric_id, {}).get('display_value', '—'))}</td>" for metric_id in metric_ids) + "</tr>")
    table.append("</tbody></table>")
    profile_sections = []
    for ticker in scope["issuers"]:
        profile = profiles[ticker]
        values = ", ".join(f"{METRIC_LABELS.get(metric_id, metric_id)} {profile['metrics'].get(metric_id, {}).get('display_value', '—')}" for metric_id in metric_ids)
        trend = ", ".join(f"{METRIC_LABELS.get(metric_id, metric_id)} {_delta_text(profile['trend'].get(metric_id, {}))}" for metric_id in metric_ids)
        watch_points = [PROFILE_WATCH_POINTS.get(ticker, item) for item in profile["watch_points"]]
        profile_sections.append(f"<article><h3>{escape(ticker)}</h3><p><b>Bản chụp:</b> {escape(values)}</p><p><b>Xu hướng:</b> {escape(trend)}</p><p><b>Đánh giá:</b> {escape(PROFILE_ASSESSMENTS.get(ticker, profile['assessment']))}</p>{li(watch_points)}</article>")
    claim_sections = []
    for claim in report["claims"]:
        localized_claim = _localized_claim(claim)
        refs = "".join(f"<li>{escape(ref['ticker'])} / {escape(ref['period'])} / {escape(ref['metric_id'])}: {escape(ref['display_value'])} · {escape(ref.get('source_locator') or 'không có vị trí')} · bằng chứng {escape(', '.join(ref.get('evidence_ids') or []) or 'không có')}</li>" for ref in claim["data_refs"])
        claim_sections.append(f"<article class='claim'><h3>{escape(localized_claim['title'])}</h3><p><b>Nhận định:</b> {escape(localized_claim['claim'])}</p><p><b>Diễn giải:</b> {escape(localized_claim['interpretation'])}</p><p><b>Hỗ trợ:</b> <code>{escape(SUPPORT_LABELS.get(claim['support'], claim['support']))}</code></p><p><b>Giới hạn:</b> {escape(localized_claim['limitation'])}</p><p><b>Tham chiếu dữ liệu:</b></p><ul>{refs}</ul></article>")
    return """<!doctype html><html lang='vi'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Analysis report</title><style>
body{font:15px/1.55 system-ui,sans-serif;max-width:1180px;margin:0 auto;padding:30px 22px 70px;color:#18212b;background:#f5f3ee}h1{margin-bottom:4px;font-size:30px}.meta,.muted{color:#66707a}.cards{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}.card{background:#fff;border:1px solid #dedad1;border-radius:10px;padding:12px 16px;min-width:140px}.card b{display:block;color:#66707a;font-size:12px}.card span{display:block;font-size:22px;font-weight:700}.note{background:#fff4cf;border-left:4px solid #d0a500;padding:12px 14px;border-radius:4px}section{margin-top:32px}table{border-collapse:collapse;width:100%;background:#fff;border:1px solid #dedad1;border-radius:10px;overflow:hidden}th,td{padding:10px;border-bottom:1px solid #ebe8e1;text-align:left}th{background:#efede7}article{background:#fff;border:1px solid #dedad1;border-radius:10px;padding:14px 16px;margin:12px 0}code{background:#eeeae2;padding:2px 5px;border-radius:4px}.claim{border-left:4px solid #566b83}ul{padding-left:22px}li{margin:6px 0}
</style><body>""" + f"<h1>{escape(report['title'])}</h1><p class='meta'>{escape(STATUS_LABELS.get(str(run['status']), str(run['status'])))} · bản chụp {escape(str(run.get('snapshot_id')))} · {escape(ARM_LABELS.get(run.get('arm'), str(run.get('arm'))))} · {escape(str(run.get('model_id')))}</p><div class='cards'><div class='card'><b>Ô hợp lệ</b><span>{quality['valid_cells']}/{quality['total_cells']}</span></div><div class='card'><b>Ô thiếu</b><span>{quality['missing_or_unaccepted_cells']}</span></div><div class='card'><b>Nhận định</b><span>{quality['claim_count']}</span></div><div class='card'><b>Có bằng chứng</b><span>{quality['claim_support_counts'].get('evidence_backed', 0)}</span></div></div><p class='note'>Số liệu lấy từ bản chụp Gold. Một nhận định chỉ được coi là có bằng chứng khi các tham chiếu dữ liệu đều có đoạn bằng chứng.</p><section><h2>Kết luận nhanh</h2><p><b>{escape(report['executive_summary']['headline'])}</b></p><ul>{takeaway_html or '<li>Chưa đủ dữ liệu để tạo kết luận so sánh.</li>'}</ul></section><section><h2>So sánh tại kỳ cuối</h2>{''.join(table)}</section><section><h2>Phân tích theo ngân hàng</h2>{''.join(profile_sections)}</section><section><h2>Nhận định và bằng chứng</h2>{''.join(claim_sections)}</section><section><h2>Giới hạn và dữ liệu thiếu</h2>{li(report['limitations'])}</section></body></html>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    view = load_report_view(args.manifest, args.db)
    report = build_analysis_report(view)
    validate_analysis_report(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "analysis-report.md").write_text(render_markdown(report), encoding="utf-8")
    (args.output_dir / "analysis-report.html").write_text(render_html(report), encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "contract_version": report["contract_version"], "claims": len(report["claims"]), "status": report["run"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
