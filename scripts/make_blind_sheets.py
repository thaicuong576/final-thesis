#!/usr/bin/env python3
"""Build blinded grading sheets from ER-9 style run files.

For each chosen question it renders the report text of every configuration, hides
the configuration label, shuffles the order with a fixed seed, and writes:
  - sheet.md      the text graders read (item codes only);
  - scores.csv    an empty score table (one row per grader x item);
  - key.csv       item code -> question, configuration (do NOT give to graders).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def render(resp: dict) -> str:
    spec = resp.get("report_spec") or {}
    out: list[str] = []
    for b in spec.get("blocks", []):
        t = b.get("type")
        if t == "headline":
            out.append("**" + b["sentence"]["text"] + "**")
        elif t == "figure":
            title = b.get("title", "")
            take = (b.get("takeaway") or {}).get("text", "")
            out.append(f"[Hình {b.get('figure_no', '')}] {title}" + (f" — {take}" if take else ""))
        elif t == "section":
            out.append("### " + b.get("title", ""))
            for s in b.get("sentences", []):
                out.append("- " + s["text"])
        elif t == "callout":
            txt = (b.get("sentence") or {}).get("text", "")
            if txt:
                out.append("> " + txt)
        else:
            sent = b.get("sentence")
            if sent:
                out.append("- " + sent["text"])
            for s in b.get("sentences", []) or []:
                out.append("- " + s["text"])
    return "\n".join(out).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="runs directories (one per source)")
    ap.add_argument("--questions", default="T01,T04,T06,T08,T09")
    ap.add_argument("--question-text", type=Path, required=True, help="JSONL with id and question")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261022)
    args = ap.parse_args()

    qtext = {}
    for line in args.question_text.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            qtext[d.get("id") or d.get("task_id")] = d.get("question") or d.get("question_text") or d.get("prompt") or d.get("text")

    runs: dict[tuple[str, str], dict] = {}
    for rd in args.runs:
        for f in Path(rd).glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("status") in ("completed", "accepted_with_limitations") and d.get("response"):
                runs[(d["task_id"], d["arm"])] = d

    arms = ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique", "template_only"]
    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    sheet, key = [], []
    for qn, q in enumerate(args.questions.split(","), 1):
        items = [(a, runs[(q, a)]) for a in arms if (q, a) in runs]
        rng.shuffle(items)
        sheet.append(f"## Câu {qn}\n\n**Câu hỏi:** {qtext.get(q, q)}\n")
        for k, (a, d) in enumerate(items):
            code = f"C{qn}-{chr(ord('a') + k)}"
            sheet.append(f"### Bản {code}\n\n{render(d['response'])}\n")
            key.append({"item": code, "question": q, "arm": a})
    (args.out / "sheet.md").write_text(
        "# Phiếu chấm mù\n\nVới mỗi bản (ví dụ C1-a), chấm 1–5 (1 = rất kém, 5 = rất tốt) ba tiêu chí: "
        "ĐÚNG (số liệu và nhận định khớp thực tế, không sai thứ hạng hay chiều), ĐỦ (trả lời đủ ý câu hỏi), "
        "DỄ ĐỌC (rõ ràng, mạch lạc). Không cần tra cứu bên ngoài. Điền vào `scores.csv`.\n\n" + "\n".join(sheet),
        encoding="utf-8",
    )
    with (args.out / "scores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["grader", "item", "dung", "du", "de_doc"])
        for g in ("N1", "N2", "N3"):
            for k in key:
                w.writerow([g, k["item"], "", "", ""])
    with (args.out / "key.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["item", "question", "arm"])
        w.writeheader()
        w.writerows(key)
    print(f"items: {len(key)}")


if __name__ == "__main__":
    main()
