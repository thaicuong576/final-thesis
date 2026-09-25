import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from thesis_data.analysis_request import (
    AnalysisRequest,
    AnalysisRequestValidationError,
    validate_analysis_request,
)
from thesis_data.application_runtime import ApplicationRuntimeContext
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
    PeerUniverse,
    QualityStatus,
    SupportedOperation,
)
from thesis_data.dataset_tool_runtime import DatasetToolError, DatasetToolRuntime
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.in_memory_provider import InMemoryFinancialDatasetProvider
from thesis_data.runtime_events import (
    InMemoryRuntimeEventRecorder,
    RuntimeEvent,
    RuntimeEventType,
)
from thesis_data.storage import create_gold_snapshot_schema


ALL_OPERATIONS = tuple(SupportedOperation)


def _catalog(ref: DatasetRef | None = None) -> DatasetCapabilityCatalog:
    ref = ref or DatasetRef(dataset_id="memory-dataset", dataset_snapshot_id="memory-snapshot")
    return DatasetCapabilityCatalog(
        dataset_ref=ref,
        entities=(
            DatasetEntity(
                entity_id="company-a",
                entity_type=DatasetEntityType.COMPANY,
                display_name="Company A",
                attributes={"sector": "bank"},
            ),
            DatasetEntity(
                entity_id="company-b",
                entity_type=DatasetEntityType.COMPANY,
                display_name="Company B",
                attributes={"sector": "bank"},
            ),
            DatasetEntity(
                entity_id="macro-vn",
                entity_type=DatasetEntityType.MACRO,
                display_name="Vietnam macro",
            ),
        ),
        periods=(DatasetPeriod(period_id="FY-2024-Q4", label="Q4 2024"),),
        metrics=(
            DatasetMetric(
                metric_id="company.roa",
                display_name="ROA",
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
                entity_ids=("company-a", "company-b"),
            ),
        ),
        supported_operations=ALL_OPERATIONS,
    )


def _request(
    ref: DatasetRef,
    *,
    target_entity_ids=("company-a",),
    period_ids=("FY-2024-Q4",),
    metric_ids=("company.roa",),
    macro_metric_ids=(),
    peer_universe_id=None,
    peer_entity_ids=(),
) -> AnalysisRequest:
    return AnalysisRequest(
        request_id="request-1",
        dataset_id=ref.dataset_id,
        dataset_snapshot_id=ref.dataset_snapshot_id,
        target_entity_ids=target_entity_ids,
        period_ids=period_ids,
        metric_ids=metric_ids,
        macro_metric_ids=macro_metric_ids,
        peer_universe_id=peer_universe_id,
        peer_entity_ids=peer_entity_ids,
        objective="Read the requested analytical facts.",
    )


def _three_peer_provider() -> tuple[InMemoryFinancialDatasetProvider, DatasetRef]:
    ref = DatasetRef(dataset_id="three-peer-dataset", dataset_snapshot_id="snapshot-1")
    catalog = DatasetCapabilityCatalog(
        dataset_ref=ref,
        entities=tuple(
            DatasetEntity(
                entity_id=entity_id,
                entity_type=DatasetEntityType.COMPANY,
                display_name=entity_id,
            )
            for entity_id in ("company-a", "company-b", "company-c")
        ),
        periods=(DatasetPeriod(period_id="FY-2024-Q4", label="Q4 2024"),),
        metrics=(
            DatasetMetric(
                metric_id="company.roa",
                display_name="ROA",
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
            ),
        ),
        peer_universes=(
            PeerUniverse(
                peer_universe_id="bank-peers",
                display_name="Bank peers",
                entity_ids=("company-a", "company-b", "company-c"),
            ),
        ),
        supported_operations=ALL_OPERATIONS,
    )
    observations = tuple(
        CanonicalObservation(
            observation_id=f"obs-{entity_id}",
            dataset_id=ref.dataset_id,
            dataset_snapshot_id=ref.dataset_snapshot_id,
            entity_id=entity_id,
            period_id="FY-2024-Q4",
            metric_id="company.roa",
            value=value,
            unit="percent",
            source_ref=f"source-{entity_id}",
            period_basis="ttm",
            reporting_scope="consolidated",
            metadata={
                "reporting_scope_authority": {
                    "authority_ref": "fixture-scope-authority.json",
                    "authority_canonical_lf_utf8_sha256": "a" * 64,
                    "review_status": "accepted",
                }
            },
            validation_status=QualityStatus.VALID,
        )
        for entity_id, value in (
            ("company-a", 1.0),
            ("company-b", 3.0),
            ("company-c", 100.0),
        )
    )
    return InMemoryFinancialDatasetProvider(catalog, observations=observations), ref


