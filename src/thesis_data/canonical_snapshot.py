"""Portable SQLite materialization for the generic canonical dataset contract."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from .dataset_contract import CanonicalObservation
from .onboarding_contract import (
    DatasetSnapshotStatus,
    DatasetSnapshotMetadata,
    OnboardingValidationReport,
    RawDatasetDescriptor,
    promote_snapshot_metadata,
)
from .onboarding_validation import CanonicalDatasetCandidate
from .schema import QualityStatus


CANONICAL_SNAPSHOT_SCHEMA_VERSION = "canonical-snapshot-v1"


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
    if candidate.source.validation_status is not QualityStatus.VALID:
        raise ValueError("canonical source must be valid before publication")
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
    _validate_candidate(candidate, accepted_metadata, raw_descriptor)
    target = Path(db_path)
    if target.exists() and target.stat().st_size > 0:
        raise ValueError("canonical snapshot target already exists and is immutable")
    target.parent.mkdir(parents=True, exist_ok=True)

    connection: sqlite3.Connection | None = None
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
                validation_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        source = candidate.source
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
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
    return accepted_metadata
