"""Build an immutable Gold snapshot with one auditable evidence record per valid cell.

The existing expanded-v4 snapshot contains source-linked observations and a
partial set of evidence snippets.  This script creates a new snapshot rather
than mutating v4.  It materializes human-reviewed derivation notes from the
adjudicated review ledger as evidence records.  These are deliberately labeled
as derivation notes, not verbatim PDF quotations, because several source PDFs
were scanned and the reviewers recorded the verified inputs/formulas instead of
an OCR quote.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_BASE_DB = Path("data/processed/gold-bank-2025-expanded-v4.sqlite")
DEFAULT_LEDGER = Path(
    "data/reconciliation/gold-bank-2025-expansion-v2/official-review-v1/"
    "official_expansion_review-ledger-promotion-v3.csv"
)
DEFAULT_OUTPUT_DB = Path("data/processed/gold-bank-2025-expanded-v5-evidence.sqlite")
DEFAULT_AUDIT_JSON = Path(
    "reports/data-foundation/gold-bank-2025-expanded-v5-evidence.json"
)
DEFAULT_AUDIT_MD = Path(
    "reports/data-foundation/gold-bank-2025-expanded-v5-evidence.md"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_pdf_page(*locators: str) -> int | None:
    """Extract the first PDF page number from a human/source locator."""

    patterns = (
        r"\bpdf_pages?\s*:\s*(\d+)",
        r"\bpdf\s*:\s*p(?:age)?\.?\s*(\d+)",
        r"\bpage\s*:\s*(\d+)",
        r"\b(?:PDF|pdf)\s+pp?\.?\s*(\d+)",
    )
    for locator in locators:
        if not locator:
            continue
        for pattern in patterns:
            match = re.search(pattern, locator)
            if match:
                return int(match.group(1))
    return None


def _load_accepted_rows(ledger_path: Path) -> list[dict[str, str]]:
    with ledger_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    accepted = [row for row in rows if row.get("adjudication_decision") == "accepted"]
    if len({row.get("target_id") for row in accepted}) != len(accepted):
        raise RuntimeError("The review ledger contains duplicate accepted target IDs")
    return accepted


def _selected_checker(row: dict[str, str]) -> tuple[str, str, str, str]:
    slot = (row.get("adjudication_source_slot") or "").strip().lower()
    if slot not in {"checker_a", "checker_b"}:
        slot = "checker_a"
    prefix = slot
    checker_id = (row.get(f"{prefix}_id") or "").strip()
    locator = (row.get(f"{prefix}_source_locator") or "").strip()
    notes = (row.get(f"{prefix}_notes") or "").strip()
    return slot, checker_id, locator, notes


def _safe_document_name(local_path: str) -> str:
    # SQLite paths were recorded on Windows; splitting both separators keeps
    # the audit portable if it is later inspected on another OS.
    return re.split(r"[\\/]", local_path)[-1]


def _markdown(audit: dict) -> str:
    lines = [
        "# Gold expanded-v5 evidence audit",
        "",
        f"- Snapshot: `{audit['snapshot_id']}`",
        f"- Base snapshot: `{audit['base_snapshot_id']}`",
        f"- Created: `{audit['created_at_utc']}`",
        f"- Base DB SHA-256: `{audit['base_db_sha256']}`",
        f"- Base DB unchanged: **{audit['base_db_unchanged']}**",
        "",
        "## Coverage",
        "",
        f"- Accepted review rows materialized: **{audit['accepted_review_rows']}**",
        f"- Valid Gold observations: **{audit['valid_observations']}**",
        f"- Valid observations with a new evidence record: **{audit['valid_with_new_evidence']}**",
        f"- Evidence coverage of valid observations: **{audit['evidence_coverage_ratio']:.1%}**",
        f"- Explicit missing observations retained: **{audit['missing_observations']}**",
        f"- Evidence snippets after build: **{audit['evidence_snippets_after']}**",
        "",
        "| Issuer | Valid observations | New reviewed evidence | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for ticker in sorted(audit["by_issuer"]):
        item = audit["by_issuer"][ticker]
        lines.append(
            f"| {ticker} | {item['valid_observations']} | "
            f"{item['new_reviewed_evidence']} | {item['coverage_ratio']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Evidence policy",
            "",
            "Each valid cell receives a page-aware `human_reviewed_derivation_note` "
            "linked to its canonical source record. The note preserves the "
            "independently reviewed inputs, formula/scope explanation, checker "
            "identity, and source locator. It is not represented as a verbatim "
            "quote from the PDF.",
            "",
            "This closes the cell-level evidence coverage gap for the current "
            "76 valid observations. It does not remove the underlying scan/OCR "
            "limitation, and it does not fill the four explicit ACB Q1 missing "
            "cells.",
            "",
            "## Verification",
            "",
        ]
    )
    for check in audit["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- **{status}** {check['name']}: {check['detail']}")
    lines.append("")
    return "\n".join(lines)


def build_snapshot(
    base_db: Path,
    ledger_path: Path,
    output_db: Path,
    audit_json: Path,
    audit_md: Path,
) -> dict:
    for path in (base_db, ledger_path):
        if not path.exists():
            raise FileNotFoundError(path)
    accepted = _load_accepted_rows(ledger_path)
    output_db.parent.mkdir(parents=True, exist_ok=True)
    # The first run may be interrupted after copying/inserting but before the
    # final audit.  Resume that exact generated artifact without overwriting
    # rows; a completed v5 snapshot is also safe to re-audit.
    if not output_db.exists():
        shutil.copy2(base_db, output_db)
    base_hash = _sha256(base_db)

    con = sqlite3.connect(output_db)
    con.row_factory = sqlite3.Row
    try:
        snapshot = con.execute(
            "SELECT snapshot_id, created_at_utc, status, config_json "
            "FROM snapshot_metadata"
        ).fetchone()
        if snapshot is None or snapshot["status"] != "gold":
            raise RuntimeError("Base database is not a Gold snapshot")
        output_snapshot_id = "gold-bank-2025-expanded-v5-evidence"
        config = json.loads(snapshot["config_json"])
        evidence_metadata = config.pop("evidence_snapshot", {})
        base_snapshot_id = evidence_metadata.get(
            "base_snapshot_id",
            "gold-bank-2025-expanded-v4"
            if snapshot["snapshot_id"] == output_snapshot_id
            else snapshot["snapshot_id"],
        )
        if snapshot["snapshot_id"] not in {base_snapshot_id, output_snapshot_id}:
            raise RuntimeError(
                f"Unexpected existing snapshot identity: {snapshot['snapshot_id']}"
            )

        valid_observations = con.execute(
            "SELECT observation_id, ticker, metric, period, source_id, "
            "source_locator, quality_status "
            "FROM metric_observations WHERE quality_status='valid' "
            "AND value IS NOT NULL"
        ).fetchall()
        observations = {
            (row["ticker"], row["period"], row["metric"]): row
            for row in valid_observations
        }
        if len(observations) != len(valid_observations):
            raise RuntimeError("Base Gold contains duplicate valid target cells")

        source_rows = {
            row["source_id"]: row
            for row in con.execute("SELECT * FROM source_records")
        }
        materialized_evidence_ids: set[str] = set()
        issuer_counts: defaultdict[str, dict[str, int]] = defaultdict(
            lambda: {"valid_observations": 0, "new_reviewed_evidence": 0}
        )
        accepted_targets: set[tuple[str, str, str]] = set()

        with con:
            for row in accepted:
                key = (row["ticker"], row["period"], row["metric"])
                observation = observations.get(key)
                if observation is None:
                    raise RuntimeError(
                        f"Accepted review row has no valid Gold observation: {row['target_id']}"
                    )
                source_id = observation["source_id"]
                source = source_rows.get(source_id)
                if source is None or source["quality_status"] != "valid":
                    raise RuntimeError(
                        f"Observation source is not valid for {row['target_id']}: {source_id}"
                    )

                slot, checker_id, review_locator, notes = _selected_checker(row)
                if not notes:
                    notes = (row.get("adjudication_reason") or "").strip()
                if not notes:
                    raise RuntimeError(f"Accepted review row has no review note: {row['target_id']}")

                evidence_id = f"gold-v5:human-reviewed:{observation['observation_id']}"
                page_number = _first_pdf_page(
                    observation["source_locator"] or "", review_locator
                )
                if page_number is None:
                    raise RuntimeError(
                        f"Could not derive a PDF page for accepted row: {row['target_id']}"
                    )
                quote = (
                    "Human-reviewed derivation note (not a verbatim source quote). "
                    f"Target {row['target_id']}; selected review slot {slot} "
                    f"({checker_id}). {notes} Review locator: {review_locator or 'not recorded'}. "
                    f"Canonical observation locator: {observation['source_locator'] or 'not recorded'}."
                )
                existing_evidence = con.execute(
                    "SELECT source_id, page_number, period, ticker, parser_status "
                    "FROM evidence_snippets WHERE evidence_id=?",
                    (evidence_id,),
                ).fetchone()
                expected_evidence = (
                    source_id,
                    page_number,
                    row["period"],
                    row["ticker"],
                    "human_reviewed_derivation_note",
                )
                if existing_evidence is None:
                    con.execute(
                        "INSERT INTO evidence_snippets "
                        "(evidence_id, source_id, source_document, page_number, "
                        "section_name, period, ticker, quote, retrieval_score, "
                        "parser_status, is_paginated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            evidence_id,
                            source_id,
                            _safe_document_name(source["local_path"]),
                            page_number,
                            f"human_reviewed_derivation:{row['metric']}:{slot}",
                            row["period"],
                            row["ticker"],
                            quote,
                            1.0,
                            "human_reviewed_derivation_note",
                            1,
                        ),
                    )
                elif tuple(existing_evidence) != expected_evidence:
                    raise RuntimeError(
                        f"Existing generated evidence does not match {row['target_id']}"
                    )
                accepted_targets.add(key)
                materialized_evidence_ids.add(evidence_id)
                issuer_counts[row["ticker"]]["new_reviewed_evidence"] += 1

        for row in valid_observations:
            issuer_counts[row["ticker"]]["valid_observations"] += 1

        con.execute(
            "UPDATE snapshot_metadata SET snapshot_id=?, created_at_utc=?, config_json=?",
            (
                output_snapshot_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(config, ensure_ascii=False, sort_keys=True),
            ),
        )
        con.execute(
            "UPDATE coverage_summary SET snapshot_id=?, summary_id=? || substr(summary_id, instr(summary_id, ':'))",
            (output_snapshot_id, output_snapshot_id),
        )

        evidence_count = con.execute(
            "SELECT COUNT(*) FROM evidence_snippets"
        ).fetchone()[0]
        new_evidence_count = con.execute(
            "SELECT COUNT(*) FROM evidence_snippets "
            "WHERE parser_status='human_reviewed_derivation_note'"
        ).fetchone()[0]
        valid_with_new = con.execute(
            "SELECT COUNT(DISTINCT o.observation_id) FROM metric_observations o "
            "JOIN evidence_snippets e ON e.source_id=o.source_id "
            "AND e.ticker=o.ticker AND e.period=o.period "
            "AND e.evidence_id LIKE 'gold-v5:human-reviewed:%' "
            "WHERE o.quality_status='valid' AND o.value IS NOT NULL"
        ).fetchone()[0]
        missing_count = con.execute(
            "SELECT COUNT(*) FROM metric_observations WHERE quality_status='missing'"
        ).fetchone()[0]
        output_snapshot = con.execute(
            "SELECT snapshot_id, status FROM snapshot_metadata"
        ).fetchone()
        if output_snapshot["snapshot_id"] != output_snapshot_id:
            raise RuntimeError("Output snapshot identity update failed")
        if len(materialized_evidence_ids) != len(accepted) or new_evidence_count != len(accepted):
            raise RuntimeError("Evidence insertion count does not match accepted review rows")
        if valid_with_new != len(valid_observations):
            raise RuntimeError(
                f"Evidence coverage is incomplete: {valid_with_new}/{len(valid_observations)}"
            )

        checks = [
            {
                "name": "base snapshot is preserved",
                "passed": _sha256(base_db) == base_hash,
                "detail": "The v4 input hash is unchanged after v5 creation.",
            },
            {
                "name": "accepted review rows map one-to-one to valid observations",
                "passed": len(accepted_targets) == len(accepted) == len(valid_observations),
                "detail": f"{len(accepted)} accepted rows, {len(valid_observations)} valid cells.",
            },
            {
                "name": "page-aware reviewed evidence is complete",
                "passed": valid_with_new == len(valid_observations),
                "detail": f"{valid_with_new}/{len(valid_observations)} valid cells have a new reviewed evidence record.",
            },
            {
                "name": "explicit missingness is retained",
                "passed": missing_count == 4,
                "detail": f"{missing_count} missing cells remain null and excluded from numeric coverage.",
            },
            {
                "name": "output remains Gold",
                "passed": output_snapshot["status"] == "gold",
                "detail": f"snapshot_metadata.status={output_snapshot['status']}.",
            },
        ]
        if not all(check["passed"] for check in checks):
            raise RuntimeError("Gold evidence snapshot audit failed")

        # The evidence INSERTs run inside the transaction context above.  The
        # identity/configuration update happens after that context so it is
        # committed explicitly, including when this script resumes a partial
        # generated artifact.
        con.commit()

        by_issuer = {}
        for ticker, counts in sorted(issuer_counts.items()):
            ratio = counts["new_reviewed_evidence"] / counts["valid_observations"]
            by_issuer[ticker] = {**counts, "coverage_ratio": ratio}

        audit = {
            "snapshot_id": output_snapshot_id,
            "base_snapshot_id": base_snapshot_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_db_sha256": base_hash,
            "base_db_unchanged": _sha256(base_db) == base_hash,
            "accepted_review_rows": len(accepted),
            "valid_observations": len(valid_observations),
            "valid_with_new_evidence": valid_with_new,
            "evidence_coverage_ratio": valid_with_new / len(valid_observations),
            "missing_observations": missing_count,
            "evidence_snippets_after": evidence_count,
            "new_reviewed_evidence": new_evidence_count,
            "by_issuer": by_issuer,
            "evidence_method": "adjudicated_human_review_derivation_notes",
            "limitations": [
                "Reviewed derivation notes are not verbatim PDF quotations.",
                "Scanned/mixed-text PDF limitations remain recorded in source audits.",
                "The four explicit ACB 2024_Q1 missing cells remain missing.",
            ],
            "checks": checks,
        }
    finally:
        con.close()

    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_md.write_text(_markdown(audit), encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-db", type=Path, default=DEFAULT_BASE_DB)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output-db", type=Path, default=DEFAULT_OUTPUT_DB)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    parser.add_argument("--audit-md", type=Path, default=DEFAULT_AUDIT_MD)
    args = parser.parse_args()
    audit = build_snapshot(
        args.base_db,
        args.ledger,
        args.output_db,
        args.audit_json,
        args.audit_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
