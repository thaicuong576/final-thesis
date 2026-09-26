import unittest

from thesis_data.acceptance import validate_stage1_claims
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_data.analysis_plan import (
    ANALYSIS_PLAN_VERSION,
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisScope,
    CausalClaimPolicy,
    FulfillmentPolicy,
    InferenceCeiling,
    MissingDataPolicy,
    RequirementType,
)
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
)
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


PERIODS = ("2024_Q1", "2024_Q2")
METRICS = ("company.roa", "company.roe")
ENTITY = "entity-a"


def _plan() -> AnalysisPlan:
    requirements = []
    for metric_id in METRICS:
        for period in PERIODS:
            allows_missing = metric_id == "company.roe" and period == "2024_Q2"
            requirements.append(
                AnalysisRequirement(
                    requirement_id=f"fact-{metric_id}-{period}",
                    requirement_type=RequirementType.FACTUAL_OBSERVATION,
                    description="Report one accepted metric-period observation.",
                    required_agents=(AnalysisAgent.COMPANY,),
                    entities=(ENTITY,),
                    periods=(period,),
                    metric_ids=(metric_id,),
                    inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                    fulfillment_policy=(
                        FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS
                        if allows_missing
                        else FulfillmentPolicy.VALID_VALUE_REQUIRED
                    ),
                    missing_data_policy=(
                        MissingDataPolicy.ACCEPTED_MISSINGNESS
                        if allows_missing
                        else MissingDataPolicy.REJECT_MISSING
                    ),
                )
            )
    for metric_id in METRICS:
        requirements.append(
            AnalysisRequirement(
                requirement_id=f"trend-{metric_id}",
                requirement_type=RequirementType.TREND,
                description="Describe the ordered period trend when supported.",
                required_agents=(AnalysisAgent.COMPANY,),
                entities=(ENTITY,),
                periods=PERIODS,
                metric_ids=(metric_id,),
                inference_ceiling=InferenceCeiling.TREND_ALLOWED,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.REJECT_MISSING,
            )
        )
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id="trend-dataset",
        dataset_snapshot_id="trend-snapshot",
        query_id="company-trend-test",
        normalized_question="Report the requested Company trend.",
        scope=AnalysisScope(
            entities=(ENTITY,), periods=PERIODS, company_metric_ids=METRICS
        ),
        requirements=tuple(requirements),
        requested_outputs=("structured_facts", "trend"),
        causal_claim_policy=CausalClaimPolicy.NO_CAUSAL_INFERENCE,
    )


