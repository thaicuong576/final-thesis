"""Build an arm-blind human queue for analysis-report-v2 packets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


DIMENSIONS = ("correctness", "usefulness", "evidence", "limitation")
DIMENSION_PROMPTS = {
    "correctness": "Are the material claims factually correct for the stated scope, periods and Gold data?",
    "usefulness": "Does the report help an analyst decide what matters and what to investigate next?",
    "evidence": "Can the material claims be followed to the correct source, page and evidence record?",
    "limitation": "Does the report state missingness, scope, definition and uncertainty limits precisely enough?",
}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _question_map(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data.get("questions", [])}


def _blind_id(manifest_path: str, report: dict[str, Any]) -> str:
    stable = f"{manifest_path}|{report['run'].get('run_id')}".encode("utf-8")
    return "arv2-" + hashlib.sha256(stable).hexdigest()[:16]


def _evidence_catalog(report: dict[str, Any]) -> list[dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for row in report.get("matrix", []):
        for metric in row.get("metrics", []):
            for evidence in metric.get("evidence", []) or []:
                catalog.setdefault(evidence["evidence_id"], evidence)
    return list(catalog.values())


def _blind_report(report: dict[str, Any], question: dict[str, Any]) -> dict[str, Any]:
    # Keep all material content needed for review, while excluding arm/model,
    # run telemetry, manifest path and claim-origin diagnostics.
    return {
        "packet_version": "analysis-report-v2-blind-packet-v1",
        "question": {
            "prompt": question.get("prompt"),
            "type": question.get("type"),
        },
        "scope": report.get("scope"),
        "executive_summary": report.get("executive_summary"),
        "data_quality": {
            key: value
            for key, value in report.get("data_quality", {}).items()
            if key not in {"claim_origin", "claim_support_counts", "model_findings"}
        },
        "profiles": report.get("profiles"),
        "claims": [
            {
                key: value
                for key, value in claim.items()
                if key not in {"origin"}
            }
            for claim in report.get("claims", [])
        ],
        "missing_cells": report.get("missing_cells"),
        "limitations": report.get("limitations"),
        "evidence_catalog": _evidence_catalog(report),
    }


def build_queue(
    reports_root: Path,
    run_dir: Path,
    questions_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"refusing_to_overwrite_nonempty:{output_dir}")
    batch_summary_path = reports_root / "batch-summary.json"
    if not batch_summary_path.exists():
        raise FileNotFoundError(batch_summary_path)
    batch = json.loads(batch_summary_path.read_text(encoding="utf-8"))
    question_map = _question_map(questions_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    packets: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in batch.get("reports", []):
        if not item.get("quality_review_eligible", False):
            skipped.append(
                {
                    "manifest": item.get("manifest"),
                    "question_id": item.get("question_id"),
                    "workload_tier": item.get("workload_tier"),
                    "issuer_count": item.get("issuer_count"),
                    "arm": item.get("arm"),
                    "failure_status": item.get("failure_status"),
                    "failure_blockers": item.get("failure_blockers", []),
                }
            )
            continue
        manifest_path = Path(item["manifest"])
        report_path = Path(item["report_dir"]) / "analysis-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        question_id = str(report["run"].get("question_id"))
        question = question_map.get(question_id)
        if question is None:
            raise RuntimeError(f"question_not_found:{question_id}")
        blind_id = _blind_id(str(manifest_path), report)
        packet = {"blind_id": blind_id, "report": _blind_report(report, question)}
        packets.append(packet)
        workload = question.get("workload") or {}
        private_map[blind_id] = {
            "manifest_path": str(manifest_path),
            "report_path": str(report_path),
            "run_id": report["run"].get("run_id"),
            "arm": report["run"].get("arm"),
            "model_id": report["run"].get("model_id"),
            "question_id": question_id,
            "workload_tier": workload.get("tier"),
            "issuer_count": len(workload.get("issuers", [])),
            "issuers": workload.get("issuers", []),
            "call_count": report["run"].get("telemetry", {}).get("call_count"),
            "input_tokens": report["run"].get("telemetry", {}).get("input_tokens"),
            "output_tokens": report["run"].get("telemetry", {}).get("output_tokens"),
            "cost_estimate_usd": report["run"].get("telemetry", {}).get("cost_estimate_usd"),
            "wall_clock_latency_ms": report["run"].get("telemetry", {}).get("wall_clock_latency_ms"),
            "status": report["run"].get("status"),
        }
        for dimension in DIMENSIONS:
            rows.append(
                {
                    "row_number": len(rows) + 1,
                    "blind_id": blind_id,
                    "dimension": dimension,
                    "prompt": DIMENSION_PROMPTS[dimension],
                    "score": "",
                    "decision_basis": "",
                }
            )

    (output_dir / "blind-packets.jsonl").write_text(
        "".join(json.dumps(packet, ensure_ascii=False, sort_keys=True) + "\n" for packet in packets),
        encoding="utf-8",
    )
    (output_dir / "private-identity-map.json").write_text(
        json.dumps(private_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "operational-manifest-summary.json").write_text(
        json.dumps(batch.get("reports", []), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "human-review-queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["row_number", "blind_id", "dimension", "prompt", "score", "decision_basis"],
        )
        writer.writeheader()
        writer.writerows(rows)
    guide = f"""# Hướng dẫn chấm mù — analysis-report-v2

