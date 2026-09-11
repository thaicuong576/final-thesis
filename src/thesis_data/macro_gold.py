"""Bounded Macro Gold contract, materialization, and experiment availability.

This module deliberately implements only the two frozen ``2024_Q4`` macro
cells.  It consumes the already-acquired candidate/adjudication artifacts and
never performs network acquisition or changes an existing snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Sequence

from .schema import MacroObservationV2, QualityStatus


MACRO_GOLD_CONTRACT_VERSION = "macro-observation-v2"
MACRO_GOLD_SNAPSHOT_ID = "gold-bank-2025-pilot-v1-adjudicated-v2-macro-v1"
EXPECTED_PARENT_SNAPSHOT_ID = "gold-bank-2025-pilot-v1-adjudicated-v2"
MACRO_GOLD_PERIOD = "2024_Q4"
MACRO_POLICY_RATE = "macro.policy_rate"
MACRO_CREDIT_GROWTH = "macro.credit_growth"
MACRO_GOLD_INDICATORS = frozenset({MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH})
MACRO_POLICY_DEFINITION_VERSION = "macro-policy-rate-sbv-refinancing-v1"
MACRO_CREDIT_DEFINITION_VERSION = "macro-credit-growth-total-credit-yoy-v1"
MACRO_EVIDENCE_ID_PREFIX = "macro-evidence:"
MACRO_ENTITY = "VN"
MACRO_POLICY_EFFECTIVE_FROM = "2023-06-19"
MACRO_POLICY_DECISION_ID = "1123/QĐ-NHNN"
MACRO_POLICY_SOURCE_STATUS = "accepted_primary_reviewed"
EXPECTED_PARENT_SCOPE = {
    "tickers": ["ACB", "TCB", "VPB"],
    "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
    "required_metrics": [
        "bank.npl_g35",
        "bank.llr_coverage",
        "bank.roa",
        "bank.roe",
    ],
}
POLICY_SOURCE_CONTRACT = {
    "sbv_policy_rates_history_api": {
        "publisher": "State Bank of Vietnam (SBV)",
        "source_identity": "SBV content structure 3450482; returned totalCount=1; record 3451452",
        "source_type": "official_headless_delivery_api",
    },
    "sbv_policy_rates_overview_page": {
        "publisher": "State Bank of Vietnam (SBV)",
        "source_identity": "SBV Lãi suất page",
        "source_type": "official_web_page",
    },
}


MACRO_OBSERVATIONS_V2_SQL = """
CREATE TABLE IF NOT EXISTS macro_observations_v2 (
    observation_id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    value REAL,
    unit TEXT,
    period TEXT NOT NULL,
    source_id TEXT,
    quality_status TEXT NOT NULL,
    reason TEXT,
    source_series_id TEXT,
    indicator_definition_version TEXT NOT NULL,
    frequency TEXT,
    observation_date TEXT,
    effective_from TEXT,
    as_of_date TEXT,
    period_basis TEXT NOT NULL,
    alignment_method TEXT,
    source_locator TEXT,
    transformation_version TEXT,
    input_observation_ids_json TEXT NOT NULL,
    adjudication_ref TEXT,
    review_check_ids_json TEXT NOT NULL,
    UNIQUE(indicator_id, period),
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
)
"""

MACRO_EVIDENCE_SQL = """
CREATE TABLE IF NOT EXISTS macro_evidence_snippets (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    indicator_id TEXT NOT NULL,
    period TEXT NOT NULL,
    source_document TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    quote TEXT NOT NULL,
    as_of_date TEXT,
    effective_from TEXT,
    parser_status TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES source_records(source_id)
)
"""


@dataclass(frozen=True)
class MacroGoldPromotionResult:
    """Result of materializing a new bounded macro-enabled snapshot."""

    eligible: bool
    blockers: tuple[str, ...] = ()
    output_path: str | None = None
    snapshot_id: str | None = None
    rows: tuple[MacroObservationV2, ...] = ()


@dataclass(frozen=True)
class MacroCellAvailability:
    """The only three runtime states relevant to the macro experiment gate."""

    status: str
    observation_id: str | None = None
    reason: str | None = None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid macro artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"macro artifact must contain an object: {path}")
    return payload


def _read_manifest(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"macro manifest is unreadable: {path}") from exc
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL in macro manifest: {path}") from exc
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ValueError("macro manifest artifact_id must be non-empty")
        if artifact_id in records:
            raise ValueError(f"duplicate macro manifest artifact: {artifact_id}")
        records[artifact_id] = item
    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _require_hash_matches(manifest: dict[str, dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    item = manifest.get(artifact_id)
    if item is None:
        raise ValueError(f"macro source missing from manifest: {artifact_id}")
    local_path = Path(str(item.get("local_path", "")))
    if not local_path.exists():
        raise ValueError(f"macro source artifact missing: {local_path}")
    expected = str(item.get("sha256", "")).upper()
    actual = _sha256(local_path)
    if not expected or actual != expected:
        raise ValueError(f"macro source hash mismatch: {artifact_id}")
    return item


def _candidate_cells(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scope = candidate.get("scope")
    if not isinstance(scope, dict) or scope.get("period") != MACRO_GOLD_PERIOD:
        raise ValueError("macro candidate scope must be exactly 2024_Q4")
    indicators = scope.get("indicators")
    if indicators != [MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH]:
        raise ValueError("macro candidate indicators do not match frozen scope")
    cells = candidate.get("candidate_cells")
    if not isinstance(cells, list):
        raise ValueError("macro candidate_cells must be a list")
    by_indicator = {item.get("indicator_id"): item for item in cells if isinstance(item, dict)}
    if set(by_indicator) != MACRO_GOLD_INDICATORS or len(cells) != 2:
        raise ValueError("macro candidate must contain exactly the two frozen cells")
    return by_indicator


def _check_passed(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.startswith("PASS"))


def _policy_review_checks(
    adjudication: dict[str, Any],
    manifest: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    policy = adjudication.get("policy_rate")
    if not isinstance(policy, dict) or policy.get("final_candidate_status") != "READY_FOR_MACRO_GOLD":
        raise ValueError("policy candidate is not READY_FOR_MACRO_GOLD")
    checks: list[str] = []
    reviewed_artifacts: set[str] = set()
    for key in ("checker_a", "checker_b"):
        checker = policy.get(key)
        if not isinstance(checker, dict) or checker.get("result") != "PASS":
            raise ValueError(f"macro policy review did not pass: {key}")
        checker_id = checker.get("checker_id")
        if not isinstance(checker_id, str) or not checker_id:
            raise ValueError(f"macro policy checker identity missing: {key}")
        checks.append(checker_id)
        source_checks = checker.get("source_checks")
        if not isinstance(source_checks, list) or not source_checks:
            raise ValueError(f"macro policy source checks missing: {key}")
        for source_check in source_checks:
            if source_check.get("hash_match") is not True:
                raise ValueError(f"macro policy source hash check failed: {key}")
            artifact_id = source_check.get("artifact_id")
            local_path = Path(str(source_check.get("local_path", "")))
            expected_hash = str(source_check.get("expected_sha256", "")).upper()
            actual_hash = str(source_check.get("actual_sha256", "")).upper()
            if not artifact_id or not expected_hash or expected_hash != actual_hash:
                raise ValueError(f"macro policy source hash record malformed: {key}")
            if not local_path.exists() or _sha256(local_path) != expected_hash:
                raise ValueError(f"macro policy reviewed artifact hash mismatch: {key}")
            reviewed_artifacts.add(str(artifact_id))
        review_checks = checker.get("checks")
        if not isinstance(review_checks, dict):
            raise ValueError(f"macro policy semantic review checks missing: {key}")
        for check_name in (
            "specifically_refinancing_rate",
            "value_exactly_4_5",
            "effective_date_interpretation",
            "locator_exact",
            "no_later_change_on_or_before_cutoff",
            "carry_forward_not_fabricated_observation",
        ):
            if not _check_passed(review_checks.get(check_name)):
                raise ValueError(f"macro policy review check failed: {key}:{check_name}")
    if len(set(checks)) != 2:
        raise ValueError("macro policy requires two independent checker identities")
    for artifact_id in POLICY_SOURCE_CONTRACT:
        item = _require_hash_matches(manifest, artifact_id)
        if artifact_id not in reviewed_artifacts:
            raise ValueError(f"macro source was not reviewed: {artifact_id}")
        if str(item.get("sha256", "")).upper() != _sha256(Path(str(item["local_path"]))):
            raise ValueError(f"macro source hash mismatch: {artifact_id}")
    return tuple(checks)


def _credit_review_checks(adjudication: dict[str, Any]) -> tuple[str, ...]:
    credit = adjudication.get("credit_growth")
    if not isinstance(credit, dict):
        raise ValueError("credit-growth adjudication is missing")
    if credit.get("final_status") != "PRIMARY_SOURCE_NOT_ESTABLISHED":
        raise ValueError("credit-growth adjudication status mismatch")
    if credit.get("missing_reason") != "DATA_UNAVAILABLE":
        raise ValueError("credit-growth adjudication missing reason mismatch")
    checks: list[str] = []
    for key in ("checker_a", "checker_b"):
        checker = credit.get(key)
        if not isinstance(checker, dict) or checker.get("result") != "PASS":
            raise ValueError(f"credit-growth missingness review did not pass: {key}")
        checker_id = checker.get("checker_id")
        if not isinstance(checker_id, str) or not checker_id:
            raise ValueError(f"credit-growth checker identity missing: {key}")
        review_checks = checker.get("checks")
        if not isinstance(review_checks, dict):
            raise ValueError(f"credit-growth review checks missing: {key}")
        for check_name in (
            "frozen_definition",
            "no_exact_q4_primary_observation",
            "no_official_year_end_stock_pair",
            "secondary_15_08_rejected",
            "accepted_missing_decision",
        ):
            if review_checks.get(check_name) is not True:
                raise ValueError(f"credit-growth review check failed: {key}:{check_name}")
        checks.append(checker_id)
    if len(set(checks)) != 2:
        raise ValueError("credit-growth missingness requires two independent checker identities")
    return tuple(checks)


def _validate_policy_source_metadata(
    manifest: dict[str, dict[str, Any]],
) -> None:
    for artifact_id, contract in POLICY_SOURCE_CONTRACT.items():
        item = manifest.get(artifact_id)
        if item is None:
            raise ValueError(f"macro source missing from manifest: {artifact_id}")
        for field, expected in contract.items():
            if item.get(field) != expected:
                raise ValueError(f"macro source metadata mismatch: {artifact_id}:{field}")
        if item.get("source_tier") != "primary":
            raise ValueError(f"macro source is not primary: {artifact_id}")
        if item.get("quality_status") != "valid":
            raise ValueError(f"macro source is not valid: {artifact_id}")
        if item.get("candidate_status") != MACRO_POLICY_SOURCE_STATUS:
            raise ValueError(f"macro source is not independently reviewed: {artifact_id}")
        if item.get("indicator_id") != MACRO_POLICY_RATE:
            raise ValueError(f"macro source indicator mismatch: {artifact_id}")


def _validate_evidence_package(evidence_package: dict[str, Any]) -> None:
    if evidence_package.get("status") != "candidate_only_not_gold":
        raise ValueError("macro evidence package status must remain candidate-only")
    evidence = evidence_package.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("macro evidence package evidence must be a list")
    policy_evidence = [
        item for item in evidence
        if isinstance(item, dict) and item.get("indicator_id") == MACRO_POLICY_RATE
    ]
    if not policy_evidence:
        raise ValueError("macro policy evidence is missing")
    for item in policy_evidence:
        if item.get("resolved_effective_from") != MACRO_POLICY_EFFECTIVE_FROM:
            raise ValueError("macro policy evidence effective date is not adjudicated")


def build_macro_gold_rows(
    candidate_path: Path,
    adjudication_path: Path,
    manifest_path: Path,
) -> tuple[MacroObservationV2, ...]:
    """Validate the final artifacts and build exactly two V2 macro rows."""

    candidate = _read_json(candidate_path)
    adjudication = _read_json(adjudication_path)
    manifest = _read_manifest(manifest_path)
    cells = _candidate_cells(candidate)
    if adjudication.get("scope", {}).get("period") != MACRO_GOLD_PERIOD:
        raise ValueError("macro adjudication period does not match frozen scope")
    if adjudication.get("promotion_performed") is not False:
        raise ValueError("macro adjudication must record promotion_performed=false")

    policy = cells[MACRO_POLICY_RATE]
    policy_adjudication = adjudication.get("policy_rate", {})
    _validate_policy_source_metadata(manifest)
    check_ids = _policy_review_checks(adjudication, manifest)
    if policy.get("source_adjudication_status") != "READY_FOR_MACRO_GOLD":
        raise ValueError("policy candidate status is not adjudicated ready")
    if policy.get("candidate_value") != 4.5 or policy.get("unit") != "percent_per_annum":
        raise ValueError("policy candidate does not match frozen value/unit")
    if policy.get("effective_from") != MACRO_POLICY_EFFECTIVE_FROM:
        raise ValueError("policy effective date does not match adjudication")
    if policy.get("observation_date") != MACRO_POLICY_EFFECTIVE_FROM:
        raise ValueError("policy observation date does not match adjudication")
    if policy.get("source_evidence", {}).get("source_effective_date") != "19/06/2023":
        raise ValueError("policy source effective date evidence is not corrected")
    if policy.get("source_evidence", {}).get("decision_identity") != "1123/QĐ-NHNN ngày 16/06/2023":
        raise ValueError("policy decision identity is not established")
    if policy_adjudication.get("candidate", {}).get("reported_effective_from") != MACRO_POLICY_EFFECTIVE_FROM:
        raise ValueError("policy adjudication effective date is not corrected")
    if policy_adjudication.get("final_candidate_status") != "READY_FOR_MACRO_GOLD":
        raise ValueError("policy adjudication status mismatch")
    policy_source = _require_hash_matches(manifest, "sbv_policy_rates_history_api")
    overview_source = _require_hash_matches(manifest, "sbv_policy_rates_overview_page")

    policy_row = MacroObservationV2(
        observation_id="macro.policy_rate|2024_Q4|macro-observation-v2",
        indicator_id=MACRO_POLICY_RATE,
        value=4.5,
        unit="percent_per_annum",
        period=MACRO_GOLD_PERIOD,
        source_id="sbv_policy_rates_history_api",
        quality_status=QualityStatus.VALID,
        source_series_id=str(policy["source_series_id"]),
        indicator_definition_version=MACRO_POLICY_DEFINITION_VERSION,
        frequency="irregular_state",
        observation_date=date.fromisoformat(MACRO_POLICY_EFFECTIVE_FROM),
        effective_from=date.fromisoformat(MACRO_POLICY_EFFECTIVE_FROM),
        as_of_date=date.fromisoformat("2024-12-31"),
        period_basis="quarter_end_state",
        alignment_method="latest_effective_state_at_period_end_v1",
        source_locator="items[0].title=19-06-2023; items[0].friendlyUrlPath=19-06-2023-1; items[0].contentFields[name=banglaiSuats][nestedContentFields name=loaiLaiSuat|giaTri|vanBanQuyetDinh]",
        transformation_version="state_carry_forward_v1",
        input_observation_ids=(),
        adjudication_ref="data/reconciliation/macro-official-2024-q4-v1/final-source-adjudication.json",
        review_check_ids=check_ids,
    )

    credit = cells[MACRO_CREDIT_GROWTH]
    credit_adjudication = adjudication.get("credit_growth", {})
    if credit.get("source_adjudication_status") != "PRIMARY_SOURCE_NOT_ESTABLISHED":
        raise ValueError("credit-growth candidate status unexpectedly changed")
    if credit.get("quality_status") != "missing" or credit.get("missing_reason") != "DATA_UNAVAILABLE":
        raise ValueError("credit-growth missing contract is not DATA_UNAVAILABLE")
    if credit.get("candidate_value") is not None:
        raise ValueError("accepted missing credit-growth row cannot contain a value")
    credit_check_ids = _credit_review_checks(adjudication)

    credit_row = MacroObservationV2(
        observation_id="macro.credit_growth|2024_Q4|macro-observation-v2",
        indicator_id=MACRO_CREDIT_GROWTH,
        value=None,
        unit="percent",
        period=MACRO_GOLD_PERIOD,
        source_id=None,
        quality_status=QualityStatus.MISSING,
        reason="DATA_UNAVAILABLE",
        source_series_id=None,
        indicator_definition_version=MACRO_CREDIT_DEFINITION_VERSION,
        frequency=None,
        observation_date=None,
        effective_from=None,
        as_of_date=None,
        period_basis="ytd_vs_end_2023",
        alignment_method=None,
        source_locator=None,
        transformation_version=None,
        input_observation_ids=(),
        adjudication_ref="data/reconciliation/macro-official-2024-q4-v1/final-source-adjudication.json",
        review_check_ids=credit_check_ids,
    )
    # Keep source artifact resolution explicit even though the missing row has
    # no accepted source.  These artifacts are the bounded negative-trace
    # inputs reviewed by both credit-growth checkers.
    _ = policy_source, overview_source
    return policy_row, credit_row


def ensure_macro_v2_schema(connection: sqlite3.Connection) -> None:
    """Create only the versioned macro tables on a copied/new snapshot."""

    connection.executescript(MACRO_OBSERVATIONS_V2_SQL + ";" + MACRO_EVIDENCE_SQL)


def _manifest_source_row(item: dict[str, Any], *, source_id: str) -> tuple[Any, ...]:
    """Convert an already validated manifest record without promoting it."""

    return (
        source_id,
        str(item["source_type"]),
        str(item["source_tier"]),
        str(item["source_url"]),
        str(item["retrieved_at_utc"]),
        str(item["local_path"]),
        str(item["sha256"]),
        str(item["publisher"]),
        "official public source; bounded macro Gold acquisition",
        str(item["quality_status"]),
        str(item.get("notes") or ""),
    )


def _read_parent_snapshot_contract(base_db: Path) -> dict[str, Any]:
    """Validate the one and only bank Gold parent before copying it."""

    if not base_db.exists():
        raise ValueError(f"macro parent database is missing: {base_db}")
    connection = sqlite3.connect(f"file:{base_db.resolve()}?mode=ro", uri=True)
    try:
        try:
            rows = connection.execute(
                "SELECT snapshot_id, status, config_json FROM snapshot_metadata"
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise ValueError("macro parent snapshot metadata is unreadable") from exc
    finally:
        connection.close()
    if len(rows) != 1:
        raise ValueError("macro parent must contain exactly one snapshot_metadata row")
    snapshot_id, status, config_json = rows[0]
    if snapshot_id != EXPECTED_PARENT_SNAPSHOT_ID:
        raise ValueError(
            f"macro parent snapshot mismatch: expected {EXPECTED_PARENT_SNAPSHOT_ID}, got {snapshot_id}"
        )
    if status != "gold":
        raise ValueError("macro parent snapshot is not gold")
    try:
        config = json.loads(config_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("macro parent snapshot config is invalid JSON") from exc
    if not isinstance(config, dict):
        raise ValueError("macro parent snapshot config must be an object")
    for key, expected in EXPECTED_PARENT_SCOPE.items():
        if config.get(key) != expected:
            raise ValueError(f"macro parent scope mismatch: {key}")
    if "macro_gold_lineage" in config:
        raise ValueError("macro parent is already macro-enriched")
    return config


def _macro_lineage_config(parent_config: dict[str, Any]) -> dict[str, Any]:
    config = dict(parent_config)
    config["macro_gold_lineage"] = {
        "parent_snapshot_id": EXPECTED_PARENT_SNAPSHOT_ID,
        "macro_contract_version": MACRO_GOLD_CONTRACT_VERSION,
        "macro_period": MACRO_GOLD_PERIOD,
        "macro_indicator_ids": sorted(MACRO_GOLD_INDICATORS),
    }
    return config


def _rebind_coverage_summary(connection: sqlite3.Connection) -> None:
    """Make inherited summaries owned by the new snapshot identity."""

    connection.execute(
        """
        UPDATE coverage_summary
        SET snapshot_id = ?,
            summary_id = ? || ':' || ticker || ':' || metric
        """,
        (MACRO_GOLD_SNAPSHOT_ID, MACRO_GOLD_SNAPSHOT_ID),
    )


def materialize_macro_gold_snapshot(
    base_db: Path,
    output_db: Path,
    candidate_path: Path,
    adjudication_path: Path,
    manifest_path: Path,
    evidence_package_path: Path | None = None,
) -> MacroGoldPromotionResult:
    """Copy a Gold bank snapshot and add the bounded MacroObservationV2 layer."""

    if output_db.exists():
        raise FileExistsError(f"refusing to overwrite existing snapshot: {output_db}")
    parent_config = _read_parent_snapshot_contract(base_db)
    rows = build_macro_gold_rows(candidate_path, adjudication_path, manifest_path)
    manifest = _read_manifest(manifest_path)
    if evidence_package_path is not None:
        evidence_package = _read_json(evidence_package_path)
        _validate_evidence_package(evidence_package)

    output_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base_db, output_db)
    try:
        connection = sqlite3.connect(output_db)
        connection.execute("PRAGMA foreign_keys = ON")
        ensure_macro_v2_schema(connection)
        for artifact_id in ("sbv_policy_rates_history_api", "sbv_policy_rates_overview_page"):
            item = manifest[artifact_id]
            connection.execute(
                """
                INSERT INTO source_records
                (source_id, source_type, source_tier, source_url, retrieved_at,
                 local_path, content_hash, publisher, license_note,
                 quality_status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _manifest_source_row(item, source_id=artifact_id),
            )
        connection.executemany(
            """
            INSERT INTO macro_observations_v2
            (observation_id, indicator_id, value, unit, period, source_id,
             quality_status, reason, source_series_id,
             indicator_definition_version, frequency, observation_date,
             effective_from, as_of_date, period_basis, alignment_method,
             source_locator, transformation_version, input_observation_ids_json,
             adjudication_ref, review_check_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.observation_id,
                    row.indicator_id,
                    row.value,
                    row.unit,
                    row.period,
                    row.source_id,
                    row.quality_status.value,
                    row.reason,
                    row.source_series_id,
                    row.indicator_definition_version,
                    row.frequency,
                    row.observation_date.isoformat() if row.observation_date else None,
                    row.effective_from.isoformat() if row.effective_from else None,
                    row.as_of_date.isoformat() if row.as_of_date else None,
                    row.period_basis,
                    row.alignment_method,
                    row.source_locator,
                    row.transformation_version,
                    json.dumps(list(row.input_observation_ids), sort_keys=True),
                    row.adjudication_ref,
                    json.dumps(list(row.review_check_ids), sort_keys=True),
                )
                for row in rows
            ],
        )
        connection.executemany(
            """
            INSERT INTO macro_evidence_snippets
            (evidence_id, source_id, indicator_id, period, source_document,
             source_locator, quote, as_of_date, effective_from, parser_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"{MACRO_EVIDENCE_ID_PREFIX}policy-rate-2024-q4-history",
                    "sbv_policy_rates_history_api",
                    MACRO_POLICY_RATE,
                    MACRO_GOLD_PERIOD,
                    "sbv-policy-rates-history-api.json",
                    "items[0].contentFields[name=banglaiSuats][nestedContentFields name=loaiLaiSuat|giaTri|vanBanQuyetDinh]",
                    "Lãi suất tái cấp vốn: 4,500%; Decision 1123/QĐ-NHNN ngày 16/06/2023; record title/effective date 19-06-2023.",
                    "2024-12-31",
                    MACRO_POLICY_EFFECTIVE_FROM,
                    "structured_content",
                ),
                (
                    f"{MACRO_EVIDENCE_ID_PREFIX}policy-rate-2024-q4-overview",
                    "sbv_policy_rates_overview_page",
                    MACRO_POLICY_RATE,
                    MACRO_GOLD_PERIOD,
                    "sbv-policy-rates-overview.html",
                    "HTML table: Lãi suất tái cấp vốn row; local lines 5271-5274",
                    "Lãi suất tái cấp vốn: 4,500%; Decision 1123/QĐ-NHNN ngày 16/06/2023; date representation is supporting only.",
                    "2024-12-31",
                    MACRO_POLICY_EFFECTIVE_FROM,
                    "html_table",
                ),
            ],
        )
        metadata_rows = connection.execute(
            "SELECT snapshot_id, status FROM snapshot_metadata"
        ).fetchall()
        if len(metadata_rows) != 1:
            raise ValueError("new macro snapshot must contain exactly one snapshot_metadata row")
        if metadata_rows[0] != (EXPECTED_PARENT_SNAPSHOT_ID, "gold"):
            raise ValueError("copied parent metadata changed before macro enrichment")
        connection.execute(
            "UPDATE snapshot_metadata SET snapshot_id = ?, config_json = ? WHERE snapshot_id = ?",
            (
                MACRO_GOLD_SNAPSHOT_ID,
                json.dumps(_macro_lineage_config(parent_config), sort_keys=True),
                EXPECTED_PARENT_SNAPSHOT_ID,
            ),
        )
        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("macro snapshot metadata lineage update did not affect one row")
        _rebind_coverage_summary(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        output_db.unlink(missing_ok=True)
        raise
    else:
        connection.close()
    return MacroGoldPromotionResult(
        eligible=True,
        output_path=str(output_db),
        snapshot_id=MACRO_GOLD_SNAPSHOT_ID,
        rows=rows,
    )


def macro_cell_availability(
    db_path: Path,
    indicator_id: str,
    period: str,
    *,
    accepted_source_tiers: Sequence[str] = ("primary",),
) -> MacroCellAvailability:
    """Classify one V2 macro cell for the experiment preflight gate."""

    if indicator_id not in MACRO_GOLD_INDICATORS or period != MACRO_GOLD_PERIOD:
        return MacroCellAvailability("blocked", reason="macro_scope_not_frozen")
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "macro_observations_v2" not in tables:
            return MacroCellAvailability("blocked", reason="macro_v2_table_missing")
        rows = connection.execute(
            """
            SELECT macro.observation_id, macro.value, macro.quality_status,
                   macro.reason, macro.adjudication_ref, macro.source_id,
                       source.quality_status AS source_quality_status,
                       source.source_tier, macro.review_check_ids_json
            FROM macro_observations_v2 AS macro
            LEFT JOIN source_records AS source ON source.source_id = macro.source_id
            WHERE macro.indicator_id = ? AND macro.period = ?
            """,
            (indicator_id, period),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != 1:
        return MacroCellAvailability("blocked", reason="macro_cell_missing_or_ambiguous")
    row = rows[0]
    if (
        row["quality_status"] == QualityStatus.VALID.value
        and row["value"] is not None
        and row["source_quality_status"] == "valid"
        and row["source_tier"] in accepted_source_tiers
    ):
        return MacroCellAvailability("valid", row["observation_id"])
    if (
        row["quality_status"] == QualityStatus.MISSING.value
        and row["value"] is None
        and row["reason"] == "DATA_UNAVAILABLE"
        and row["adjudication_ref"]
        and _has_independent_review_ids(row["review_check_ids_json"])
    ):
        return MacroCellAvailability("missing", row["observation_id"], row["reason"])
    return MacroCellAvailability("blocked", row["observation_id"], row["reason"])


def _has_independent_review_ids(raw: str | None) -> bool:
    try:
        checks = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return False
    return (
        isinstance(checks, list)
        and len(checks) >= 2
        and all(isinstance(check, str) and check for check in checks)
        and len(set(checks)) == len(checks)
    )