def _sector_provider() -> tuple[InMemoryFinancialDatasetProvider, DatasetRef]:
    ref = DatasetRef(dataset_id="sector-dataset", dataset_snapshot_id="snapshot-1")
    catalog = DatasetCapabilityCatalog(
        dataset_ref=ref,
        entities=(
            DatasetEntity(
                entity_id="sector-bank",
                entity_type=DatasetEntityType.SECTOR,
                display_name="Banking sector",
            ),
            DatasetEntity(
                entity_id="company-a",
                entity_type=DatasetEntityType.COMPANY,
                display_name="Company A",
            ),
            DatasetEntity(
                entity_id="macro-vn",
                entity_type=DatasetEntityType.MACRO,
                display_name="Vietnam macro",
            ),
        ),
        periods=(DatasetPeriod(period_id="FY-2024-Q4", label="Q4 2024"),),
        metrics=(
            DatasetMetric(
                metric_id="sector.credit_growth",
                display_name="Sector credit growth",
                analytical_level=AnalyticalLevel.SECTOR,
                default_unit="percent",
            ),
            DatasetMetric(
                metric_id="company.roa",
                display_name="ROA",
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
        supported_operations=ALL_OPERATIONS,
    )
    observation = CanonicalObservation(
        observation_id="obs-sector-credit-growth",
        dataset_id=ref.dataset_id,
        dataset_snapshot_id=ref.dataset_snapshot_id,
        entity_id="sector-bank",
        period_id="FY-2024-Q4",
        metric_id="sector.credit_growth",
        value=12.0,
        unit="percent",
        source_ref="source-sector",
        validation_status=QualityStatus.VALID,
    )
    return InMemoryFinancialDatasetProvider(catalog, observations=(observation,)), ref


class Phase25ContractTests(unittest.TestCase):
    def test_dataset_ref_requires_dataset_and_snapshot_identity(self):
        with self.assertRaises(ValidationError):
            DatasetRef(dataset_id="", dataset_snapshot_id="snapshot")
        with self.assertRaises(ValidationError):
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="")

    def test_canonical_observations_preserve_valid_missing_and_never_zero_fill(self):
        valid = CanonicalObservation(
            observation_id="obs-valid",
            dataset_id="dataset",
            dataset_snapshot_id="snapshot",
            entity_id="company-a",
            period_id="period-q4",
            metric_id="company.roa",
            value=1.2,
            unit="percent",
            source_ref="source-a",
            validation_status=QualityStatus.VALID,
        )
        missing = CanonicalObservation(
            observation_id="obs-missing",
            dataset_id="dataset",
            dataset_snapshot_id="snapshot",
            entity_id="company-a",
            period_id="period-q4",
            metric_id="company.roe",
            validation_status=QualityStatus.MISSING,
            missing_reason="DATA_UNAVAILABLE",
        )

        self.assertEqual(valid.validation_status, QualityStatus.VALID)
        self.assertIsNone(missing.value)
        with self.assertRaises(ValueError):
            CanonicalObservation(
                observation_id="obs-invalid",
                dataset_id="dataset",
                dataset_snapshot_id="snapshot",
                entity_id="company-a",
                period_id="period-q4",
                metric_id="company.roe",
                value=0.0,
                validation_status=QualityStatus.MISSING,
                missing_reason="DATA_UNAVAILABLE",
            )
        with self.assertRaisesRegex(ValueError, "provenance"):
            CanonicalObservation(
                observation_id="obs-unprovenanced",
                dataset_id="dataset",
                dataset_snapshot_id="snapshot",
                entity_id="bank-peers",
                period_id="period-q4",
                metric_id="company.roa",
                value=1.5,
                unit="percent",
                validation_status=QualityStatus.VALID,
            )
        derived = CanonicalObservation(
            observation_id="obs-derived",
            dataset_id="dataset",
            dataset_snapshot_id="snapshot",
            entity_id="bank-peers",
            period_id="period-q4",
            metric_id="company.roa",
            value=1.5,
            unit="percent",
            validation_status=QualityStatus.VALID,
            derivation_method="peer_median_v1",
            input_observation_ids=("obs-a", "obs-b"),
        )
        self.assertIsNone(derived.source_ref)
        self.assertEqual(derived.input_observation_ids, ("obs-a", "obs-b"))

    def test_capability_catalog_rejects_duplicate_identity_types(self):
        base = _catalog()
        for field_name, items in (
            ("entities", base.entities),
            ("periods", base.periods),
            ("metrics", base.metrics),
            ("peer_universes", base.peer_universes),
        ):
            payload = base.model_dump(mode="python")
            payload[field_name] = (items[0], items[0])
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    DatasetCapabilityCatalog(**payload)

    def test_analysis_request_validation_uses_catalog_only(self):
        catalog = _catalog()
        ref = catalog.dataset_ref
        validate_analysis_request(_request(ref), catalog)

        cases = (
            ("dataset", {"dataset_id": "wrong"}, "dataset_id_mismatch"),
            ("snapshot", {"dataset_snapshot_id": "wrong"}, "dataset_snapshot_id_mismatch"),
            ("entity", {"target_entity_ids": ("unknown",)}, "unsupported_entity"),
            ("period", {"period_ids": ("FY-2025-Q1",)}, "unsupported_period"),
            ("metric", {"metric_ids": ("company.unknown",)}, "unsupported_metric"),
            (
                "macro metric",
                {"metric_ids": ("macro.unknown",), "macro_metric_ids": ("macro.unknown",)},
                "unsupported_macro_metric",
            ),
            (
                "peer universe",
                {"peer_universe_id": "unknown"},
                "unsupported_peer_universe",
            ),
        )
        for name, updates, expected in cases:
            with self.subTest(name=name):
                request = _request(ref).model_copy(update=updates)
                with self.assertRaisesRegex(AnalysisRequestValidationError, expected):
                    validate_analysis_request(request, catalog)


class GoldProviderTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, DatasetRef]:
        db_path = root / "arbitrary-gold.sqlite"
        create_gold_snapshot_schema(db_path)
        connection = sqlite3.connect(db_path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-snapshot-arbitrary", "2026-09-11T00:00:00Z", "gold", "{}"),
        )
        connection.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("source-company", "filing", "primary", "https://example.test/company", "2026-09-11", "private/company.pdf", "hash-company", "Issuer", "public", "valid", None),
                ("source-policy", "policy", "primary", "https://example.test/policy", "2026-09-11", "private/policy.html", "hash-policy", "SBV", "public", "valid", None),
            ),
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("obs-a-roa", "entity-a", "bank", "company.roa", 1.2, "percent", "FY-2024-Q4", "2024-12-31", "point_in_time", "source-company", "page:1", "valid", None),
                ("obs-b-roa", "entity-b", "bank", "company.roa", 1.8, "percent", "FY-2024-Q4", "2024-12-31", "point_in_time", "source-company", "page:2", "valid", None),
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
                "obs-policy", "macro.policy", 4.5, "percent_per_annum", "FY-2024-Q4", "source-policy",
                "valid", None, "sbv-policy", "definition-v1", "event", "2023-06-19",
                "2023-06-19", "2024-12-31", "state_at_period_end", "latest_effective_state_v1",
                "decision:1123", "state-carry-forward-v1", "[]", "adjudication-policy", "[\"check-a\",\"check-b\"]",
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
                "obs-credit-missing", "macro.credit", None, None, "FY-2024-Q4", None,
                "missing", "DATA_UNAVAILABLE", None, "definition-v1", None, None,
                None, "2024-12-31", "year_end", "official_year_end_or_missing_v1",
                "adjudication:credit-growth", "credit-growth-v1", "[]", "adjudication-credit", "[\"check-a\",\"check-b\"]",
            ),
        )
        connection.execute(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("evidence-company", "source-company", "company.pdf", 1, "ROA", "FY-2024-Q4", "entity-a", "ROA was 1.2 percent.", 1.0, "text", 1),
        )
        connection.execute(
            """
            INSERT INTO macro_evidence_snippets VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("evidence-policy", "source-policy", "macro.policy", "FY-2024-Q4", "policy.html", "decision:1123", "SBV refinancing rate is 4.5%.", "2024-12-31", "2023-06-19", "html"),
        )
        connection.commit()
        connection.close()
        return db_path, DatasetRef(
            dataset_id="arbitrary-gold",
            dataset_snapshot_id="gold-snapshot-arbitrary",
        )

    def test_gold_capabilities_are_discovered_from_arbitrary_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self.fixture(Path(directory))
            provider = GoldSqliteDatasetProvider(db_path, dataset_id="arbitrary-gold")
            catalog = provider.get_capabilities(ref)

        self.assertEqual(catalog.entity_ids, frozenset({"entity-a", "entity-b", "VN"}))
        self.assertEqual(catalog.period_ids, frozenset({"FY-2024-Q4"}))
        self.assertEqual(catalog.metric_ids, frozenset({"company.roa", "macro.policy", "macro.credit"}))
        self.assertEqual(catalog.peer_universe("sector:bank").entity_ids, ("entity-a", "entity-b"))
        self.assertNotIn("ACB", catalog.entity_ids)

    def test_gold_provider_maps_company_macro_missing_peer_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self.fixture(Path(directory))
            provider = GoldSqliteDatasetProvider(db_path, dataset_id="arbitrary-gold")
            company = provider.get_metric(ref, "entity-a", "FY-2024-Q4", "company.roa")
            macro = provider.get_macro_observation(ref, "VN", "FY-2024-Q4", "macro.policy")
            missing = provider.get_macro_observation(ref, "VN", "FY-2024-Q4", "macro.credit")
            with self.assertRaisesRegex(DatasetProviderError, "verified reporting scopes"):
                provider.get_peer_benchmark(ref, "sector:bank", "FY-2024-Q4", ("company.roa",))
            evidence = provider.get_evidence(ref, ("source-policy",), period_id="FY-2024-Q4", metric_id="macro.policy")
            company_evidence = provider.get_evidence(
                ref,
                ("source-company",),
                entity_id="entity-a",
                period_id="FY-2024-Q4",
                metric_id="company.roa",
            )
            source = provider.get_source(ref, "source-policy")

        self.assertEqual(company.entity_id, "entity-a")
        self.assertEqual(company.value, 1.2)
        self.assertIsNone(company.reporting_scope)
        self.assertEqual(macro.value, 4.5)
        self.assertEqual(missing.validation_status, QualityStatus.MISSING)
        self.assertIsNone(missing.value)
        self.assertEqual(missing.missing_reason, "DATA_UNAVAILABLE")
        self.assertIsNone(evidence[0].entity_id)
        self.assertEqual(evidence[0].metric_id, "macro.policy")
        self.assertEqual(len(company_evidence), 1)
        self.assertIsNone(company_evidence[0].metric_id)
        self.assertNotIn("local_path", source.model_dump())

    def test_gold_provider_rejects_peer_entities_outside_universe(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self.fixture(Path(directory))
            provider = GoldSqliteDatasetProvider(db_path, dataset_id="arbitrary-gold")

            with self.assertRaisesRegex(DatasetProviderError, "outside"):
                provider.get_peer_benchmark(
                    ref,
                    "sector:bank",
                    "FY-2024-Q4",
                    ("company.roa",),
                    peer_entity_ids=("entity-a", "not-a-peer"),
                )

    def test_gold_provider_rejects_snapshot_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path, ref = self.fixture(Path(directory))
            provider = GoldSqliteDatasetProvider(db_path, dataset_id="arbitrary-gold")
            wrong = ref.model_copy(update={"dataset_snapshot_id": "wrong-snapshot"})

            with self.assertRaisesRegex(ValueError, "snapshot_id"):
                provider.get_capabilities(wrong)


class ApplicationRuntimeTests(unittest.TestCase):
    def provider(self) -> tuple[InMemoryFinancialDatasetProvider, DatasetRef]:
        catalog = _catalog()
        ref = catalog.dataset_ref
        observations = (
            CanonicalObservation(
                observation_id="memory-company-roa",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="company-a",
                period_id="FY-2024-Q4",
                metric_id="company.roa",
                value=1.2,
                unit="percent",
                source_ref="source-company",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="memory-policy",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="macro-vn",
                period_id="FY-2024-Q4",
                metric_id="macro.policy",
                value=4.5,
                unit="percent_per_annum",
                source_ref="source-policy",
                validation_status=QualityStatus.VALID,
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
                content_hash="hash-company",
                validation_status=QualityStatus.VALID,
            ),
        )
        evidence = (
            DatasetEvidence(
                evidence_id="memory-evidence",
                source_ref="source-company",
                entity_id="company-a",
                period_id="FY-2024-Q4",
                metric_id="company.roa",
                locator="page:1",
                quote="ROA was 1.2 percent.",
            ),
        )
        return InMemoryFinancialDatasetProvider(
            catalog,
            observations=observations,
            sources=sources,
            evidence=evidence,
        ), ref

    def test_peer_benchmark_uses_explicit_subset_and_derivation_inputs(self):
        provider, ref = _three_peer_provider()
        request = _request(
            ref,
            peer_universe_id="bank-peers",
            peer_entity_ids=("company-a", "company-b"),
        )
        runtime = DatasetToolRuntime(
            ApplicationRuntimeContext.from_request(request, provider),
        )

        benchmark = runtime.get_peer_benchmark(
            "bank-peers",
            "FY-2024-Q4",
            ("company.roa",),
        )[0]

        self.assertEqual(benchmark.value, 2.0)
        self.assertEqual(
            set(benchmark.input_observation_ids),
            {"obs-company-a", "obs-company-b"},
        )
        self.assertEqual(benchmark.metadata["requested_denominator"], 2)
        self.assertEqual(benchmark.metadata["eligible_denominator"], 2)
        self.assertNotIn("obs-company-c", benchmark.input_observation_ids)
        self.assertIsNone(benchmark.source_ref)
        self.assertEqual(
            benchmark.metadata["requested_peer_entity_ids"], ["company-a", "company-b"]
        )
        self.assertEqual(
            benchmark.metadata["eligible_peer_entity_ids"], ["company-a", "company-b"]
        )

    def test_batch_and_peer_tools_enforce_analytical_levels(self):
        provider, ref = self.provider()
        request = _request(
            ref,
            metric_ids=("company.roa", "macro.policy"),
            macro_metric_ids=("macro.policy",),
            peer_universe_id="bank-peers",
        )
        runtime = DatasetToolRuntime(
            ApplicationRuntimeContext.from_request(request, provider),
        )

        company_batch = runtime.get_entity_metrics(
            "company-a",
            ("FY-2024-Q4",),
            ("company.roa",),
        )
        self.assertEqual(len(company_batch), 1)
        with self.assertRaisesRegex(DatasetToolError, "analytical level"):
            runtime.get_entity_metrics(
                "company-a",
                ("FY-2024-Q4",),
                ("macro.policy",),
            )
        with self.assertRaisesRegex(DatasetToolError, "company-level"):
            runtime.get_peer_benchmark(
                "bank-peers",
                "FY-2024-Q4",
                ("macro.policy",),
            )
        macro_observation = runtime.get_macro_observation(
            "macro-vn",
            "FY-2024-Q4",
            "macro.policy",
        )
        self.assertEqual(macro_observation.value, 4.5)

    def test_sector_entity_requires_sector_metric_for_single_and_batch_tools(self):
        provider, ref = _sector_provider()
        request = _request(
            ref,
            target_entity_ids=("sector-bank",),
            metric_ids=("sector.credit_growth", "company.roa", "macro.policy"),
            macro_metric_ids=("macro.policy",),
        )
        runtime = DatasetToolRuntime(
            ApplicationRuntimeContext.from_request(request, provider),
        )

        single = runtime.get_metric(
            "sector-bank",
            "FY-2024-Q4",
            "sector.credit_growth",
        )
        batch = runtime.get_entity_metrics(
            "sector-bank",
            ("FY-2024-Q4",),
            ("sector.credit_growth",),
        )
        self.assertEqual(single.value, 12.0)
        self.assertEqual(len(batch), 1)

        for metric_id in ("company.roa", "macro.policy"):
            with self.subTest(operation="get_metric", metric_id=metric_id):
                with self.assertRaisesRegex(DatasetToolError, "analytical level"):
                    runtime.get_metric("sector-bank", "FY-2024-Q4", metric_id)
            with self.subTest(operation="get_entity_metrics", metric_id=metric_id):
                with self.assertRaisesRegex(DatasetToolError, "analytical level"):
                    runtime.get_entity_metrics(
                        "sector-bank",
                        ("FY-2024-Q4",),
                        (metric_id,),
                    )

    def test_in_memory_provider_rejects_peer_entities_outside_universe(self):
        provider, ref = _three_peer_provider()
        with self.assertRaisesRegex(DatasetProviderError, "outside"):
            provider.get_peer_benchmark(
                ref,
                "bank-peers",
                "FY-2024-Q4",
                ("company.roa",),
                peer_entity_ids=("company-a", "not-a-peer"),
            )

    def test_application_runtime_executes_with_non_sqlite_provider(self):
        provider, ref = self.provider()
        request = _request(ref, peer_universe_id="bank-peers")
        recorder = InMemoryRuntimeEventRecorder(request.request_id)
        context = ApplicationRuntimeContext.from_request(
            request,
            provider,
            event_sink=recorder,
        )
        runtime = DatasetToolRuntime(context, actor="company", task_id="task-1")
        context.assign_task("task-1", "orchestrator")
        context.start_agent("task-1", "company")
        result = runtime.execute(
            "get_metric",
            {"entity_id": "company-a", "period_id": "FY-2024-Q4", "metric_id": "company.roa"},
        )
        evidence = runtime.execute(
            "get_evidence",
            {
                "source_refs": ["source-company"],
                "entity_id": "company-a",
                "period_id": "FY-2024-Q4",
                "metric_id": "company.roa",
            },
        )
        context.record_agent_output("task-1", "company", artifact_refs=("claim:company-roa",))

        self.assertEqual(result.output["value"], 1.2)
        self.assertEqual(evidence.output[0]["evidence_id"], "memory-evidence")
        self.assertEqual(
            [event.event_type for event in recorder.events],
            [
                RuntimeEventType.TASK_ASSIGNED,
                RuntimeEventType.AGENT_STARTED,
                RuntimeEventType.TOOL_STARTED,
                RuntimeEventType.TOOL_COMPLETED,
                RuntimeEventType.TOOL_STARTED,
                RuntimeEventType.TOOL_COMPLETED,
                RuntimeEventType.AGENT_OUTPUT_CREATED,
            ],
        )
        self.assertEqual([event.sequence for event in recorder.events], list(range(1, 8)))
        self.assertNotIn("sqlite3", Path("src/thesis_data/dataset_tool_runtime.py").read_text(encoding="utf-8"))

    def test_tool_scope_rejects_entity_period_metric_peer_and_evidence_source(self):
        provider, ref = self.provider()
        request = _request(ref, peer_universe_id="bank-peers")
        recorder = InMemoryRuntimeEventRecorder(request.request_id)
        runtime = DatasetToolRuntime(
            ApplicationRuntimeContext.from_request(request, provider, event_sink=recorder),
            task_id="task-1",
        )
        cases = (
            (
                "entity",
                "get_metric",
                {"entity_id": "company-b", "period_id": "FY-2024-Q4", "metric_id": "company.roa"},
            ),
            (
                "period",
                "get_metric",
                {"entity_id": "company-a", "period_id": "FY-2025-Q1", "metric_id": "company.roa"},
            ),
            (
                "metric",
                "get_metric",
                {"entity_id": "company-a", "period_id": "FY-2024-Q4", "metric_id": "macro.policy"},
            ),
            (
                "peer",
                "get_peer_benchmark",
                {"peer_universe_id": "other", "period_id": "FY-2024-Q4", "metric_ids": ["company.roa"]},
            ),
            (
                "evidence source",
                "get_evidence",
                {"source_refs": ["source-company"], "entity_id": "company-a"},
            ),
        )
        for name, operation, arguments in cases:
            with self.subTest(name=name):
                with self.assertRaises(DatasetToolError):
                    runtime.execute(operation, arguments)
        self.assertEqual(
            recorder.events[-1].event_type,
            RuntimeEventType.RUN_BLOCKED,
        )

    def test_runtime_events_reject_reasoning_and_local_paths(self):
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_id="event-1",
                run_id="run-1",
                sequence=1,
                event_type=RuntimeEventType.AGENT_STARTED,
                actor="company",
                public_payload={"reasoning": "private chain"},
            )
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_id="event-2",
                run_id="run-1",
                sequence=1,
                event_type=RuntimeEventType.TOOL_COMPLETED,
                actor="company",
                artifact_refs=(r"C:\Users\private\report.json",),
            )
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_id="event-3",
                run_id="run-1",
                sequence=1,
                event_type=RuntimeEventType.RUN_FAILED,
                actor="provider",
                summary=r"provider failed while reading C:\Users\private\file.sqlite",
            )
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_id="event-4",
                run_id="run-1",
                sequence=1,
                event_type=RuntimeEventType.RUN_FAILED,
                actor="provider",
                public_payload={"details": r"failed at C:\Users\private\file.sqlite"},
            )
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_id="event-5",
                run_id="run-1",
                sequence=1,
                event_type=RuntimeEventType.RUN_FAILED,
                actor="provider",
                artifact_refs=(r"artifact generated from C:\Users\private\file.sqlite",),
            )

    def test_provider_exception_uses_stable_public_failure_summary(self):
        provider, ref = self.provider()

        class FailingProvider(InMemoryFinancialDatasetProvider):
            def get_metric(self, *args, **kwargs):
                raise DatasetProviderError(
                    r"provider failed while reading C:\Users\private\file.sqlite"
                )

        failing = FailingProvider(
            provider._catalog,
            observations=provider._observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        request = _request(ref)
        recorder = InMemoryRuntimeEventRecorder(request.request_id)
        runtime = DatasetToolRuntime(
            ApplicationRuntimeContext.from_request(request, failing, event_sink=recorder),
        )

        with self.assertRaises(DatasetToolError):
            runtime.execute(
                "get_metric",
                {
                    "entity_id": "company-a",
                    "period_id": "FY-2024-Q4",
                    "metric_id": "company.roa",
                },
            )
        self.assertEqual(recorder.events[-1].event_type, RuntimeEventType.RUN_FAILED)
        self.assertEqual(recorder.events[-1].summary, "dataset provider failed")
        self.assertNotIn("private", recorder.events[-1].summary)

    def test_application_modules_do_not_depend_on_sqlite_or_gold_config(self):
        for filename in (
            "src/thesis_data/dataset_contract.py",
            "src/thesis_data/dataset_provider.py",
            "src/thesis_data/analysis_request.py",
            "src/thesis_data/application_runtime.py",
            "src/thesis_data/dataset_tool_runtime.py",
        ):
            source = Path(filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertNotIn("sqlite3", source)
                self.assertNotIn("GoldConfig", source)


if __name__ == "__main__":
    unittest.main()
