#!/usr/bin/env python3
"""Redraw the two ER-9 thesis charts in plain black-on-white with Vietnamese labels.

Reads experiments/er9/analysis/{arm_summary,pairwise_diffs}.csv and overwrites
figure_er9_cost_latency.png and figure_er9_pairwise_diff.png in the same folder.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 10, "axes.edgecolor": "black", "axes.linewidth": 0.8})

D = Path(sys.argv[1] if len(sys.argv) > 1 else "experiments/er9/analysis")
arms = {r["arm"]: r for r in csv.DictReader(open(D / "arm_summary.csv", encoding="utf-8"))}
order = ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique"]
names = ["A\nmột tác tử", "B\nphân cấp", "C\nphân cấp\ncó phản biện"]

# --- cost / latency ---
fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9))
tok = [float(arms[a]["mean_total_tokens"]) for a in order]
sec = [float(arms[a]["mean_duration_ms"]) / 1000 for a in order]
for ax, vals, title, fmt in ((axes[0], tok, "Token trung bình mỗi lượt", "{:,.0f}"),
                             (axes[1], sec, "Thời gian xử lý (giây)", "{:.1f}")):
    bars = ax.bar(names, vals, color="white", edgecolor="black", hatch="///", linewidth=0.9, width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v).replace(",", "."), ha="center", va="bottom", fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(vals) * 1.15)
fig.tight_layout()
fig.savefig(D / "figure_er9_cost_latency.png", dpi=200, facecolor="white")
plt.close(fig)

# --- pairwise differences ---
rows = list(csv.DictReader(open(D / "pairwise_diffs.csv", encoding="utf-8")))
get = {(r["pair"], r["metric"]): r for r in rows}
metrics = [("coverage_score", "Độ phủ chỉ tiêu", 1), ("cross_level_findings_count", "Phát hiện liên tầng mỗi lượt", 1),
           ("total_tokens", "Token mỗi lượt", 1), ("duration_ms", "Thời gian xử lý (giây)", 1 / 1000)]
pairs = ["B - A", "C - B", "C - A"]
fig, axes = plt.subplots(1, 4, figsize=(6.8, 2.1))
for ax, (m, title, k) in zip(axes, metrics):
    for i, p in enumerate(pairs):
        r = get[(p, m)]
        mean, lo, hi = (float(r["mean_diff"]) * k, float(r["ci_95_lower"]) * k, float(r["ci_95_upper"]) * k)
        y = len(pairs) - 1 - i
        ax.plot([lo, hi], [y, y], color="black", linewidth=1.2)
        ax.plot([mean], [y], marker="o", markersize=5, color="white", markeredgecolor="black")
    ax.set_ylim(-0.6, len(pairs) - 0.4)
    ax.axvline(0, color="black", linewidth=0.6, linestyle="--")
    ax.set_yticks(range(len(pairs)))
    ax.set_yticklabels([p.replace(" - ", " − ") for p in reversed(pairs)] if ax is axes[0] else [])
    ax.set_title(title, fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(D / "figure_er9_pairwise_diff.png", dpi=200, facecolor="white")
print("ok")
