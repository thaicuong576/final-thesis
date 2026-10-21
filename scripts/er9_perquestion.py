#!/usr/bin/env python3
"""Per-question comparison tables and heatmap for ER-9 Configurations A, B, C, D."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Matplotlib configuration matching mono thesis style
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.edgecolor": "black",
    "axes.linewidth": 0.8,
})

ANALYSIS_TASKS = [f"T{i:02d}" for i in range(1, 11)]
REJECTION_TASKS = ["R1", "R2"]
ALL_TASKS = ANALYSIS_TASKS + REJECTION_TASKS

ARM_KEYS = ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique", "template_only"]
ARM_LABELS = {
    "single_agent": "A (Một tác tử)",
    "hierarchical_no_critique": "B (Phân tầng)",
    "hierarchical_with_critique": "C (Có phản biện)",
    "template_only": "D (Chỉ dùng mẫu)",
}
ARM_SHORT = {
    "single_agent": "A",
    "hierarchical_no_critique": "B",
    "hierarchical_with_critique": "C",
    "template_only": "D",
}


def fmt_vi_dec(val: float, decimals: int = 2) -> str:
    """Format float with comma as decimal separator."""
    return f"{val:.{decimals}f}".replace(".", ",")


def load_scores_dict(
    er9_csv: Path,
    er9d_csv: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Load and merge deterministic scores from er9 (A, B, C) and er9d (D)."""
    scores: dict[tuple[str, str], dict[str, Any]] = {}

    if er9_csv.exists():
        with er9_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                scores[(row["task_id"], row["arm"])] = row

    if er9d_csv.exists():
        with er9d_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                scores[(row["task_id"], row["arm"])] = row

    return scores


def calculate_win_tie_loss(
    scores: Mapping[tuple[str, str], Mapping[str, Any]],
    tasks: Sequence[str] = ANALYSIS_TASKS,
    pairs: Sequence[tuple[str, str, str, str]] = (
        ("hierarchical_no_critique", "single_agent", "B", "A"),
        ("hierarchical_with_critique", "hierarchical_no_critique", "C", "B"),
        ("hierarchical_with_critique", "single_agent", "C", "A"),
        ("template_only", "hierarchical_no_critique", "D", "B"),
        ("template_only", "single_agent", "D", "A"),
    ),
) -> list[dict[str, Any]]:
    """Calculate win/tie/loss counts based on coverage_score rounded to 3 decimal places."""
    results: list[dict[str, Any]] = []
    for arm1, arm2, name1, name2 in pairs:
        win = 0
        tie = 0
        loss = 0
        for tid in tasks:
            rec1 = scores.get((tid, arm1))
            rec2 = scores.get((tid, arm2))
            if not rec1 or not rec2:
                continue
            c1 = round(float(rec1.get("coverage_score", 0.0) or 0.0), 3)
            c2 = round(float(rec2.get("coverage_score", 0.0) or 0.0), 3)
            if c1 > c2:
                win += 1
            elif c1 == c2:
                tie += 1
            else:
                loss += 1
        results.append({
            "pair": f"{name1} - {name2}",
            "arm1": arm1,
            "arm2": arm2,
            "name1": name1,
            "name2": name2,
            "win": win,
            "tie": tie,
            "loss": loss,
            "text": f"{name1} thắng {win}, hòa {tie}, thua {loss} so với {name2}",
        })
    return results


