from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from thesis_data.dataset_contract import AnalyticalLevel
from thesis_data.onboarding_contract import (
    DatasetSnapshotMetadata,
    DatasetSnapshotStatus,
    FieldMappingSpec,
    FieldMetricMapping,
    MetricDefinition,
    MetricRegistry,
    OnboardingIssueCode,
    OnboardingValidationIssue,
    OnboardingValidationReport,
    OnboardingValidationStatus,
    RawDatasetDescriptor,
    StagedField,
    build_snapshot_metadata,
    compute_dataset_snapshot_id,
    compute_field_mapping_version,
    demo_metric_registry,
    validate_field_mapping,
    validate_snapshot_metadata,
)


class Phase0AOnboardingContractTests(unittest.TestCase):
    def raw(self, content_hash: str = "hash-a") -> RawDatasetDescriptor:
        return RawDatasetDescriptor(
            raw_dataset_id="raw-upload-1",
            source_type="csv",
            original_name="financials.csv",
            content_hash=content_hash,
            ingested_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )

    def mapping(self) -> FieldMappingSpec:
        return FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="company.roa",
                    unit="percent",
                    analytical_level=AnalyticalLevel.COMPANY,
                ),
                FieldMetricMapping(
                    raw_field="ROE (%)",
                    metric_id="company.roe",
                    unit="percent",
                    analytical_level=AnalyticalLevel.COMPANY,
                ),
            ),
        )

    def test_raw_descriptor_has_no_physical_path_identity(self):
        self.assertEqual(self.raw().source_type, "csv")
        with self.assertRaises(ValidationError):
            payload = self.raw().model_dump(mode="python")
            payload["original_name"] = r"C:\private\financials.csv"
            RawDatasetDescriptor(**payload)

    def test_staged_field_is_preview_only(self):
        field = StagedField(
            field_name="ROA (%)",
            inferred_data_type="numeric",
            sample_values=(1.2, 1.8),
            null_count=0,
        )
        self.assertEqual(field.inferred_data_type, "numeric")

    def test_demo_registry_is_definition_not_capability(self):
        registry = demo_metric_registry()
        self.assertIsNotNone(registry.get("company.roa"))
        self.assertIsNotNone(registry.get("macro.policy_rate"))
        self.assertIsNone(registry.get("company.not_in_registry"))

    def test_explicit_mapping_passes_against_available_headers(self):
        issues = validate_field_mapping(
            self.mapping(),
            ("Company", "Quarter", "ROA (%)", "ROE (%)"),
            demo_metric_registry(),
        )
        self.assertEqual(issues, ())

    def test_mapping_reports_missing_field_unsupported_metric_and_unit_conflict(self):
        mapping = FieldMappingSpec(
            entity_field="MissingCompany",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="company.unknown",
                    unit="ratio",
                    analytical_level=AnalyticalLevel.COMPANY,
                ),
            ),
        )
        issues = validate_field_mapping(
            mapping,
            ("Company", "Quarter", "ROA (%)"),
            demo_metric_registry(),
        )
        self.assertEqual(
            {issue.code for issue in issues},
            {OnboardingIssueCode.ENTITY_MAPPING_INVALID, OnboardingIssueCode.METRIC_UNSUPPORTED},
        )

        wrong_unit = FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="company.roa",
                    unit="ratio",
                    analytical_level=AnalyticalLevel.COMPANY,
                ),
            ),
        )
        unit_issues = validate_field_mapping(
            wrong_unit,
            ("Company", "Quarter", "ROA (%)"),
            demo_metric_registry(),
        )
        self.assertEqual(unit_issues[0].code, OnboardingIssueCode.UNIT_MISMATCH)

    def test_mapping_rejects_duplicate_metric_or_identity_fields(self):
        with self.assertRaisesRegex(ValueError, "mapped raw fields"):
            FieldMappingSpec(
                entity_field="Company",
                period_field="Quarter",
                metric_mappings=(
                    FieldMetricMapping(
                        raw_field="ROA",
                        metric_id="company.roa",
                        unit="percent",
                        analytical_level=AnalyticalLevel.COMPANY,
                    ),
                    FieldMetricMapping(
                        raw_field="ROA",
                        metric_id="company.roe",
                        unit="percent",
                        analytical_level=AnalyticalLevel.COMPANY,
                    ),
                ),
            )

    def test_snapshot_identity_changes_with_source_or_mapping_version(self):
        mapping_version = compute_field_mapping_version(self.mapping())
        changed_mapping = self.mapping().model_copy(
            update={
                "metric_mappings": (
                    self.mapping().metric_mappings[0].model_copy(
                        update={"raw_field": "Return on assets (%)"}
                    ),
                    self.mapping().metric_mappings[1],
                )
            }
        )
        changed_mapping_version = compute_field_mapping_version(changed_mapping)
        first = compute_dataset_snapshot_id("dataset", "hash-a", mapping_version, "validation-v1")
        same = compute_dataset_snapshot_id("dataset", "hash-a", mapping_version, "validation-v1")
        source_changed = compute_dataset_snapshot_id("dataset", "hash-b", mapping_version, "validation-v1")
        mapping_changed = compute_dataset_snapshot_id(
            "dataset", "hash-a", changed_mapping_version, "validation-v1"
        )
        self.assertEqual(first, same)
        self.assertNotEqual(first, source_changed)
        self.assertNotEqual(first, mapping_changed)
        self.assertNotEqual(mapping_version, changed_mapping_version)

    def test_snapshot_metadata_binds_raw_source_and_identity(self):
        metadata = build_snapshot_metadata(
            "dataset",
            self.raw(),
            mapping_version="mapping-v1",
            validation_version="validation-v1",
            status=DatasetSnapshotStatus.CANDIDATE,
            created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )
        validate_snapshot_metadata(self.raw(), metadata)
        self.assertEqual(metadata.source_content_hash, "hash-a")
        self.assertEqual(metadata.status, DatasetSnapshotStatus.CANDIDATE)
        with self.assertRaisesRegex(ValueError, "hash"):
            validate_snapshot_metadata(self.raw("hash-b"), metadata)

    def test_forged_snapshot_id_is_rejected(self):
        metadata = build_snapshot_metadata(
            "dataset",
            self.raw(),
            mapping_version="mapping-v1",
            validation_version="validation-v1",
        )
        forged = metadata.model_copy(update={"dataset_snapshot_id": "snapshot-forged"})
        with self.assertRaisesRegex(ValueError, "snapshot ID"):
            validate_snapshot_metadata(self.raw(), forged)

    def test_valid_report_has_no_issues_and_invalid_report_requires_issue(self):
        valid = OnboardingValidationReport(
            dataset_id="dataset",
            candidate_snapshot_id="snapshot-1",
            status=OnboardingValidationStatus.VALID,
            row_count=2,
            accepted_observation_count=4,
            missing_observation_count=0,
            rejected_row_count=0,
        )
        self.assertEqual(valid.status, OnboardingValidationStatus.VALID)
        with self.assertRaisesRegex(ValueError, "requires issues"):
            OnboardingValidationReport(
                dataset_id="dataset",
                candidate_snapshot_id="snapshot-1",
                status=OnboardingValidationStatus.INVALID,
                row_count=2,
                accepted_observation_count=0,
                missing_observation_count=0,
                rejected_row_count=2,
            )
        invalid = OnboardingValidationReport(
            dataset_id="dataset",
            candidate_snapshot_id="snapshot-1",
            status=OnboardingValidationStatus.INVALID,
            issues=(
                OnboardingValidationIssue(
                    code=OnboardingIssueCode.VALUE_INVALID,
                    message="invalid numeric value",
                    row_number=2,
                ),
            ),
            row_count=2,
            accepted_observation_count=1,
            missing_observation_count=0,
            rejected_row_count=1,
        )
        self.assertEqual(len(invalid.issues), 1)

    def test_snapshot_metadata_schema_is_explicit_and_strict(self):
        with self.assertRaises(ValidationError):
            DatasetSnapshotMetadata(
                dataset_id="dataset",
                dataset_snapshot_id="snapshot",
                status=DatasetSnapshotStatus.CANDIDATE,
                created_at=datetime.now(timezone.utc),
                source_content_hash="hash",
                mapping_version="mapping-v1",
                validation_version="validation-v1",
                local_path="C:/private/file.csv",
            )


if __name__ == "__main__":
    unittest.main()
