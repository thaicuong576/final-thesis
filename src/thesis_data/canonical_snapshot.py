"""Portable SQLite materialization for the generic canonical dataset contract."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sqlite3

from .dataset_contract import CanonicalObservation, DatasetEvidence
from .evidence_contract import DatasetDocument
from .onboarding_contract import (
    DatasetSnapshotStatus,
    DatasetSnapshotMetadata,
    OnboardingValidationReport,
    RawDatasetDescriptor,
    compute_content_manifest_hash,
    compute_dataset_snapshot_id,
    promote_snapshot_metadata,
)
from .onboarding_validation import CanonicalDatasetCandidate
from .schema import QualityStatus


CANONICAL_SNAPSHOT_SCHEMA_VERSION = "canonical-snapshot-v2"


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
            validation_status TEXT NOT NULL,
            missing_reason TEXT,
            derivation_method TEXT,
            input_observation_ids_json TEXT NOT NULL,
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
) -> None:
    if accepted_metadata.status is not DatasetSnapshotStatus.ACCEPTED:
        raise ValueError("materialization requires accepted metadata")
    if candidate.source.content_hash != raw_descriptor.content_hash:
        raise ValueError("canonical source hash does not match raw descriptor")
    source_refs = [item.source_ref for item in candidate.all_sources]
    if len(source_refs) != len(set(source_refs)):
        raise ValueError("canonical source refs must be unique")
    if any(item.validation_status is not QualityStatus.VALID for item in candidate.all_sources):
        raise ValueError("every canonical source must be valid before publication")
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
    if any(item.source_ref != candidate.source.source_ref for item in candidate.observations):
        raise ValueError("every CSV observation must use the canonical CSV source")
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
    for universe in candidate.peer_universes:
        if not set(universe.entity_ids).issubset(entity_ids):
            raise ValueError("peer universe contains an unknown entity")


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

    manifest_hash = compute_content_manifest_hash(
        sources=candidate.all_sources,
        documents=candidate.documents,
        evidence=candidate.evidence,
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
    bound_candidate = replace(
        candidate,
        metadata=final_metadata,
        observations=tuple(
            item.model_copy(
                update={
                    "dataset_id": final_metadata.dataset_id,
                    "dataset_snapshot_id": final_snapshot_id,
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
    connection.execute(
        """
        INSERT INTO observations (
            observation_id, dataset_id, dataset_snapshot_id, entity_id,
            period_id, metric_id, value, unit, source_ref, validation_status,
            missing_reason, derivation_method, input_observation_ids_json,
            metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            _enum_value(item.validation_status),
            item.missing_reason,
            item.derivation_method,
            _json(list(item.input_observation_ids)),
            _json(item.metadata),
        ),
    )


def materialize_canonical_snapshot(
    db_path: Path,
    candidate: CanonicalDatasetCandidate,
    raw_descriptor: RawDatasetDescriptor,
    validation_report: OnboardingValidationReport,
) -> DatasetSnapshotMetadata:
    """Promote and atomically materialize one accepted canonical snapshot."""

    accepted_metadata = promote_snapshot_metadata(
        raw_descriptor,
        candidate.metadata,
        validation_report,
    )
    candidate, accepted_metadata = _bind_candidate_to_final_snapshot(
        candidate,
        accepted_metadata,
        raw_descriptor,
    )
    _validate_candidate(candidate, accepted_metadata, raw_descriptor)
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