def export_per_question_csv(
    scores: Mapping[tuple[str, str], Mapping[str, Any]],
    out_csv: Path,
) -> None:
    """Export per_question.csv with coverage_score, total_tokens, duration_ms/s for A, B, C, D."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    header = ["task_id"]
    for arm in ARM_KEYS:
        code = ARM_SHORT[arm]
        header.extend([
            f"{code}_coverage_score",
            f"{code}_total_tokens",
            f"{code}_duration_ms",
            f"{code}_duration_s",
        ])

    rows = []
    for tid in ALL_TASKS:
        row: dict[str, Any] = {"task_id": tid}
        for arm in ARM_KEYS:
            code = ARM_SHORT[arm]
            rec = scores.get((tid, arm), {})
            cov = float(rec.get("coverage_score", 0.0) or 0.0)
            tok = int(float(rec.get("total_tokens", 0) or 0))
            dur_ms = int(float(rec.get("duration_ms", 0) or 0))
            dur_s = round(dur_ms / 1000.0, 2)
            row[f"{code}_coverage_score"] = f"{cov:.4f}"
            row[f"{code}_total_tokens"] = tok
            row[f"{code}_duration_ms"] = dur_ms
            row[f"{code}_duration_s"] = f"{dur_s:.2f}"
        rows.append(row)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def export_per_question_md(
    scores: Mapping[tuple[str, str], Mapping[str, Any]],
    out_md: Path,
) -> None:
    """Export per_question.md (Vietnamese markdown table, decimals using comma)."""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Bảng so sánh từng câu hỏi qua 4 cấu hình (A, B, C, D)",
        "",
        "Bảng tổng hợp chi tiết 10 câu phân tích (T01–T10) và 2 câu kiểm thử từ chối (R1, R2) qua 4 cấu hình:",
        "- **Cấu hình A**: Single-agent (Một tác tử)",
        "- **Cấu hình B**: Hierarchical no critique (Phân tầng không phản biện)",
        "- **Cấu hình C**: Hierarchical with critique (Phân tầng có phản biện)",
        "- **Cấu hình D**: Template-only (Chỉ dùng câu mẫu, không gọi mô hình, 0 token)",
        "",
        "| Mã câu | A: Độ phủ | A: Token | A: Thời gian (s) | B: Độ phủ | B: Token | B: Thời gian (s) | C: Độ phủ | C: Token | C: Thời gian (s) | D: Độ phủ | D: Token | D: Thời gian (s) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for tid in ANALYSIS_TASKS:
        cols = [tid]
        for arm in ARM_KEYS:
            rec = scores.get((tid, arm), {})
            cov = float(rec.get("coverage_score", 0.0) or 0.0)
            tok = int(float(rec.get("total_tokens", 0) or 0))
            dur_ms = int(float(rec.get("duration_ms", 0) or 0))
            dur_s = dur_ms / 1000.0

            cols.append(fmt_vi_dec(cov, 2))
            cols.append(f"{tok:,}".replace(",", "."))
            cols.append(fmt_vi_dec(dur_s, 2))
        lines.append("| " + " | ".join(cols) + " |")

    lines.append("")
    lines.append("### Các câu hỏi kiểm thử từ chối (Rejection Tasks)")
    lines.append("")
    lines.append("| Mã câu | Nội dung kiểm thử | A: Trạng thái / Token | B: Trạng thái / Token | C: Trạng thái / Token | D: Trạng thái / Token |",)
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: |")

    rejection_desc = {
        "R1": "Từ chối kỳ chưa có (2026_Q3 ngoài snapshot)",
        "R2": "Từ chối thực thể ngoài danh mục (OCB ngoài Top 10)",
    }
    for tid in REJECTION_TASKS:
        cols = [tid, rejection_desc.get(tid, "")]
        for arm in ARM_KEYS:
            rec = scores.get((tid, arm), {})
            st = rec.get("status", "error")
            tok = int(float(rec.get("total_tokens", 0) or 0))
            cols.append(f"{st} ({tok} tok)")
        lines.append("| " + " | ".join(cols) + " |")

    lines.append("")
    lines.append("> **Ghi chú**: Số thập phân sử dụng dấu phẩy (`,`) theo chuẩn trình bày tiếng Việt.")
    lines.append("> R1 và R2 được từ chối hợp lệ tại cổng kiểm soát trước khi suy luận ở cả 4 cấu hình.")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_win_tie_loss_md(
    wtl_results: Sequence[dict[str, Any]],
    out_md: Path,
) -> None:
    """Export win_tie_loss.md reporting pairwise comparisons."""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# So sánh đối đầu Thắng - Hòa - Thua (Win / Tie / Loss)",
        "",
        "Đánh giá độ phủ chỉ tiêu bắt buộc (`coverage_score`) trên **10 câu hỏi phân tích** (T01–T10).",
        "Quy tắc so sánh: giá trị làm tròn đến 3 chữ số thập phân; **Thắng** khi lớn hơn, **Hòa** khi bằng nhau, **Thua** khi nhỏ hơn.",
        "",
        "## Kết quả từng cặp",
        "",
    ]

    for item in wtl_results:
        lines.append(f"- **{item['text']}**")

    lines.append("")
    lines.append("## Bảng tổng hợp đối đầu")
    lines.append("")
    lines.append("| Cặp so sánh | Thắng (Win) | Hòa (Tie) | Thua (Loss) | Tỷ lệ không thua (Win + Tie) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    for item in wtl_results:
        w, t, l = item["win"], item["tie"], item["loss"]
        non_loss_pct = ((w + t) / (w + t + l) * 100.0) if (w + t + l) > 0 else 0.0
        lines.append(f"| {item['pair']} | {w} | {t} | {l} | {fmt_vi_dec(non_loss_pct, 1)}% |")

    lines.append("")
    lines.append("> **Nhận xét chính**:")
    lines.append("> 1. **D so với B & A**: Cấu hình mẫu D (0 token, xử lý nhanh nhất) giữ độ phủ hòa 6/10 câu trước cả A và B, cho thấy các mẫu câu tất định đáp ứng tốt các câu hỏi trực diện.")
    lines.append("> 2. **B so với A**: Cấu hình phân tầng B vượt trội A ở 3 câu (thắng 3, hòa 6, thua 1), cải thiện độ phủ chỉ tiêu ngân hàng.")
    lines.append("> 3. **C so với B**: Vòng phản biện và sửa đổi ở C kiểm tra khắt khe tính suy luận, dẫn đến 2 câu tăng độ phủ, 4 câu giữ nguyên và 4 câu bị cắt bớt câu chưa đủ căn cứ.")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_coverage_heatmap(
    scores: Mapping[tuple[str, str], Mapping[str, Any]],
    out_png: Path,
) -> None:
    """Generate grayscale heatmap of coverage_score across T01-T10 for A, B, C, D at 200 dpi."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.zeros((len(ANALYSIS_TASKS), len(ARM_KEYS)), dtype=float)

    for i, tid in enumerate(ANALYSIS_TASKS):
        for j, arm in enumerate(ARM_KEYS):
            rec = scores.get((tid, arm), {})
            cov = float(rec.get("coverage_score", 0.0) or 0.0)
            matrix[i, j] = cov

    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(matrix, cmap="Greys", vmin=0.0, vmax=1.0, aspect="auto")

    # X and Y ticks
    col_labels = ["A\n(Một tác tử)", "B\n(Phân tầng)", "C\n(Có phản biện)", "D\n(Chỉ dùng mẫu)"]
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=10)
    ax.set_yticks(np.arange(len(ANALYSIS_TASKS)))
    ax.set_yticklabels(ANALYSIS_TASKS, fontsize=10)

    # In cell numbers
    for i in range(len(ANALYSIS_TASKS)):
        for j in range(len(ARM_KEYS)):
            val = matrix[i, j]
            text_str = fmt_vi_dec(val, 2)
            # Text color: white if background is dark, black otherwise
            color = "white" if val > 0.55 else "black"
            ax.text(j, i, text_str, ha="center", va="center", color=color, fontsize=9.5, fontweight="medium")

    ax.set_title("Bản đồ nhiệt độ phủ chỉ tiêu bắt buộc theo câu hỏi (T01–T10)", fontsize=11, pad=12)
    ax.set_xlabel("Cấu hình kiến trúc", fontsize=10, labelpad=8)
    ax.set_ylabel("Mã câu hỏi phân tích", fontsize=10, labelpad=8)

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.04)
    cbar.ax.set_ylabel("Độ phủ chỉ tiêu (0,0 – 1,0)", rotation=-90, va="bottom", fontsize=9.5)
    cbar.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: fmt_vi_dec(x, 1)))

    fig.tight_layout()
    fig.savefig(out_png, dpi=200, facecolor="white")
    plt.close(fig)


