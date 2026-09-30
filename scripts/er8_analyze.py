#!/usr/bin/env python3
"""Analysis and reporting for ER-8 A/B/C evaluation experiment.

Computes:
  1. Summary tables by arm and question category.
  2. Paired differences C-B, B-A, C-A with 95% bootstrap confidence intervals (exploratory).
  3. Exported CSV tables and publication-grade matplotlib PNG figures.
  4. Vietnamese summary report in experiments/er8/RESULTS.md formatted for Chapter 5.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    HAS_MATPLOTLIB = False


def read_scores_csv(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parsed: dict[str, Any] = dict(r)
            for k, v in r.items():
                if v == "" or v is None:
                    parsed[k] = None
                    continue
                try:
                    if "." in v:
                        parsed[k] = float(v)
                    else:
                        parsed[k] = int(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def bootstrap_ci(
    diffs: Sequence[float],
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 20260930,
) -> tuple[float, float, float]:
    """Compute mean difference and non-parametric bootstrap confidence interval."""
    if not diffs:
        return 0.0, 0.0, 0.0
    mean_val = sum(diffs) / len(diffs)
    if len(diffs) == 1:
        return mean_val, mean_val, mean_val

    rng = random.Random(seed)
    boot_means = []
    n = len(diffs)
    for _ in range(n_bootstrap):
        sample = [rng.choice(diffs) for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()

    lower_idx = int((1.0 - ci) / 2.0 * n_bootstrap)
    upper_idx = int((1.0 - (1.0 - ci) / 2.0) * n_bootstrap)
    lower_idx = max(0, min(n_bootstrap - 1, lower_idx))
    upper_idx = max(0, min(n_bootstrap - 1, upper_idx))

    return mean_val, boot_means[lower_idx], boot_means[upper_idx]


def analyze_evaluation(
    *,
    scores_csv: Path,
    output_dir: Path,
    results_md: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_scores_csv(scores_csv)
    if not rows:
        print("No rows found in scores CSV.")
        return

    # 1. Summary by Arm
    arms = ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique"]
    arm_labels = {
        "single_agent": "Arm A (Single-Agent)",
        "hierarchical_no_critique": "Arm B (Hierarchical không phản biện)",
        "hierarchical_with_critique": "Arm C (Hierarchical có phản biện)",
    }

    metrics_to_avg = [
        "completed",
        "protocol_success",
        "numeric_correctness",
        "traceability_score",
        "coverage_score",
        "discard_rate",
        "cross_level_findings_count",
        "duration_ms",
        "model_calls",
        "total_tokens",
        "revision_rounds",
    ]

    arm_summary_data = []
    arm_rows_map: dict[str, list[dict[str, Any]]] = {a: [] for a in arms}
    for r in rows:
        a = r.get("arm")
        if a in arm_rows_map:
            arm_rows_map[a].append(r)

    for a in arms:
        a_rows = arm_rows_map[a]
        n_total = len(a_rows)
        row_dict: dict[str, Any] = {
            "arm": a,
            "label": arm_labels.get(a, a),
            "total_runs": n_total,
        }
        for m in metrics_to_avg:
            vals = [r[m] for r in a_rows if r.get(m) is not None]
            avg = (sum(vals) / len(vals)) if vals else 0.0
            row_dict[f"mean_{m}"] = round(avg, 4)
        arm_summary_data.append(row_dict)

    # Write arm_summary.csv
    summary_csv = output_dir / "arm_summary.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(arm_summary_data[0].keys()))
        writer.writeheader()
        writer.writerows(arm_summary_data)
    print(f"Written: {summary_csv}")

    # 2. Paired Differences across (task_id, rep)
    # Group runs by (task_id, rep)
    paired_groups: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for r in rows:
        k = (r["task_id"], r["rep"])
        if k not in paired_groups:
            paired_groups[k] = {}
        paired_groups[k][r["arm"]] = r

    diff_pairs = [
        ("C - B", "hierarchical_with_critique", "hierarchical_no_critique"),
        ("B - A", "hierarchical_no_critique", "single_agent"),
        ("C - A", "hierarchical_with_critique", "single_agent"),
    ]

    pairwise_results = []
    diff_metrics = [
        ("protocol_success", "Tỷ lệ thành công thức nghiệm"),
        ("numeric_correctness", "Tính đúng số"),
        ("coverage_score", "Độ phủ chỉ tiêu"),
        ("traceability_score", "Truy vết observation"),
        ("discard_rate", "Tỷ lệ câu bị loại"),
        ("cross_level_findings_count", "Số liên kết tầng"),
        ("total_tokens", "Tổng token tiêu thụ"),
        ("duration_ms", "Thời gian xử lý (ms)"),
    ]

    for pair_name, arm_x, arm_y in diff_pairs:
        for metric_key, metric_desc in diff_metrics:
            diff_list: list[float] = []
            for (tid, rep), arm_dict in paired_groups.items():
                rx = arm_dict.get(arm_x)
                ry = arm_dict.get(arm_y)
                if rx and ry and rx.get(metric_key) is not None and ry.get(metric_key) is not None:
                    d = float(rx[metric_key]) - float(ry[metric_key])
                    diff_list.append(d)

            mean_d, ci_lo, ci_hi = bootstrap_ci(diff_list)
            pairwise_results.append({
                "pair": pair_name,
                "metric": metric_key,
                "description": metric_desc,
                "n_pairs": len(diff_list),
                "mean_diff": round(mean_d, 4),
                "ci_95_lower": round(ci_lo, 4),
                "ci_95_upper": round(ci_hi, 4),
                "exploratory_note": "Khám phá (cỡ mẫu nhỏ)",
            })

    # Write pairwise_diffs.csv
    pairwise_csv = output_dir / "pairwise_diffs.csv"
    with open(pairwise_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(pairwise_results[0].keys()))
        writer.writeheader()
        writer.writerows(pairwise_results)
    print(f"Written: {pairwise_csv}")

    # 3. Generate PNG figures with matplotlib (if available)
    if not HAS_MATPLOTLIB or plt is None:
        print("Note: matplotlib not installed; skipping PNG figure generation.")
        return

    plt.rcParams.update({"font.sans-serif": "DejaVu Sans", "figure.autolayout": True})

    # Figure 1: Completion and Accuracy by Arm
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    x = range(len(arms))
    width = 0.35
    completion_rates = [d["mean_protocol_success"] * 100 for d in arm_summary_data]
    accuracy_rates = [d["mean_numeric_correctness"] * 100 for d in arm_summary_data]

    b1 = ax.bar([i - width / 2 for i in x], completion_rates, width, label="Thành công (%)", color="#2b5c8f")
    b2 = ax.bar([i + width / 2 for i in x], accuracy_rates, width, label="Đúng số (%)", color="#2a9d8f")

    ax.set_ylabel("Tỷ lệ (%)")
    ax.set_title("ER-8: Tỷ lệ hoàn thành & Tính đúng số giữa 3 Arm")
    ax.set_xticks(x)
    ax.set_xticklabels([arm_labels[a] for a in arms], rotation=10, ha="right", fontsize=9)
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in b1 + b2:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8)

    fig1_path = output_dir / "figure_er8_completion_accuracy.png"
    plt.savefig(fig1_path)
    plt.close()
    print(f"Written: {fig1_path}")

    # Figure 2: Cost and Latency
    fig, ax1 = plt.subplots(figsize=(8, 5), dpi=300)
    ax2 = ax1.twinx()

    tokens = [d["mean_total_tokens"] for d in arm_summary_data]
    durations = [d["mean_duration_ms"] / 1000.0 for d in arm_summary_data]

    b1 = ax1.bar([i - width / 2 for i in x], tokens, width, label="Tokens (Input+Output)", color="#e76f51")
    b2 = ax2.bar([i + width / 2 for i in x], durations, width, label="Độ trễ (giây)", color="#e9c46a")

    ax1.set_ylabel("Tokens tiêu thụ")
    ax2.set_ylabel("Thời gian trung bình (giây)")
    ax1.set_title("ER-8: Chi phí Tokens & Độ trễ thực thi theo Arm")
    ax1.set_xticks(x)
    ax1.set_xticklabels([arm_labels[a] for a in arms], rotation=10, ha="right", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig2_path = output_dir / "figure_er8_cost_latency.png"
    plt.savefig(fig2_path)
    plt.close()
    print(f"Written: {fig2_path}")

    # Figure 3: Paired differences with 95% Bootstrap CI
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    selected_metrics = ["protocol_success", "numeric_correctness", "coverage_score", "cross_level_findings_count"]
    metric_labels = {
        "protocol_success": "Thành công",
        "numeric_correctness": "Đúng số",
        "coverage_score": "Độ phủ",
        "cross_level_findings_count": "Liên kết tầng",
    }

    pairs = ["C - B", "B - A", "C - A"]
    colors = {"C - B": "#264653", "B - A": "#2a9d8f", "C - A": "#e76f51"}

    y_pos = 0
    y_ticks = []
    y_labels = []

    for m in selected_metrics:
        for p in pairs:
            item = next((item for item in pairwise_results if item["pair"] == p and item["metric"] == m), None)
            if item:
                m_diff = item["mean_diff"]
                ci_l = item["ci_95_lower"]
                ci_u = item["ci_95_upper"]
                err_l = m_diff - ci_l
                err_u = ci_u - m_diff

                ax.errorbar(
                    m_diff,
                    y_pos,
                    xerr=[[err_l], [err_u]],
                    fmt="o",
                    color=colors[p],
                    capsize=4,
                    label=p if y_pos < 3 else "",
                )
                y_ticks.append(y_pos)
                y_labels.append(f"{metric_labels[m]} ({p})")
                y_pos += 1
        y_pos += 0.5  # gap between metric groups

    ax.axvline(0, color="gray", linestyle="--", alpha=0.7)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=8)
    ax.set_xlabel("Chênh lệch trung bình theo cặp (Kèm 95% Bootstrap CI)")
    ax.set_title("ER-8: So sánh cặp Arm A/B/C với Khoảng tin cậy Bootstrap")
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    # Unique legend entries
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(by_label.values(), by_label.keys(), loc="lower right")

    fig3_path = output_dir / "figure_er8_pairwise_diff.png"
    plt.savefig(fig3_path)
    plt.close()
    print(f"Written: {fig3_path}")

    # 4. Generate experiments/er8/RESULTS.md in Vietnamese
    results_content = f"""# Báo cáo Đánh giá Thực nghiệm A/B/C (ER-8)

