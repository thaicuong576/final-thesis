"""Deterministic normalization and validation for the CSV vertical slice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import re

from .csv_onboarding import CsvStagedDataset
from .dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    canonical_observation_id,
    DatasetEvidence,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetSource,
    PeerUniverse,
)
from .evidence_contract import DatasetDocument
from .onboarding_contract import (
    DatasetSnapshotMetadata,
    FieldMappingSpec,
    MetricRegistry,
    OnboardingIssueCode,
    OnboardingValidationIssue,
    OnboardingValidationReport,
    OnboardingValidationStatus,
    build_snapshot_metadata,
    compute_content_manifest_hash,
    compute_field_mapping_version,
    compute_dataset_snapshot_id,
    validate_field_mapping,
)
from .schema import QualityStatus


ONBOARDING_VALIDATION_VERSION = "csv-onboarding-validation-v1"
_PERIOD_PATTERNS = (
    re.compile(r"^(?P<year>\d{4})_Q(?P<quarter>[1-4])$"),
    re.compile(r"^(?P<year>\d{4})Q(?P<quarter>[1-4])$"),
    re.compile(r"^Q(?P<quarter>[1-4])-(?P<year>\d{4})$"),
)
_NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|\s)[.]{1,2}[\\/]|"
    r"(?:^|\s)/(?:home|Users|mnt|tmp)(?:/|$))",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class CanonicalDatasetCandidate:
    """Canonical objects produced before snapshot acceptance/materialization."""

    metadata: DatasetSnapshotMetadata
    source: DatasetSource
    entities: tuple[DatasetEntity, ...]
    periods: tuple[DatasetPeriod, ...]
    metrics: tuple[DatasetMetric, ...]
    observations: tuple[CanonicalObservation, ...]
    peer_universes: tuple[PeerUniverse, ...] = ()
    additional_sources: tuple[DatasetSource, ...] = ()
    documents: tuple[DatasetDocument, ...] = ()
    evidence: tuple[DatasetEvidence, ...] = ()

    @property
    def all_sources(self) -> tuple[DatasetSource, ...]:
        """Return the primary structured source followed by additions."""

        return (self.source, *self.additional_sources)


@dataclass(frozen=True)
class CsvNormalizationResult:
    candidate: CanonicalDatasetCandidate
    validation_report: OnboardingValidationReport


def normalize_period(value: str) -> str:
    """Normalize exactly the supported quarter spellings to ``YYYY_Qn``."""

    normalized = value.strip()
    for pattern in _PERIOD_PATTERNS:
        match = pattern.fullmatch(normalized)
        if match:
            return f"{match.group('year')}_Q{match.group('quarter')}"
    raise ValueError("period must use YYYY_Qn, YYYYQn, or Qn-YYYY")


def _parse_number(value: str) -> float:
    normalized = value.strip()
    if not _NUMBER_PATTERN.fullmatch(normalized):
        raise ValueError("numeric value must use an unambiguous decimal format")
    parsed = float(normalized)
    if not math.isfinite(parsed):
        raise ValueError("numeric value must be finite")
    return parsed


def _entity_type(level: AnalyticalLevel) -> DatasetEntityType:
    return DatasetEntityType(level.value)


def _source_ref(staged: CsvStagedDataset) -> str:
    return f"csv:{staged.raw_descriptor.raw_dataset_id}:{staged.raw_descriptor.content_hash}"


def _issue(
    code: OnboardingIssueCode,
    message: str,
    *,
    row_number: int | None = None,
    field_name: str | None = None,
    metric_id: str | None = None,
) -> OnboardingValidationIssue:
    return OnboardingValidationIssue(
        code=code,
        message=message,
        row_number=row_number,
        field_name=field_name,
        metric_id=metric_id,
    )


def _public_label(value: str) -> str:
    label = value.strip()
    if not label:
        return "CSV upload"
    if _PATH_PATTERN.search(label):
        raise ValueError("publisher label must not contain a local path")
    return label


def normalize_csv_dataset(
    staged: CsvStagedDataset,
    *,
    dataset_id: str,
    mapping: FieldMappingSpec,
    registry: MetricRegistry,
    publisher: str = "User-supplied CSV",
    created_at: datetime | None = None,
) -> CsvNormalizationResult:
    """Normalize staged rows using only an explicit, registry-checked mapping."""

    mapping_issues = list(validate_field_mapping(mapping, staged.headers, registry))
    known_definitions = {
        item.metric_id: registry.get(item.metric_id)
        for item in mapping.metric_mappings
    }
    known_definitions = {
        metric_id: definition
        for metric_id, definition in known_definitions.items()
        if definition is not None
    }
    mapping_levels = {
        item.analytical_level
        for item in mapping.metric_mappings
        if item.metric_id in known_definitions
    }
    if len(mapping_levels) > 1:
        mapping_issues.append(
            _issue(
                OnboardingIssueCode.MAPPING_INVALID,
                "one raw entity field cannot represent multiple analytical levels without explicit semantics",
                field_name=mapping.entity_field,
            )
        )

    mapping_version = compute_field_mapping_version(mapping)
    metadata = build_snapshot_metadata(
        dataset_id,
        staged.raw_descriptor,
        mapping_version=mapping_version,
        validation_version=ONBOARDING_VALIDATION_VERSION,
        created_at=created_at,
    )
    source = DatasetSource(
        source_ref=_source_ref(staged),
        source_type="csv",
        source_tier="user_supplied",
        source_url=f"urn:csv:{staged.raw_descriptor.content_hash}",
        publisher=_public_label(publisher),
        retrieved_at=staged.raw_descriptor.ingested_at.isoformat(),
        content_hash=staged.raw_descriptor.content_hash,
        validation_status=QualityStatus.PENDING_VALIDATION,
    )

    metric_mappings = tuple(
        item for item in mapping.metric_mappings if item.metric_id in known_definitions
    )
    metrics = tuple(
        DatasetMetric(
            metric_id=item.metric_id,
            display_name=known_definitions[item.metric_id].display_name,
            analytical_level=known_definitions[item.metric_id].analytical_level,
            default_unit=item.unit,
        )
        for item in metric_mappings
    )
    entities: dict[str, DatasetEntity] = {}
    periods: dict[str, DatasetPeriod] = {}
    observations: list[CanonicalObservation] = []
    issues: list[OnboardingValidationIssue] = mapping_issues
    duplicate_keys: dict[tuple[str, str, str], int] = {}
    rejected_rows: set[int] = set()
    accepted_count = 0
    missing_count = 0

    if not staged.rows:
        issues.append(
            _issue(
                OnboardingIssueCode.EMPTY_REQUIRED_FIELD,
                "CSV must contain at least one data row",
                field_name="rows",
            )
        )

    can_process_rows = not mapping_issues and bool(metric_mappings)
    for row_number, row in enumerate(staged.rows, start=2):
        values = dict(zip(staged.headers, row))
        raw_entity = values.get(mapping.entity_field, "")
        entity_id = raw_entity.strip()
        row_invalid = False
        if not entity_id:
            issues.append(
                _issue(
                    OnboardingIssueCode.ENTITY_MAPPING_INVALID,
                    "entity value must be non-empty",
                    row_number=row_number,
                    field_name=mapping.entity_field,
                )
            )
            rejected_rows.add(row_number)
            row_invalid = True

        raw_period = values.get(mapping.period_field, "")
        period_id: str | None = None
        try:
            period_id = normalize_period(raw_period)
        except ValueError:
            issues.append(
                _issue(
                    OnboardingIssueCode.PERIOD_INVALID,
                    "period does not use a supported exact quarter format",
                    row_number=row_number,
                    field_name=mapping.period_field,
                )
            )
            rejected_rows.add(row_number)
            row_invalid = True

        if not can_process_rows or row_invalid or period_id is None or not entity_id:
            if not can_process_rows and staged.rows:
                rejected_rows.add(row_number)
            continue

        entities.setdefault(
            entity_id,
            DatasetEntity(
                entity_id=entity_id,
                entity_type=_entity_type(metric_mappings[0].analytical_level),
                display_name=entity_id,
            ),
        )
        periods.setdefault(period_id, DatasetPeriod(period_id=period_id, label=period_id))

        for item in metric_mappings:
            raw_value = values.get(item.raw_field, "")
            key = (entity_id, period_id, item.metric_id)
            if key in duplicate_keys:
                issues.append(
                    _issue(
                        OnboardingIssueCode.DUPLICATE_OBSERVATION,
                        f"duplicate canonical identity; first row was {duplicate_keys[key]}",
                        row_number=row_number,
                        field_name=item.raw_field,
                        metric_id=item.metric_id,
                    )
                )
                rejected_rows.add(row_number)
            else:
                duplicate_keys[key] = row_number

            observation_id = canonical_observation_id(
                metadata.dataset_snapshot_id,
                entity_id,
                period_id,
                item.metric_id,
            )
            common = {
                "observation_id": observation_id,
                "dataset_id": dataset_id,
                "dataset_snapshot_id": metadata.dataset_snapshot_id,
                "entity_id": entity_id,
                "period_id": period_id,
                "metric_id": item.metric_id,
                "unit": item.unit,
                "source_ref": source.source_ref,
                "metadata": {
                    "raw_row_number": row_number,
                    "raw_field": item.raw_field,
                },
            }
            if not raw_value.strip():
                observations.append(
                    CanonicalObservation(
                        **common,
                        validation_status=QualityStatus.MISSING,
                        missing_reason="DATA_UNAVAILABLE",
                    )
                )
                missing_count += 1
                continue
            try:
                parsed_value = _parse_number(raw_value)
            except ValueError:
                issues.append(
                    _issue(
                        OnboardingIssueCode.VALUE_INVALID,
                        "mapped metric value is not an unambiguous finite decimal",
                        row_number=row_number,
                        field_name=item.raw_field,
                        metric_id=item.metric_id,
                    )
                )
                rejected_rows.add(row_number)
                continue
            observations.append(
                CanonicalObservation(
                    **common,
                    value=parsed_value,
                    validation_status=QualityStatus.VALID,
                )
            )
            accepted_count += 1

    status = (
        OnboardingValidationStatus.VALID
        if not any(issue.severity.value == "ERROR" for issue in issues)
        else OnboardingValidationStatus.INVALID
    )
    if status is OnboardingValidationStatus.VALID:
        source = source.model_copy(update={"validation_status": QualityStatus.VALID})
    content_manifest_hash = compute_content_manifest_hash(
        sources=(source,),
        observations=tuple(observations),
        mapping_version=mapping_version,
        validation_version=ONBOARDING_VALIDATION_VERSION,
    )
    final_snapshot_id = compute_dataset_snapshot_id(
        dataset_id,
        staged.raw_descriptor.content_hash,
        mapping_version,
        ONBOARDING_VALIDATION_VERSION,
        content_manifest_hash,
    )
    metadata = metadata.model_copy(
        update={
            "dataset_snapshot_id": final_snapshot_id,
            "content_manifest_hash": content_manifest_hash,
        }
    )
    observations = [
        item.model_copy(
            update={
                "dataset_snapshot_id": final_snapshot_id,
                "observation_id": canonical_observation_id(
                    final_snapshot_id,
                    item.entity_id,
                    item.period_id,
                    item.metric_id,
                ),
            }
        )
        for item in observations
    ]
    report = OnboardingValidationReport(
        dataset_id=dataset_id,
        candidate_snapshot_id=metadata.dataset_snapshot_id,
        status=status,
        issues=tuple(issues),
        row_count=staged.row_count,
        accepted_observation_count=accepted_count,
        missing_observation_count=missing_count,
        rejected_row_count=len(rejected_rows),
    )
    candidate = CanonicalDatasetCandidate(
        metadata=metadata,
        source=source,
        entities=tuple(entities.values()),
        periods=tuple(periods.values()),
        metrics=metrics,
        observations=tuple(observations),
    )
    return CsvNormalizationResult(candidate=candidate, validation_report=report)
