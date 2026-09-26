"""Portable SQLite materialization for the generic canonical dataset contract."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import re
import sqlite3

from .dataset_contract import (
    CalculationInputReceipt,
    CanonicalObservation,
    DatasetEvidence,
    DerivedCalculationReceipt,
    canonical_observation_id,
)
from .evidence_contract import DatasetDocument
from .onboarding_contract import (
    DatasetSnapshotStatus,
    DatasetSnapshotMetadata,
    OnboardingValidationReport,
    RawDatasetDescriptor,
    compute_content_manifest_hash,
    compute_dataset_snapshot_id,
    promote_snapshot_metadata,
    validate_snapshot_metadata,
)
from .onboarding_validation import CanonicalDatasetCandidate
from .metrics import operational_derived_formula
from .schema import QualityStatus
from .source_artifacts import VerifiedSourceArtifacts


CANONICAL_SNAPSHOT_SCHEMA_VERSION = "canonical-snapshot-v3"


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


CANONICAL_CALCULATION_RECEIPT_METADATA_KEY = "__derived_calculation_receipt_v1"
_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
_SOURCE_TYPES = {
    "api",
    "filing",
    "issuer_ir",
    "market_data",
    "policy",
    "research_report",
}


def _unit_matches(actual: str | None, expected: str) -> bool:
    if expected == "percent":
        return actual in {"%", "percent", "percentage_points"}
    return actual == expected


def _expected_input_periods(
    output_period_id: str,
    period_rule: str,
    input_count: int,
) -> tuple[str, ...]:
    if period_rule == "same_period":
        return (output_period_id,) * input_count
    if period_rule != "q4_ttm":
        raise ValueError(f"unsupported derived period rule: {period_rule}")
    try:
        year_text, quarter_text = output_period_id.split("_Q", 1)
        year = int(year_text)
        quarter = int(quarter_text)
    except (ValueError, TypeError) as exc:
        raise ValueError("TTM derived output period must use YYYY_Qn") from exc
    if quarter != 4 or input_count != 4:
        raise ValueError("current TTM formula requires a Q4 output and four ordered inputs")
    prior_period = f"{year - 1}_Q4"
    return (output_period_id, prior_period, output_period_id, prior_period)


def _calculate_derived_receipt(
    observation: CanonicalObservation,
    observation_by_id: dict[str, CanonicalObservation],
) -> DerivedCalculationReceipt:
    formula = operational_derived_formula(
        observation.metric_id,
        observation.derivation_method or "",
    )
    if formula is None:
        raise ValueError(
            f"derived formula is unsupported for operational promotion: "
            f"{observation.metric_id}/{observation.derivation_method}"
        )
    if observation.validation_status is not QualityStatus.VALID or observation.value is None:
        raise ValueError("derived calculation requires a valid numeric candidate")
    if observation.period_basis != formula.output_period_basis:
        raise ValueError("derived output period basis does not match its formula")
    if not _unit_matches(observation.unit, formula.output_unit):
        raise ValueError("derived output unit does not match its formula")
    if len(observation.input_observation_ids) != len(formula.input_metric_ids):
        raise ValueError("derived input count does not match its formula")
    expected_periods = _expected_input_periods(
        observation.period_id,
        formula.period_rule,
        len(formula.input_metric_ids),
    )
    inputs: list[CanonicalObservation] = []
    for index, input_id in enumerate(observation.input_observation_ids):
        source_input = observation_by_id.get(input_id)
        if source_input is None:
            raise ValueError(f"derived input observation does not resolve: {input_id}")
        if source_input.validation_status is not QualityStatus.VALID or source_input.value is None:
            raise ValueError(f"derived input observation is not accepted numeric data: {input_id}")
        if source_input.entity_id != observation.entity_id:
            raise ValueError(f"derived input entity does not match output: {input_id}")
        if source_input.metric_id != formula.input_metric_ids[index]:
            raise ValueError(f"derived input metric/order does not match formula: {input_id}")
        if source_input.period_id != expected_periods[index]:
            raise ValueError(f"derived input period does not match formula: {input_id}")
        if source_input.period_basis != formula.input_period_bases[index]:
            raise ValueError(f"derived input period basis does not match formula: {input_id}")
        if source_input.reporting_scope != observation.reporting_scope:
            raise ValueError(f"derived input reporting scope does not match output: {input_id}")
        if source_input.unit != formula.input_units[index]:
            raise ValueError(f"derived input unit does not match formula: {input_id}")
        inputs.append(source_input)

    input_values = tuple(Decimal(str(item.value)) for item in inputs)
    result = formula.calculate(input_values)
    if result.quality_status is not QualityStatus.VALID or result.value is None:
        raise ValueError(f"derived formula could not calculate a valid value: {formula.formula_version}")
    if result.formula_version != formula.formula_version:
        raise ValueError("deterministic calculation returned an unexpected formula version")
    if result.period_basis != formula.output_period_basis:
        raise ValueError("deterministic calculation returned an unexpected period basis")
    if not _unit_matches(result.unit, formula.output_unit):
        raise ValueError("deterministic calculation returned an unexpected unit")

    calculated_output = result.value
    candidate_output = Decimal(str(observation.value))
    difference = abs(candidate_output - calculated_output)
    if difference > formula.tolerance:
        raise ValueError(
            f"derived candidate value differs from deterministic calculation: "
            f"{observation.metric_id} difference={difference} tolerance={formula.tolerance}"
        )
    return DerivedCalculationReceipt(
        formula_version=formula.formula_version,
        ordered_inputs=tuple(
            CalculationInputReceipt(
                observation_id=item.observation_id,
                metric_id=item.metric_id,
                period_id=item.period_id,
                value=Decimal(str(item.value)),
                unit=item.unit,
                period_basis=item.period_basis,
                reporting_scope=item.reporting_scope,
            )
            for item in inputs
        ),
        calculated_output=calculated_output,
        candidate_output=candidate_output,
        unit=observation.unit,
        tolerance=formula.tolerance,
        absolute_difference=difference,
        result="passed",
    )


def _create_schema(connection: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE dataset_metadata (
            dataset_id TEXT PRIMARY KEY,
            dataset_snapshot_id TEXT NOT NULL UNIQUE,
            contract_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_content_hash TEXT NOT NULL,
            mapping_version TEXT NOT NULL,
            validation_version TEXT NOT NULL,
            content_manifest_hash TEXT NOT NULL,
            CHECK (status = 'accepted')
        )
        """,
        """
        CREATE TABLE sources (
            source_ref TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_tier TEXT NOT NULL,
            source_url TEXT NOT NULL,
            publisher TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            notes TEXT
        )
        """,
        """
        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            display_name TEXT NOT NULL,
            attributes_json TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE periods (
            period_id TEXT PRIMARY KEY,
            label TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE metrics (
            metric_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            analytical_level TEXT NOT NULL,
            default_unit TEXT
        )
        """,
        """
        CREATE TABLE observations (
            observation_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            dataset_snapshot_id TEXT NOT NULL,
            entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            period_id TEXT NOT NULL REFERENCES periods(period_id),
            metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
            value REAL,
            unit TEXT,
            source_ref TEXT REFERENCES sources(source_ref),
            source_locator TEXT,
            period_basis TEXT,
            reporting_scope TEXT,
            validation_status TEXT NOT NULL,
            missing_reason TEXT,
            derivation_method TEXT,
            input_observation_ids_json TEXT NOT NULL,
            review_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            UNIQUE (dataset_snapshot_id, entity_id, period_id, metric_id)
        )
        """,
        """
        CREATE TABLE peer_universes (
            peer_universe_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE peer_universe_members (
            peer_universe_id TEXT NOT NULL REFERENCES peer_universes(peer_universe_id),
            entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            PRIMARY KEY (peer_universe_id, entity_id)
        )
        """,
        """
        CREATE TABLE documents (
            contract_version TEXT NOT NULL,
            document_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            dataset_snapshot_id TEXT NOT NULL,
            source_ref TEXT NOT NULL REFERENCES sources(source_ref),
            document_type TEXT NOT NULL,
            title TEXT NOT NULL,
            publisher TEXT,
            content_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE evidence (
            evidence_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            dataset_snapshot_id TEXT NOT NULL,
            source_ref TEXT NOT NULL REFERENCES sources(source_ref),
            document_id TEXT NOT NULL REFERENCES documents(document_id),
            entity_id TEXT REFERENCES entities(entity_id),
            period_id TEXT REFERENCES periods(period_id),
            metric_id TEXT REFERENCES metrics(metric_id),
            locator TEXT NOT NULL,
            quote TEXT NOT NULL
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)


def _validate_candidate(
    candidate: CanonicalDatasetCandidate,
    accepted_metadata: DatasetSnapshotMetadata,
    raw_descriptor: RawDatasetDescriptor,
    verified_source_artifacts: VerifiedSourceArtifacts | None,
) -> CanonicalDatasetCandidate:
    if accepted_metadata.status is not DatasetSnapshotStatus.ACCEPTED:
        raise ValueError("materialization requires accepted metadata")
    if not _SHA256_PATTERN.fullmatch(raw_descriptor.content_hash):
        raise ValueError("raw source content hash must be an exact SHA-256")
    if candidate.source.content_hash != raw_descriptor.content_hash:
        raise ValueError("canonical source hash does not match raw descriptor")
    source_refs = [item.source_ref for item in candidate.all_sources]
    if len(source_refs) != len(set(source_refs)):
        raise ValueError("canonical source refs must be unique")
    for source in candidate.all_sources:
        tier = getattr(source.source_tier, "value", source.source_tier)
        if not _SHA256_PATTERN.fullmatch(source.content_hash):
            raise ValueError("canonical source content hash must be an exact SHA-256")
        if source.validation_status is QualityStatus.VALID:
            if source.source_type not in _SOURCE_TYPES:
                raise ValueError("accepted canonical source type is unsupported")
            continue
        if tier == "user_supplied" and source.validation_status is QualityStatus.PENDING_VALIDATION:
            continue
        raise ValueError("non-user-supplied canonical sources must be valid before publication")
    accepted_primary_sources = tuple(
        source
        for source in candidate.all_sources
        if source.validation_status is QualityStatus.VALID
        and getattr(source.source_tier, "value", source.source_tier) == "primary"
    )
    if accepted_primary_sources:
        if (
            not isinstance(verified_source_artifacts, VerifiedSourceArtifacts)
            or not verified_source_artifacts.matches(candidate.all_sources)
        ):
            raise ValueError(
                "accepted primary evidence requires bytes verified beneath an explicit evidence root"
            )
    elif verified_source_artifacts is not None and (
        not isinstance(verified_source_artifacts, VerifiedSourceArtifacts)
        or not verified_source_artifacts.matches(candidate.all_sources)
    ):
        raise ValueError("verified primary evidence does not match candidate sources")
    if not candidate.entities or not candidate.periods or not candidate.metrics:
        raise ValueError("accepted canonical snapshot must contain entities, periods, and metrics")
    entity_ids = {item.entity_id for item in candidate.entities}
    period_ids = {item.period_id for item in candidate.periods}
    metric_ids = {item.metric_id for item in candidate.metrics}
    if any(item.dataset_id != accepted_metadata.dataset_id for item in candidate.observations):
        raise ValueError("observation dataset ID does not match snapshot metadata")
    if any(
        item.dataset_snapshot_id != accepted_metadata.dataset_snapshot_id
        for item in candidate.observations
    ):
        raise ValueError("observation snapshot ID does not match snapshot metadata")
    if any(item.entity_id not in entity_ids for item in candidate.observations):
        raise ValueError("observation entity is absent from candidate catalog")
    if any(item.period_id not in period_ids for item in candidate.observations):
        raise ValueError("observation period is absent from candidate catalog")
    if any(item.metric_id not in metric_ids for item in candidate.observations):
        raise ValueError("observation metric is absent from candidate catalog")
    source_by_ref = {item.source_ref: item for item in candidate.all_sources}
    document_ids = [item.document_id for item in candidate.documents]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("document IDs must be unique")
    evidence_ids = [item.evidence_id for item in candidate.evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence IDs must be unique")
    document_id_set = set(document_ids)
    document_sources = {
        document.document_id: document.source_ref
        for document in candidate.documents
    }
    for document in candidate.documents:
        if (
            document.dataset_id != accepted_metadata.dataset_id
            or document.dataset_snapshot_id != accepted_metadata.dataset_snapshot_id
        ):
            raise ValueError("document dataset identity does not match snapshot metadata")
        if document.source_ref not in source_refs:
            raise ValueError("document source does not resolve to the snapshot")
        if document.content_hash != source_by_ref[document.source_ref].content_hash:
            raise ValueError("document content hash does not match its source record")
    for item in candidate.evidence:
        if (
            item.source_ref not in source_refs
            or item.document_id not in document_id_set
        ):
            raise ValueError("evidence source/document does not resolve in the snapshot")
        if item.source_ref != document_sources[item.document_id]:
            raise ValueError("evidence source does not match its document source")
        if item.entity_id is not None and item.entity_id not in entity_ids:
            raise ValueError("evidence entity does not resolve in the snapshot")
        if item.period_id is not None and item.period_id not in period_ids:
            raise ValueError("evidence period does not resolve in the snapshot")
        if item.metric_id is not None and item.metric_id not in metric_ids:
            raise ValueError("evidence metric does not resolve in the snapshot")
    identities = [
        (item.entity_id, item.period_id, item.metric_id)
        for item in candidate.observations
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate canonical observation identity cannot be materialized")
    observation_ids = [item.observation_id for item in candidate.observations]
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("duplicate observation IDs cannot be materialized")
    observation_id_set = set(observation_ids)
    observation_by_id = {item.observation_id: item for item in candidate.observations}
    for item in candidate.observations:
        expected_observation_id = canonical_observation_id(
            accepted_metadata.dataset_snapshot_id,
            item.entity_id,
            item.period_id,
            item.metric_id,
        )
        if item.observation_id != expected_observation_id:
            raise ValueError("observation ID is not derived from final snapshot identity")
        if any(ref not in observation_id_set for ref in item.input_observation_ids):
            raise ValueError("observation lineage reference does not resolve in candidate")
        if item.validation_status is QualityStatus.PENDING_VALIDATION:
            raise ValueError("accepted canonical snapshot cannot contain pending observations")
        if item.validation_status in {QualityStatus.CONFLICTING, QualityStatus.INVALID, QualityStatus.ESTIMATED}:
            raise ValueError("accepted canonical snapshot cannot contain unresolved observations")
        if item.validation_status is QualityStatus.VALID:
            if not item.source_locator or not item.period_basis or not item.reporting_scope:
                raise ValueError("valid observation requires locator, period basis, and reporting scope")
            if item.period_basis not in {"point_in_time", "quarter_only", "ytd", "annual", "ttm"}:
                raise ValueError("valid observation period basis is unsupported")
            if item.reporting_scope not in {"consolidated", "separate", "system"}:
                raise ValueError("valid observation reporting scope is unsupported")
            if item.review is None:
                raise ValueError("valid observation requires explicit source reconciliation review")
            if item.derivation_method is not None:
                if item.source_ref is not None:
                    raise ValueError("derived observation source_ref must be null")
                if item.review.decision != "reproduced_derived_value" or not item.input_observation_ids:
                    raise ValueError("derived observation review must reproduce its formula from inputs")
                for input_id in item.input_observation_ids:
                    source_input = observation_by_id[input_id]
                    if (
                        source_input.validation_status is not QualityStatus.VALID
                        or source_input.value is None
                    ):
                        raise ValueError("derived observation inputs must be valid numeric observations")
            else:
                if item.review.decision != "matched_reported_value" or item.input_observation_ids:
                    raise ValueError("direct observation review must match a reported value")
                source = source_by_ref.get(item.source_ref or "")
                if source is None or source.validation_status is not QualityStatus.VALID:
                    raise ValueError("direct observation source must resolve to a valid source record")
                if getattr(source.source_tier, "value", source.source_tier) not in {"primary", "cross_check"}:
                    raise ValueError("direct observation source tier is not eligible for analysis")
            if not item.review.primary_evidence:
                raise ValueError("valid observation review requires primary evidence")
            review_locators = {reference.locator for reference in item.review.primary_evidence}
            for reference in item.review.primary_evidence:
                review_source = source_by_ref.get(reference.source_ref)
                if (
                    review_source is None
                    or review_source.validation_status is not QualityStatus.VALID
                    or getattr(review_source.source_tier, "value", review_source.source_tier) != "primary"
                    or review_source.source_type not in _SOURCE_TYPES
                ):
                    raise ValueError("review primary evidence does not resolve to a valid primary source")
            if item.derivation_method is None:
                if (item.source_ref, item.source_locator) not in {
                    (reference.source_ref, reference.locator)
                    for reference in item.review.primary_evidence
                }:
                    raise ValueError("direct observation source and locator must match reviewed primary evidence")
            elif item.source_locator not in review_locators:
                raise ValueError("derived observation locator must match reviewed primary evidence")
            if item.derivation_method and not item.input_observation_ids:
                raise ValueError("derived observation requires input lineage")
        elif item.validation_status is QualityStatus.MISSING:
            if item.value is not None or not item.missing_reason:
                raise ValueError("missing observation requires a null value and reason")
    for universe in candidate.peer_universes:
        if not set(universe.entity_ids).issubset(entity_ids):
            raise ValueError("peer universe contains an unknown entity")

    validated_observations: list[CanonicalObservation] = []
    for item in candidate.observations:
        if item.validation_status is QualityStatus.VALID and item.derivation_method is not None:
            receipt = _calculate_derived_receipt(item, observation_by_id)
            if item.calculation_receipt is not None and item.calculation_receipt != receipt:
                raise ValueError("provided derived calculation receipt does not match recomputation")
            validated_observations.append(
                item.model_copy(update={"calculation_receipt": receipt})
            )
        else:
            if item.calculation_receipt is not None:
                raise ValueError("calculation receipt is only allowed on valid derived observations")
            validated_observations.append(item)
    return replace(candidate, observations=tuple(validated_observations))


def _bind_candidate_to_final_snapshot(
    candidate: CanonicalDatasetCandidate,
    accepted_metadata: DatasetSnapshotMetadata,
    raw_descriptor: RawDatasetDescriptor,
) -> tuple[CanonicalDatasetCandidate, DatasetSnapshotMetadata]:
    """Bind all candidate objects to the deterministic complete-content ID."""

    if candidate.metadata.dataset_id != accepted_metadata.dataset_id:
        raise ValueError("candidate dataset ID does not match accepted metadata")
    for observation in candidate.observations:
        if (
            observation.dataset_id != accepted_metadata.dataset_id
            or observation.dataset_snapshot_id != candidate.metadata.dataset_snapshot_id
        ):
            raise ValueError("candidate observation identity does not match candidate metadata")
    for document in candidate.documents:
        if (
            document.dataset_id != accepted_metadata.dataset_id
            or document.dataset_snapshot_id != candidate.metadata.dataset_snapshot_id
        ):
            raise ValueError("candidate document identity does not match candidate metadata")

    provisional_observation_ids = [
        item.observation_id for item in candidate.observations
    ]
    if len(provisional_observation_ids) != len(set(provisional_observation_ids)):
        raise ValueError("candidate observation IDs must be unique before final binding")
    provisional_observation_id_set = set(provisional_observation_ids)
    for observation in candidate.observations:
        if any(
            ref not in provisional_observation_id_set
            for ref in observation.input_observation_ids
        ):
            raise ValueError("candidate observation lineage reference does not resolve")

    manifest_hash = compute_content_manifest_hash(
        sources=candidate.all_sources,
        documents=candidate.documents,
        evidence=candidate.evidence,
        observations=candidate.observations,
        mapping_version=accepted_metadata.mapping_version,
        validation_version=accepted_metadata.validation_version,
    )
    final_snapshot_id = compute_dataset_snapshot_id(
        accepted_metadata.dataset_id,
        raw_descriptor.content_hash,
        accepted_metadata.mapping_version,
        accepted_metadata.validation_version,
        manifest_hash,
    )
    final_metadata = accepted_metadata.model_copy(
        update={
            "dataset_snapshot_id": final_snapshot_id,
            "content_manifest_hash": manifest_hash,
        }
    )
    observation_id_map = {
        item.observation_id: canonical_observation_id(
            final_snapshot_id,
            item.entity_id,
            item.period_id,
            item.metric_id,
        )
        for item in candidate.observations
    }
    final_observation_ids = list(observation_id_map.values())
    if len(final_observation_ids) != len(set(final_observation_ids)):
        raise ValueError("duplicate final observation IDs cannot be materialized")
    bound_candidate = replace(
        candidate,
        metadata=final_metadata,
        observations=tuple(
            item.model_copy(
                update={
                    "dataset_id": final_metadata.dataset_id,
                    "dataset_snapshot_id": final_snapshot_id,
                    "observation_id": observation_id_map[item.observation_id],
                    "input_observation_ids": tuple(
                        observation_id_map[ref]
                        for ref in item.input_observation_ids
                    ),
                    "calculation_receipt": (
                        item.calculation_receipt.model_copy(
                            update={
                                "ordered_inputs": tuple(
                                    input_receipt.model_copy(
                                        update={
                                            "observation_id": observation_id_map[
                                                input_receipt.observation_id
                                            ]
                                        }
                                    )
                                    for input_receipt in item.calculation_receipt.ordered_inputs
                                )
                            }
                        )
                        if item.calculation_receipt is not None
                        else None
                    ),
                }
            )
            for item in candidate.observations
        ),
        documents=tuple(
            item.model_copy(
                update={
                    "dataset_id": final_metadata.dataset_id,
                    "dataset_snapshot_id": final_snapshot_id,
                }
            )
            for item in candidate.documents
        ),
    )
    return bound_candidate, final_metadata


def _insert_observation(connection: sqlite3.Connection, item: CanonicalObservation) -> None:
    metadata = dict(item.metadata)
    if CANONICAL_CALCULATION_RECEIPT_METADATA_KEY in metadata:
        raise ValueError("observation metadata uses a reserved calculation receipt key")
    if item.calculation_receipt is not None:
        metadata[CANONICAL_CALCULATION_RECEIPT_METADATA_KEY] = item.calculation_receipt.model_dump(mode="json")
    connection.execute(
        """
        INSERT INTO observations (
            observation_id, dataset_id, dataset_snapshot_id, entity_id,
            period_id, metric_id, value, unit, source_ref, source_locator,
            period_basis, reporting_scope, validation_status, missing_reason,
            derivation_method, input_observation_ids_json, review_json,
            metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.observation_id,
            item.dataset_id,
            item.dataset_snapshot_id,
            item.entity_id,
            item.period_id,
            item.metric_id,
            item.value,
            item.unit,
            item.source_ref,
            item.source_locator,
            item.period_basis,
            item.reporting_scope,
            _enum_value(item.validation_status),
            item.missing_reason,
            item.derivation_method,
            _json(list(item.input_observation_ids)),
            _json(item.review.model_dump(mode="json") if item.review is not None else {}),
            _json(metadata),
        ),
    )


