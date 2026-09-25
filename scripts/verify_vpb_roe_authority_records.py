#!/usr/bin/env python3
"""Verify portable VPB ROE hashes and the read-only Gold v5 gate."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_REL = "reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json"
ATTESTATION_REL = "reports/data-foundation/vpb-roe-parent-equity-independent-review-attestation-20260925.json"

def fail(message: str) -> None:
    raise SystemExit(f"VPB_AUTHORITY_VERIFY: FAIL: {message}")

def canonical_bytes(raw: bytes) -> bytes:
    return raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")

def canonical_sha256(raw: bytes) -> str:
    return hashlib.sha256(canonical_bytes(raw)).hexdigest().upper()

def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()

def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected JSON object: {path}")
    return value

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=ROOT,
                        help="root for ignored evidence; defaults to this repository and fails closed if absent")
    return parser.parse_args()

def git_blob(rev: str, rel: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{Path(rel).as_posix()}"], cwd=ROOT,
                          check=True, capture_output=True).stdout

def require_markers(rel: str, markers: tuple[str, ...]) -> None:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            fail(f"policy marker missing from {rel}: {marker}")

def verify(evidence_root: Path) -> dict:
    evidence_root = evidence_root.resolve()
    authority = read_json(ROOT / AUTHORITY_REL)
    modes = authority["hashing_convention"]
    if modes["tracked_text_sha256"] != "canonical_lf_utf8_sha256" or modes["immutable_evidence_sha256"] != "raw_file_bytes_sha256":
        fail("hashing convention is missing or inconsistent")
    if authority.get("status") != "independent_review_accepted":
        fail("authority is not independently accepted")
    if authority.get("eligibility") != "eligible_for_five_issuer_comparative_roe_scope_on_gold_v5":
        fail("scoped comparison eligibility is not open")

    expected_policy_refs = [
        "docs/DECISIONS.md#D-063",
        "docs/DECISIONS.md#D-072",
        "docs/DATA-CONTRACT.md#Hash modes for repository evidence manifests",
        "AGENTS.md#Operating principles 2",
    ]
    if authority.get("policy_refs") != expected_policy_refs:
        fail("authority policy references changed")
    require_markers(
        "docs/DECISIONS.md",
        (
            "## D-063:",
            "parent_attributable_equity",
            "gate is open only because attestation",
            "## D-072:",
            "eligible comparative gate result alone",
            "five-issuer comparison gate is open",
        ),
    )
    require_markers(
        "docs/DATA-CONTRACT.md",
        (
            "## Hash modes for repository evidence manifests",
            "canonical_lf_utf8_sha256",
            "raw_file_bytes_sha256",
            "explicit `--evidence-root`",
        ),
    )
    require_markers(
        "AGENTS.md",
        (
            "canonical_lf_utf8_sha256",
            "raw_file_bytes_sha256",
            "explicit `--evidence-root`",
        ),
    )

    controls = {}
    forbidden_living_controls = {
        "AGENTS.md",
        "docs/DATA-CONTRACT.md",
        "docs/DECISIONS.md",
        ".agent/memory/lessons-learned.md",
        "scripts/verify_vpb_roe_authority_records.py",
    }
    control_refs = {item["artifact_ref"] for item in authority["control_artifacts"]}
    if control_refs & forbidden_living_controls:
        fail(f"authority byte-pins living repository controls: {sorted(control_refs & forbidden_living_controls)}")
    for item in authority["control_artifacts"]:
        rel = item["artifact_ref"]
        if item.get("hash_mode") != "canonical_lf_utf8_sha256":
            fail(f"wrong control hash mode: {rel}")
        raw = (ROOT / rel).read_bytes()
        digest = canonical_sha256(raw)
        if digest != item["sha256"]:
            fail(f"control hash mismatch: {rel}")
        normalized = canonical_bytes(raw)
        for variant in (normalized, normalized.replace(b"\n", b"\r\n")):
            if canonical_sha256(variant) != digest:
                fail(f"LF/CRLF portability mismatch: {rel}")
        if canonical_sha256(git_blob("HEAD", rel)) != digest:
            fail(f"Git blob/control hash mismatch: {rel}")
        controls[rel] = digest

    raw_artifacts = {}
    for group in ("source_artifacts", "review_artifacts", "snapshot_artifacts"):
        for item in authority[group]:
            rel = item["artifact_ref"]
            if item.get("hash_mode") != "raw_file_bytes_sha256":
                fail(f"wrong evidence hash mode: {rel}")
            path = evidence_root / rel
            if not path.is_file():
                fail(f"missing ignored evidence {rel}; pass --evidence-root explicitly")
            digest = raw_sha256(path.read_bytes())
            if digest != item["sha256"]:
                fail(f"raw evidence hash mismatch: {rel}")
            raw_artifacts[rel] = digest
    gate = authority["comparative_definition_gate_rerun"]
    if gate.get("gate_manifest_hash_mode") != "raw_file_bytes_sha256":
        fail("gate manifest hash mode is missing")
    gate_rel = gate["gate_manifest_ref"]
    gate_path = evidence_root / gate_rel
    if not gate_path.is_file():
        fail(f"missing gate manifest {gate_rel}; pass --evidence-root explicitly")
    gate_digest = raw_sha256(gate_path.read_bytes())
    if gate_digest != gate["gate_manifest_sha256"]:
        fail("gate manifest raw-byte hash mismatch")
    raw_artifacts[gate_rel] = gate_digest

    attestation = read_json(ROOT / ATTESTATION_REL)
    if (attestation["reviewer_task_path"], attestation["reviewed_head_sha"], attestation["verdict"]) != (
        "/root/vpb_d072_reviewer_luna", "2b292ddf21bd6be8a550f81fb518fca5dc419efb", "ACCEPT"):
        fail("reviewer task, exact head or verdict mismatch")
    if attestation["source_artifact_hashes_raw_sha256"] != dict(sorted(raw_artifacts.items())):
        fail("attestation source hashes mismatch")
    for rel, digest in attestation["reviewed_control_hashes_canonical_lf_utf8_sha256"].items():
        if canonical_sha256(git_blob(attestation["reviewed_head_sha"], rel)) != digest:
            fail(f"reviewed-head control hash mismatch: {rel}")
    for rel, digest in attestation["record_update_control_hashes_canonical_lf_utf8_sha256"].items():
        if controls.get(rel) != digest:
            fail(f"record-update control hash mismatch: {rel}")
    attestation_control = next((i for i in authority["control_artifacts"] if i["artifact_ref"] == ATTESTATION_REL), None)
    authority_review = authority["independent_review_attestation"]
    if not attestation_control or authority_review["sha256"] != attestation_control["sha256"] or authority_review["hash_mode"] != "canonical_lf_utf8_sha256":
        fail("authority does not bind the canonical attestation hash")
    if (authority_review["verdict"], authority_review["reviewed_head_sha"]) != ("ACCEPT", attestation["reviewed_head_sha"]):
        fail("authority acceptance does not match attestation")

    recalculation = attestation["reviewer_recalculation_confirmation"]
    with localcontext() as context:
        context.prec = 50
        profit = Decimal(str(recalculation["profit_attributable_to_bank_shareholders_2024"]))
        quantum = Decimal("0.0000000000000001")
        parent_roe = (profit / Decimal(str(recalculation["average_parent_attributable_equity"])) * 100).quantize(quantum, rounding=ROUND_HALF_UP)
        total_roe = (profit / Decimal(str(recalculation["average_total_equity"])) * 100).quantize(quantum, rounding=ROUND_HALF_UP)
    if str(parent_roe) != recalculation["roe_parent_equity_percent_16dp"] or str(total_roe) != recalculation["roe_total_equity_percent_16dp"]:
        fail("reviewer-confirmed Q4 recomputation mismatch")

    review_rel = next(i["artifact_ref"] for i in authority["review_artifacts"] if "adjudicated-v1.csv" in i["artifact_ref"])
    promotion_rel = next(i["artifact_ref"] for i in authority["review_artifacts"] if "promotion-v4.csv" in i["artifact_ref"])
    with (evidence_root / review_rel).open(encoding="utf-8-sig", newline="") as stream:
        reviews = {r["target_id"]: r for r in csv.DictReader(stream)}
    with (evidence_root / promotion_rel).open(encoding="utf-8-sig", newline="") as stream:
        promotion = {r["target_id"]: r for r in csv.DictReader(stream)}
    targets = [f"VPB:2024_Q{q}:bank.roe" for q in range(1, 5)]
    if any(t not in reviews or any(reviews[t][k] != "accepted" for k in ("checker_a_decision", "checker_b_decision", "adjudication_decision")) for t in targets):
        fail("adjudicated VPB review is incomplete or not accepted")
    if any(promotion.get(t, {}).get("register_review_status", "").strip() for t in targets):
        fail("original promotion-ledger blank status changed")

    sidecar = read_json(ROOT / "reports/data-foundation/vpb-roe-promotion-review-status-reconciliation-20260925.json")
    confirmation = sidecar["distinct_confirmation"]
    if confirmation["status"] != "accepted" or confirmation["attestation_ref"] != ATTESTATION_REL or confirmation["reviewer_task_path"] != attestation["reviewer_task_path"] or confirmation["reviewed_head_sha"] != attestation["reviewed_head_sha"]:
        fail("status sidecar reviewer/head binding mismatch")
    for key, rel in (("readme", "data/reconciliation/gold-bank-2025-expansion-v3/VPB-parent-roe-review-v1/README.md"),
                     ("packet_manifest", "data/reconciliation/gold-bank-2025-expansion-v3/VPB-parent-roe-review-v1/VPB_parent_roe_manifest-v2.json")):
        item = sidecar["current_packet_control_hashes"][key]
        if item["hash_mode"] != "canonical_lf_utf8_sha256" or item["sha256"] != controls[rel]:
            fail(f"sidecar control hash mismatch: {rel}")

    sys.path.insert(0, str(ROOT / "src"))
    from thesis_data.comparative_gate import audit_comparative_definition_gate
    from thesis_data.schema import GoldConfig
    manifest = read_json(gate_path)
    scope = manifest["scope"]
    config = GoldConfig(tickers=tuple(scope["tickers"]), periods=tuple(scope["periods"]), required_metrics=tuple(scope["required_metrics"]))
    db_path = evidence_root / authority["snapshot_artifacts"][0]["artifact_ref"]
    result = audit_comparative_definition_gate(db_path, gate_path, config)
    actual = (result.eligible, result.blockers, result.checked_cells, result.valid_cells, result.missing_cells)
    recorded = (gate["eligible"], tuple(gate["blockers"]), gate["cells_checked"], gate["valid_cells"], gate["missing_cells"])
    if actual != (True, (), 80, 76, 4) or actual != recorded:
        fail(f"comparative gate result changed: {actual!r}")
    connection = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    try:
        rows = connection.execute("SELECT period,value,unit,period_basis,quality_status,source_locator FROM metric_observations WHERE ticker='VPB' AND metric='bank.roe' ORDER BY period").fetchall()
    finally:
        connection.close()
    observed = {r[0]: r[1] for r in rows}
    expected = {r["period"]: r["roe_percent_4dp"] for r in authority["accepted_results"]}
    if observed != expected or len(rows) != 4 or any(r[2] != "%" or r[3] != "ttm" or r[4] != "valid" or "parent_attributable_equity" not in r[5] for r in rows):
        fail(f"Gold v5 VPB ROE mismatch: {observed!r}")
    return {"result": "PASS", "evidence_root": str(evidence_root), "tracked_text_hash_mode": "canonical_lf_utf8_sha256",
            "lf_crlf_variants_checked": 2 * len(controls), "git_blob_hashes_checked": len(controls),
            "policy_markers_checked": expected_policy_refs,
            "reviewed_head_controls_checked": len(attestation["reviewed_control_hashes_canonical_lf_utf8_sha256"]),
            "control_hashes": controls, "raw_evidence_hashes": dict(sorted(raw_artifacts.items())),
            "reviewer_task_path": attestation["reviewer_task_path"], "reviewed_head_sha": attestation["reviewed_head_sha"],
            "verdict": attestation["verdict"], "q4_recalculation": {"parent_equity_roe_percent": str(parent_roe), "total_equity_alternative_percent": str(total_roe)},
            "comparative_gate": {"eligible": result.eligible, "blockers": list(result.blockers), "cells": result.checked_cells, "valid": result.valid_cells, "missing": result.missing_cells},
            "gold_v5_vpb_roe": observed}

if __name__ == "__main__":
    try:
        print(json.dumps(verify(parse_args().evidence_root), ensure_ascii=False, indent=2, sort_keys=True))
    except (OSError, UnicodeError, json.JSONDecodeError, sqlite3.Error, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        fail(str(exc))
