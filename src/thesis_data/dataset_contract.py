"""Versioned, application-level financial dataset contracts.

These contracts deliberately do not encode SQLite tables, ticker identity, or
Gold-specific storage.  A Gold snapshot is one provider implementation of this
generic application boundary.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
import math
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .schema import QualityStatus, SourceTier


DATASET_CONTRACT_VERSION = "dataset-contract-v1"


def canonical_observation_id(
    dataset_snapshot_id: str,
    entity_id: str,
    period_id: str,
    metric_id: str,
) -> str:
    """Derive one observation identity from the final snapshot and cell key."""

    identity = {
        "dataset_snapshot_id": dataset_snapshot_id,
        "entity_id": entity_id,
        "period_id": period_id,
        "metric_id": metric_id,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"observation-{sha256(encoded).hexdigest()}"


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
    document_id: str | None = Field(default=None, min_length=1)
    entity_id: str | None = Field(default=None, min_length=1)
    period_id: str | None = Field(default=None, min_length=1)
    metric_id: str | None = Field(default=None, min_length=1)
    locator: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class ObservationEvidenceRef(BaseModel):
    """One exact source location used to reconcile an observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_ref: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class ObservationReview(BaseModel):
    """Human decision that ties one value to primary evidence or its inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
    decision: Literal["matched_reported_value", "reproduced_derived_value"]
    primary_evidence: tuple[ObservationEvidenceRef, ...] = Field(min_length=1)
    resolution_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_refs(self) -> "ObservationReview":
        identities = [(item.source_ref, item.locator) for item in self.primary_evidence]
        if len(identities) != len(set(identities)):
            raise ValueError("review primary evidence references must be unique")
        try:
            datetime.fromisoformat(self.reviewed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("reviewed_at must be an ISO date-time") from exc
        return self


class CalculationInputReceipt(BaseModel):
    """One ordered, accepted input captured by a derived calculation receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    value: Decimal
    unit: str = Field(min_length=1)
    period_basis: str = Field(min_length=1)
    reporting_scope: str = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("calculation input value must be finite")
        return value


class DerivedCalculationReceipt(BaseModel):
    """Auditable result of deterministic arithmetic at snapshot promotion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    formula_version: str = Field(min_length=1)
    ordered_inputs: tuple[CalculationInputReceipt, ...] = Field(min_length=1)
    calculated_output: Decimal
    candidate_output: Decimal
    unit: str = Field(min_length=1)
    tolerance: Decimal = Field(ge=Decimal("0"))
    absolute_difference: Decimal = Field(ge=Decimal("0"))
    result: Literal["passed"]

    @field_validator("calculated_output", "candidate_output", "tolerance", "absolute_difference")
    @classmethod
    def values_must_be_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("calculation receipt values must be finite")
        return value

    @model_validator(mode="after")
    def difference_must_match_and_pass(self) -> "DerivedCalculationReceipt":
        expected_difference = abs(self.candidate_output - self.calculated_output)
        if self.absolute_difference != expected_difference:
            raise ValueError("calculation receipt difference does not match its outputs")
        if self.absolute_difference > self.tolerance:
            raise ValueError("calculation receipt exceeds its tolerance")
        return self


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
    source_locator: str | None = Field(default=None, min_length=1)
    period_basis: str | None = Field(default=None, min_length=1)
    reporting_scope: str | None = Field(default=None, min_length=1)
    review: ObservationReview | None = None
    validation_status: QualityStatus
    missing_reason: str | None = None
    derivation_method: str | None = Field(default=None, min_length=1)
    input_observation_ids: tuple[str, ...] = Field(default_factory=tuple)
    calculation_receipt: DerivedCalculationReceipt | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_value_state(self) -> "CanonicalObservation":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("canonical observation value must be finite")
        if len(self.input_observation_ids) != len(set(self.input_observation_ids)):
            raise ValueError("input observation IDs must be unique")
        if any(not item.strip() for item in self.input_observation_ids):
            raise ValueError("input observation IDs must be non-empty")
        if self.calculation_receipt is not None:
            if self.derivation_method is None:
                raise ValueError("direct observation cannot carry a derived calculation receipt")
            if self.calculation_receipt.formula_version != self.derivation_method:
                raise ValueError("calculation receipt formula version does not match observation")
            if tuple(item.observation_id for item in self.calculation_receipt.ordered_inputs) != self.input_observation_ids:
                raise ValueError("calculation receipt inputs do not match observation lineage")
            if self.value is None or self.calculation_receipt.candidate_output != Decimal(str(self.value)):
                raise ValueError("calculation receipt output does not match observation value")
            if self.unit != self.calculation_receipt.unit:
                raise ValueError("calculation receipt unit does not match observation")
        if self.validation_status is QualityStatus.VALID:
            has_source_provenance = self.source_ref not in (None, "")
            has_derivation_provenance = bool(
                self.derivation_method and self.input_observation_ids
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
    source_refs: tuple[str, ...] = Field(default_factory=tuple)
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
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("source refs must be unique")
        if any(not item.strip() for item in self.source_refs):
            raise ValueError("source refs must be non-empty")
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
