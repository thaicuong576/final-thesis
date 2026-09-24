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
CONTENT_MANIFEST_VERSION = "content-manifest-v1"


class DatasetSnapshotStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    INVALID = "invalid"


class OnboardingValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"


class OnboardingIssueSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


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


def compute_onboarding_issue_id(
    code: OnboardingIssueCode | str,
    *,
    row_number: int | None = None,
    field_name: str | None = None,
    metric_id: str | None = None,
) -> str:
    """Derive a stable issue identity from deterministic validation context."""

    code_value = code.value if isinstance(code, OnboardingIssueCode) else str(code)
    payload = {
        "code": code_value,
        "row_number": row_number,
        "field_name": field_name,
        "metric_id": metric_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"onboarding-issue-{sha256(encoded).hexdigest()}"


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
    content_manifest_hash: str | None = Field(default=None, min_length=1)

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
        if self.content_manifest_hash is not None:
            _require_text(self.content_manifest_hash, "content_manifest_hash")
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
        identity_fields = [self.entity_field, self.period_field]
        if self.source_ref_field:
            identity_fields.append(self.source_ref_field)
        if len(identity_fields) != len(set(identity_fields)):
            raise ValueError("identity/source fields must be distinct")
        reserved = set(identity_fields)
        if reserved.intersection(fields):
            raise ValueError("identity/source fields cannot also be metric fields")
        return self


class OnboardingValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str | None = Field(default=None, min_length=1)
    code: OnboardingIssueCode
    severity: OnboardingIssueSeverity = OnboardingIssueSeverity.ERROR
    message: str = Field(min_length=1)
    row_number: int | None = Field(default=None, ge=1)
    field_name: str | None = Field(default=None, min_length=1)
    metric_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_issue_identity(self) -> "OnboardingValidationIssue":
        expected_id = compute_onboarding_issue_id(
            self.code,
            row_number=self.row_number,
            field_name=self.field_name,
            metric_id=self.metric_id,
        )
        if self.issue_id is None:
            self.issue_id = expected_id
        elif self.issue_id != expected_id:
            raise ValueError("issue_id must match deterministic validation context")
        return self


class OnboardingValidationReport(BaseModel):
    """Deterministic structural validation result for one candidate snapshot.

    A VALID report means the candidate is structurally well-formed. It does not
    mean its values have been reconciled to primary sources or accepted for
    analysis.
    """

    model_config = ConfigDict(extra="forbid")

    contract_version: str = ONBOARDING_CONTRACT_VERSION
    dataset_id: str = Field(min_length=1)
    candidate_snapshot_id: str = Field(min_length=1)
    status: OnboardingValidationStatus
    issues: tuple[OnboardingValidationIssue, ...] = Field(default_factory=tuple)
    row_count: int = Field(ge=0)
    candidate_observation_count: int = Field(ge=0)
    missing_observation_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report_state(self) -> "OnboardingValidationReport":
        if self.contract_version != ONBOARDING_CONTRACT_VERSION:
            raise ValueError("unsupported onboarding contract version")
        if self.rejected_row_count > self.row_count:
            raise ValueError("rejected_row_count cannot exceed row_count")
        error_issues = tuple(
            issue
            for issue in self.issues
            if issue.severity is OnboardingIssueSeverity.ERROR
        )
        if self.status is OnboardingValidationStatus.VALID:
            if error_issues:
                raise ValueError("VALID onboarding report cannot contain ERROR issues")
            if self.rejected_row_count != 0:
                raise ValueError("VALID onboarding report requires zero rejected rows")
        if self.status is OnboardingValidationStatus.INVALID and not error_issues:
            raise ValueError(
                "INVALID onboarding report requires issues with at least one ERROR"
            )
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
    content_manifest_hash: str | None = None,
) -> str:
    """Derive a stable snapshot identity from source and accepted transformations."""

    parts = {
        "dataset_id": _require_text(dataset_id, "dataset_id"),
        "source_content_hash": _require_text(source_content_hash, "source_content_hash"),
        "mapping_version": _require_text(mapping_version, "mapping_version"),
        "validation_version": _require_text(validation_version, "validation_version"),
    }
    if content_manifest_hash is not None:
        parts["content_manifest_hash"] = _require_text(
            content_manifest_hash,
            "content_manifest_hash",
        )
    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"snapshot-{sha256(encoded).hexdigest()}"


