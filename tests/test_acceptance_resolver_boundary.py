import json
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest

from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_data.canonical_snapshot import materialize_canonical_snapshot
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.csv_onboarding import stage_csv_bytes
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    ObservationEvidenceRef,
    ObservationReview,
    PeerUniverse,
    canonical_observation_id,
)
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.evidence_contract import DatasetDocument
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.in_memory_provider import InMemoryFinancialDatasetProvider
from thesis_data.onboarding_contract import (
    FieldMappingSpec,
    FieldMetricMapping,
    demo_metric_registry,
)
from thesis_data.onboarding_validation import normalize_csv_dataset, reconcile_candidate_observations
from thesis_data.schema import ClaimDataRef, QualityStatus
from thesis_data.storage import create_gold_snapshot_schema


class AcceptanceResolverBoundaryTests(unittest.TestCase):
    def _memory_provider(self):
        ref = DatasetRef(dataset_id="memory-dataset", dataset_snapshot_id="memory-snapshot")
        catalog = DatasetCapabilityCatalog(
            dataset_ref=ref,
            entities=(
                DatasetEntity(
                    entity_id="entity-a",
                    entity_type=DatasetEntityType.COMPANY,
                    display_name="Entity A",
                ),
                DatasetEntity(
                    entity_id="entity-b",
                    entity_type=DatasetEntityType.COMPANY,
                    display_name="Entity B",
                ),
                DatasetEntity(
                    entity_id="entity-c",
                    entity_type=DatasetEntityType.COMPANY,
                    display_name="Entity C",
                ),
                DatasetEntity(
                    entity_id="macro-vn",
                    entity_type=DatasetEntityType.MACRO,
                    display_name="Vietnam macro",
                ),
            ),
            periods=(DatasetPeriod(period_id="2024_Q4", label="Q4 2024"),),
            metrics=(
                DatasetMetric(
                    metric_id="company.roa",
                    display_name="ROA",
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                ),
                DatasetMetric(
                    metric_id="company.derived",
                    display_name="Derived ROA",
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                ),
                DatasetMetric(
                    metric_id="company.missing",
                    display_name="Missing ROA",
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                ),
                DatasetMetric(
                    metric_id="macro.policy",
                    display_name="Policy rate",
                    analytical_level=AnalyticalLevel.MACRO,
                    default_unit="percent_per_annum",
                ),
            ),
            peer_universes=(
                PeerUniverse(
                    peer_universe_id="bank-peers",
                    display_name="Bank peers",
                    entity_ids=("entity-a", "entity-b", "entity-c"),
                ),
            ),
            supported_operations=tuple(
                {
                    "get_metric",
                    "get_entity_metrics",
                    "get_peer_benchmark",
                    "get_evidence",
                    "get_source",
                    "get_macro_observation",
                    "resolve_observation",
                }
            ),
        )
        observations = (
            CanonicalObservation(
                observation_id="obs-memory-a",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a",
                period_id="2024_Q4",
                metric_id="company.roa",
                value=1.0,
                unit="percent",
                source_ref="source-company",
                source_locator="page:1",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="obs-memory-b",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-b",
                period_id="2024_Q4",
                metric_id="company.roa",
                value=3.0,
                unit="percent",
                source_ref="source-company",
                source_locator="page:2",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="obs-memory-c",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-c",
                period_id="2024_Q4",
                metric_id="company.roa",
                value=100.0,
                unit="percent",
                source_ref="source-company",
                source_locator="page:3",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="obs-memory-macro",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="macro-vn",
                period_id="2024_Q4",
                metric_id="macro.policy",
                value=4.5,
                unit="percent_per_annum",
                source_ref="source-macro",
                source_locator="decision:1123",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="obs-memory-missing",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a",
                period_id="2024_Q4",
                metric_id="company.missing",
                validation_status=QualityStatus.MISSING,
                missing_reason="DATA_UNAVAILABLE",
            ),
            CanonicalObservation(
                observation_id="obs-memory-derived",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a",
                period_id="2024_Q4",
                metric_id="company.derived",
                value=2.0,
                unit="percent",
                validation_status=QualityStatus.VALID,
                derivation_method="formula-v1",
                input_observation_ids=("obs-memory-a", "obs-memory-b"),
            ),
        )
        sources = (
            DatasetSource(
                source_ref="source-company",
                source_type="filing",
                source_tier="primary",
                source_url="https://example.test/company",
                publisher="Issuer",
                retrieved_at="2026-09-11",
                content_hash="company-hash",
                validation_status=QualityStatus.VALID,
            ),
            DatasetSource(
                source_ref="source-macro",
                source_type="policy",
                source_tier="primary",
                source_url="https://example.test/macro",
                publisher="SBV",
                retrieved_at="2026-09-11",
                content_hash="macro-hash",
                validation_status=QualityStatus.VALID,
            ),
        )
        evidence = (
            DatasetEvidence(
                evidence_id="evidence-memory-company",
                source_ref="source-company",
                entity_id="entity-a",
                period_id="2024_Q4",
                locator="page:1",
                quote="ROA was 1 percent.",
            ),
            DatasetEvidence(
                evidence_id="evidence-memory-macro",
                source_ref="source-macro",
                period_id="2024_Q4",
                metric_id="macro.policy",
                locator="decision:1",
                quote="The policy rate is 4.5 percent.",
            ),
        )
        return InMemoryFinancialDatasetProvider(
            catalog,
            observations=observations,
            sources=sources,
            evidence=evidence,
        ), ref

    @staticmethod
    def _ref(ref_id, ref_type, entity, metric):
        return ClaimDataRef(
            ref_id=ref_id,
            ref_type=ref_type,
            entity=entity,
            period="2024_Q4",
            metric_id=metric,
        )

    def test_in_memory_resolver_routes_observations_evidence_and_benchmark(self):
        provider, ref = self._memory_provider()
        resolver = ProviderStage1DatasetResolver(provider, ref)

        company = resolver.resolve_observation_ref(
            self._ref("obs-memory-a", "observation", "entity-a", "company.roa")
        )
        macro = resolver.resolve_observation_ref(
            self._ref("obs-memory-macro", "macro_observation", "macro-vn", "macro.policy")
        )
        missing = resolver.resolve_observation_ref(
            self._ref("obs-memory-missing", "missing_cell", "entity-a", "company.missing")
        )
        derived = resolver.resolve_observation_ref(
            self._ref("obs-memory-derived", "derived_metric", "entity-a", "company.derived")
        )
        evidence = resolver.resolve_evidence("evidence-memory-company")
        source = resolver.resolve_source("source-company")
        benchmark = resolver.resolve_benchmark(
            peer_universe_id="bank-peers",
            peer_entity_ids=("entity-a", "entity-b"),
            period_id="2024_Q4",
            metric_id="company.roa",
        )

        self.assertEqual(company.value, 1.0)
        self.assertEqual(macro.value, 4.5)
        self.assertEqual(missing.validation_status, QualityStatus.MISSING)
        self.assertEqual(missing.missing_reason, "DATA_UNAVAILABLE")
        self.assertEqual(derived.derivation_method, "formula-v1")
        self.assertEqual(derived.input_observation_ids, ("obs-memory-a", "obs-memory-b"))
        self.assertEqual(evidence.evidence_id, "evidence-memory-company")
        self.assertEqual(evidence.metric_id, None)
        self.assertEqual(source.source_ref, "source-company")
        self.assertEqual(benchmark.value, 2.0)
        self.assertEqual(set(benchmark.input_observation_ids), {"obs-memory-a", "obs-memory-b"})
        self.assertNotIn("obs-memory-c", benchmark.input_observation_ids)

    def test_memory_resolver_returns_canonical_resource_for_acceptance_scope_check(self):
        provider, ref = self._memory_provider()
        resolver = ProviderStage1DatasetResolver(provider, ref)
        observation = resolver.resolve_observation_ref(
            self._ref("obs-memory-a", "observation", "entity-b", "company.roa")
        )
        self.assertEqual(observation.entity_id, "entity-a")
        self.assertEqual(observation.metric_id, "company.roa")

    def _gold_fixture(self, root: Path, *, ambiguous_evidence: bool = False):
        db_path = root / "gold.sqlite"
        create_gold_snapshot_schema(db_path)
        connection = sqlite3.connect(db_path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-snapshot", "2026-09-11T00:00:00Z", "gold", "{}"),
        )
        connection.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "source-company",
                    "filing",
                    "primary",
                    "https://example.test/company",
                    "2026-09-11",
                    "private/company.pdf",
                    "company-hash",
                    "Issuer",
                    "public",
                    "valid",
                    None,
                ),
                (
                    "source-macro",
                    "policy",
                    "primary",
                    "https://example.test/macro",
                    "2026-09-11",
                    "private/macro.html",
                    "macro-hash",
                    "SBV",
                    "public",
                    "valid",
                    None,
                ),
            ),
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "obs-gold-a",
                    "entity-a",
                    "bank",
                    "company.roa",
                    1.0,
                    "percent",
                    "2024_Q4",
                    "2024-12-31",
                    "point_in_time",
                    "source-company",
                    "page:1",
                    "valid",
                    None,
                ),
                (
                    "obs-gold-b",
                    "entity-b",
                    "bank",
                    "company.roa",
                    3.0,
                    "percent",
                    "2024_Q4",
                    "2024-12-31",
                    "point_in_time",
                    "source-company",
                    "page:2",
                    "valid",
                    None,
                ),
                (
                    "obs-gold-c",
                    "entity-c",
                    "bank",
                    "company.roa",
                    100.0,
                    "percent",
                    "2024_Q4",
                    "2024-12-31",
                    "point_in_time",
                    "source-company",
                    "page:3",
                    "valid",
                    None,
                ),
                (
                    "obs-gold-missing",
                    "entity-a",
                    "bank",
                    "company.missing",
                    None,
                    "percent",
                    "2024_Q4",
                    "2024-12-31",
                    "point_in_time",
                    None,
                    None,
                    "missing",
                    "DATA_UNAVAILABLE",
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO macro_observations_v2 (
                observation_id, indicator_id, value, unit, period, source_id,
                quality_status, reason, source_series_id,
                indicator_definition_version, frequency, observation_date,
                effective_from, as_of_date, period_basis, alignment_method,
                source_locator, transformation_version,
                input_observation_ids_json, adjudication_ref, review_check_ids_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "obs-gold-macro",
                "macro.policy",
                4.5,
                "percent_per_annum",
                "2024_Q4",
                "source-macro",
                "valid",
                None,
                "sbv-policy",
                "definition-v1",
                "event",
                "2023-06-19",
                "2023-06-19",
                "2024-12-31",
                "state_at_period_end",
                "latest_effective_state_v1",
                "decision:1123",
                "state-carry-forward-v1",
                "[]",
                "adjudication-policy",
                '["check-a","check-b"]',
            ),
        )
        connection.execute(
            """
            INSERT INTO derived_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "derived-gold-roa",
                "entity-a",
                "bank",
                "company.derived",
                2.0,
                "percent",
                "2024_Q4",
                "derived_period_v1",
                json.dumps(["obs-gold-a", "obs-gold-b"]),
                "formula-v1",
                "valid",
                None,
            ),
        )
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "evidence-gold-company",
                    "source-company",
                    "company.pdf",
                    1,
                    "ROA",
                    "2024_Q4",
                    "entity-a",
                    "ROA was 1 percent.",
                    1.0,
                    "text",
                    1,
                ),
            ),
        )
        connection.execute(
            "INSERT INTO macro_evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "evidence-gold-macro",
                "source-macro",
                "macro.policy",
                "2024_Q4",
                "policy.html",
                "decision:1123",
                "The SBV refinancing rate is 4.5 percent.",
                "2024-12-31",
                "2023-06-19",
                "html",
            ),
        )
        if ambiguous_evidence:
            connection.execute(
                "INSERT INTO macro_evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "evidence-gold-company",
                    "source-macro",
                    "macro.policy",
                    "2024_Q4",
                    "policy.html",
                    "decision:1123",
                    "Duplicate evidence ID in another domain.",
                    "2024-12-31",
                    "2023-06-19",
                    "html",
                ),
            )
        connection.commit()
        connection.close()
        return db_path, DatasetRef(
            dataset_id="gold-dataset",
            dataset_snapshot_id="gold-snapshot",
        )

    def test_gold_resolver_supports_typed_observations_derived_evidence_and_peer_subset(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self._gold_fixture(Path(directory))
            provider = GoldSqliteDatasetProvider(db_path, dataset_id=ref.dataset_id)
            resolver = ProviderStage1DatasetResolver(provider, ref)

            company = resolver.resolve_observation_ref(
                self._ref("obs-gold-a", "observation", "entity-a", "company.roa")
            )
            macro = resolver.resolve_observation_ref(
                self._ref("obs-gold-macro", "macro_observation", "VN", "macro.policy")
            )
            missing = resolver.resolve_observation_ref(
                self._ref("obs-gold-missing", "missing_cell", "entity-a", "company.missing")
            )
            derived = resolver.resolve_observation_ref(
                self._ref("derived-gold-roa", "derived_metric", "entity-a", "company.derived")
            )
            company_evidence = resolver.resolve_evidence("evidence-gold-company")
            macro_evidence = resolver.resolve_evidence("evidence-gold-macro")
            benchmark = resolver.resolve_benchmark(
                peer_universe_id="sector:bank",
                peer_entity_ids=("entity-a", "entity-b"),
                period_id="2024_Q4",
                metric_id="company.roa",
            )

        self.assertEqual(company.value, 1.0)
        self.assertEqual(company.source_locator, "page:1")
        self.assertEqual(macro.value, 4.5)
        self.assertEqual(macro.source_locator, "decision:1123")
        self.assertEqual(missing.validation_status, QualityStatus.MISSING)
        self.assertEqual(derived.derivation_method, "formula-v1")
        self.assertEqual(derived.input_observation_ids, ("obs-gold-a", "obs-gold-b"))
        self.assertIsNone(derived.source_ref)
        self.assertEqual(company_evidence.metric_id, None)
        self.assertEqual(macro_evidence.metric_id, "macro.policy")
        self.assertEqual(benchmark.value, 2.0)
        self.assertEqual(set(benchmark.input_observation_ids), {"obs-gold-a", "obs-gold-b"})
        self.assertNotIn("obs-gold-c", benchmark.input_observation_ids)

    def test_gold_exact_evidence_unknown_and_cross_domain_ambiguity_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self._gold_fixture(Path(directory), ambiguous_evidence=True)
            provider = GoldSqliteDatasetProvider(db_path, dataset_id=ref.dataset_id)
            resolver = ProviderStage1DatasetResolver(provider, ref)

            self.assertIsNone(resolver.resolve_evidence("unknown-evidence"))
            with self.assertRaisesRegex(DatasetProviderError, "ambiguous"):
                resolver.resolve_evidence("evidence-gold-company")

    def _canonical_fixture(self, root: Path):
        staged = stage_csv_bytes(
            b"Company,Quarter,ROA (%)\nBANK-X,Q4-2024,1.2\n",
            raw_dataset_id="resolver-upload",
            original_name="financials.csv",
        )
        mapping = FieldMappingSpec(
            entity_field="Company",
            period_field="Quarter",
            metric_mappings=(
                FieldMetricMapping(
                    raw_field="ROA (%)",
                    metric_id="bank.roa",
                    unit="percent",
                    analytical_level="company",
                ),
            ),
        )
        result = normalize_csv_dataset(
            staged,
            dataset_id="canonical-dataset",
            mapping=mapping,
            registry=demo_metric_registry(),
            created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        )
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
        )
        evidence = DatasetEvidence(
            evidence_id="evidence-canonical-company",
            source_ref=document_source.source_ref,
            document_id=document.document_id,
            entity_id="BANK-X",
            period_id="2024_Q4",
            locator="page:1",
            quote="The filing reports profitability for the quarter.",
        )
        candidate = replace(
            result.candidate,
            documents=(document,),
            evidence=(evidence,),
        )
        reviewed = reconcile_candidate_observations(
            candidate,
            primary_sources=(document_source,),
            reviews={
                canonical_observation_id(
                    candidate.metadata.dataset_snapshot_id,
                    "BANK-X",
                    "2024_Q4",
                    "bank.roa",
                ): ObservationReview(
                    reviewer_id="fixture-reviewer",
                    reviewed_at="2026-09-11T00:00:00+00:00",
                    decision="matched_reported_value",
                    primary_evidence=(
                        ObservationEvidenceRef(
                            source_ref=document_source.source_ref,
                            locator="page:1; section:profitability; row:ROA",
                        ),
                    ),
                    resolution_note="Fixture observation manually reconciled to the filing.",
                )
            },
            period_bases={
                canonical_observation_id(
                    candidate.metadata.dataset_snapshot_id,
                    "BANK-X",
                    "2024_Q4",
                    "bank.roa",
                ): "ttm"
            },
            reporting_scopes={
                canonical_observation_id(
                    candidate.metadata.dataset_snapshot_id,
                    "BANK-X",
                    "2024_Q4",
                    "bank.roa",
                ): "consolidated"
            },
        )
        db_path = root / "canonical.sqlite"
        accepted = materialize_canonical_snapshot(
            db_path,
            reviewed,
            staged.raw_descriptor,
            result.validation_report,
        )
        observation_id = canonical_observation_id(
            accepted.dataset_snapshot_id,
            "BANK-X",
            "2024_Q4",
            "bank.roa",
        )
        return db_path, DatasetRef(
            dataset_id="canonical-dataset",
            dataset_snapshot_id=accepted.dataset_snapshot_id,
        ), observation_id

    def test_canonical_resolver_uses_exact_observation_and_evidence_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref, observation_id = self._canonical_fixture(Path(directory))
            provider = CanonicalSqliteDatasetProvider(db_path)
            resolver = ProviderStage1DatasetResolver(provider, ref)

            observation = resolver.resolve_observation_ref(
                self._ref(observation_id, "observation", "BANK-X", "bank.roa")
            )
            evidence = resolver.resolve_evidence("evidence-canonical-company")
            source = resolver.resolve_source("document-source:filing-1")

        self.assertEqual(observation.value, 1.2)
        self.assertEqual(evidence.evidence_id, "evidence-canonical-company")
        self.assertIsNone(evidence.metric_id)
        self.assertEqual(source.source_ref, "document-source:filing-1")

    def test_resolver_rejects_provider_result_from_another_dataset(self):
        provider, ref = self._memory_provider()

        class WrongIdentityProvider:
            def resolve_observation(self, dataset_ref, observation_id):
                return CanonicalObservation(
                    observation_id=observation_id,
                    dataset_id="other-dataset",
                    dataset_snapshot_id="other-snapshot",
                    entity_id="entity-a",
                    period_id="2024_Q4",
                    metric_id="company.roa",
                    value=1.0,
                    unit="percent",
                    source_ref="source-company",
                    validation_status=QualityStatus.VALID,
                )

        resolver = ProviderStage1DatasetResolver(WrongIdentityProvider(), ref)
        with self.assertRaisesRegex(DatasetProviderError, "dataset reference"):
            resolver.resolve_observation_ref(
                self._ref("obs-memory-a", "observation", "entity-a", "company.roa")
            )


if __name__ == "__main__":
    unittest.main()