Gói này có **{len(packets)} report** và **{len(rows)} dòng chấm**: mỗi report cần chấm 4 chiều
`correctness`, `usefulness`, `evidence`, `limitation`. Có thêm {len(skipped)} manifest bị
provider fail/non-model; chúng không có report để chấm và vẫn được giữ trong
`operational-manifest-summary.json` để tính reliability.

## Quy tắc giữ mù

- Chỉ mở `blind-packets.jsonl` và `human-review-queue.csv`.
- Không mở `private-identity-map.json` trong lúc chấm. File đó chứa arm/model/run
  và chỉ được dùng sau khi review hoàn tất để unblind.
- Issuer, kỳ và số liệu vẫn hiện; đó là thông tin cần thiết để kiểm tra tính đúng.
- Không suy đoán arm từ độ dài, văn phong hoặc số claim.

## Cách chấm một packet

1. Tìm `blind_id` trong `human-review-queue.csv`.
2. Đọc cùng `blind_id` trong `blind-packets.jsonl`: question, scope, headline,
   profiles, claims, evidence catalog và limitations.
3. Kiểm tra claim quan trọng bằng Gold data/evidence được hiển thị trong packet.
4. Điền `score` từ 0 đến 4 và viết một hoặc hai câu vào `decision_basis` cho từng chiều.

Nếu dùng reviewer console, mở `research/evaluation-ui/review.html`, nạp hai file trên, chấm từng
packet rồi bấm **Tải CSV đã chấm**. Console chỉ đọc dữ liệu local và không gọi model.

## Thang điểm

| Chiều | 0 | 2 | 4 |
|---|---|---|---|
| Correctness | Sai nghiêm trọng hoặc bịa | Đúng một phần nhưng có lỗi/caveat trọng yếu | Đúng trong scope đã khai báo |
| Usefulness | Không giúp trả lời câu hỏi | Tóm tắt được nhưng “so what” yếu | Ưu tiên rõ điều đáng chú ý và việc cần theo dõi |
| Evidence | Không có/sai/misleading | Có tham chiếu nhưng chưa truy được đầy đủ | Claim truy được tới đúng source/page/evidence |
| Limitation | Che giấu hoặc nói sai giới hạn | Disclaimer chung chung | Nêu rõ missingness, scope, definition và uncertainty |

Điểm 1 và 3 dùng cho mức trung gian. Chấm report, không chấm độ dài hay số claim.

## Format bắt buộc

- `score`: số nguyên `0`, `1`, `2`, `3` hoặc `4`.
- `decision_basis`: không để trống khi đã có score; nêu lý do quan sát được.
- Không thay đổi `row_number`, `blind_id`, `dimension` hoặc `prompt`.

Sau khi lưu CSV, chạy:

```powershell
python scripts/validate_analysis_report_v2_human_queue.py `
  reports/analysis-report-v2-human-review-gold-v5-20260909 `
  --require-complete
```

Validator phải báo `valid=true`, `complete=true`, `filled_scores={len(rows)}`. Chỉ sau
đó mới chạy aggregator để unblind và tính quality/cost/latency/crossover.
"""
    (output_dir / "HUMAN-REVIEW-GUIDE-VI.md").write_text(guide, encoding="utf-8")
    summary = {
        "packet_count": len(packets),
        "row_count": len(rows),
        "dimensions": list(DIMENSIONS),
        "scale": "0-4",
        "arm_identity_stored_separately": True,
        "status": "pending_human_review",
        "skipped_noneligible_manifest_count": len(skipped),
    }
    (output_dir / "build-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports_root", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("questions", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    summary = build_queue(args.reports_root, args.run_dir, args.questions, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
