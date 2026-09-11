"""Versioned, application-level financial dataset contracts.

These contracts deliberately do not encode SQLite tables, ticker identity, or
Gold-specific storage.  A Gold snapshot is one provider implementation of this
generic application boundary.
"""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import QualityStatus, SourceTier


DATASET_CONTRACT_VERSION = "dataset-contract-v1"


class DatasetEntityType(StrEnum):
    COMPANY = "company"
    MACRO = "macro"
    SECTOR = "sector"
    OTHER = "other"


class AnalyticalLevel(StrEnum):
    COMPANY = "company"
    SECTOR = "sector"
    MACRO = "macro"
    OTHER = "other"


class DatasetRef(BaseModel):
    """Immutable identity of the dataset used by one analysis run."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    dataset_snapshot_id: str = Field(min_length=1)


class DatasetEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(min_length=1)
    entity_type: DatasetEntityType
    display_name: str = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class DatasetPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class DatasetMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    analytical_level: AnalyticalLevel
    default_unit: str | None = Field(default=None, min_length=1)


class DatasetSource(BaseModel):
    """Safe source metadata; physical local paths are intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_tier: SourceTier | str
    source_url: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    validation_status: QualityStatus
    notes: str | None = None


class DatasetEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    entity_id: str | None = Field(default=None, min_length=1)
    period_id: str | None = Field(default=None, min_length=1)
    metric_id: str | None = Field(default=None, min_length=1)
    locator: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class CanonicalObservation(BaseModel):
    """One value or explicit missing state in an application dataset."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_snapshot_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    value: float | None = None
    unit: str | None = Field(default=None, min_length=1)
    source_ref: str | None = Field(default=None, min_length=1)
    validation_status: QualityStatus
    missing_reason: str | None = None
    derivation_method: str | None = Field(default=None, min_length=1)
    input_observation_ids: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_value_state(self) -> "CanonicalObservation":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("canonical observation value must be finite")
        if len(self.input_observation_ids) != len(set(self.input_observation_ids)):
            raise ValueError("input observation IDs must be unique")
        if any(not item.strip() for item in self.input_observation_ids):
            raise ValueError("input observation IDs must be non-empty")
        if self.validation_status is QualityStatus.VALID:
            has_source_provenance = self.source_ref not in (None, "")
            has_derivation_provenance = bool(
                self.derivation_method and self.input_observation_ids
            )
            if has_source_provenance and (
                self.derivation_method is not None or self.input_observation_ids
            ):
                raise ValueError(
                    "valid canonical observation must use source or derivation provenance"
                )
            if not has_source_provenance and not has_derivation_provenance:
                raise ValueError(
                    "valid canonical observation requires source or derivation provenance"
                )
            missing = {
                name: value
                for name, value in (("value", self.value), ("unit", self.unit))
                if value in (None, "")
            }
            if missing:
                raise ValueError(
                    "valid canonical observation missing: " + ",".join(sorted(missing))
                )
        elif self.validation_status is QualityStatus.MISSING:
            if self.value is not None:
                raise ValueError("missing canonical observation cannot contain a value")
            if not self.missing_reason:
                raise ValueError("missing canonical observation requires missing_reason")
        elif self.value is None and not self.missing_reason:
            raise ValueError("null non-valid canonical observation requires missing_reason")
        return self


class SupportedOperation(StrEnum):
    GET_METRIC = "get_metric"
    GET_ENTITY_METRICS = "get_entity_metrics"
    GET_PEER_BENCHMARK = "get_peer_benchmark"
    GET_EVIDENCE = "get_evidence"
    GET_SOURCE = "get_source"
    GET_MACRO_OBSERVATION = "get_macro_observation"
    RESOLVE_OBSERVATION = "resolve_observation"


class PeerUniverse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peer_universe_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    entity_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_entities(self) -> "PeerUniverse":
        if len(set(self.entity_ids)) != len(self.entity_ids):
            raise ValueError("peer universe entity IDs must be unique")
        return self

    def effective_entity_ids(self, requested_entity_ids: Sequence[str] | None = None) -> tuple[str, ...]:
        """Resolve an optional explicit subset without silently widening scope."""

        requested = tuple(requested_entity_ids or ())
        if len(requested) != len(set(requested)):
            raise ValueError("requested peer entity IDs must be unique")
        if not set(requested).issubset(self.entity_ids):
            raise ValueError("requested peer entity is outside the peer universe")
        return tuple(sorted(requested or self.entity_ids))


class DatasetCapabilityCatalog(BaseModel):
    """Authoritative capabilities discovered from one dataset snapshot."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str = DATASET_CONTRACT_VERSION
    dataset_ref: DatasetRef
    entities: tuple[DatasetEntity, ...] = Field(min_length=1)
    periods: tuple[DatasetPeriod, ...] = Field(min_length=1)
    metrics: tuple[DatasetMetric, ...] = Field(min_length=1)
    peer_universes: tuple[PeerUniverse, ...] = Field(default_factory=tuple)
    supported_operations: tuple[SupportedOperation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_catalog(self) -> "DatasetCapabilityCatalog":
        if self.contract_version != DATASET_CONTRACT_VERSION:
            raise ValueError("unsupported dataset contract version")
        for field_name, values, identity in (
            ("entities", self.entities, "entity_id"),
            ("periods", self.periods, "period_id"),
            ("metrics", self.metrics, "metric_id"),
            ("peer_universes", self.peer_universes, "peer_universe_id"),
        ):
            ids = [getattr(item, identity) for item in values]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {field_name} IDs")
        operations = list(self.supported_operations)
        if len(operations) != len(set(operations)):
            raise ValueError("supported operations must be unique")
        entity_ids = {item.entity_id for item in self.entities}
        for universe in self.peer_universes:
            if not set(universe.entity_ids).issubset(entity_ids):
                raise ValueError(
                    f"peer universe contains unsupported entity: {universe.peer_universe_id}"
                )
        return self

    @property
    def entity_ids(self) -> frozenset[str]:
        return frozenset(item.entity_id for item in self.entities)

    @property
    def period_ids(self) -> frozenset[str]:
        return frozenset(item.period_id for item in self.periods)

    @property
    def metric_ids(self) -> frozenset[str]:
        return frozenset(item.metric_id for item in self.metrics)

    @property
    def macro_metric_ids(self) -> frozenset[str]:
        return frozenset(
            item.metric_id
            for item in self.metrics
            if item.analytical_level is AnalyticalLevel.MACRO
        )

    def peer_universe(self, universe_id: str) -> PeerUniverse | None:
        return next(
            (item for item in self.peer_universes if item.peer_universe_id == universe_id),
            None,
        )
