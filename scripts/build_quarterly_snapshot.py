"""Build a multi-period operational bank snapshot from transcribed filing inputs (D-079).

Input: one CSV of primary inputs (million VND converted to billion VND upstream), one row per
(entity, metric, period) with the filing URL, its SHA-256 and an exact page locator:

    entity_id,metric_id,period_id,value,unit,period_basis,source_locator,source_url,source_sha256

Primary metrics recognised (all billion_vnd):
    point_in_time: bank.input.npl_group_{3,4,5}_balance, bank.input.gross_customer_loans,
                   bank.input.loan_loss_provisions, bank.input.total_assets,
                   bank.input.total_equity, bank.input.non_controlling_interests
    ytd:           bank.input.profit_after_tax, bank.input.parent_attributable_profit

Derived (recomputed here with versioned formulas; receipts are written at materialisation):
    NPL group 3-5 balance, parent-attributable equity, NPL ratio, LLR coverage, and TTM ROA/ROE
    (interim formula: YTD(t) - YTD(t-4) + FY(y-1), over the average of the year-opening and
    closing balance). A ratio is produced only when every input exists; otherwise it is absent.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thesis_data.dataset_contract import (  # noqa: E402
    AnalyticalLevel,
    CanonicalObservation,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetSource,
    ObservationEvidenceRef,
    ObservationReview,
    PeerUniverse,
    canonical_observation_id,
)
from thesis_data.evidence_contract import DatasetDocument  # noqa: E402
from thesis_data.metrics import (  # noqa: E402
    calculate_llr,
    calculate_npl,
    calculate_npl_g35_balance,
    calculate_parent_attributable_equity,
    operational_derived_formula,
)
from thesis_data.onboarding_contract import (  # noqa: E402
    DatasetSnapshotStatus,
    OnboardingValidationReport,
    OnboardingValidationStatus,
    RawDatasetDescriptor,
    build_snapshot_metadata,
)
from thesis_data.onboarding_validation import CanonicalDatasetCandidate  # noqa: E402
from thesis_data.schema import QualityStatus  # noqa: E402
from thesis_data.user_upload import materialize_user_upload_snapshot  # noqa: E402

DATASET_ID = "bank-quarterly-top10-operational-v1"
PEER_UNIVERSE_ID = "sector:bank"
PROTECTED_NAMES = ("gold", "finance_master", "analysis_runs")
POINT = {
    "bank.input.npl_group_3_balance", "bank.input.npl_group_4_balance", "bank.input.npl_group_5_balance",
    "bank.input.gross_customer_loans", "bank.input.loan_loss_provisions", "bank.input.total_assets",
    "bank.input.total_equity", "bank.input.non_controlling_interests",
}
YTD = {"bank.input.profit_after_tax", "bank.input.parent_attributable_profit"}
RATIOS = ("bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe")
LABELS = {
    "bank.npl_g35": "Tỷ lệ nợ xấu (nhóm 3–5)",
    "bank.llr_coverage": "Tỷ lệ bao phủ nợ xấu",
    "bank.roa": "ROA",
    "bank.roe": "ROE",
}
VERIFIED_QUARTERLY_LOSSES = {
    # STB incurred an audited net loss of (2,752.462) billion VND in Q4 2025 due to
    # 9,232.152 billion VND in credit provisions in Q4 alone, reducing 9-month YTD profit
    # from 8,691.573 billion VND to full-year 5,939.111 billion VND (B03/TCTD-HN, B03a/TCTD).
    ("STB", "2025_Q4"),
}


class BuildError(RuntimeError):
    pass


def _prev(period: str, years: int = 1, quarter: int | None = None) -> str:
    y, q = period.split("_Q")
    return f"{int(y) - years}_Q{quarter or q}"


def build(inputs_csv: Path, out: Path, *, names: dict[str, str] | None = None, dataset_id: str = DATASET_ID,
          ratio_periods: set[str] | None = None) -> dict:
    out = out.resolve()
    if any(p in out.name.lower() for p in PROTECTED_NAMES):
        raise BuildError(f"refusing to write a protected store: {out.name}")
    raw = inputs_csv.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise BuildError("no input rows")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    raw_hash = hashlib.sha256(raw).hexdigest()
    descriptor = RawDatasetDescriptor(
        raw_dataset_id=f"{dataset_id}-inputs", source_type="filing", original_name=inputs_csv.name,
        content_hash=raw_hash, ingested_at=now,
    )
    metadata = build_snapshot_metadata(
        dataset_id, descriptor, mapping_version="quarterly-bank-inputs-v1",
        validation_version="quarterly-bank-arithmetic-v1", status=DatasetSnapshotStatus.CANDIDATE, created_at=now,
    )
    snap = metadata.dataset_snapshot_id

    sources: dict[tuple[str, str], DatasetSource] = {}
    documents: dict[str, DatasetDocument] = {}
    cells: dict[tuple[str, str, str], dict] = {}
    for i, r in enumerate(rows, start=2):
        metric, entity, period = r["metric_id"].strip(), r["entity_id"].strip().upper(), r["period_id"].strip()
        if metric not in POINT | YTD:
            raise BuildError(f"row {i}: unsupported metric {metric}")
        basis = "point_in_time" if metric in POINT else "ytd"
        if r.get("period_basis", basis).strip() != basis or r.get("unit", "billion_vnd").strip() != "billion_vnd":
            raise BuildError(f"row {i}: {metric} must be billion_vnd/{basis}")
        if "page" not in r["source_locator"]:
            raise BuildError(f"row {i}: source_locator needs a page")
        key = (entity, metric, period)
        if key in cells:
            raise BuildError(f"row {i}: duplicate cell {key}")
        skey = (r["source_url"].strip(), r["source_sha256"].strip().lower())
        if skey not in sources:
            ref = f"source:{entity.lower()}:{hashlib.sha256('|'.join(skey).encode()).hexdigest()[:12]}"
            sources[skey] = DatasetSource(
                source_ref=ref, source_type="filing", source_tier="primary", source_url=skey[0],
                publisher=f"{entity} (công bố thông tin)", retrieved_at=now_iso, content_hash=skey[1] or raw_hash,
                validation_status=QualityStatus.VALID, notes="Báo cáo tài chính hợp nhất (bản công bố)",
            )
            documents[ref] = DatasetDocument(
                document_id=f"document:{ref}", dataset_id=dataset_id, dataset_snapshot_id=snap, source_ref=ref,
                document_type="consolidated_financial_statements", title=f"{entity} BCTC hợp nhất",
                publisher=f"{entity}", content_hash=skey[1] or raw_hash, metadata={},
            )
        cells[key] = {"value": Decimal(r["value"]), "basis": basis, "loc": r["source_locator"].strip(),
                      "source": sources[skey]}

    entities = sorted({k[0] for k in cells})
    periods = sorted({k[2] for k in cells})

    # Validate intra-year YTD profit monotonicity:
    # Cumulative year-to-date profit within a single calendar year must be non-decreasing,
    # unless an audited quarterly net loss is verified and documented with primary filing provenance.
    for entity in entities:
        for metric in sorted(YTD):
            by_year: dict[str, list[str]] = {}
            for (e, m, p) in cells:
                if e == entity and m == metric:
                    y = p.split("_Q")[0]
                    by_year.setdefault(y, []).append(p)
            for y, pers in by_year.items():
                pers.sort()
                for idx in range(len(pers) - 1):
                    p_prev, p_curr = pers[idx], pers[idx + 1]
                    v_prev = cells[(entity, metric, p_prev)]["value"]
                    v_curr = cells[(entity, metric, p_curr)]["value"]
                    if v_curr < v_prev:
                        if (entity, p_curr) in VERIFIED_QUARTERLY_LOSSES:
                            continue
                        raise BuildError(
                            f"non-monotonic YTD profit: {entity} {metric} decreased from {v_prev} in {p_prev} to {v_curr} in {p_curr}"
                        )

    observations: list[CanonicalObservation] = []
    evidence: list[DatasetEvidence] = []
    ids: dict[tuple[str, str, str], str] = {}

    def oid(entity, metric, period):
        return ids.setdefault((entity, metric, period), canonical_observation_id(snap, entity, period, metric))

    def add_evidence(entity, metric, period, source_ref, loc, value):
        evidence.append(DatasetEvidence(
            evidence_id=f"evidence:{oid(entity, metric, period)}", source_ref=source_ref,
            document_id=f"document:{source_ref}", entity_id=entity, period_id=period, metric_id=metric,
            locator=loc, quote=f"{entity} {metric} {period} = {value}",
        ))

    for (entity, metric, period), c in cells.items():
        observations.append(CanonicalObservation(
            observation_id=oid(entity, metric, period), dataset_id=dataset_id, dataset_snapshot_id=snap,
            entity_id=entity, period_id=period, metric_id=metric, value=float(c["value"]), unit="billion_vnd",
            source_ref=c["source"].source_ref, source_locator=c["loc"], period_basis=c["basis"],
            reporting_scope="consolidated", validation_status=QualityStatus.VALID,
            review=ObservationReview(
                reviewer_id="claude-orchestrator-filing-transcription", reviewed_at=now_iso,
                decision="matched_reported_value",
                primary_evidence=(ObservationEvidenceRef(source_ref=c["source"].source_ref, locator=c["loc"]),),
                resolution_note="Transcribed from the filing; accepted after arithmetic cross-checks.",
            ),
            metadata={"provenance": "filing_transcription"},
        ))
        add_evidence(entity, metric, period, c["source"].source_ref, c["loc"], c["value"])

    def derive(entity, metric, period, value, version, inputs, unit, basis):
        first = cells.get(inputs[0]) or derived_cells[inputs[0]]
        src, loc = first["source"], first["loc"]
        observations.append(CanonicalObservation(
            observation_id=oid(entity, metric, period), dataset_id=dataset_id, dataset_snapshot_id=snap,
            entity_id=entity, period_id=period, metric_id=metric, value=float(value), unit=unit,
            source_ref=None, source_locator=loc, period_basis=basis, reporting_scope="consolidated",
            validation_status=QualityStatus.VALID, derivation_method=version,
            input_observation_ids=tuple(oid(*k) for k in inputs),
            review=ObservationReview(
                reviewer_id="claude-orchestrator-filing-transcription", reviewed_at=now_iso,
                decision="reproduced_derived_value",
                primary_evidence=(ObservationEvidenceRef(source_ref=src.source_ref, locator=loc),),
                resolution_note=f"Recomputed from accepted inputs with {version}.",
            ),
            metadata={"provenance": "filing_transcription"},
        ))
        add_evidence(entity, metric, period, src.source_ref, loc, value)
        derived_cells[(entity, metric, period)] = {"value": Decimal(str(value)), "source": src, "loc": loc}

    derived_cells: dict[tuple[str, str, str], dict] = {}
    v = lambda e, m, p: (cells.get((e, m, p)) or derived_cells.get((e, m, p)) or {}).get("value")  # noqa: E731
    for e in entities:
        for p in periods:
            g = [v(e, f"bank.input.npl_group_{n}_balance", p) for n in (3, 4, 5)]
            if all(x is not None for x in g):
                r = calculate_npl_g35_balance(*g)
                derive(e, "bank.input.npl_g35_balance", p, r.value, r.formula_version,
                       tuple((e, f"bank.input.npl_group_{n}_balance", p) for n in (3, 4, 5)), "billion_vnd", "point_in_time")
            eq, nci = v(e, "bank.input.total_equity", p), v(e, "bank.input.non_controlling_interests", p)
            if eq is not None and nci is not None:
                r = calculate_parent_attributable_equity(eq, nci)
                derive(e, "bank.input.parent_attributable_equity", p, r.value, r.formula_version,
                       ((e, "bank.input.total_equity", p), (e, "bank.input.non_controlling_interests", p)),
                       "billion_vnd", "point_in_time")

    computed: dict[str, dict[str, dict[str, float]]] = {}
    for e in entities:
        for p in periods:
            if ratio_periods and p not in ratio_periods:
                continue
            g = [v(e, f"bank.input.npl_group_{n}_balance", p) for n in (3, 4, 5)]
            gross = v(e, "bank.input.gross_customer_loans", p)
            if all(x is not None for x in g) and gross:
                r = calculate_npl(*g, gross)
                derive(e, "bank.npl_g35", p, r.value, r.formula_version,
                       tuple((e, f"bank.input.npl_group_{n}_balance", p) for n in (3, 4, 5)) + ((e, "bank.input.gross_customer_loans", p),),
                       "percent", "point_in_time")
                computed.setdefault(e, {}).setdefault(p, {})["bank.npl_g35"] = float(r.value)
            prov, nplb = v(e, "bank.input.loan_loss_provisions", p), v(e, "bank.input.npl_g35_balance", p)
            if prov is not None and nplb:
                r = calculate_llr(prov, nplb)
                derive(e, "bank.llr_coverage", p, r.value, r.formula_version,
                       ((e, "bank.input.loan_loss_provisions", p), (e, "bank.input.npl_g35_balance", p)),
                       "percent", "point_in_time")
                computed.setdefault(e, {}).setdefault(p, {})["bank.llr_coverage"] = float(r.value)
            same, fy = _prev(p), _prev(p, quarter=4)
            for metric, flow, stock, version in (
                ("bank.roa", "bank.input.profit_after_tax", "bank.input.total_assets", "roa-ttm-interim-v1"),
                ("bank.roe", "bank.input.parent_attributable_profit", "bank.input.parent_attributable_equity", "roe-ttm-interim-v1"),
            ):
                if p.endswith("_Q4"):
                    version = version.replace("interim", "annual-ytd")
                    keys = ((e, flow, p), (e, stock, p), (e, stock, fy))
                else:
                    keys = ((e, flow, p), (e, flow, same), (e, flow, fy), (e, stock, p), (e, stock, fy))
                vals = [v(*k) for k in keys]
                if any(x is None for x in vals):
                    continue
                r = operational_derived_formula(metric, version).calculate(tuple(vals))
                if r.value is None:
                    continue
                derive(e, metric, p, r.value, version, keys, "percent", "ttm")
                computed.setdefault(e, {}).setdefault(p, {})[metric] = float(r.value)

    metric_ids = sorted({o.metric_id for o in observations})
    candidate = CanonicalDatasetCandidate(
        metadata=metadata,
        source=next(iter(sources.values())),
        additional_sources=tuple(list(sources.values())[1:]),
        entities=tuple(
            DatasetEntity(entity_id=e, entity_type=DatasetEntityType.COMPANY, display_name=(names or {}).get(e, e),
                          attributes={"sector": "bank", "provenance": "filing_transcription"})
            for e in entities
        ),
        periods=tuple(DatasetPeriod(period_id=p, label=p) for p in periods),
        metrics=tuple(
            DatasetMetric(metric_id=m, display_name=LABELS.get(m, m.removeprefix("bank.input.").replace("_", " ")),
                          analytical_level=AnalyticalLevel.COMPANY,
                          default_unit="percent" if m in RATIOS else "billion_vnd")
            for m in metric_ids
        ),
        observations=tuple(observations),
        documents=tuple(documents.values()),
        evidence=tuple(evidence),
        peer_universes=(PeerUniverse(peer_universe_id=PEER_UNIVERSE_ID,
                                     display_name=f"Nhóm {len(entities)} ngân hàng niêm yết", entity_ids=tuple(entities)),),
    )
    report = OnboardingValidationReport(
        dataset_id=dataset_id, candidate_snapshot_id=snap, status=OnboardingValidationStatus.VALID,
        row_count=len(rows), candidate_observation_count=len(observations), missing_observation_count=0,
        rejected_row_count=0,
    )
    tmp = out.with_suffix(".building.sqlite")
    if tmp.exists():
        tmp.unlink()
    materialize_user_upload_snapshot(
        SimpleNamespace(status="accepted", candidate=candidate, raw_descriptor=descriptor, report=report), tmp)
    conn = sqlite3.connect(tmp)
    try:
        conn.execute("INSERT INTO peer_universes VALUES (?, ?)", (PEER_UNIVERSE_ID, f"Nhóm {len(entities)} ngân hàng niêm yết"))
        conn.executemany("INSERT INTO peer_universe_members VALUES (?, ?)", [(PEER_UNIVERSE_ID, e) for e in entities])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BuildError("integrity check failed")
    finally:
        conn.close()
    if out.exists():
        out.unlink()
    tmp.replace(out)
    manifest = {
        "dataset_id": dataset_id, "dataset_snapshot_id": snap, "file": out.name,
        "file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "inputs_sha256": raw_hash,
        "banks": entities, "periods": periods, "ratios": computed,
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the multi-period operational bank snapshot.")
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--names", type=Path)
    ap.add_argument("--first-ratio-period", default="2024_Q1")
    args = ap.parse_args()
    names = json.loads(args.names.read_text(encoding="utf-8")) if args.names else None
    rows = list(csv.DictReader(io.StringIO(args.inputs.read_text(encoding="utf-8-sig"))))
    ratio_periods = {r["period_id"] for r in rows if r["period_id"] >= args.first_ratio_period}
    try:
        m = build(args.inputs, args.out, names=names, ratio_periods=ratio_periods)
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    print(m["dataset_snapshot_id"], m["file_sha256"])
    for e, per in m["ratios"].items():
        for p, r in sorted(per.items()):
            print(e, p, {k.split(".")[-1]: round(x, 2) for k, x in r.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