Tài liệu này tổng hợp kết quả chạy thử nghiệm A/B/C trên bộ dữ liệu kiểm chứng Gold v5 (`gold-bank-2025-expanded-v5-evidence`), phục vụ phân tích thực nghiệm tại **Chương 5** của khóa luận tốt nghiệp.

> **Ghi chú tiến độ:** Báo cáo này được tạo bởi công cụ đánh giá tự động (harness & deterministic scorer). Dữ liệu mẫu dưới đây phản ánh kết quả chạy offline / dry-run phục vụ nghiệm thu bộ công cụ; phiên bản chính thức sẽ được kích hoạt khi chạy model trực tiếp theo ngân sách được duyệt.

---

## 1. Thiết kế Thí nghiệm và Các Nhánh So Sánh (Arms)

Thực nghiệm so sánh 3 kiến trúc xử lý trên cùng một câu hỏi và cùng một ảnh chụp dữ liệu (Gold v5):

- **Arm A (`single_agent`)**: Mô hình đơn lẻ, đóng vai trò đường cơ sở (baseline). Điều phối viên tổng hợp trực tiếp báo cáo từ tập dữ kiện tất định, không có sự tham gia của các chuyên viên độc lập và không có vòng phản biện ngữ nghĩa.
- **Arm B (`hierarchical_no_critique`)**: Kiến trúc phân tầng thích ứng theo loại câu hỏi. Các chuyên viên chuyên trách (doanh nghiệp, ngành, liên kết tầng) lập luận và trích xuất câu phân tích; kiểm chứng câu tự động; điều phối viên ghép khối báo cáo, không có vòng phản biện.
- **Arm C (`hierarchical_with_critique`)**: Kiến trúc phân tầng đầy đủ. Cùng điều phối viên và chuyên viên như Arm B, bổ sung thêm chuyên viên phản biện ngữ nghĩa (Semantic Critic) với tối đa 2 vòng tái lập luận và sửa đổi có định hướng.

