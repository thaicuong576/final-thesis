import unittest

from thesis_data.acceptance import validate_stage1_claims
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
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
)
from thesis_data.dataset_provider import peer_benchmark_observation_id
from thesis_data.in_memory_provider import InMemoryFinancialDatasetProvider
from thesis_data.schema import (
    AcceptancePolicy,
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    InferenceType,
    QualityStatus,
    StructuredAssertion,
)


class ProviderNeutralAcceptanceTests(unittest.TestCase):
    def setUp(self):
        ref = DatasetRef(dataset_id="memory-dataset", dataset_snapshot_id="memory-snapshot")
        catalog = DatasetCapabilityCatalog(
            dataset_ref=ref,
            entities=(
                DatasetEntity(entity_id="entity-a", entity_type=DatasetEntityType.COMPANY, display_name="Entity A"),
                DatasetEntity(entity_id="entity-b", entity_type=DatasetEntityType.COMPANY, display_name="Entity B"),
                DatasetEntity(entity_id="macro-vn", entity_type=DatasetEntityType.MACRO, display_name="Vietnam macro"),
            ),
            periods=(DatasetPeriod(period_id="2024_Q4", label="Q4 2024"),),
            metrics=(
                DatasetMetric(metric_id="company.roa", display_name="ROA", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),
                DatasetMetric(metric_id="company.derived", display_name="Derived ROA", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),
                DatasetMetric(metric_id="company.missing", display_name="Missing ROA", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),
                DatasetMetric(metric_id="macro.policy", display_name="Policy rate", analytical_level=AnalyticalLevel.MACRO, default_unit="percent_per_annum"),
                DatasetMetric(metric_id="macro.missing", display_name="Missing macro", analytical_level=AnalyticalLevel.MACRO, default_unit="percent"),
            ),
            peer_universes=(PeerUniverse(peer_universe_id="bank-peers", display_name="Bank peers", entity_ids=("entity-a", "entity-b")),),
            supported_operations=(
                "get_metric", "get_entity_metrics", "get_peer_benchmark", "get_evidence",
                "get_source", "get_macro_observation", "resolve_observation",
            ),
        )
        observations = (
            CanonicalObservation(
                observation_id="observation-a", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a", period_id="2024_Q4", metric_id="company.roa", value=1.0, unit="percent",
                source_ref="source-company", validation_status=QualityStatus.VALID,
                metadata={"source_locator": "page:1"},
            ),
            CanonicalObservation(
                observation_id="observation-b", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-b", period_id="2024_Q4", metric_id="company.roa", value=3.0, unit="percent",
                source_ref="source-company", validation_status=QualityStatus.VALID,
                metadata={"source_locator": "page:2"},
            ),
            CanonicalObservation(
                observation_id="derived-a", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a", period_id="2024_Q4", metric_id="company.derived", value=2.0, unit="percent",
                validation_status=QualityStatus.VALID, derivation_method="formula-v1",
                input_observation_ids=("observation-a", "observation-b"),
            ),
            CanonicalObservation(
                observation_id="missing-a", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="entity-a", period_id="2024_Q4", metric_id="company.missing",
                validation_status=QualityStatus.MISSING, missing_reason="DATA_UNAVAILABLE",
            ),
            CanonicalObservation(
                observation_id="macro-policy", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="macro-vn", period_id="2024_Q4", metric_id="macro.policy", value=4.5,
                unit="percent_per_annum", source_ref="source-macro", validation_status=QualityStatus.VALID,
                metadata={"source_locator": "decision:1"},
            ),
            CanonicalObservation(
                observation_id="macro-missing", dataset_id=ref.dataset_id, dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id="macro-vn", period_id="2024_Q4", metric_id="macro.missing",
                validation_status=QualityStatus.MISSING, missing_reason="DATA_UNAVAILABLE",
                metadata={"adjudication_ref": "review:1"},
            ),
        )
        sources = (
            DatasetSource(
                source_ref="source-company", source_type="filing", source_tier="primary",
                source_url="https://example.test/company", publisher="Issuer", retrieved_at="2026-09-11",
                content_hash="company-hash", validation_status=QualityStatus.VALID,
            ),
            DatasetSource(
                source_ref="source-macro", source_type="official", source_tier="primary",
                source_url="https://example.test/macro", publisher="Official publisher", retrieved_at="2026-09-11",
                content_hash="macro-hash", validation_status=QualityStatus.VALID,
            ),
        )
        evidence = (
            DatasetEvidence(
                evidence_id="evidence-company", source_ref="source-company", entity_id="entity-a",
                period_id="2024_Q4", locator="page:1", quote="The filing reports the metric.",
            ),
            DatasetEvidence(
                evidence_id="evidence-macro", source_ref="source-macro", period_id="2024_Q4",
                metric_id="macro.policy", locator="decision:1", quote="The official source reports the state.",
            ),
        )
        provider = InMemoryFinancialDatasetProvider(catalog, observations=observations, sources=sources, evidence=evidence)
        self.resolver = ProviderStage1DatasetResolver(provider, ref)
        self.policy = AcceptancePolicy(policy_version="provider-neutral-test-v1", provisional_threshold=0.75)

    def _claim(self, *, entity="entity-a", metric_id="company.roa", value=1.0,
               ref_id="observation-a", ref_type="observation", evidence=(),
               source_refs=("source-company",), unit=None, assertion_type=AssertionType.METRIC_VALUE,
               operator=None, comparison_universe=None, formula_version=None):
        period = "2024_Q4"
        data_ref = ClaimDataRef(ref_id=ref_id, ref_type=ref_type, entity=entity, period=period, metric_id=metric_id)
        assertion = StructuredAssertion(
            assertion_id="assertion-1", assertion_type=assertion_type, entity=entity, period=period,
            metric_id=metric_id, asserted_value=value, unit=unit or ("percent" if value is not None else None),
            operator=operator, data_refs=(data_ref,), formula_version=formula_version,
        )
        scope_entities = ("entity-a", "entity-b") if comparison_universe else (entity,)
        return AtomicClaim(
            claim_id="claim-1", claim_text="A structured assertion.", claim_type="numeric", title="Metric",
            interpretation="Provider-resolved.", limitation="Test fixture.",
            scope=ClaimScope(entities=scope_entities, periods=(period,), metric_ids=(metric_id,), comparison_universe=comparison_universe),
            assertions=(assertion,), evidence_refs=evidence, source_refs=source_refs,
            inference_type=InferenceType.COMPARISON if comparison_universe else InferenceType.FACT,
            support="evidence_backed" if evidence else "partially_supported",
        )

    def test_generic_metric_claim_uses_provider_resolver(self):
        claim = self._claim()
        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)
        self.assertTrue(result.passed)
        self.assertEqual(result.gate_results["numeric_accuracy"].passed_count, 1)

    def test_scope_mismatch_is_evaluated_by_acceptance_not_hidden_by_resolver(self):
        claim = self._claim()
        bad_ref = ClaimDataRef(ref_id="observation-a", ref_type="observation", entity="entity-b", period="2024_Q4", metric_id="company.roa")
        claim = claim.model_copy(update={"assertions": (claim.assertions[0].model_copy(update={"data_refs": (bad_ref,)}),)})
        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)
        self.assertFalse(result.passed)
        self.assertIn("reference_scope_mismatch", " ".join(result.gate_results["reference_validity"].violations))

    def test_comparison_reference_is_resolved_by_provider(self):
        left = ClaimDataRef(ref_id="observation-a", ref_type="observation", entity="entity-a", period="2024_Q4", metric_id="company.roa")
        right = ClaimDataRef(ref_id="observation-b", ref_type="observation", entity="entity-b", period="2024_Q4", metric_id="company.roa")
        assertion = StructuredAssertion(
            assertion_id="comparison-1", assertion_type=AssertionType.COMPARISON, entity="entity-a", period="2024_Q4",
            metric_id="company.roa", asserted_value=1.0, unit="percent", operator=AssertionOperator.LT,
            data_refs=(left,), reference_ref=right,
        )
        claim = AtomicClaim(
            claim_id="comparison-claim", claim_text="Entity A is below Entity B.", claim_type="comparison",
            title="Comparison", interpretation="Provider-resolved.", limitation="Test fixture.",
            scope=ClaimScope(entities=("entity-a", "entity-b"), periods=("2024_Q4",), metric_ids=("company.roa",)),
            assertions=(assertion,), evidence_refs=(), source_refs=("source-company",),
            inference_type=InferenceType.COMPARISON, support="evidence_backed",
        )
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_derived_metric_uses_canonical_derivation_provenance(self):
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_explicit_missingness_uses_resolved_missing_state(self):
        claim = self._claim(metric_id="company.missing", value=None, ref_id="missing-a", ref_type="missing_cell", assertion_type=AssertionType.MISSINGNESS, operator=AssertionOperator.MISSING)
        claim = claim.model_copy(update={"critical": False, "claim_type": "context"})
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_valid_observation_cannot_satisfy_missing_cell_reference(self):
        claim = self._claim(value=None, ref_id="observation-a", ref_type="missing_cell", assertion_type=AssertionType.MISSINGNESS, operator=AssertionOperator.MISSING)
        claim = claim.model_copy(update={"critical": False, "claim_type": "context"})
        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)
        self.assertFalse(result.gate_results["reference_validity"].passed)
        self.assertIn("missing_cell_reference_not_missing", " ".join(result.gate_results["reference_validity"].violations))

    def test_macro_observation_is_resolved_without_physical_routing(self):
        claim = self._claim(entity="macro-vn", metric_id="macro.policy", value=4.5, unit="percent_per_annum", ref_id="macro-policy", ref_type="macro_observation", source_refs=("source-macro",))
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_macro_accepted_missingness_requires_canonical_state(self):
        claim = self._claim(entity="macro-vn", metric_id="macro.missing", value=None, ref_id="macro-missing", ref_type="macro_observation", evidence=(), source_refs=(), assertion_type=AssertionType.MISSINGNESS, operator=AssertionOperator.MISSING)
        claim = claim.model_copy(update={"critical": False, "claim_type": "context"})
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_benchmark_is_provider_derived_and_not_recomputed_by_core(self):
        benchmark_id = peer_benchmark_observation_id(self.resolver.dataset_ref, "bank-peers", "2024_Q4", "company.roa", ("entity-a", "entity-b"))
        benchmark_ref = ClaimDataRef(ref_id=benchmark_id, ref_type="benchmark", entity="bank-peers", period="2024_Q4", metric_id="company.roa")
        data_refs = (
            ClaimDataRef(ref_id="observation-a", ref_type="observation", entity="entity-a", period="2024_Q4", metric_id="company.roa"),
            ClaimDataRef(ref_id="observation-b", ref_type="observation", entity="entity-b", period="2024_Q4", metric_id="company.roa"),
        )
        assertion = StructuredAssertion(
            assertion_id="aggregate-1", assertion_type=AssertionType.AGGREGATE, entity="bank-peers", period="2024_Q4",
            metric_id="company.roa", asserted_value=2.0, unit="percent", operator=AssertionOperator.EQ,
            data_refs=data_refs, benchmark_ref=benchmark_ref,
        )
        claim = AtomicClaim(
            claim_id="aggregate-claim", claim_text="Peer median is 2 percent.", claim_type="comparison",
            title="Peer median", interpretation="Provider-derived benchmark.", limitation="Test fixture.",
            scope=ClaimScope(entities=("entity-a", "entity-b"), periods=("2024_Q4",), metric_ids=("company.roa",), comparison_universe="bank-peers"),
            assertions=(assertion,), evidence_refs=(), source_refs=("source-company",),
            inference_type=InferenceType.COMPARISON, support="evidence_backed",
        )
        self.assertTrue(validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy).passed)

    def test_direct_observation_route_requires_exact_locator(self):
        provider = self.resolver._provider
        observations = list(provider._observations)
        observations[0] = observations[0].model_copy(update={"metadata": {}})
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim()

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("observation_source_locator_missing", " ".join(result.gate_results["reference_validity"].violations))
        self.assertFalse(result.gate_results["critical_evidence_coverage"].passed)

    def test_direct_observation_route_requires_valid_primary_source(self):
        provider = self.resolver._provider
        invalid_source = provider._sources["source-company"].model_copy(
            update={"validation_status": QualityStatus.INVALID}
        )
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=provider._observations,
            sources=(invalid_source, provider._sources["source-macro"]),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim()

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("observation_source_unaccepted", " ".join(result.gate_results["reference_validity"].violations))

    def test_direct_observation_route_requires_primary_source_tier(self):
        provider = self.resolver._provider
        secondary_source = provider._sources["source-company"].model_copy(
            update={"source_tier": "secondary"}
        )
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=provider._observations,
            sources=(secondary_source, provider._sources["source-macro"]),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim()

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("observation_source_tier_not_primary", " ".join(result.gate_results["reference_validity"].violations))

    def test_direct_observation_route_requires_a_source_reference(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"source_ref": None})
            if item.observation_id == "observation-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim()

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("observation_source_missing", " ".join(result.gate_results["reference_validity"].violations))

    def test_cross_metric_reference_cannot_be_repaired_by_provider_resolution(self):
        claim = self._claim()
        wrong_metric_ref = ClaimDataRef(
            ref_id="observation-a", ref_type="observation", entity="entity-a",
            period="2024_Q4", metric_id="company.derived",
        )
        assertion = claim.assertions[0].model_copy(update={"data_refs": (wrong_metric_ref,)})
        claim = claim.model_copy(update={
            "scope": claim.scope.model_copy(update={"metric_ids": ("company.roa", "company.derived")}),
            "assertions": (assertion,),
        })

        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("reference_scope_mismatch", " ".join(result.gate_results["reference_validity"].violations))

    def test_cross_entity_reference_cannot_be_repaired_by_provider_resolution(self):
        claim = self._claim()
        wrong_entity_ref = ClaimDataRef(
            ref_id="observation-a", ref_type="observation", entity="entity-b",
            period="2024_Q4", metric_id="company.roa",
        )
        assertion = claim.assertions[0].model_copy(update={"data_refs": (wrong_entity_ref,)})
        claim = claim.model_copy(update={
            "scope": claim.scope.model_copy(update={"entities": ("entity-a", "entity-b")}),
            "assertions": (assertion,),
        })

        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("reference_scope_mismatch", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_formula_mismatch(self):
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="wrong-formula",
        )

        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_formula_version_mismatch", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_invalid_primary_input_source(self):
        provider = self.resolver._provider
        invalid_source = provider._sources["source-company"].model_copy(
            update={"validation_status": QualityStatus.INVALID}
        )
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=provider._observations,
            sources=(invalid_source, provider._sources["source-macro"]),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_source_unaccepted", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_missing_primary_input_locator(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"metadata": {}})
            if item.observation_id == "observation-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_source_locator_missing", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_missing_primary_input_source(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"source_ref": None})
            if item.observation_id == "observation-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_source_missing", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_checks_claim_against_exact_observation_value(self):
        claim = self._claim(
            metric_id="company.derived", value=2.5, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("numeric_value_mismatch", " ".join(result.gate_results["numeric_accuracy"].violations))

    def test_derived_metric_route_rejects_missing_or_unaccepted_input(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"input_observation_ids": ("missing-input",)})
            if item.observation_id == "derived-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_missing_or_ambiguous", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_unaccepted_input_observation(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"validation_status": QualityStatus.INVALID})
            if item.observation_id == "observation-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_unaccepted", " ".join(result.gate_results["reference_validity"].violations))

    def test_derived_metric_route_rejects_incomplete_input_value_unit_or_period(self):
        provider = self.resolver._provider
        cases = (
            ({"value": None}, "derived_input_value_missing"),
            ({"unit": ""}, "derived_input_unit_missing"),
            ({"period_id": ""}, "derived_input_scope_missing"),
        )
        for update, expected_violation in cases:
            with self.subTest(update=update):
                observations = [
                    item.model_copy(update=update)
                    if item.observation_id == "observation-a"
                    else item
                    for item in provider._observations
                ]
                broken_provider = InMemoryFinancialDatasetProvider(
                    provider._catalog,
                    observations=observations,
                    sources=provider._sources.values(),
                    evidence=provider._evidence,
                )
                resolver = ProviderStage1DatasetResolver(
                    broken_provider, self.resolver.dataset_ref
                )
                claim = self._claim(
                    metric_id="company.derived", value=2.0, ref_id="derived-a",
                    ref_type="derived_metric", formula_version="formula-v1",
                )

                result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

                self.assertFalse(result.passed)
                self.assertIn(
                    expected_violation,
                    " ".join(result.gate_results["reference_validity"].violations),
                )

    def test_derived_metric_route_rejects_lineage_cycles(self):
        provider = self.resolver._provider
        observations = [
            item.model_copy(update={"input_observation_ids": ("derived-a",)})
            if item.observation_id == "derived-a"
            else item
            for item in provider._observations
        ]
        broken_provider = InMemoryFinancialDatasetProvider(
            provider._catalog,
            observations=observations,
            sources=provider._sources.values(),
            evidence=provider._evidence,
        )
        resolver = ProviderStage1DatasetResolver(broken_provider, self.resolver.dataset_ref)
        claim = self._claim(
            metric_id="company.derived", value=2.0, ref_id="derived-a",
            ref_type="derived_metric", formula_version="formula-v1",
        )

        result = validate_stage1_claims(resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("derived_input_cycle", " ".join(result.gate_results["reference_validity"].violations))

    def test_unlinked_same_source_snippet_cannot_support_numeric_claim(self):
        claim = self._claim(evidence=("evidence-company",))

        result = validate_stage1_claims(self.resolver, (claim,), claim.scope, self.policy)

        self.assertFalse(result.passed)
        self.assertIn("numeric_document_evidence_unlinked", " ".join(result.gate_results["critical_evidence_coverage"].violations))

    def test_narrative_claim_still_requires_and_accepts_document_evidence(self):
        claim = self._claim(evidence=("evidence-company",))
        assertion = claim.assertions[0].model_copy(update={
            "assertion_type": AssertionType.REFERENCE_ONLY,
            "asserted_value": None,
            "unit": None,
        })
        narrative_claim = claim.model_copy(update={
            "claim_type": "policy",
            "claim_text": "The filing describes the issuer's profitability context.",
            "assertions": (assertion,),
            "inference_type": InferenceType.INTERPRETATION,
        })

        result = validate_stage1_claims(
            self.resolver, (narrative_claim,), narrative_claim.scope, self.policy
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.gate_results["critical_evidence_coverage"].passed)


if __name__ == "__main__":
    unittest.main()