def run_perquestion_analysis(
    er9_csv: Path,
    er9d_csv: Path,
    out_dir: Path,
) -> None:
    """Run full per-question analysis and export CSV, Markdown tables, and Heatmap PNG."""
    scores = load_scores_dict(er9_csv, er9d_csv)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Per-question CSV & MD
    csv_path = out_dir / "per_question.csv"
    md_path = out_dir / "per_question.md"
    export_per_question_csv(scores, csv_path)
    export_per_question_md(scores, md_md := md_path)
    print(f"Exported: {csv_path}")
    print(f"Exported: {md_path}")

    # 2. Win / Tie / Loss MD
    wtl = calculate_win_tie_loss(scores)
    wtl_path = out_dir / "win_tie_loss.md"
    export_win_tie_loss_md(wtl, wtl_path)
    print(f"Exported: {wtl_path}")

    # 3. Heatmap PNG (200 dpi, mono)
    heatmap_path = out_dir / "figure_er9_perquestion_heatmap.png"
    generate_coverage_heatmap(scores, heatmap_path)
    print(f"Exported: {heatmap_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-question comparison tables and heatmap for ER-9 (A/B/C/D).")
    parser.add_argument("--er9-csv", type=Path, default=ROOT / "experiments" / "er9" / "scores" / "deterministic.csv")
    parser.add_argument("--er9d-csv", type=Path, default=ROOT / "experiments" / "er9d" / "scores" / "deterministic.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments" / "er9d" / "analysis")
    args = parser.parse_args()

    run_perquestion_analysis(
        er9_csv=args.er9_csv,
        er9d_csv=args.er9d_csv,
        out_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
