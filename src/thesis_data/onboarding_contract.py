"""Phase 0A contracts for explicit dataset onboarding.

This module defines the boundary before a raw source becomes a canonical
snapshot.  It intentionally contains no CSV parser, SQLite access, Gold
knowledge, or LLM mapping approval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .dataset_contract import AnalyticalLevel


ONBOARDING_CONTRACT_VERSION = "onboarding-contract-v1"


class DatasetSnapshotStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    INVALID = "invalid"


class OnboardingValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"


class OnboardingIssueCode(StrEnum):
    ENTITY_MAPPING_INVALID = "ENTITY_MAPPING_INVALID"
    PERIOD_INVALID = "PERIOD_INVALID"
    METRIC_UNSUPPORTED = "METRIC_UNSUPPORTED"
    VALUE_INVALID = "VALUE_INVALID"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    SOURCE_REQUIRED = "SOURCE_REQUIRED"
    EMPTY_REQUIRED_FIELD = "EMPTY_REQUIRED_FIELD"
    MAPPING_INVALID = "MAPPING_INVALID"


def _require_text(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value


class RawDatasetDescriptor(BaseModel):
    """Identity of an immutable raw input without exposing a local path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_dataset_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    original_name: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    ingested_at: datetime

    @model_validator(mode="after")
    def validate_identity_fields(self) -> "RawDatasetDescriptor":
        for field_name in ("raw_dataset_id", "source_type", "original_name", "content_hash"):
            _require_text(getattr(self, field_name), field_name)
        if "/" in self.original_name or "\\" in self.original_name:
            raise ValueError("original_name must not be a physical path")
        return self


class DatasetSnapshotMetadata(BaseModel):
    """Immutable metadata binding a candidate/accepted snapshot to its inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = ONBOARDING_CONTRACT_VERSION
    dataset_id: str = Field(min_length=1)
    dataset_snapshot_id: str = Field(min_length=1)
    status: DatasetSnapshotStatus
    created_at: datetime
    source_content_hash: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    validation_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_metadata(self) -> "DatasetSnapshotMetadata":
        if self.contract_version != ONBOARDING_CONTRACT_VERSION:
            raise ValueError("unsupported onboarding contract version")
        for field_name in (
            "dataset_id",
            "dataset_snapshot_id",
            "source_content_hash",
            "mapping_version",
            "validation_version",
        ):
            _require_text(getattr(self, field_name), field_name)
        return self


class StagedField(BaseModel):
    """Preview-only field inference; it does not establish financial meaning."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1)
    inferred_data_type: str = Field(min_length=1)
    sample_values: tuple[Any, ...] = Field(default_factory=tuple)
    null_count: int = Field(ge=0)


