import unittest

from pydantic import ValidationError

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
    validate_analysis_plan_request,
    build_tcb_macro_analysis_plan,
)
from thesis_data.analysis_request import AnalysisRequest
from thesis_data.dataset_contract import CanonicalObservation, DatasetRef
from thesis_data.schema import (
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    HardGateResult,
    InferenceType,
    QualityStatus,
    Stage1ValidationReport,
    StructuredAssertion,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticContractError,
    SemanticDimension,
    SemanticDimensionResult,
    StructuredCriticResult,
    deterministic_coverage_violations,
    validate_structured_critic_result,
)


def _minimal_plan(
    *,
    requirement: AnalysisRequirement | None = None,
    dataset_ref: DatasetRef | None = None,
) -> AnalysisPlan:
    dataset_ref = dataset_ref or DatasetRef(
        dataset_id="test-dataset",
        dataset_snapshot_id="test-snapshot",
    )
    requirement = requirement or AnalysisRequirement(
        requirement_id="R1",
        requirement_type=RequirementType.FACTUAL_OBSERVATION,
        description="Report the observation.",
        required_agents=(AnalysisAgent.MACRO,),
        entities=("VN",),
        periods=("2024_Q4",),
        metric_ids=("macro.credit_growth",),
        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
        fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
        missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
    )
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        query_id="test-query",
        normalized_question="Report the observation.",
        scope=AnalysisScope(
            entities=("VN",),
            periods=("2024_Q4",),
            macro_indicator_ids=("macro.credit_growth",),
        ),
        requirements=(requirement,),
        requested_outputs=("structured_facts",),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY,
    )


class _ResolverFixture:
    def __init__(self, observation: CanonicalObservation | None):
        self.dataset_ref = DatasetRef(
            dataset_id="test-dataset",
            dataset_snapshot_id="test-snapshot",
        )
        self._observation = observation

    def resolve_observation_ref(self, ref):
        return self._observation


def _missing_observation(
    *,
    status: QualityStatus = QualityStatus.MISSING,
    missing_reason: str | None = "DATA_UNAVAILABLE",
    value: float | None = None,
) -> CanonicalObservation:
    kwargs = {
        "observation_id": "macro-credit-growth-missing",
        "dataset_id": "test-dataset",
        "dataset_snapshot_id": "test-snapshot",
        "entity_id": "VN",
        "period_id": "2024_Q4",
        "metric_id": "macro.credit_growth",
        "validation_status": status,
        "missing_reason": missing_reason,
        "value": value,
    }
    if status is QualityStatus.VALID:
        kwargs.update(
            unit="percent",
            source_ref="source:official",
            missing_reason=None,
        )
    return CanonicalObservation(**kwargs)


def _missing_resolver(
    *,
    status: QualityStatus = QualityStatus.MISSING,
    missing_reason: str | None = "DATA_UNAVAILABLE",
    value: float | None = None,
) -> _ResolverFixture:
    return _ResolverFixture(
        _missing_observation(
            status=status,
            missing_reason=missing_reason,
            value=value,
        )
    )