### Ràng buộc thực nghiệm công bằng:
1. **Lập kế hoạch đồng nhất**: Cả 3 arm vận hành với chế độ `planner_mode="rules_only"`, đảm bảo cấu trúc phân rã công việc (plan) hoàn toàn tất định và giống hệt nhau giữa 3 arm cho cùng một câu hỏi.
2. **Ngân sách token và kiểm soát dừng**: Giới hạn tối đa 3.000.000 tokens cho toàn bộ lượt chạy, dừng khẩn cấp nếu vượt ngưỡng.
3. **Mẫu số bất biến**: Mọi lượt chạy thất bại hoặc bị từ chối đều được lưu vết đầy đủ trong trace và tính vào mẫu số đánh giá tỷ lệ thành công.

---

## 2. Bảng Tổng Hợp Kết Quả Giữa Các Arm

| Chỉ số Đánh giá | Arm A (Single-Agent) | Arm B (Phân tầng - Không phản biện) | Arm C (Phân tầng - Có phản biện) |
|---|:---:|:---:|:---:|
| **Số lượt chạy** | {arm_summary_data[0]["total_runs"]} | {arm_summary_data[1]["total_runs"]} | {arm_summary_data[2]["total_runs"]} |
| **Tỷ lệ thành công thức nghiệm** | {arm_summary_data[0]["mean_protocol_success"]*100:.1f}% | {arm_summary_data[1]["mean_protocol_success"]*100:.1f}% | {arm_summary_data[2]["mean_protocol_success"]*100:.1f}% |
| **Tính đúng số (Numeric Correctness)** | {arm_summary_data[0]["mean_numeric_correctness"]*100:.1f}% | {arm_summary_data[1]["mean_numeric_correctness"]*100:.1f}% | {arm_summary_data[2]["mean_numeric_correctness"]*100:.1f}% |
| **Truy vết nguồn (Traceability)** | {arm_summary_data[0]["mean_traceability_score"]*100:.1f}% | {arm_summary_data[1]["mean_traceability_score"]*100:.1f}% | {arm_summary_data[2]["mean_traceability_score"]*100:.1f}% |
| **Độ phủ chỉ tiêu (Coverage)** | {arm_summary_data[0]["mean_coverage_score"]*100:.1f}% | {arm_summary_data[1]["mean_coverage_score"]*100:.1f}% | {arm_summary_data[2]["mean_coverage_score"]*100:.1f}% |
| **Tỷ lệ câu bị loại (Discard Rate)** | {arm_summary_data[0]["mean_discard_rate"]*100:.1f}% | {arm_summary_data[1]["mean_discard_rate"]*100:.1f}% | {arm_summary_data[2]["mean_discard_rate"]*100:.1f}% |
| **Số liên kết tầng phát hiện** | {arm_summary_data[0]["mean_cross_level_findings_count"]:.2f} | {arm_summary_data[1]["mean_cross_level_findings_count"]:.2f} | {arm_summary_data[2]["mean_cross_level_findings_count"]:.2f} |
| **Thời gian thực thi trung bình (ms)** | {arm_summary_data[0]["mean_duration_ms"]:.0f} | {arm_summary_data[1]["mean_duration_ms"]:.0f} | {arm_summary_data[2]["mean_duration_ms"]:.0f} |
| **Số lần gọi mô hình (Calls)** | {arm_summary_data[0]["mean_model_calls"]:.1f} | {arm_summary_data[1]["mean_model_calls"]:.1f} | {arm_summary_data[2]["mean_model_calls"]:.1f} |
| **Tổng Tokens tiêu thụ** | {arm_summary_data[0]["mean_total_tokens"]:.0f} | {arm_summary_data[1]["mean_total_tokens"]:.0f} | {arm_summary_data[2]["mean_total_tokens"]:.0f} |
| **Số vòng sửa đổi (Revisions)** | {arm_summary_data[0]["mean_revision_rounds"]:.1f} | {arm_summary_data[1]["mean_revision_rounds"]:.1f} | {arm_summary_data[2]["mean_revision_rounds"]:.1f} |