def _manifest_item(value: Any, *, identity_field: str, drop_fields: set[str]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        item = value.model_dump(mode="json")
    elif isinstance(value, dict):
        item = dict(value)
    else:
        raise TypeError("content manifest items must be mappings or Pydantic models")
    item = {
        str(key): child
        for key, child in item.items()
        if key not in drop_fields
    }
    if not str(item.get(identity_field, "")).strip():
        raise ValueError(f"content manifest item requires {identity_field}")
    return item


def _manifest_observation_items(values: Sequence[Any]) -> list[dict[str, Any]]:
    """Serialize observations without snapshot-derived identity fields.

    Candidate observation IDs are provisional until the final snapshot ID is
    known.  Lineage therefore records the referenced observations' canonical
    content rather than their provisional IDs, while the complete observation
    list remains part of the manifest.
    """

    base_items: list[tuple[dict[str, Any], tuple[str, ...]]] = []
    by_observation_id: dict[str, dict[str, Any]] = {}
    duplicate_observation_ids: set[str] = set()
    for value in values:
        item = _manifest_item(
            value,
            identity_field="entity_id",
            drop_fields={
                "dataset_id",
                "dataset_snapshot_id",
                "observation_id",
                "input_observation_ids",
            },
        )
        if isinstance(value, BaseModel):
            raw = value.model_dump(mode="json")
        elif isinstance(value, dict):
            raw = dict(value)
        else:
            raise TypeError("content manifest items must be mappings or Pydantic models")
        observation_id = str(raw.get("observation_id", "")).strip()
        if not observation_id:
            raise ValueError("content manifest observation requires observation_id")
        if observation_id in by_observation_id:
            duplicate_observation_ids.add(observation_id)
        else:
            by_observation_id[observation_id] = item
        lineage_refs = tuple(
            str(ref).strip() for ref in raw.get("input_observation_ids", ())
        )
        base_items.append((item, lineage_refs))

    items: list[dict[str, Any]] = []
    for base_item, lineage_refs in base_items:
        item = dict(base_item)
        if not lineage_refs:
            item["input_observation_content"] = []
            items.append(item)
            continue
        ambiguous_refs = [ref for ref in lineage_refs if ref in duplicate_observation_ids]
        if ambiguous_refs:
            raise ValueError(
                "content manifest observation lineage references duplicate observation: "
                + ",".join(sorted(ambiguous_refs))
            )
        missing_refs = [ref for ref in lineage_refs if ref not in by_observation_id]
        if missing_refs:
            raise ValueError(
                "content manifest observation lineage references unknown observation: "
                + ",".join(sorted(missing_refs))
            )
        item["input_observation_content"] = sorted(
            (dict(by_observation_id[ref]) for ref in lineage_refs),
            key=lambda child: (
                child.get("entity_id", ""),
                child.get("period_id", ""),
                child.get("metric_id", ""),
                json.dumps(child, sort_keys=True, separators=(",", ":")),
            ),
        )
        items.append(item)

    return sorted(
        items,
        key=lambda item: (
            item["entity_id"],
            item.get("period_id", ""),
            item.get("metric_id", ""),
        ),
    )


def compute_content_manifest_hash(
    *,
    sources: Sequence[Any],
    documents: Sequence[Any] = (),
    evidence: Sequence[Any] = (),
    observations: Sequence[Any] = (),
    mapping_version: str,
    validation_version: str,
) -> str:
    """Hash the complete accepted analytical content universe deterministically.

    Dataset/snapshot identity fields on documents are derived from this hash,
    so they are intentionally excluded to avoid a circular identity. Content,
    provenance, locators, quotes, and canonical observations remain part of
    the manifest.
    """

    source_items = [
        _manifest_item(
            item,
            identity_field="source_ref",
            drop_fields={"retrieved_at"},
        )
        for item in sources
    ]
    document_items = [
        _manifest_item(
            item,
            identity_field="document_id",
            drop_fields={"dataset_id", "dataset_snapshot_id"},
        )
        for item in documents
    ]
    evidence_items = [
        _manifest_item(
            item,
            identity_field="evidence_id",
            drop_fields=set(),
        )
        for item in evidence
    ]
    observation_items = _manifest_observation_items(observations)
    payload = {
        "manifest_version": CONTENT_MANIFEST_VERSION,
        "mapping_version": _require_text(mapping_version, "mapping_version"),
        "validation_version": _require_text(validation_version, "validation_version"),
        "sources": sorted(source_items, key=lambda item: item["source_ref"]),
        "documents": sorted(document_items, key=lambda item: item["document_id"]),
        "evidence": sorted(evidence_items, key=lambda item: item["evidence_id"]),
        "observations": observation_items,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"manifest-{sha256(encoded).hexdigest()}"


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
    content_manifest_hash: str | None = None,
    status: DatasetSnapshotStatus = DatasetSnapshotStatus.CANDIDATE,
    created_at: datetime | None = None,
) -> DatasetSnapshotMetadata:
    """Create metadata whose identity is bound to immutable raw content."""

    requested_status = DatasetSnapshotStatus(status)
    if requested_status is DatasetSnapshotStatus.ACCEPTED:
        raise ValueError(
            "build_snapshot_metadata cannot create ACCEPTED metadata without a validation report"
        )

    snapshot_id = compute_dataset_snapshot_id(
        dataset_id,
        raw_descriptor.content_hash,
        mapping_version,
        validation_version,
        content_manifest_hash,
    )
    return DatasetSnapshotMetadata(
        dataset_id=dataset_id,
        dataset_snapshot_id=snapshot_id,
        status=requested_status,
        created_at=created_at or datetime.now(timezone.utc),
        source_content_hash=raw_descriptor.content_hash,
        mapping_version=mapping_version,
        validation_version=validation_version,
        content_manifest_hash=content_manifest_hash,
    )


def promote_snapshot_metadata(
    raw_descriptor: RawDatasetDescriptor,
    metadata: DatasetSnapshotMetadata,
    validation_report: OnboardingValidationReport,
    *,
    source_reconciled: bool = False,
) -> DatasetSnapshotMetadata:
    """Promote metadata after structural validation and source reconciliation."""

    validate_snapshot_metadata(raw_descriptor, metadata)
    if metadata.status is not DatasetSnapshotStatus.CANDIDATE:
        raise ValueError("only CANDIDATE snapshot metadata can be promoted")
    if validation_report.dataset_id != metadata.dataset_id:
        raise ValueError("validation report dataset ID does not match snapshot metadata")
    if validation_report.candidate_snapshot_id != metadata.dataset_snapshot_id:
        raise ValueError("validation report snapshot ID does not match snapshot metadata")
    if validation_report.status is not OnboardingValidationStatus.VALID:
        raise ValueError("only a VALID onboarding report can promote a snapshot")
    if not source_reconciled:
        raise ValueError(
            "structural validation alone cannot accept a snapshot; source reconciliation is required"
        )
    return metadata.model_copy(update={"status": DatasetSnapshotStatus.ACCEPTED})


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
        metadata.content_manifest_hash,
    )
    if metadata.dataset_snapshot_id != expected_id:
        raise ValueError("snapshot ID does not match source and transformation versions")


def demo_metric_registry() -> MetricRegistry:
    """Return the bank metric IDs used by the metric dictionary.

    This registry validates candidate mappings only; it does not claim that
    any dataset contains accepted observations.
    """

    return MetricRegistry(
        definitions=(
            MetricDefinition(
                metric_id="bank.roa",
                display_name="Return on assets",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Profitability relative to company assets.",
            ),
            MetricDefinition(
                metric_id="bank.roe",
                display_name="Return on equity",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Profitability relative to company equity.",
            ),
            MetricDefinition(
                metric_id="bank.npl_g35",
                display_name="Share of loans in groups 3–5",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Group 3–5 loans relative to gross customer loans.",
            ),
            MetricDefinition(
                metric_id="bank.llr_coverage",
                display_name="Provision coverage of group 3–5 NPL",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
                description="Loan loss provisions relative to group 3–5 NPL balance.",
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