class MetricDefinition(BaseModel):
    """Registry definition, distinct from a metric available in one snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    analytical_level: AnalyticalLevel
    default_unit: str = Field(min_length=1)
    description: str = Field(min_length=1)


class MetricRegistry(BaseModel):
    """Small explicit registry used to validate mappings before normalization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = ONBOARDING_CONTRACT_VERSION
    definitions: tuple[MetricDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_definitions(self) -> "MetricRegistry":
        if self.contract_version != ONBOARDING_CONTRACT_VERSION:
            raise ValueError("unsupported onboarding contract version")
        metric_ids = [item.metric_id for item in self.definitions]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("metric registry IDs must be unique")
        return self

    def get(self, metric_id: str) -> MetricDefinition | None:
        return next(
            (item for item in self.definitions if item.metric_id == metric_id),
            None,
        )


class FieldMetricMapping(BaseModel):
    """One explicit raw-column to canonical-metric mapping."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_field: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    analytical_level: AnalyticalLevel


class FieldMappingSpec(BaseModel):
    """Explicit field mapping; it is never inferred or approved by an LLM."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_field: str = Field(min_length=1)
    period_field: str = Field(min_length=1)
    metric_mappings: tuple[FieldMetricMapping, ...] = Field(min_length=1)
    source_ref_field: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_mapping_identity(self) -> "FieldMappingSpec":
        fields = [item.raw_field for item in self.metric_mappings]
        metric_ids = [item.metric_id for item in self.metric_mappings]
        if len(fields) != len(set(fields)):
            raise ValueError("mapped raw fields must be unique")
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("mapped metric IDs must be unique")
        reserved = {self.entity_field, self.period_field}
        if self.source_ref_field:
            reserved.add(self.source_ref_field)
        if reserved.intersection(fields):
            raise ValueError("identity/source fields cannot also be metric fields")
        return self


class OnboardingValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: OnboardingIssueCode
    message: str = Field(min_length=1)
    row_number: int | None = Field(default=None, ge=1)
    field_name: str | None = Field(default=None, min_length=1)
    metric_id: str | None = Field(default=None, min_length=1)


class OnboardingValidationReport(BaseModel):
    """Deterministic publication decision for one candidate snapshot."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str = ONBOARDING_CONTRACT_VERSION
    dataset_id: str = Field(min_length=1)
    candidate_snapshot_id: str = Field(min_length=1)
    status: OnboardingValidationStatus
    issues: tuple[OnboardingValidationIssue, ...] = Field(default_factory=tuple)
    row_count: int = Field(ge=0)
    accepted_observation_count: int = Field(ge=0)
    missing_observation_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report_state(self) -> "OnboardingValidationReport":
        if self.contract_version != ONBOARDING_CONTRACT_VERSION:
            raise ValueError("unsupported onboarding contract version")
        if self.status is OnboardingValidationStatus.VALID and self.issues:
            raise ValueError("VALID onboarding report cannot contain issues")
        if self.status is OnboardingValidationStatus.INVALID and not self.issues:
            raise ValueError("INVALID onboarding report requires issues")
        return self


def validate_field_mapping(
    mapping: FieldMappingSpec,
    available_fields: Sequence[str],
    registry: MetricRegistry,
) -> tuple[OnboardingValidationIssue, ...]:
    """Validate explicit mapping metadata without reading raw rows or storage."""

    available = set(available_fields)
    issues: list[OnboardingValidationIssue] = []

    for field_name, code in (
        (mapping.entity_field, OnboardingIssueCode.ENTITY_MAPPING_INVALID),
        (mapping.period_field, OnboardingIssueCode.PERIOD_INVALID),
    ):
        if field_name not in available:
            issues.append(
                OnboardingValidationIssue(
                    code=code,
                    message=f"required raw field is unavailable: {field_name}",
                    field_name=field_name,
                )
            )
    if mapping.source_ref_field and mapping.source_ref_field not in available:
        issues.append(
            OnboardingValidationIssue(
                code=OnboardingIssueCode.SOURCE_REQUIRED,
                message=f"source field is unavailable: {mapping.source_ref_field}",
                field_name=mapping.source_ref_field,
            )
        )

    for item in mapping.metric_mappings:
        if item.raw_field not in available:
            issues.append(
                OnboardingValidationIssue(
                    code=OnboardingIssueCode.MAPPING_INVALID,
                    message=f"mapped raw field is unavailable: {item.raw_field}",
                    field_name=item.raw_field,
                    metric_id=item.metric_id,
                )
            )
        definition = registry.get(item.metric_id)
        if definition is None:
            issues.append(
                OnboardingValidationIssue(
                    code=OnboardingIssueCode.METRIC_UNSUPPORTED,
                    message=f"metric is not present in the registry: {item.metric_id}",
                    field_name=item.raw_field,
                    metric_id=item.metric_id,
                )
            )
            continue
        if item.unit != definition.default_unit:
            issues.append(
                OnboardingValidationIssue(
                    code=OnboardingIssueCode.UNIT_MISMATCH,
                    message=(
                        f"mapping unit {item.unit!r} does not match registry unit "
                        f"{definition.default_unit!r}"
                    ),
                    field_name=item.raw_field,
                    metric_id=item.metric_id,
                )
            )
        if item.analytical_level is not definition.analytical_level:
            issues.append(
                OnboardingValidationIssue(
                    code=OnboardingIssueCode.MAPPING_INVALID,
                    message="mapping analytical level does not match registry definition",
                    field_name=item.raw_field,
                    metric_id=item.metric_id,
                )
            )
    return tuple(issues)


def compute_dataset_snapshot_id(
    dataset_id: str,
    source_content_hash: str,
    mapping_version: str,
    validation_version: str,
) -> str:
    """Derive a stable snapshot identity from source and accepted transformations."""

    parts = {
        "dataset_id": _require_text(dataset_id, "dataset_id"),
        "source_content_hash": _require_text(source_content_hash, "source_content_hash"),
        "mapping_version": _require_text(mapping_version, "mapping_version"),
        "validation_version": _require_text(validation_version, "validation_version"),
    }
    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"snapshot-{sha256(encoded).hexdigest()}"


def compute_field_mapping_version(mapping: FieldMappingSpec) -> str:
    """Create a stable version identity for one accepted explicit mapping."""

    encoded = json.dumps(
        mapping.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"mapping-{sha256(encoded).hexdigest()}"


def build_snapshot_metadata(
    dataset_id: str,
    raw_descriptor: RawDatasetDescriptor,
    *,
    mapping_version: str,
    validation_version: str,
    status: DatasetSnapshotStatus = DatasetSnapshotStatus.CANDIDATE,
    created_at: datetime | None = None,
) -> DatasetSnapshotMetadata:
    """Create metadata whose identity is bound to immutable raw content."""

    snapshot_id = compute_dataset_snapshot_id(
        dataset_id,
        raw_descriptor.content_hash,
        mapping_version,
        validation_version,
    )
    return DatasetSnapshotMetadata(
        dataset_id=dataset_id,
        dataset_snapshot_id=snapshot_id,
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
        source_content_hash=raw_descriptor.content_hash,
        mapping_version=mapping_version,
        validation_version=validation_version,
    )


def validate_snapshot_metadata(
    raw_descriptor: RawDatasetDescriptor,
    metadata: DatasetSnapshotMetadata,
) -> None:
    """Fail closed if metadata does not describe the exact source/version tuple."""

    if metadata.source_content_hash != raw_descriptor.content_hash:
        raise ValueError("snapshot source content hash does not match raw descriptor")
    expected_id = compute_dataset_snapshot_id(
        metadata.dataset_id,
        raw_descriptor.content_hash,
        metadata.mapping_version,
        metadata.validation_version,
    )
    if metadata.dataset_snapshot_id != expected_id:
        raise ValueError("snapshot ID does not match source and transformation versions")


def demo_metric_registry() -> MetricRegistry:
    """Return a small definition registry, not a claim of dataset availability."""

    return MetricRegistry(
        definitions=(
            MetricDefinition(
                metric_id="company.roa",
                display_name="Return on assets",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Profitability relative to company assets.",
            ),
            MetricDefinition(
                metric_id="company.roe",
                display_name="Return on equity",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Profitability relative to company equity.",
            ),
            MetricDefinition(
                metric_id="company.npl",
                display_name="Non-performing loan ratio",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Non-performing loans relative to the defined loan base.",
            ),
            MetricDefinition(
                metric_id="sector.credit_growth",
                display_name="Sector credit growth",
                analytical_level=AnalyticalLevel.SECTOR,
                default_unit="percent",
                description="Credit growth for a declared sector universe.",
            ),
            MetricDefinition(
                metric_id="macro.policy_rate",
                display_name="Policy rate",
                analytical_level=AnalyticalLevel.MACRO,
                default_unit="percent_per_annum",
                description="An explicitly defined macro policy-rate observation.",
            ),
        )
    )