---

## 3. Phân Tích Chênh Lệch Theo Cặp (Pairwise Differences)

Khoảng tin cậy 95% được ước tính qua phương pháp phi tham số Bootstrap (1.000 lần lặp lại trên các cặp cùng tác vụ và lần lặp). Do quy mô mẫu thực nghiệm có giới hạn, các phân tích này mang tính khám phá (exploratory).

"""

    for p in pairs:
        results_content += f"\n### Chênh lệch cặp: {p}\n\n"
        results_content += "| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |\n"
        results_content += "|---|:---:|:---:|:---:|\n"
        p_items = [item for item in pairwise_results if item["pair"] == p]
        for it in p_items:
            results_content += f"| {it['description']} | {it['mean_diff']:+.4f} | [{it['ci_95_lower']:+.4f}, {it['ci_95_upper']:+.4f}] | Khám phá |\n"

    results_content += f"""
---

## 4. Các Biểu Đồ Minh Họa Phục Vụ Chương 5

Các đồ thị phân tích đã được xuất tại thư mục `experiments/er8/analysis/`:

1. **Tỷ lệ hoàn thành & Tính đúng số giữa các arm**: `figure_er8_completion_accuracy.png`
2. **Chi phí tokens & Thời gian thực thi**: `figure_er8_cost_latency.png`
3. **So sánh chênh lệch cặp với khoảng tin cậy Bootstrap**: `figure_er8_pairwise_diff.png`

