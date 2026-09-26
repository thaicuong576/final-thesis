from dataclasses import replace
import hashlib
import sqlite3
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from thesis_data.analysis_request import AnalysisRequest
from thesis_data.application_runtime import ApplicationRuntimeContext
from thesis_data.canonical_snapshot import materialize_canonical_snapshot
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.csv_onboarding import stage_csv_bytes
from thesis_data.dataset_tool_runtime import DatasetToolRuntime
from thesis_data.dataset_contract import DatasetSource, ObservationEvidenceRef, ObservationReview
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.onboarding_contract import (
    FieldMappingSpec,
    FieldMetricMapping,
    OnboardingIssueCode,
    demo_metric_registry,
)
from thesis_data.onboarding_validation import (
    normalize_csv_dataset,
    normalize_period,
    reconcile_candidate_observations,
)
from thesis_data.schema import QualityStatus
from thesis_data.source_artifacts import resolve_primary_source_artifacts


REVIEWED_FILING_BYTES = b"fixture reviewed filing used by CSV onboarding tests"


class Phase0BCsvOnboardingTests(unittest.TestCase):
    def mapping(self, *, include_roe: bool = True, metric_id: str = "bank.roa") -> FieldMappingSpec:
        metrics = [
            FieldMetricMapping(
                raw_field="ROA (%)",
                metric_id=metric_id,
                unit="percent",
                analytical_level="company",
            )
        ]
        if include_roe:
            metrics.append(
                FieldMetricMapping(
                    raw_field="ROE (%)",
                    metric_id="bank.roe",
                    unit="percent",
                    analytical_level="company",
                )
            )
        return FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=tuple(metrics),
        )

    def stage(self, csv_text: str, *, raw_dataset_id: str = "upload-1"):
        return stage_csv_bytes(
            csv_text.encode("utf-8"),
            raw_dataset_id=raw_dataset_id,
            original_name="financials.csv",
        )

    def normalize(self, csv_text: str, *, mapping: FieldMappingSpec | None = None):
        staged = self.stage(csv_text)
        return normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=mapping or self.mapping(),
            registry=demo_metric_registry(),
        )

    def reviewed_candidate(self, result):
        """Explicit synthetic filing review used only by materialization tests."""
        primary = DatasetSource(
            source_ref="filing:reviewed-csv-fixture",
            source_type="filing",
            source_tier="primary",
            source_url="https://example.test/filing.pdf",
            publisher="Fixture issuer",
            retrieved_at="2026-09-24T00:00:00+00:00",
            content_hash=hashlib.sha256(REVIEWED_FILING_BYTES).hexdigest(),
            validation_status=QualityStatus.VALID,
        )
        numeric = [item for item in result.candidate.observations if item.value is not None]
        reviews = {
            item.observation_id: ObservationReview(
                reviewer_id="fixture-reviewer",
                reviewed_at="2026-09-24T00:00:00+00:00",
                decision="matched_reported_value",
                primary_evidence=(
                    ObservationEvidenceRef(
                        source_ref=primary.source_ref,
                        locator=f"PDF page 1 / row {item.entity_id} / {item.metric_id}",
                    ),
                ),
                resolution_note="Fixture observation manually matched to the filing row.",
            )
            for item in numeric
        }
        return reconcile_candidate_observations(
            result.candidate,
            primary_sources=(primary,),
            reviews=reviews,
            period_bases={
                item.observation_id: (
                    "ttm" if item.metric_id in {"bank.roa", "bank.roe"} else "point_in_time"
                )
                for item in numeric
            },
            reporting_scopes={item.observation_id: "consolidated" for item in numeric},
        )

    def valid_text(self) -> str:
        return "Company,Quarter,ROA (%),ROE (%)\nBANK-X,Q4-2024,1.2,12.0\nBANK-Y,Q4-2024,1.8,15.0\n"

    def test_staging_is_byte_hashed_and_preview_only(self):
        content = self.valid_text().encode("utf-8")
        staged = stage_csv_bytes(
            content,
            raw_dataset_id="arbitrary-upload",
            original_name="financials.csv",
        )
        self.assertEqual(staged.raw_descriptor.content_hash, hashlib.sha256(content).hexdigest())
        self.assertEqual(staged.headers, ("Company", "Quarter", "ROA (%)", "ROE (%)"))
        self.assertEqual(staged.row_count, 2)
        self.assertEqual(staged.rows[0], ("BANK-X", "Q4-2024", "1.2", "12.0"))
        self.assertEqual(staged.staged_fields[2].inferred_data_type, "number")
        self.assertEqual(staged.staged_fields[2].field_name, "ROA (%)")

    def test_malformed_duplicate_or_path_named_csv_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate CSV header"):
            self.stage("Company,Company\nBANK-X,BANK-X\n")
        with self.assertRaisesRegex(ValueError, "malformed CSV"):
            self.stage('Company,Quarter\n"BANK-X,Q4-2024\n')
        with self.assertRaises(ValidationError):
            stage_csv_bytes(
                self.valid_text().encode(),
                raw_dataset_id="upload-1",
                original_name=r"C:\private\financials.csv",
            )
        with self.assertRaisesRegex(ValueError, "raw_dataset_id"):
            stage_csv_bytes(
                self.valid_text().encode(),
                raw_dataset_id=r"C:\private\financials.csv",
                original_name="financials.csv",
            )
        for raw_dataset_id in ("tenant/upload", r"tenant\upload", "/home/user/file.csv", "/tmp/file.csv"):
            with self.subTest(raw_dataset_id=raw_dataset_id):
                with self.assertRaisesRegex(ValueError, "path separators"):
                    stage_csv_bytes(
                        self.valid_text().encode(),
                        raw_dataset_id=raw_dataset_id,
                        original_name="financials.csv",
                    )

    def test_period_normalization_is_exact_and_general(self):
        for value in ("2024_Q4", "2024Q4", "Q4-2024", "Q1-2025"):
            with self.subTest(value=value):
                self.assertRegex(normalize_period(value), r"^\d{4}_Q[1-4]$")
        for value in ("Q5-2024", "2024-M13", "next quarter", "Q4 maybe 2024"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_period(value)

    def test_explicit_mapping_is_required_and_mapping_errors_block(self):
        staged = self.stage("Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n")
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        self.assertEqual(result.validation_report.status.value, "INVALID")
        self.assertIn(OnboardingIssueCode.MAPPING_INVALID, {item.code for item in result.validation_report.issues})

        unsupported = self.mapping(metric_id="bank.not_registered")
        unsupported_result = self.normalize(self.valid_text(), mapping=unsupported)
        self.assertIn(
            OnboardingIssueCode.METRIC_UNSUPPORTED,
            {item.code for item in unsupported_result.validation_report.issues},
        )
        wrong_level = FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="bank.roa",
                    unit="percent",
                    analytical_level="sector",
                ),
            ),
        )
        wrong_level_result = self.normalize(self.valid_text(), mapping=wrong_level)
        self.assertIn(
            OnboardingIssueCode.MAPPING_INVALID,
            {item.code for item in wrong_level_result.validation_report.issues},
        )
        wrong_unit = FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="bank.roa",
                    unit="ratio",
                    analytical_level="company",
                ),
            ),
        )
        wrong_unit_result = self.normalize(
            "Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n",
            mapping=wrong_unit,
        )
        self.assertIn(
            OnboardingIssueCode.UNIT_MISMATCH,
            {item.code for item in wrong_unit_result.validation_report.issues},
        )

    def test_entity_period_and_numeric_validation_fail_without_guessing(self):
        cases = (
            ("Company,Quarter,ROA (%)\n ,Q4-2024,1.2\n", OnboardingIssueCode.ENTITY_MAPPING_INVALID),
            ("Company,Quarter,ROA (%)\nBANK-X,Q5-2024,1.2\n", OnboardingIssueCode.PERIOD_INVALID),
            ("Company,Quarter,ROA (%)\nBANK-X,Q4-2024,abc\n", OnboardingIssueCode.VALUE_INVALID),
            ("Company,Quarter,ROA (%)\nBANK-X,Q4-2024,\"1,25\"\n", OnboardingIssueCode.VALUE_INVALID),
        )
        mapping = self.mapping(include_roe=False)
        for text, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                result = self.normalize(text, mapping=mapping)
                self.assertEqual(result.validation_report.status.value, "INVALID")
                self.assertIn(expected_code, {item.code for item in result.validation_report.issues})

    def test_blank_metric_is_explicit_missing_and_entity_ids_are_arbitrary(self):
        result = self.normalize(
            "Company,Quarter,ROA (%)\n issuer_001 ,2025Q1,\nCOMPANY-ALPHA,Q1-2025,2.5\n",
            mapping=self.mapping(include_roe=False),
        )
        self.assertEqual(result.validation_report.status.value, "VALID")
        self.assertEqual(result.validation_report.candidate_observation_count, 1)
        self.assertEqual(result.validation_report.missing_observation_count, 1)
        numeric = next(item for item in result.candidate.observations if item.value is not None)
        self.assertEqual(numeric.validation_status, QualityStatus.PENDING_VALIDATION)
        self.assertEqual(result.candidate.source.validation_status, QualityStatus.PENDING_VALIDATION)
        missing = next(item for item in result.candidate.observations if item.value is None)
        self.assertEqual(missing.validation_status, QualityStatus.MISSING)
        self.assertEqual(missing.missing_reason, "DATA_UNAVAILABLE")
        self.assertEqual({item.entity_id for item in result.candidate.entities}, {"issuer_001", "COMPANY-ALPHA"})
        self.assertEqual({item.period_id for item in result.candidate.periods}, {"2025_Q1"})

    def test_duplicate_canonical_identity_is_not_silently_deduplicated(self):
        result = self.normalize(
            "Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n BANK-X ,2024_Q4,1.3\n",
            mapping=self.mapping(include_roe=False),
        )
        self.assertEqual(result.validation_report.status.value, "INVALID")
        self.assertIn(
            OnboardingIssueCode.DUPLICATE_OBSERVATION,
            {item.code for item in result.validation_report.issues},
        )
        self.assertEqual(len(result.candidate.observations), 2)
        duplicate_issue = next(
            item for item in result.validation_report.issues
            if item.code is OnboardingIssueCode.DUPLICATE_OBSERVATION
        )
        self.assertEqual(duplicate_issue.row_number, 3)
        self.assertTrue(duplicate_issue.issue_id)

    def test_snapshot_identity_changes_with_content_or_mapping(self):
        first = self.normalize(self.valid_text()).candidate.metadata.dataset_snapshot_id
        changed_content = self.normalize(self.valid_text().replace("1.2", "1.3")).candidate.metadata.dataset_snapshot_id
        changed_mapping = self.normalize(
            self.valid_text(),
            mapping=self.mapping(include_roe=False),
        ).candidate.metadata.dataset_snapshot_id
        self.assertNotEqual(first, changed_content)
        self.assertNotEqual(first, changed_mapping)

    def test_end_to_end_csv_to_canonical_provider_and_runtime(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        self.assertEqual(result.validation_report.status.value, "VALID")
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "canonical.sqlite"
            candidate = self.reviewed_candidate(result)
            accepted = self.materialize(
                db_path,
                candidate,
                staged.raw_descriptor,
                result.validation_report,
            )
            self.assertEqual(accepted.status.value, "accepted")
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id="csv-dataset")
            ref = provider.current_dataset_ref()
            catalog = provider.get_capabilities(ref)
            request = AnalysisRequest(
                request_id="csv-request",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                target_entity_ids=("BANK-X",),
                period_ids=("2024_Q4",),
                metric_ids=("bank.roa", "bank.roe"),
                objective="Read CSV-backed company metrics.",
            )
            runtime = DatasetToolRuntime(ApplicationRuntimeContext.from_request(request, provider))
            observation = runtime.get_metric("BANK-X", "2024_Q4", "bank.roa")

        self.assertEqual(observation.value, 1.2)
        self.assertEqual(catalog.entity_ids, frozenset({"BANK-X", "BANK-Y"}))
        self.assertEqual(catalog.period_ids, frozenset({"2024_Q4"}))
        self.assertEqual(catalog.metric_ids, frozenset({"bank.roa", "bank.roe"}))
        self.assertNotIn("bank.npl_g35", catalog.metric_ids)
        self.assertNotIn("macro.policy_rate", catalog.metric_ids)

    def test_wrong_dataset_or_snapshot_ref_is_rejected(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "canonical.sqlite"
            self.materialize(
                db_path, candidate, staged.raw_descriptor, result.validation_report
            )
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id="csv-dataset")
            ref = provider.current_dataset_ref()
            with self.assertRaisesRegex(ValueError, "dataset_id"):
                provider.get_capabilities(ref.model_copy(update={"dataset_id": "wrong"}))
            with self.assertRaisesRegex(ValueError, "snapshot"):
                provider.get_capabilities(ref.model_copy(update={"dataset_snapshot_id": "wrong"}))

    def test_invalid_candidate_cannot_be_promoted_or_materialized(self):
        text = "Company,Quarter,ROA (%)\nBANK-X,Q4-2024,abc\n"
        staged = self.stage(text)
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(include_roe=False),
            registry=demo_metric_registry(),
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "VALID"):
                self.materialize(
                    Path(directory) / "invalid.sqlite",
                    result.candidate,
                    staged.raw_descriptor,
                    result.validation_report,
                )

    def test_promotion_rejects_unhashed_sources_and_csv_relabelled_as_primary(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        primary = candidate.additional_sources[0]
        with tempfile.TemporaryDirectory() as directory:
            invalid_hash_candidate = replace(
                candidate,
                additional_sources=(primary.model_copy(update={"content_hash": "not-a-sha256"}),),
            )
            with self.assertRaisesRegex(ValueError, "source content hash"):
                self.materialize(
                    Path(directory) / "invalid-hash.sqlite",
                    invalid_hash_candidate,
                    staged.raw_descriptor,
                    result.validation_report,
                )

            relabeled_csv_candidate = replace(
                candidate,
                additional_sources=(primary.model_copy(update={"source_type": "csv"}),),
            )
            with self.assertRaisesRegex(ValueError, "source type"):
                self.materialize(
                    Path(directory) / "relabeled-csv.sqlite",
                    relabeled_csv_candidate,
                    staged.raw_descriptor,
                    result.validation_report,
                )

            forged_hash_candidate = replace(
                candidate,
                additional_sources=(primary.model_copy(update={"content_hash": "d" * 64}),),
            )
            with self.assertRaisesRegex(ValueError, "explicit evidence root"):
                materialize_canonical_snapshot(
                    Path(directory) / "unverified-primary.sqlite",
                    forged_hash_candidate,
                    staged.raw_descriptor,
                    result.validation_report,
                )

    def test_evidence_root_resolver_checks_primary_bytes_against_source_hash(self):
        result = self.normalize(self.valid_text())
        candidate = self.reviewed_candidate(result)
        source = candidate.additional_sources[0]
        with tempfile.TemporaryDirectory() as directory:
            evidence_root = Path(directory) / "evidence"
            evidence_root.mkdir()
            artifact_path = evidence_root / "filing.pdf"
            artifact_path.write_bytes(b"different filing bytes")
            with self.assertRaisesRegex(ValueError, "SHA-256 verification failed"):
                resolve_primary_source_artifacts(
                    sources=candidate.all_sources,
                    artifact_paths={source.source_ref: artifact_path},
                    evidence_root=evidence_root,
                )

    def materialize(self, db_path, candidate, raw_descriptor, validation_report):
        evidence_root = Path(db_path).parent / "source-evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        artifact_paths = {}
        primary_sources = [
            source for source in candidate.all_sources
            if source.validation_status is QualityStatus.VALID
            and getattr(source.source_tier, "value", source.source_tier) == "primary"
        ]
        for index, source in enumerate(primary_sources):
            artifact_path = evidence_root / f"primary-{index}.pdf"
            artifact_path.write_bytes(REVIEWED_FILING_BYTES)
            artifact_paths[source.source_ref] = artifact_path
        verified = resolve_primary_source_artifacts(
            sources=candidate.all_sources,
            artifact_paths=artifact_paths,
            evidence_root=evidence_root,
        )
        return materialize_canonical_snapshot(
            db_path,
            candidate,
            raw_descriptor,
            validation_report,
            verified_source_artifacts=verified,
        )

    def test_materialization_rolls_back_on_write_failure(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        duplicate_entity = replace(candidate, entities=candidate.entities + (candidate.entities[0],))
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "rollback.sqlite"
            with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
                self.materialize(
                    db_path,
                    duplicate_entity,
                    staged.raw_descriptor,
                    result.validation_report,
                )
            if db_path.exists() and db_path.stat().st_size > 0:
                connection = sqlite3.connect(db_path)
                try:
                    tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                    self.assertNotIn("dataset_metadata", tables)
                finally:
                    connection.close()

    def test_canonical_provider_persists_no_physical_path_and_exposes_source(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "canonical.sqlite"
            self.materialize(
                db_path, candidate, staged.raw_descriptor, result.validation_report
            )
            provider = CanonicalSqliteDatasetProvider(db_path)
            ref = provider.current_dataset_ref()
            source = provider.get_source(ref, result.candidate.source.source_ref)
            connection = sqlite3.connect(db_path)
            try:
                metadata_rows = connection.execute("SELECT * FROM dataset_metadata").fetchall()
                source_rows = connection.execute("SELECT source_url, publisher FROM sources").fetchall()
            finally:
                connection.close()
        self.assertIsNotNone(source)
        self.assertEqual(source.source_type, "csv")
        self.assertTrue(source.source_url.startswith("urn:csv:"))
        self.assertNotIn("financials.csv", str(metadata_rows))
        self.assertNotIn("\\", str(source_rows))
        self.assertNotIn("/private/", str(source_rows))

    def test_provider_rejects_persisted_observation_identity_corruption(self):
        for column in ("dataset_id", "dataset_snapshot_id"):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as directory:
                staged = self.stage(self.valid_text())
                result = normalize_csv_dataset(
                    staged,
                    dataset_id="csv-dataset",
                    mapping=self.mapping(),
                    registry=demo_metric_registry(),
                )
                candidate = self.reviewed_candidate(result)
                db_path = Path(directory) / "corrupt.sqlite"
                self.materialize(
                    db_path, candidate, staged.raw_descriptor, result.validation_report
                )
                connection = sqlite3.connect(db_path)
                try:
                    connection.execute(f"UPDATE observations SET {column} = ?", ("corrupt",))
                    connection.commit()
                finally:
                    connection.close()
                provider = CanonicalSqliteDatasetProvider(db_path, dataset_id="csv-dataset")
                ref = provider.current_dataset_ref()
                with self.assertRaisesRegex(DatasetProviderError, "persisted observation"):
                    provider.get_metric(ref, "BANK-X", "2024_Q4", "bank.roa")
                with self.assertRaisesRegex(DatasetProviderError, "persisted observation"):
                    provider.get_entity_metrics(ref, "BANK-X", ("2024_Q4",), ("bank.roa",))
                connection = sqlite3.connect(db_path)
                try:
                    observation_id = connection.execute(
                        "SELECT observation_id FROM observations WHERE entity_id = 'BANK-X'"
                    ).fetchone()[0]
                finally:
                    connection.close()
                with self.assertRaisesRegex(DatasetProviderError, "persisted observation"):
                    provider.resolve_observation(ref, observation_id)

    def test_structural_csv_validation_never_accepts_numeric_values_by_itself(self):
        staged = self.stage("Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n")
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(include_roe=False),
            registry=demo_metric_registry(),
        )
        self.assertEqual(result.validation_report.status.value, "VALID")
        self.assertEqual(result.candidate.observations[0].validation_status, QualityStatus.PENDING_VALIDATION)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "pending observations"):
                self.materialize(
                    Path(directory) / "unreviewed.sqlite",
                    result.candidate,
                    staged.raw_descriptor,
                    result.validation_report,
                )

    def test_provider_rejects_wrong_canonical_json_types(self):
        for table, column, operation in (
            ("entities", "attributes_json", "capabilities"),
            ("observations", "metadata_json", "observation"),
        ):
            with self.subTest(table=table), tempfile.TemporaryDirectory() as directory:
                staged = self.stage(self.valid_text())
                result = normalize_csv_dataset(
                    staged,
                    dataset_id="csv-dataset",
                    mapping=self.mapping(),
                    registry=demo_metric_registry(),
                )
                candidate = self.reviewed_candidate(result)
                db_path = Path(directory) / "malformed-json.sqlite"
                self.materialize(
                    db_path, candidate, staged.raw_descriptor, result.validation_report
                )
                connection = sqlite3.connect(db_path)
                try:
                    connection.execute(f"UPDATE {table} SET {column} = ?", ("[]",))
                    connection.commit()
                finally:
                    connection.close()
                provider = CanonicalSqliteDatasetProvider(db_path, dataset_id="csv-dataset")
                ref = provider.current_dataset_ref()
                with self.assertRaisesRegex(DatasetProviderError, "must be an object"):
                    if operation == "capabilities":
                        provider.get_capabilities(ref)
                    else:
                        provider.get_metric(ref, "BANK-X", "2024_Q4", "bank.roa")

    def test_provider_rejects_invalid_canonical_json(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "invalid-json.sqlite"
            self.materialize(
                db_path, candidate, staged.raw_descriptor, result.validation_report
            )
            connection = sqlite3.connect(db_path)
            try:
                connection.execute("UPDATE entities SET attributes_json = ?", ("not-json",))
                connection.commit()
            finally:
                connection.close()
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id="csv-dataset")
            with self.assertRaisesRegex(DatasetProviderError, "metadata JSON is invalid"):
                provider.get_capabilities(provider.current_dataset_ref())

    def test_paths_cannot_enter_persisted_csv_source_data(self):
        for label in ("/home/user/file.csv", "/Users/user/file.csv", "/mnt/data/file.csv", "/tmp/file.csv"):
            with self.subTest(label=label):
                staged = self.stage(self.valid_text())
                with self.assertRaisesRegex(ValueError, "local path"):
                    normalize_csv_dataset(
                        staged,
                        dataset_id="csv-dataset",
                        mapping=self.mapping(),
                        registry=demo_metric_registry(),
                        publisher=label,
                    )

    def test_failed_new_target_is_removed_and_retry_succeeds(self):
        staged = self.stage(self.valid_text())
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
        )
        candidate = self.reviewed_candidate(result)
        duplicate_entity = replace(
            candidate,
            entities=candidate.entities + (candidate.entities[0],),
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "retry.sqlite"
            with self.assertRaises(sqlite3.IntegrityError):
                self.materialize(
                    db_path,
                    duplicate_entity,
                    staged.raw_descriptor,
                    result.validation_report,
                )
            self.assertFalse(db_path.exists())
            accepted = self.materialize(
                db_path,
                candidate,
                staged.raw_descriptor,
                result.validation_report,
            )
            self.assertEqual(accepted.status, "accepted")
            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
