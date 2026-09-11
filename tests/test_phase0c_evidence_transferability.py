from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from thesis_data.analysis_request import AnalysisRequest
from thesis_data.application_runtime import ApplicationRuntimeContext
from thesis_data.canonical_snapshot import CANONICAL_SNAPSHOT_SCHEMA_VERSION, materialize_canonical_snapshot
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.csv_onboarding import stage_csv_bytes
from thesis_data.dataset_contract import DatasetEvidence, DatasetSource
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.dataset_tool_runtime import DatasetToolRuntime
from thesis_data.evidence_contract import DatasetDocument
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.onboarding_contract import FieldMappingSpec, FieldMetricMapping, demo_metric_registry
from thesis_data.onboarding_validation import normalize_csv_dataset
from thesis_data.storage import create_gold_snapshot_schema
from thesis_data.schema import QualityStatus
from thesis_data.transferability import run_metric_probe


class Phase0CEvidenceBoundaryTests(unittest.TestCase):
    def mapping(self) -> FieldMappingSpec:
        return FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="company.roa",
                    unit="percent",
                    analytical_level="company",
                ),
            ),
        )

    def normalized(self):
        staged = stage_csv_bytes(
            b"Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n",
            raw_dataset_id="phase0c-upload",
            original_name="financials.csv",
        )
        result = normalize_csv_dataset(
            staged,
            dataset_id="csv-dataset",
            mapping=self.mapping(),
            registry=demo_metric_registry(),
            created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )
        return staged, result

    def with_evidence(self):
        staged, result = self.normalized()
        document_source = DatasetSource(
            source_ref="document-source:filing-1",
            source_type="pdf",
            source_tier="primary",
            source_url="urn:document:filing-1",
            publisher="Issuer reporting service",
            retrieved_at="2026-09-11T00:00:00+00:00",
            content_hash="document-source-hash",
            validation_status=QualityStatus.VALID,
        )
        document = DatasetDocument(
            document_id="document-filing-1",
            dataset_id=result.candidate.metadata.dataset_id,
            dataset_snapshot_id=result.candidate.metadata.dataset_snapshot_id,
            source_ref=document_source.source_ref,
            document_type="financial_filing",
            title="Quarterly filing extract",
            publisher="Issuer reporting service",
            content_hash="document-content-hash",
            metadata={"extraction": "pre_extracted", "language": "en"},
        )
        evidence = DatasetEvidence(
            evidence_id="evidence-roa-context",
            source_ref=document_source.source_ref,
            document_id=document.document_id,
            entity_id="BANK-X",
            period_id="2024_Q4",
            metric_id=None,
            locator="page:1/section:profitability",
            quote="The filing reports profitability for the quarter.",
        )
        candidate = replace(
            result.candidate,
            additional_sources=(document_source,),
            documents=(document,),
            evidence=(evidence,),
        )
        return staged, replace(result, candidate=candidate)

    def _request(
        self,
        ref,
        *,
        dataset_id=None,
        snapshot_id=None,
        entity="BANK-X",
        metric="company.roa",
        period="2024_Q4",
    ):
        return AnalysisRequest(
            request_id="phase0c-request",
            dataset_id=dataset_id or ref.dataset_id,
            dataset_snapshot_id=snapshot_id or ref.dataset_snapshot_id,
            target_entity_ids=(entity,),
            period_ids=(period,),
            metric_ids=(metric,),
            objective="Read one portable observation.",
        )

    def test_document_contract_is_minimal_and_rejects_physical_paths(self):
        valid = DatasetDocument(
            document_id="document-1",
            dataset_id="dataset-1",
            dataset_snapshot_id="snapshot-1",
            source_ref="source:1",
            document_type="filing",
            title="Filing",
            publisher="Publisher",
            content_hash="hash",
        )
        self.assertEqual(valid.contract_version, "document-contract-v1")
        self.assertEqual(valid.metadata, {})
        for field, value in (
            ("source_ref", "source/path"),
            ("publisher", r"C:\private\filing.pdf"),
            ("publisher", "/home/private/filing.pdf"),
            ("title", r"C:\private\report.pdf"),
            ("title", "/home/user/report.pdf"),
            ("title", "/Users/user/report.pdf"),
            ("metadata", {"local_path": "private/filing.pdf"}),
        ):
            with self.subTest(field=field, value=value):
                payload = valid.model_dump()
                payload[field] = value
                with self.assertRaises(ValidationError):
                    DatasetDocument(**payload)

    def test_dataset_evidence_can_remain_unbound_to_metric(self):
        evidence = DatasetEvidence(
            evidence_id="evidence-1",
            source_ref="source-1",
            document_id="document-1",
            entity_id="BANK-X",
            period_id="2024_Q4",
            locator="page:1",
            quote="A contextual statement.",
        )
        self.assertIsNone(evidence.metric_id)

    def test_csv_snapshot_without_evidence_does_not_advertise_get_evidence(self):
        staged, result = self.normalized()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.sqlite"
            materialize_canonical_snapshot(path, result.candidate, staged.raw_descriptor, result.validation_report)
            provider = CanonicalSqliteDatasetProvider(path)
            capabilities = provider.get_capabilities(provider.current_dataset_ref())
        self.assertNotIn("get_evidence", {item.value for item in capabilities.supported_operations})

    def test_evidence_rows_are_advertised_and_retrieved_deterministically(self):
        staged, result = self.with_evidence()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.sqlite"
            materialize_canonical_snapshot(path, result.candidate, staged.raw_descriptor, result.validation_report)
            provider = CanonicalSqliteDatasetProvider(path)
            ref = provider.current_dataset_ref()
            capabilities = provider.get_capabilities(ref)
            document_source_ref = result.candidate.documents[0].source_ref
            evidence = provider.get_evidence(ref, (document_source_ref,))
            filtered = provider.get_evidence(
                ref,
                (document_source_ref,),
                entity_id="BANK-X",
                period_id="2024_Q4",
            )
            runtime = DatasetToolRuntime(ApplicationRuntimeContext.from_request(
                self._request(ref), provider
            ))
            runtime.get_metric("BANK-X", "2024_Q4", "company.roa")
            runtime_evidence = runtime.get_evidence(
                (document_source_ref,),
                entity_id="BANK-X",
                period_id="2024_Q4",
            )
            connection = sqlite3.connect(path)
            try:
                persisted_sources = {
                    row[0] for row in connection.execute("SELECT source_ref FROM sources")
                }
                persisted_observation_source = connection.execute(
                    "SELECT source_ref FROM observations"
                ).fetchone()[0]
                persisted_document_source = connection.execute(
                    "SELECT source_ref FROM documents"
                ).fetchone()[0]
                persisted_evidence_source = connection.execute(
                    "SELECT source_ref FROM evidence"
                ).fetchone()[0]
                accepted_snapshot_id = connection.execute(
                    "SELECT dataset_snapshot_id FROM dataset_metadata"
                ).fetchone()[0]
                bound_ids = connection.execute(
                    "SELECT dataset_snapshot_id FROM observations"
                ).fetchall()
                document_bound_id = connection.execute(
                    "SELECT dataset_snapshot_id FROM documents"
                ).fetchone()[0]
                evidence_bound_id = connection.execute(
                    "SELECT dataset_snapshot_id FROM evidence"
                ).fetchone()[0]
            finally:
                connection.close()
        self.assertIn("get_evidence", {item.value for item in capabilities.supported_operations})
        self.assertEqual(evidence, filtered)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].document_id, "document-filing-1")
        self.assertIsNone(evidence[0].metric_id)
        self.assertEqual(runtime_evidence, filtered)
        self.assertNotEqual(result.candidate.source.source_ref, document_source_ref)
        self.assertEqual(persisted_sources, {result.candidate.source.source_ref, document_source_ref})
        self.assertEqual(persisted_observation_source, result.candidate.source.source_ref)
        self.assertEqual(persisted_document_source, document_source_ref)
        self.assertEqual(persisted_evidence_source, document_source_ref)
        self.assertTrue(accepted_snapshot_id.startswith("snapshot-"))
        self.assertEqual({row[0] for row in bound_ids}, {accepted_snapshot_id})
        self.assertEqual(document_bound_id, accepted_snapshot_id)
        self.assertEqual(evidence_bound_id, accepted_snapshot_id)

    def test_snapshot_manifest_identity_binds_documents_and_evidence(self):
        staged, result = self.with_evidence()

        def materialize(candidate, directory, filename):
            path = Path(directory) / filename
            accepted = materialize_canonical_snapshot(
                path,
                candidate,
                staged.raw_descriptor,
                result.validation_report,
            )
            return accepted.dataset_snapshot_id

        with tempfile.TemporaryDirectory() as directory:
            base_id = materialize(result.candidate, directory, "base.sqlite")
            same_id = materialize(result.candidate, directory, "same.sqlite")
            changed_document = result.candidate.documents[0].model_copy(
                update={"content_hash": "changed-document-content"}
            )
            changed_document_id = materialize(
                replace(result.candidate, documents=(changed_document,)),
                directory,
                "changed-document.sqlite",
            )
            changed_quote = result.candidate.evidence[0].model_copy(
                update={"quote": "A changed contextual statement."}
            )
            changed_quote_id = materialize(
                replace(result.candidate, evidence=(changed_quote,)),
                directory,
                "changed-quote.sqlite",
            )
            changed_locator = result.candidate.evidence[0].model_copy(
                update={"locator": "page:2/section:profitability"}
            )
            changed_locator_id = materialize(
                replace(result.candidate, evidence=(changed_locator,)),
                directory,
                "changed-locator.sqlite",
            )

        self.assertEqual(base_id, same_id)
        self.assertNotEqual(base_id, changed_document_id)
        self.assertNotEqual(base_id, changed_quote_id)
        self.assertNotEqual(base_id, changed_locator_id)

    def test_publication_rejects_invalid_multi_source_provenance(self):
        staged, result = self.with_evidence()
        cases = {
            "evidence source mismatch": replace(
                result.candidate,
                evidence=(result.candidate.evidence[0].model_copy(
                    update={"source_ref": result.candidate.source.source_ref}
                ),),
            ),
            "unknown evidence source": replace(
                result.candidate,
                evidence=(result.candidate.evidence[0].model_copy(
                    update={"source_ref": "unknown-source"}
                ),),
            ),
            "unknown document": replace(
                result.candidate,
                evidence=(result.candidate.evidence[0].model_copy(
                    update={"document_id": "unknown-document"}
                ),),
            ),
            "document snapshot mismatch": replace(
                result.candidate,
                documents=(result.candidate.documents[0].model_copy(
                    update={"dataset_snapshot_id": "wrong-snapshot"}
                ),),
            ),
            "duplicate source refs": replace(
                result.candidate,
                additional_sources=(result.candidate.source,),
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, candidate in cases.items():
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        materialize_canonical_snapshot(
                            Path(directory) / (re.sub(r"[^a-z]+", "-", name) + ".sqlite"),
                            candidate,
                            staged.raw_descriptor,
                            result.validation_report,
                        )

    def test_evidence_and_document_identity_must_match_snapshot(self):
        staged, result = self.with_evidence()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.sqlite"
            materialize_canonical_snapshot(path, result.candidate, staged.raw_descriptor, result.validation_report)
            connection = sqlite3.connect(path)
            connection.execute("UPDATE evidence SET dataset_id = ?", ("wrong",))
            connection.commit()
            connection.close()
            provider = CanonicalSqliteDatasetProvider(path)
            ref = provider.current_dataset_ref()
            with self.assertRaisesRegex(DatasetProviderError, "persisted evidence identity"):
                provider.get_evidence(ref, (result.candidate.documents[0].source_ref,))

            connection = sqlite3.connect(path)
            connection.execute("UPDATE evidence SET dataset_id = ?", (ref.dataset_id,))
            connection.execute("UPDATE documents SET dataset_snapshot_id = ?", ("wrong",))
            connection.commit()
            connection.close()
            with self.assertRaisesRegex(DatasetProviderError, "document identity"):
                provider.get_evidence(ref, (result.candidate.documents[0].source_ref,))

    def test_provider_supports_one_canonical_schema_and_contract_version(self):
        staged, result = self.normalized()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical.sqlite"
            materialize_canonical_snapshot(path, result.candidate, staged.raw_descriptor, result.validation_report)
            for column, value, message in (
                ("schema_version", "canonical-snapshot-future", "schema version"),
                ("contract_version", "onboarding-contract-future", "contract version"),
            ):
                with self.subTest(column=column):
                    connection = sqlite3.connect(path)
                    connection.execute(f"UPDATE dataset_metadata SET {column} = ?", (value,))
                    connection.commit()
                    connection.close()
                    with self.assertRaisesRegex(DatasetProviderError, message):
                        CanonicalSqliteDatasetProvider(path).current_dataset_ref()
                    connection = sqlite3.connect(path)
                    connection.execute(
                        f"UPDATE dataset_metadata SET {column} = ?",
                        (CANONICAL_SNAPSHOT_SCHEMA_VERSION if column == "schema_version" else "onboarding-contract-v1",),
                    )
                    connection.commit()
                    connection.close()

    def test_phase0b_snapshot_without_optional_evidence_tables_remains_readable(self):
        staged, result = self.normalized()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-canonical.sqlite"
            materialize_canonical_snapshot(path, result.candidate, staged.raw_descriptor, result.validation_report)
            connection = sqlite3.connect(path)
            connection.execute("DROP TABLE evidence")
            connection.execute("DROP TABLE documents")
            connection.commit()
            connection.close()
            provider = CanonicalSqliteDatasetProvider(path)
            capabilities = provider.get_capabilities(provider.current_dataset_ref())
        self.assertNotIn("get_evidence", {item.value for item in capabilities.supported_operations})

    def test_same_application_helper_reads_canonical_and_gold_providers(self):
        staged, result = self.normalized()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical_path = root / "canonical.sqlite"
            materialize_canonical_snapshot(canonical_path, result.candidate, staged.raw_descriptor, result.validation_report)
            canonical_provider = CanonicalSqliteDatasetProvider(canonical_path)
            canonical_ref = canonical_provider.current_dataset_ref()
            canonical_request = self._request(canonical_ref)
            canonical_observation = run_metric_probe(
                canonical_provider,
                canonical_ref,
                canonical_request,
                entity_id="BANK-X",
                period_id="2024_Q4",
                metric_id="company.roa",
            )

            gold_path = root / "validated.sqlite"
            create_gold_snapshot_schema(gold_path)
            connection = sqlite3.connect(gold_path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-snapshot-fixture", "2026-09-11T00:00:00Z", "gold", "{}"),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "gold-source", "filing", "primary", "https://example.test/filing",
                    "2026-09-11", "private/fixture.pdf", "gold-source-hash", "Issuer",
                    "test", "valid", None,
                ),
            )
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "gold-observation-1", "BANK-GOLD", "banking", "company.roa", 9.9,
                    "percent", "FY-2024-Q4", "2024-12-31", "point_in_time", "gold-source",
                    "fixture:page:1", "valid", None,
                ),
            )
            connection.commit()
            connection.close()
            gold_provider = GoldSqliteDatasetProvider(gold_path, dataset_id="gold-fixture")
            gold_ref = gold_provider.current_dataset_ref()
            gold_request = self._request(
                gold_ref,
                entity="BANK-GOLD",
                metric="company.roa",
                period="FY-2024-Q4",
            )
            gold_observation = run_metric_probe(
                gold_provider,
                gold_ref,
                gold_request,
                entity_id="BANK-GOLD",
                period_id="FY-2024-Q4",
                metric_id="company.roa",
            )

        self.assertEqual(canonical_observation.value, 1.2)
        self.assertEqual(gold_observation.value, 9.9)
        helper_source = Path("src/thesis_data/transferability.py").read_text(encoding="utf-8")
        for forbidden in ("Gold", "sqlite", "CSV", "metric_observations", "ACB", "TCB", "VPB", "MBB", "VCB"):
            self.assertNotIn(forbidden, helper_source)


if __name__ == "__main__":
    unittest.main()