class CompanyTrendCoverageTests(unittest.TestCase):
    def setUp(self):
        self.dataset_ref = DatasetRef(
            dataset_id="trend-dataset", dataset_snapshot_id="trend-snapshot"
        )
        entities = (ENTITY, "entity-b")
        periods = (*PERIODS, "2024_Q3")
        metrics = (*METRICS, "company.cir")
        catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=tuple(
                DatasetEntity(
                    entity_id=entity_id,
                    entity_type=DatasetEntityType.COMPANY,
                    display_name=entity_id,
                )
                for entity_id in entities
            ),
            periods=tuple(
                DatasetPeriod(period_id=period, label=period) for period in periods
            ),
            metrics=tuple(
                DatasetMetric(
                    metric_id=metric_id,
                    display_name=metric_id,
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                )
                for metric_id in metrics
            ),
            supported_operations=(
                "get_metric",
                "get_entity_metrics",
                "get_peer_benchmark",
                "get_evidence",
                "get_source",
                "get_macro_observation",
                "resolve_observation",
            ),
        )
        valid_cells = (
            (ENTITY, "company.roa", "2024_Q1", 1.0),
            (ENTITY, "company.roa", "2024_Q2", 1.2),
            (ENTITY, "company.roe", "2024_Q1", 12.0),
            (ENTITY, "company.roa", "2024_Q3", 1.4),
            ("entity-b", "company.roa", "2024_Q1", 3.0),
        )
        observations = [
            CanonicalObservation(
                observation_id=f"obs-{entity}-{metric}-{period}",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id=entity,
                period_id=period,
                metric_id=metric,
                value=value,
                unit="percent",
                source_ref="source-company",
                source_locator=f"page:{index}",
                period_basis="quarter_only",
                reporting_scope="consolidated",
                validation_status=QualityStatus.VALID,
            )
            for index, (entity, metric, period, value) in enumerate(valid_cells, start=1)
        ]
        observations.append(
            CanonicalObservation(
                observation_id="obs-entity-a-company.roe-2024_Q2",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id=ENTITY,
                period_id="2024_Q2",
                metric_id="company.roe",
                validation_status=QualityStatus.MISSING,
                missing_reason="DATA_UNAVAILABLE",
            )
        )
        provider = InMemoryFinancialDatasetProvider(
            catalog,
            observations=observations,
            sources=(
                DatasetSource(
                    source_ref="source-company",
                    source_type="filing",
                    source_tier="primary",
                    source_url="https://example.test/filing",
                    publisher="Company",
                    retrieved_at="2026-09-26",
                    content_hash="fixture-hash",
                    validation_status=QualityStatus.VALID,
                ),
            ),
            evidence=(
                DatasetEvidence(
                    evidence_id="evidence-roa-q1",
                    source_ref="source-company",
                    entity_id=ENTITY,
                    period_id="2024_Q1",
                    metric_id="company.roa",
                    locator="page:1",
                    quote="Reported ROA observation.",
                ),
            ),
        )
        self.resolver = ProviderStage1DatasetResolver(provider, self.dataset_ref)
        self.policy = AcceptancePolicy(
            policy_version="company-trend-coverage-test-v1",
            provisional_threshold=0.75,
        )
        self.plan = _plan()
        self.workload_scope = ClaimScope(
            entities=(ENTITY,), periods=PERIODS, metric_ids=METRICS
        )

    def _ref(self, metric_id: str, period: str, *, entity: str = ENTITY, ref_type="observation"):
        return ClaimDataRef(
            ref_id=f"obs-{entity}-{metric_id}-{period}",
            ref_type=ref_type,
            entity=entity,
            period=period,
            metric_id=metric_id,
        )

    def _matrix_claim(self) -> AtomicClaim:
        assertions = []
        for metric_id, period, value in (
            ("company.roa", "2024_Q1", 1.0),
            ("company.roa", "2024_Q2", 1.2),
            ("company.roe", "2024_Q1", 12.0),
        ):
            assertions.append(
                StructuredAssertion(
                    assertion_id=f"value-{metric_id}-{period}",
                    assertion_type=AssertionType.METRIC_VALUE,
                    entity=ENTITY,
                    period=period,
                    metric_id=metric_id,
                    asserted_value=value,
                    unit="percent",
                    data_refs=(self._ref(metric_id, period),),
                )
            )
        assertions.append(
            StructuredAssertion(
                assertion_id="missing-company.roe-2024_Q2",
                assertion_type=AssertionType.MISSINGNESS,
                entity=ENTITY,
                period="2024_Q2",
                metric_id="company.roe",
                operator=AssertionOperator.MISSING,
                data_refs=(
                    self._ref("company.roe", "2024_Q2", ref_type="missing_cell"),
                ),
            )
        )
        return AtomicClaim(
            claim_id="company-matrix",
            claim_text="The requested metric and period observations were reviewed.",
            claim_type="factual",
            title="Company facts",
            interpretation="Each period has one accepted value or missing state.",
            limitation="One fixture snapshot.",
            scope=self.workload_scope,
            assertions=tuple(assertions),
            evidence_refs=("evidence-roa-q1",),
            source_refs=("source-company",),
            inference_type=InferenceType.FACT,
            support="evidence_backed",
        )

    def _validate(self, claims):
        return validate_stage1_claims(
            self.resolver,
            tuple(claims),
            self.workload_scope,
            self.policy,
            plan=self.plan,
        )

    def test_complete_company_matrix_accepts_explicit_accepted_missing_cell(self):
        result = self._validate((self._matrix_claim(),))
        self.assertTrue(result.passed, result.model_dump_json())
        self.assertTrue(result.gate_results["scope_compliance"].passed)

    def test_dropped_matrix_cell_fails_stage1(self):
        claim = self._matrix_claim()
        reduced = claim.model_copy(
            update={
                "assertions": tuple(
                    assertion
                    for assertion in claim.assertions
                    if assertion.assertion_id != "value-company.roe-2024_Q1"
                )
            }
        )
        result = self._validate((reduced,))
        self.assertFalse(result.passed)
        self.assertIn(
            "company_metric_period_missing:entity-a|company.roe|2024_Q1",
            result.gate_results["scope_compliance"].violations,
        )

    def test_duplicate_cell_fails_stage1(self):
        claim = self._matrix_claim()
        duplicate = claim.assertions[0].model_copy(
            update={"assertion_id": "duplicate-roa-q1"}
        )
        result = self._validate(
            (claim, claim.model_copy(update={"claim_id": "duplicate-claim", "assertions": (duplicate,)}))
        )
        self.assertFalse(result.passed)
        self.assertIn(
            "company_metric_period_duplicate:entity-a|company.roa|2024_Q1",
            result.gate_results["scope_compliance"].violations,
        )

    def test_extra_and_wrong_scope_cells_fail_stage1(self):
        claim = self._matrix_claim()
        extra = StructuredAssertion(
            assertion_id="extra-roa-q3",
            assertion_type=AssertionType.METRIC_VALUE,
            entity=ENTITY,
            period="2024_Q3",
            metric_id="company.roa",
            asserted_value=1.4,
            unit="percent",
            data_refs=(self._ref("company.roa", "2024_Q3"),),
        )
        expanded = claim.model_copy(
            update={
                "scope": claim.scope.model_copy(
                    update={"periods": (*PERIODS, "2024_Q3")}
                ),
                "assertions": (*claim.assertions, extra),
            }
        )
        result = self._validate((expanded,))
        self.assertFalse(result.passed)
        self.assertIn(
            "company_metric_period_extra:entity-a|company.roa|2024_Q3",
            result.gate_results["scope_compliance"].violations,
        )

        first = claim.assertions[0]
        wrong_ref = self._ref("company.roa", "2024_Q1", entity="entity-b")
        wrong_scope = claim.model_copy(
            update={
                "scope": claim.scope.model_copy(update={"entities": (ENTITY, "entity-b")}),
                "assertions": (
                    first.model_copy(update={"data_refs": (wrong_ref,)}),
                    *claim.assertions[1:],
                ),
            }
        )
        wrong_result = self._validate((wrong_scope,))
        self.assertFalse(wrong_result.passed)
        self.assertIn(
            "company_metric_period_numeric_lineage_mismatch:entity-a|company.roa|2024_Q1",
            wrong_result.gate_results["scope_compliance"].violations,
        )

    def test_invalid_missing_row_fails_closed(self):
        claim = self._matrix_claim()
        missing_index = next(
            index
            for index, assertion in enumerate(claim.assertions)
            if assertion.assertion_type is AssertionType.MISSINGNESS
        )
        invalid = claim.assertions[missing_index].model_copy(
            update={"operator": AssertionOperator.EXISTS}
        )
        assertions = list(claim.assertions)
        assertions[missing_index] = invalid
        result = self._validate((claim.model_copy(update={"assertions": tuple(assertions)}),))
        self.assertFalse(result.passed)
        self.assertIn(
            "company_metric_period_missingness_invalid:entity-a|company.roe|2024_Q2",
            result.gate_results["scope_compliance"].violations,
        )

    def test_range_trend_assertion_cannot_replace_period_cells(self):
        trend = StructuredAssertion(
            assertion_id="roa-trend",
            assertion_type=AssertionType.TREND,
            entity=ENTITY,
            period="2024_Q2",
            metric_id="company.roa",
            asserted_value=1.2,
            unit="percent",
            operator=AssertionOperator.INCREASE,
            data_refs=(self._ref("company.roa", "2024_Q2"),),
            reference_ref=self._ref("company.roa", "2024_Q1"),
        )
        trend_claim = AtomicClaim(
            claim_id="trend-only",
            claim_text="ROA increased over the requested period.",
            claim_type="trend",
            title="ROA trend",
            interpretation="The range-level trend is directionally increasing.",
            limitation="The trend does not replace per-period observations.",
            scope=ClaimScope(
                entities=(ENTITY,), periods=PERIODS, metric_ids=("company.roa",)
            ),
            assertions=(trend,),
            source_refs=("source-company",),
            inference_type=InferenceType.TREND,
        )
        result = self._validate((trend_claim,))
        self.assertFalse(result.passed)
        violations = result.gate_results["scope_compliance"].violations
        self.assertIn(
            "company_metric_period_missing:entity-a|company.roa|2024_Q1", violations
        )
        self.assertIn(
            "company_metric_period_missing:entity-a|company.roa|2024_Q2", violations
        )


if __name__ == "__main__":
    unittest.main()
