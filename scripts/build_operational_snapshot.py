"""Build one operational canonical snapshot from several bank CSVs (D-077).

Each CSV uses the new-bank upload format and is checked by the same validator as the web upload
(structure, page locators, units, recomputed NPL / LLR coverage / ROA / ROE with calculation
receipts). The accepted per-bank candidates are merged into a single snapshot whose peer universe
contains every bank, so medians and ranks are computed over the whole group. The Gold v5
benchmark is never read or written.

    python scripts/build_operational_snapshot.py \
        --inputs data/onboarding/top10-2025 \
        --evidence-root data/raw/official/bank-2025-top10-v1 \
        --out data/processed/bank-2025-top10-operational-v1.sqlite
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thesis_data.dataset_contract import PeerUniverse  # noqa: E402
from thesis_data.user_upload import (  # noqa: E402
    materialize_user_upload_snapshot,
    validate_and_parse_upload_csv,
)

DATASET_ID = "bank-2025-top10-operational-v1"
PEER_UNIVERSE_ID = "sector:bank"
PROTECTED_NAMES = ("gold", "finance_master", "analysis_runs")


class BuildError(RuntimeError):
    pass


def _display_names(inputs: Path) -> dict[str, str]:
    path = inputs / "banks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build(inputs: Path, out: Path, evidence_root: Path | None = None, *, dataset_id: str = DATASET_ID) -> dict:
    out = out.resolve()
    if any(name in out.name.lower() for name in PROTECTED_NAMES):
        raise BuildError(f"refusing to write a protected store: {out.name}")
    csvs = sorted(inputs.glob("*.csv"))
    if not csvs:
        raise BuildError(f"no CSV inputs in {inputs}")
    names = _display_names(inputs)

    results = []
    for path in csvs:
        ticker = path.name.split("-")[0].upper()
        content = path.read_bytes()
        result = validate_and_parse_upload_csv(
            content,
            upload_id=f"{dataset_id}-{ticker.lower()}",
            form_entity_id=ticker,
            form_display_name=names.get(ticker),
        )
        if result.status != "accepted" or result.candidate is None:
            issues = "; ".join(f"row {i.row} {i.field}: {i.message_vi}" for i in result.row_issues)
            raise BuildError(f"{path.name} rejected: {issues or 'no accepted candidate'}")
        if evidence_root is not None:
            pdfs = list(evidence_root.glob(f"{ticker}_*.pdf"))
            declared = {o.get("source_sha256", "").upper() for o in _rows(content)}
            actual = {hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in pdfs}
            if not pdfs or not declared & actual:
                raise BuildError(f"{ticker}: declared source_sha256 does not match any evidence PDF")
        results.append((ticker, result))

    base = results[0][1].candidate
    snapshot_id = f"{dataset_id}-{hashlib.sha256(b''.join(p.read_bytes() for p in csvs)).hexdigest()[:16]}"
    metadata = base.metadata.model_copy(
        update={
            "dataset_id": dataset_id,
            "dataset_snapshot_id": snapshot_id,
            "created_at": datetime.now(timezone.utc),
        }
    )

    def rebind(item):
        return item.model_copy(update={"dataset_id": dataset_id, "dataset_snapshot_id": snapshot_id})

    entities, periods, metrics, observations, sources, documents, evidence = {}, {}, {}, [], [], [], []
    for _, result in results:
        cand = result.candidate
        for e in cand.entities:
            # These banks are transcribed from audited filings for the operational peer group,
            # not ad-hoc user uploads, so the upload-only restrictions must not apply.
            attrs = {k: v for k, v in (e.attributes or {}).items() if k != "user_supplied"}
            attrs["provenance"] = "audited_filing_transcription"
            entities[e.entity_id] = e.model_copy(update={"attributes": attrs})
        for p in cand.periods:
            periods[p.period_id] = p
        for m in cand.metrics:
            metrics[m.metric_id] = m
        observations.extend(rebind(o) for o in cand.observations)
        sources.extend(cand.all_sources)
        documents.extend(rebind(d) for d in cand.documents)
        evidence.extend(cand.evidence)

    merged = dataclasses.replace(
        base,
        metadata=metadata,
        source=sources[0],
        additional_sources=tuple(sources[1:]),
        entities=tuple(entities.values()),
        periods=tuple(sorted(periods.values(), key=lambda p: p.period_id)),
        metrics=tuple(metrics.values()),
        observations=tuple(observations),
        documents=tuple(documents),
        evidence=tuple(evidence),
        peer_universes=(
            PeerUniverse(
                peer_universe_id=PEER_UNIVERSE_ID,
                display_name=f"Nhóm {len(entities)} ngân hàng niêm yết",
                entity_ids=tuple(sorted(entities)),
            ),
        ),
    )
    merged_result = dataclasses.replace(results[0][1], candidate=merged)

    tmp = out.with_suffix(".building.sqlite")
    if tmp.exists():
        tmp.unlink()
    materialize_user_upload_snapshot(merged_result, tmp)
    conn = sqlite3.connect(tmp)
    try:
        for universe in merged.peer_universes:
            conn.execute("INSERT INTO peer_universes VALUES (?, ?)", (universe.peer_universe_id, universe.display_name))
            conn.executemany(
                "INSERT INTO peer_universe_members VALUES (?, ?)",
                [(universe.peer_universe_id, e) for e in universe.entity_ids],
            )
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BuildError("integrity check failed")
    finally:
        conn.close()
    if out.exists():
        out.unlink()
    tmp.replace(out)

    table = {
        ticker: {m.metric_id: round(float(m.computed_value), 4) for m in result.metrics}
        for ticker, result in results
    }
    manifest = {
        "dataset_id": dataset_id,
        "dataset_snapshot_id": snapshot_id,
        "file": out.name,
        "file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "banks": sorted(table),
        "metrics": table,
        "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in csvs},
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _rows(content: bytes) -> list[dict]:
    import csv
    import io

    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--evidence-root", type=Path)
    ap.add_argument("--dataset-id", default=DATASET_ID)
    args = ap.parse_args()
    try:
        manifest = build(args.inputs, args.out, args.evidence_root, dataset_id=args.dataset_id)
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"{manifest['dataset_snapshot_id']}  {manifest['file_sha256']}")
    for bank, m in manifest["metrics"].items():
        print(bank, m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
