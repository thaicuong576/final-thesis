"""Fetch a bounded, hash-recorded set of official source documents.

Downloads are append-only. Existing files and manifests are never overwritten;
the command must be pointed at a new output directory/manifest for a new run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def _download(url: str, destination: Path) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": "final-thesis-source-audit/1.0"})
    with urlopen(request, timeout=60) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read()
    if not body:
        raise ValueError(f"empty response for {url}")
    digest = hashlib.sha256(body).hexdigest()
    destination.write_bytes(body)
    return len(body), digest, content_type


def fetch(plan_path: Path, output_dir: Path, manifest_path: Path) -> list[dict]:
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {manifest_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or not plan:
        raise ValueError("download plan must be a non-empty list")

    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for item in plan:
        required = {"source_id", "ticker", "period", "url", "filename", "publisher"}
        missing = required - set(item)
        if missing:
            raise ValueError(f"plan item missing fields: {sorted(missing)}")
        destination = output_dir / item["filename"]
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite source file: {destination}")
        size, digest, content_type = _download(item["url"], destination)
        if item["filename"].lower().endswith(".pdf") and not destination.read_bytes()[:5] == b"%PDF-":
            raise ValueError(f"download is not a PDF: {item['url']}")
        records.append(
            {
                **item,
                "local_path": str(destination),
                "bytes": size,
                "content_type": content_type,
                "content_hash": f"sha256:{digest}",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "quality_status": "retrieved_pending_validation",
                "license_note": "public issuer disclosure; verify permitted thesis reuse",
            }
        )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    records = fetch(args.plan, args.output_dir, args.manifest)
    print(f"downloaded_sources={len(records)} bytes={sum(item['bytes'] for item in records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
