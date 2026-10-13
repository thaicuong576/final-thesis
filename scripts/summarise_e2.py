#!/usr/bin/env python3
"""Summarise E2 and E2R evaluation results from deterministic.csv files."""

import csv
import sys
from pathlib import Path


def summarise_file(csv_path: Path) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        return []

    results = []
    reps = sorted(set(r.get("rep", "0") for r in reader), key=lambda x: int(x) if x.isdigit() else x)
    for rep in reps:
        rows = [r for r in reader if r.get("rep", "0") == rep]
        completed = [r for r in rows if r.get("completed") == "1"]

        matched = sum(int(r["numbers_matched"]) for r in rows if r.get("numbers_matched"))
        checked = sum(int(r["numbers_checked"]) for r in rows if r.get("numbers_checked"))

        covs = [float(r["coverage_score"]) for r in completed if r.get("coverage_score")]
        mean_cov = sum(covs) / len(covs) if covs else 0.0

        discarded = sum(int(r["sentences_discarded"]) for r in rows if r.get("sentences_discarded"))
        proposed = sum(int(r["sentences_proposed"]) for r in rows if r.get("sentences_proposed"))
        discard_rate = (discarded / proposed) if proposed > 0 else 0.0

        correct_rej = sum(int(r["correct_rejection"]) for r in rows if r.get("correct_rejection"))
        rej_total = len([r for r in rows if r.get("task_id", "").startswith("R")])

        traces = [float(r["traceability_score"]) for r in completed if r.get("traceability_score")]
        mean_trace = sum(traces) / len(traces) if traces else 0.0

        results.append({
            "file": str(csv_path),
            "rep": rep,
            "total_runs": len(rows),
            "completed_runs": len(completed),
            "numbers_matched": matched,
            "numbers_checked": checked,
            "mean_coverage": mean_cov,
            "sentences_discarded": discarded,
            "sentences_proposed": proposed,
            "discard_rate": discard_rate,
            "correct_rejections": correct_rej,
            "rejections_total": rej_total,
            "traceability": mean_trace,
        })
    return results


def main() -> None:
    if len(sys.argv) > 1:
        csv_paths = [Path(p) for p in sys.argv[1:]]
    else:
        root = Path(__file__).resolve().parent.parent
        candidates = [
            root / "experiments/e2/gpt-5.4-nano/scores/deterministic.csv",
            root / "experiments/e2/gpt-5.4-mini/scores/deterministic.csv",
            root / "experiments/e2/gpt-5.6-luna/scores/deterministic.csv",
            root / "experiments/e2r/gpt-5.6-luna/scores/deterministic.csv",
        ]
        csv_paths = [p for p in candidates if p.exists()]

    if not csv_paths:
        print("No deterministic.csv files found.")
        sys.exit(1)

    print(f"{'Target / Model':<35} | {'Rep':<4} | {'Numbers':<12} | {'Mean Cov':<9} | {'Discarded/Prop':<15} | {'Disc %':<7} | {'Rejections':<11} | {'Trace':<6}")
    print("-" * 115)

    for path in csv_paths:
        summaries = summarise_file(path)
        # derive label from path
        parts = path.parts
        label = path.parent.parent.name
        if "e2r" in parts:
            label = f"e2r/{label}"
        elif "e2" in parts:
            label = f"e2/{label}"

        for s in summaries:
            num_str = f"{s['numbers_matched']}/{s['numbers_checked']}"
            disc_str = f"{s['sentences_discarded']}/{s['sentences_proposed']}"
            rej_str = f"{s['correct_rejections']}/{s['rejections_total']}"
            disc_pct = f"{s['discard_rate'] * 100:.1f}%"
            print(
                f"{label:<35} | {s['rep']:<4} | {num_str:<12} | {s['mean_coverage']:<9.3f} | {disc_str:<15} | {disc_pct:<7} | {rej_str:<11} | {s['traceability']:<6.3f}"
            )


if __name__ == "__main__":
    main()