def _missing_claim() -> AtomicClaim:
    reference = ClaimDataRef(
        ref_id="macro-credit-growth-missing",
        ref_type="macro_observation",
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
    )
    assertion = StructuredAssertion(
        assertion_id="a1",
        assertion_type=AssertionType.MISSINGNESS,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        operator=AssertionOperator.MISSING,
        data_refs=(reference,),
    )
    return AtomicClaim(
        claim_id="claim-macro-credit-missing",
        claim_text="System credit growth is unavailable for 2024_Q4.",
        claim_type="factual",
        title="Credit-growth missingness",
        interpretation="The unavailable observation is disclosed.",
        limitation="No value is fabricated.",
        scope=ClaimScope(
            entities=("VN",),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _limitation_claim() -> AtomicClaim:
    reference = ClaimDataRef(
        ref_id="macro-context-reference",
        ref_type="macro_observation",
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
    )
    assertion = StructuredAssertion(
        assertion_id="limitation-a1",
        assertion_type=AssertionType.REFERENCE_ONLY,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        data_refs=(reference,),
    )
    return AtomicClaim(
        claim_id="claim-limitation",
        claim_text="One quarter cannot establish a causal relationship.",
        claim_type="limitation",
        title="Causal limitation",
        interpretation="The result is associational rather than causal.",
        limitation="A single period does not establish causality.",
        scope=ClaimScope(
            entities=("VN", "TCB"),
            periods=("2024_Q4",),
            metric_ids=(
                "macro.policy_rate",
                "macro.credit_growth",
                "bank.roa",
                "bank.roe",
            ),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.INTERPRETATION,
    )


def _numeric_claim() -> AtomicClaim:
    reference = ClaimDataRef(
        ref_id="macro-credit-growth-value",
        ref_type="macro_observation",
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
    )
    assertion = StructuredAssertion(
        assertion_id="numeric-a1",
        assertion_type=AssertionType.METRIC_VALUE,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        asserted_value=15.08,
        unit="percent",
        data_refs=(reference,),
    )
    return AtomicClaim(
        claim_id="claim-macro-credit-growth-value",
        claim_text="System credit growth was 15.08% in 2024_Q4.",
        claim_type="factual",
        title="Credit-growth value",
        interpretation="The reported value is available.",
        limitation="The observation is limited to the defined period.",
        scope=ClaimScope(
            entities=("VN",),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _mixed_scope_claim(*, off_scope_assertion: StructuredAssertion) -> AtomicClaim:
    macro_reference = ClaimDataRef(
        ref_id="macro-credit-growth-reference-only",
        ref_type="macro_observation",
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
    )
    macro_assertion = StructuredAssertion(
        assertion_id="macro-reference-only",
        assertion_type=AssertionType.REFERENCE_ONLY,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        data_refs=(macro_reference,),
    )
    return AtomicClaim(
        claim_id="claim-mixed-scope",
        claim_text="The requested macro context is discussed with a separate bank fact.",
        claim_type="factual",
        title="Mixed-scope claim",
        interpretation="Only assertions in the requirement scope can fulfill it.",
        limitation="The bank assertion is outside the macro requirement scope.",
        scope=ClaimScope(
            entities=("VN", "TCB"),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth", "bank.roa"),
        ),
        assertions=(macro_assertion, off_scope_assertion),
        inference_type=InferenceType.FACT,
    )


def _bank_missing_assertion() -> StructuredAssertion:
    reference = ClaimDataRef(
        ref_id="bank-roa-missing",
        ref_type="observation",
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
    )
    return StructuredAssertion(
        assertion_id="bank-missing",
        assertion_type=AssertionType.MISSINGNESS,
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
        operator=AssertionOperator.MISSING,
        data_refs=(reference,),
    )


def _bank_numeric_assertion() -> StructuredAssertion:
    reference = ClaimDataRef(
        ref_id="bank-roa-value",
        ref_type="observation",
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
    )
    return StructuredAssertion(
        assertion_id="bank-numeric",
        assertion_type=AssertionType.METRIC_VALUE,
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
        asserted_value=1.2,
        unit="percent",
        data_refs=(reference,),
    )


def _macro_missingness_with_unrelated_bank_ref_claim() -> AtomicClaim:
    unrelated_reference = ClaimDataRef(
        ref_id="bank-roa-missing-for-macro-assertion",
        ref_type="observation",
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
    )
    assertion = StructuredAssertion(
        assertion_id="macro-missingness-with-bank-ref",
        assertion_type=AssertionType.MISSINGNESS,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        operator=AssertionOperator.MISSING,
        data_refs=(unrelated_reference,),
    )
    return AtomicClaim(
        claim_id="claim-macro-missingness-with-unrelated-ref",
        claim_text="Macro credit growth is unavailable.",
        claim_type="factual",
        title="Mismatched missingness reference",
        interpretation="The reference is intentionally outside the assertion cell.",
        limitation="The reference must not be used as macro evidence.",
        scope=ClaimScope(
            entities=("VN", "TCB"),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth", "bank.roa"),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _passing_stage1() -> Stage1ValidationReport:
    gates = {
        gate_id: HardGateResult(
            gate_id=gate_id,
            passed=True,
            rate=0.0,
            required_rate=0.0,
            evaluation_unit="test",
            evaluated_count=0,
            passed_count=0,
        )
        for gate_id in (
            "numeric_accuracy",
            "reference_validity",
            "critical_evidence_coverage",
            "scope_compliance",
            "fabricated_or_unaccepted_records",
            "blocking_contradictions",
        )
    }
    return Stage1ValidationReport(passed=True, gate_results=gates)


def _result(
    *,
    requirement_ids=("R1",),
    claims=("claim-macro-credit-missing",),
    link_results=(),
    unfulfilled_requirement_ids=(),
) -> StructuredCriticResult:
    dimensions = tuple(
        SemanticDimensionResult(
            dimension=dimension,
            score=1.0,
            rationale="deterministic test rationale",
            supporting_claim_ids=claims,
            affected_requirement_ids=requirement_ids,
        )
        for dimension in SemanticDimension
    )
    return StructuredCriticResult(
        evaluator_version="future-critic-v1",
        dimension_scores=dimensions,
        fulfilled_requirement_ids=requirement_ids,
        unfulfilled_requirement_ids=unfulfilled_requirement_ids,
        applicable_link_results=link_results,
    )


class Phase3AContractTests(unittest.TestCase):
    def test_valid_analysis_plan_construction(self):
        plan = _minimal_plan()

        self.assertEqual(plan.plan_version, ANALYSIS_PLAN_VERSION)
        self.assertEqual(plan.scope.macro_indicator_ids, ("macro.credit_growth",))

    def test_duplicate_requirement_ids_fail(self):
        plan = _minimal_plan()
        payload = plan.model_dump(mode="python")
        requirement = plan.requirements[0].model_dump(mode="python")
        payload["requirements"] = (requirement, requirement)

        with self.assertRaisesRegex(ValueError, "duplicate requirement IDs"):
            AnalysisPlan(**payload)

    def test_frozen_tcb_macro_question_has_expected_requirements(self):
        dataset_ref = DatasetRef(
            dataset_id="gold-finance",
            dataset_snapshot_id="gold-snapshot",
        )
        plan = build_tcb_macro_analysis_plan(dataset_ref)

        self.assertEqual(plan.query_id, "TCB_macro_to_bank_q4")
        self.assertEqual(
            {item.requirement_id for item in plan.requirements},
            {"R1", "R2", "R3", "R4", "R5", "R6", "R7"},
        )
        self.assertEqual(plan.causal_claim_policy, CausalClaimPolicy.ASSOCIATION_ONLY)
        self.assertEqual(plan.scope.macro_indicator_ids, (
            "macro.policy_rate",
            "macro.credit_growth",
        ))
        self.assertEqual(plan.scope.company_metric_ids, ("bank.roa", "bank.roe"))
        self.assertEqual(plan.applicable_links[0].link_id, "L1")
        self.assertEqual(
            plan.applicable_links[0].source_metric_ids,
            ("macro.policy_rate", "macro.credit_growth"),
        )
        self.assertEqual(
            plan.applicable_links[0].target_metric_ids,
            ("bank.roa", "bank.roe"),
        )
        self.assertEqual(
            plan.requirements[5].fulfillment_policy,
            FulfillmentPolicy.DISCLOSURE_REQUIRED,
        )

    def test_credit_growth_accepted_missingness_is_permitted(self):
        plan = _minimal_plan()
        result = _result()

        validate_structured_critic_result(
            plan,
            result,
            (_missing_claim(),),
            stage1_report=_passing_stage1(),
            dataset_resolver=_missing_resolver(),
        )

    def test_unavailable_credit_growth_needs_no_fabricated_numeric_value(self):
        claim = _missing_claim()

        self.assertIsNone(claim.assertions[0].asserted_value)
        validate_structured_critic_result(
            _minimal_plan(),
            _result(),
            (claim,),
            stage1_report=_passing_stage1(),
            dataset_resolver=_missing_resolver(),
        )

    def test_off_scope_missingness_cannot_fulfill_macro_requirement(self):
        claim = _mixed_scope_claim(off_scope_assertion=_bank_missing_assertion())
        with self.assertRaisesRegex(
            SemanticContractError,
            "missing_aware_requirement_has_no_value_or_missingness:R1",
        ):
            validate_structured_critic_result(
                _minimal_plan(),
                _result(claims=("claim-mixed-scope",)),
                (claim,),
                stage1_report=_passing_stage1(),
                dataset_resolver=_ResolverFixture(
                    _missing_observation().model_copy(
                        update={
                            "observation_id": "bank-roa-missing",
                            "entity_id": "TCB",
                            "metric_id": "bank.roa",
                        }
                    )
                ),
            )

    def test_unrelated_ref_cannot_prove_matching_missingness_assertion(self):
        claim = _macro_missingness_with_unrelated_bank_ref_claim()
        bank_missing = _missing_observation().model_copy(
            update={
                "observation_id": "bank-roa-missing-for-macro-assertion",
                "entity_id": "TCB",
                "metric_id": "bank.roa",
            }
        )
        with self.assertRaisesRegex(
            SemanticContractError,
            "accepted_missingness_matching_ref_missing:macro-missingness-with-bank-ref",
        ):
            validate_structured_critic_result(
                _minimal_plan(),
                _result(
                    claims=("claim-macro-missingness-with-unrelated-ref",),
                ),
                (claim,),
                stage1_report=_passing_stage1(),
                dataset_resolver=_ResolverFixture(bank_missing),
            )

    def test_off_scope_numeric_value_cannot_fulfill_valid_macro_requirement(self):
        requirement = AnalysisRequirement(
            requirement_id="R1",
            requirement_type=RequirementType.FACTUAL_OBSERVATION,
            description="Report the observation.",
            required_agents=(AnalysisAgent.MACRO,),
            entities=("VN",),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
            inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
            fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
            missing_data_policy=MissingDataPolicy.REJECT_MISSING,
        )
        claim = _mixed_scope_claim(off_scope_assertion=_bank_numeric_assertion())
        with self.assertRaisesRegex(
            SemanticContractError,
            "valid_value_required_not_fulfilled:R1",
        ):
            validate_structured_critic_result(
                _minimal_plan(requirement=requirement),
                _result(claims=("claim-mixed-scope",)),
                (claim,),
            )

    def test_matching_numeric_assertion_fulfills_valid_value_requirement(self):
        requirement = AnalysisRequirement(
            requirement_id="R1",
            requirement_type=RequirementType.FACTUAL_OBSERVATION,
            description="Report the observation.",
            required_agents=(AnalysisAgent.MACRO,),
            entities=("VN",),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
            inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
            fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
            missing_data_policy=MissingDataPolicy.REJECT_MISSING,
        )
        validate_structured_critic_result(
            _minimal_plan(requirement=requirement),
            _result(claims=("claim-macro-credit-growth-value",)),
            (_numeric_claim(),),
            stage1_report=_passing_stage1(),
        )

    def test_association_only_plan_rejects_causal_inference_ceiling(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="gold-finance", dataset_snapshot_id="gold-snapshot")
        )
        payload = plan.model_dump(mode="python")
        requirements = [item.model_dump(mode="python") for item in plan.requirements]
        requirements[4]["inference_ceiling"] = InferenceCeiling.CAUSAL
        payload["requirements"] = tuple(requirements)

        with self.assertRaisesRegex(ValueError, "causal inference ceiling"):
            AnalysisPlan(**payload)

    def test_semantic_score_outside_range_fails(self):
        with self.assertRaises(ValidationError):
            SemanticDimensionResult(
                dimension=SemanticDimension.GROUNDEDNESS,
                score=1.01,
                rationale="invalid",
            )

    def test_critic_unknown_requirement_fails_closed(self):
        result = _result(requirement_ids=("R999",))

        with self.assertRaisesRegex(SemanticContractError, "unknown_requirement_id:R999"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))

    def test_critic_unknown_claim_fails_closed(self):
        result = _result(claims=("claim-unknown",))

        with self.assertRaisesRegex(SemanticContractError, "unknown_claim_id:claim-unknown"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))

    def test_critic_unknown_link_fails_closed(self):
        link_result = ApplicableLinkResult(
            link_id="L999",
            score=1.0,
            rationale="invalid link",
        )
        result = _result(link_results=(link_result,))

        with self.assertRaisesRegex(SemanticContractError, "unknown_link_id:L999"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))

    def test_analysis_plan_dataset_identity_matches_analysis_request(self):
        dataset_ref = DatasetRef(
            dataset_id="dataset-a",
            dataset_snapshot_id="snapshot-1",
        )
        plan = _minimal_plan(dataset_ref=dataset_ref)
        request = AnalysisRequest(
            request_id="request-1",
            dataset_id="dataset-a",
            dataset_snapshot_id="snapshot-1",
            target_entity_ids=("VN",),
            period_ids=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
            macro_metric_ids=("macro.credit_growth",),
            objective="Report the observation.",
        )
        validate_analysis_plan_request(plan, request)
        self.assertEqual(plan.dataset_ref, dataset_ref)

        mismatched = request.model_copy(update={"dataset_snapshot_id": "snapshot-2"})
        with self.assertRaisesRegex(ValueError, "dataset identity"):
            validate_analysis_plan_request(plan, mismatched)

    def test_plan_dataset_identity_mismatch_with_resolver_fails_closed(self):
        plan = _minimal_plan()
        resolver = _ResolverFixture(_missing_observation())
        resolver.dataset_ref = DatasetRef(
            dataset_id="other-dataset",
            dataset_snapshot_id="other-snapshot",
        )
        with self.assertRaisesRegex(
            SemanticContractError, "analysis_plan_dataset_identity_mismatch"
        ):
            validate_structured_critic_result(
                plan,
                _result(),
                (_missing_claim(),),
                stage1_report=_passing_stage1(),
                dataset_resolver=resolver,
            )

    def test_valid_macro_observation_cannot_satisfy_accepted_missingness(self):
        valid = _missing_observation(
            status=QualityStatus.VALID,
            missing_reason=None,
            value=15.08,
        )
        with self.assertRaisesRegex(
            SemanticContractError, "accepted_missingness_state_not_proven"
        ):
            validate_structured_critic_result(
                _minimal_plan(),
                _result(),
                (_missing_claim(),),
                stage1_report=_passing_stage1(),
                dataset_resolver=_ResolverFixture(valid),
            )

    def test_pending_conflicting_invalid_cells_cannot_satisfy_accepted_missingness(self):
        for status in (
            QualityStatus.PENDING_VALIDATION,
            QualityStatus.CONFLICTING,
            QualityStatus.INVALID,
            QualityStatus.ESTIMATED,
        ):
            with self.subTest(status=status):
                with self.assertRaisesRegex(
                    SemanticContractError, "accepted_missingness_state_not_proven"
                ):
                    validate_structured_critic_result(
                        _minimal_plan(),
                        _result(),
                        (_missing_claim(),),
                        stage1_report=_passing_stage1(),
                        dataset_resolver=_missing_resolver(
                            status=status,
                            missing_reason="REVIEW_REQUIRED",
                        ),
                    )

    def test_accepted_missingness_requires_resolver_even_when_stage1_passes(self):
        with self.assertRaisesRegex(
            SemanticContractError, "accepted_missingness_resolver_required"
        ):
            validate_structured_critic_result(
                _minimal_plan(),
                _result(),
                (_missing_claim(),),
                stage1_report=_passing_stage1(),
            )

    def test_every_applicable_link_has_exactly_one_result(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="gold-finance", dataset_snapshot_id="gold-snapshot")
        )
        violations = deterministic_coverage_violations(
            plan,
            _result(requirement_ids=(), claims=()),
            (),
        )
        self.assertIn("omitted_link_result:L1", violations)

        link_result = ApplicableLinkResult(
            link_id="L1",
            score=1.0,
            rationale="covered",
        )
        no_omission = deterministic_coverage_violations(
            plan,
            _result(requirement_ids=(), claims=(), link_results=(link_result,)),
            (),
        )
        self.assertNotIn("omitted_link_result:L1", no_omission)

        with self.assertRaisesRegex(ValidationError, "unique"):
            StructuredCriticResult(
                evaluator_version="future-critic-v1",
                dimension_scores=_result(requirement_ids=(), claims=()).dimension_scores,
                applicable_link_results=(link_result, link_result),
            )

    def test_r6_uses_disclosure_semantics_not_numeric_value_semantics(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="gold-finance", dataset_snapshot_id="gold-snapshot")
        )
        r6 = next(item for item in plan.requirements if item.requirement_id == "R6")
        self.assertEqual(r6.fulfillment_policy, FulfillmentPolicy.DISCLOSURE_REQUIRED)

        with self.assertRaisesRegex(ValueError, "limitation disclosure"):
            AnalysisRequirement(
                requirement_id="R6-bad",
                requirement_type=RequirementType.LIMITATION_MISSINGNESS_DISCLOSURE,
                description="Disclose a limitation.",
                required_agents=(AnalysisAgent.ORCHESTRATOR,),
                entities=("VN",),
                periods=("2024_Q4",),
                metric_ids=("macro.credit_growth",),
                inference_ceiling=InferenceCeiling.LIMITATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.NOT_APPLICABLE,
            )

        link_result = ApplicableLinkResult(
            link_id="L1",
            score=1.0,
            rationale="covered",
        )
        validate_structured_critic_result(
            plan,
            _result(
                requirement_ids=("R6",),
                claims=("claim-limitation",),
                link_results=(link_result,),
                unfulfilled_requirement_ids=("R1", "R2", "R3", "R4", "R5", "R7"),
            ),
            (_limitation_claim(),),
        )


if __name__ == "__main__":
    unittest.main()