def materialize_canonical_snapshot(
    db_path: Path,
    candidate: CanonicalDatasetCandidate,
    raw_descriptor: RawDatasetDescriptor,
    validation_report: OnboardingValidationReport,
    *,
    verified_source_artifacts: VerifiedSourceArtifacts | None = None,
) -> DatasetSnapshotMetadata:
    """Promote and atomically materialize one accepted canonical snapshot."""

    validate_snapshot_metadata(raw_descriptor, candidate.metadata)
    if candidate.metadata.status is not DatasetSnapshotStatus.CANDIDATE:
        raise ValueError("only CANDIDATE snapshot metadata can be materialized")
    if validation_report.dataset_id != candidate.metadata.dataset_id:
        raise ValueError("validation report dataset ID does not match snapshot metadata")
    if validation_report.candidate_snapshot_id != candidate.metadata.dataset_snapshot_id:
        raise ValueError("validation report snapshot ID does not match snapshot metadata")
    if validation_report.status.value != "VALID":
        raise ValueError("only a VALID structural validation report can materialize a snapshot")
    reconciliation_metadata = candidate.metadata.model_copy(
        update={"status": DatasetSnapshotStatus.ACCEPTED}
    )
    candidate = _validate_candidate(
        candidate,
        reconciliation_metadata,
        raw_descriptor,
        verified_source_artifacts,
    )
    accepted_metadata = promote_snapshot_metadata(
        raw_descriptor,
        candidate.metadata,
        validation_report,
        source_reconciled=True,
    )
    candidate, accepted_metadata = _bind_candidate_to_final_snapshot(
        candidate,
        accepted_metadata,
        raw_descriptor,
    )
    candidate = _validate_candidate(
        candidate,
        accepted_metadata,
        raw_descriptor,
        verified_source_artifacts,
    )
    target = Path(db_path)
    target_existed_before = target.exists()
    if target_existed_before and target.stat().st_size > 0:
        raise ValueError("canonical snapshot target already exists and is immutable")
    target.parent.mkdir(parents=True, exist_ok=True)

    connection: sqlite3.Connection | None = None
    operation_failed = False
    try:
        connection = sqlite3.connect(target)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN")
        _create_schema(connection)
        connection.execute(
            """
            INSERT INTO dataset_metadata (
                dataset_id, dataset_snapshot_id, contract_version, schema_version,
                status, created_at, source_content_hash, mapping_version,
                validation_version, content_manifest_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                accepted_metadata.dataset_id,
                accepted_metadata.dataset_snapshot_id,
                accepted_metadata.contract_version,
                CANONICAL_SNAPSHOT_SCHEMA_VERSION,
                _enum_value(accepted_metadata.status),
                accepted_metadata.created_at.isoformat(),
                accepted_metadata.source_content_hash,
                accepted_metadata.mapping_version,
                accepted_metadata.validation_version,
                accepted_metadata.content_manifest_hash,
            ),
        )
        for source in candidate.all_sources:
            connection.execute(
                """
                INSERT INTO sources (
                    source_ref, source_type, source_tier, source_url, publisher,
                    retrieved_at, content_hash, validation_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.source_ref,
                    source.source_type,
                    _enum_value(source.source_tier),
                    source.source_url,
                    source.publisher,
                    source.retrieved_at,
                    source.content_hash,
                    _enum_value(source.validation_status),
                    source.notes,
                ),
            )
        for entity in candidate.entities:
            connection.execute(
                "INSERT INTO entities VALUES (?, ?, ?, ?)",
                (
                    entity.entity_id,
                    _enum_value(entity.entity_type),
                    entity.display_name,
                    _json(entity.attributes),
                ),
            )
        for period in candidate.periods:
            connection.execute(
                "INSERT INTO periods VALUES (?, ?)",
                (period.period_id, period.label),
            )
        for metric in candidate.metrics:
            connection.execute(
                "INSERT INTO metrics VALUES (?, ?, ?, ?)",
                (
                    metric.metric_id,
                    metric.display_name,
                    _enum_value(metric.analytical_level),
                    metric.default_unit,
                ),
            )
        for observation in candidate.observations:
            _insert_observation(connection, observation)
        for universe in candidate.peer_universes:
            connection.execute(
                "INSERT INTO peer_universes VALUES (?, ?)",
                (universe.peer_universe_id, universe.display_name),
            )
            connection.executemany(
                "INSERT INTO peer_universe_members VALUES (?, ?)",
                ((universe.peer_universe_id, entity_id) for entity_id in universe.entity_ids),
            )
        for document in candidate.documents:
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document.contract_version,
                    document.document_id,
                    document.dataset_id,
                    document.dataset_snapshot_id,
                    document.source_ref,
                    document.document_type,
                    document.title,
                    document.publisher,
                    document.content_hash,
                    _json(document.metadata),
                ),
            )
        for item in candidate.evidence:
            connection.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.evidence_id,
                    accepted_metadata.dataset_id,
                    accepted_metadata.dataset_snapshot_id,
                    item.source_ref,
                    item.document_id,
                    item.entity_id,
                    item.period_id,
                    item.metric_id,
                    item.locator,
                    item.quote,
                ),
            )
        connection.commit()
    except Exception:
        operation_failed = True
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
        if operation_failed and not target_existed_before and target.exists():
            try:
                target.unlink()
            except OSError:
                pass
    return accepted_metadata
