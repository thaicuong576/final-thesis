"""Summarize a JSONL PDF-quality audit for the target annual-report corpus."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def ticker_from_path(path: str) -> str:
    parts = Path(path).parts
    try:
        index = parts.index("annual_reports_2023_2025")
        return parts[index + 1]
    except (ValueError, IndexError):
        return Path(path).stem.split("_")[0]


def year_from_path(path: str) -> str:
    stem = Path(path).stem
    for token in ("23", "24", "25"):
        if f"_{token}CN_" in stem:
            return f"20{token}"
    return "unknown"


def quality_label(record: dict) -> str:
    pages = int(record.get("page_count") or 0)
    text_pages = int(record.get("text_layer_pages") or 0)
    if pages and text_pages == pages:
        return "text_layer"
    if text_pages:
        return "mixed_text_layer"
    return "scan_or_no_text_layer"


def render(records: list[dict], input_path: Path) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[ticker_from_path(record["path"])].append(record)

    target_years = {"2023", "2024", "2025"}
    target_tickers = sorted(grouped)
    target_cells = len(target_tickers) * len(target_years)
    observed_cells = sum(
        1
        for ticker_records in grouped.values()
        for year in {year_from_path(item["path"]) for item in ticker_records}
        if year != "unknown"
    )
    fully_covered = sum(
        1
        for ticker_records in grouped.values()
        if target_years <= {year_from_path(item["path"]) for item in ticker_records}
    )

    quality_counts: dict[str, int] = defaultdict(int)
    for record in records:
        quality_counts[quality_label(record)] += 1

    lines = [
        "# Target annual-report inventory v1",
        "",
        "Status: `source_available_not_gold`",
        "",
        "This is a read-only inventory of the downloaded annual-report PDFs for the five-bank expansion scope. It proves document availability and parser quality only; it does not accept any metric value into Gold.",
        "",
        "## Coverage",
        "",
        f"- Audited documents: **{len(records)}**",
        f"- Target issuers: **{len(target_tickers)}** ({', '.join(target_tickers)})",
        f"- Target years: **2023–2025**",
        f"- Issuer-year files: **{observed_cells}/{target_cells}**",
        f"- Issuers with all three years: **{fully_covered}/{len(target_tickers)}**",
        f"- Parser quality: **{', '.join(f'{key}={value}' for key, value in sorted(quality_counts.items()))}**",
        "",
        "## Issuer summary",
        "",
        "| Issuer | Files | Years | Pages | Text-layer pages | Quality mix |",
        "|---|---:|---|---:|---:|---|",
    ]
    for ticker in target_tickers:
        ticker_records = sorted(grouped[ticker], key=lambda item: year_from_path(item["path"]))
        years = sorted({year_from_path(item["path"]) for item in ticker_records})
        pages = sum(int(item.get("page_count") or 0) for item in ticker_records)
        text_pages = sum(int(item.get("text_layer_pages") or 0) for item in ticker_records)
        mix: dict[str, int] = defaultdict(int)
        for item in ticker_records:
            mix[quality_label(item)] += 1
        mix_text = ", ".join(f"{key}={value}" for key, value in sorted(mix.items()))
        lines.append(
            f"| {ticker} | {len(ticker_records)} | {', '.join(years)} | {pages} | {text_pages} | {mix_text} |"
        )

    lines.extend(
        [
            "",
            "## Document detail",
            "",
            "| Issuer | Year | Pages | Text-layer pages | Quality | Extraction errors | Path |",
            "|---|---:|---:|---:|---|---:|---|",
        ]
    )
    for record in sorted(records, key=lambda item: (ticker_from_path(item["path"]), year_from_path(item["path"]))):
        errors = len(record.get("extraction_errors") or [])
        path = record["path"].replace("\\", "/")
        lines.append(
            f"| {ticker_from_path(record['path'])} | {year_from_path(record['path'])} | "
            f"{record.get('page_count', 0)} | {record.get('text_layer_pages', 0)} | "
            f"{quality_label(record)} | {errors} | `{path}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation and next gate",
            "",
            "- The corpus is large enough to support a document-reading workload: five issuers, three years, and fifteen PDFs.",
            "- Annual reports are not interchangeable with quarterly observations. They cannot be copied into 2024 Q1–Q3 cells or used as a quarterly substitute.",
            "- A scan or mixed text layer requires page-level visual/OCR extraction before an evidence snippet can be attached.",
            "- To promote an expanded metric cell, the pipeline still requires the frozen definition, unit, period basis, consolidation basis, source locator, evidence snippet, and the independent review gate.",
            "- Until those gates pass, these files belong to the source/evidence layer and remain outside Gold and outside benchmark claims.",
            "",
            "## Input",
            "",
            f"- Audit JSONL: `{input_path.as_posix()}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    records = read_records(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(records, args.input), encoding="utf-8")
    print(json.dumps({"documents": len(records), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