---

## 5. Hạn Chế Của Đợt Đánh Giá

1. **Chấm điểm tất định**: Phiên bản này ưu tiên tính khách quan, đo lường tự động trên bằng chứng số liệu và bộ kiểm chứng câu; chưa bao gồm gói chấm mù định tính từ chuyên gia con người.
2. **Quy mô tập tác vụ**: Gồm 12 câu hỏi tiêu biểu đại diện cho 5 loại hình câu hỏi chính (hồ sơ, xu hướng, xếp hạng, đối đầu, thiếu dữ liệu/từ chối).
3. **Lập kế hoạch tất định**: Chế độ `planner_mode="rules_only"` giúp đảm bảo tính tương đương giữa các arm nhưng làm giảm bớt tính tự do thích ứng của mô hình ngôn ngữ lớn ở tầng lập kế hoạch.
"""

    results_md.parent.mkdir(parents=True, exist_ok=True)
    results_md.write_text(results_content, encoding="utf-8")
    print(f"Written results report: {results_md}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze ER-8 evaluation results")
    parser.add_argument("--scores-csv", type=Path, default=ROOT / "experiments" / "er8" / "scores" / "deterministic.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments" / "er8" / "analysis")
    parser.add_argument("--results-md", type=Path, default=ROOT / "experiments" / "er8" / "RESULTS.md")

    args = parser.parse_args()

    analyze_evaluation(
        scores_csv=args.scores_csv,
        output_dir=args.output_dir,
        results_md=args.results_md,
    )


if __name__ == "__main__":
    main()
