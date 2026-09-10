import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.acceptance import (
    ACCEPTANCE_MODEL_VERSION,
    atomic_claim_to_legacy_composite_claim,
    legacy_composite_claim_to_atomic,
    quality_score,
    validate_stage1_claims,
)
from thesis_data.composite_schema import CompositeClaim
from thesis_data.schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AcceptanceRound,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    InferenceType,
    QualityDimensionScores,
    ReportAcceptanceState,
    ReportStatementLink,
    HardGateResult,
    StructuredAssertion,
    UnresolvedReasonCode,
)
from thesis_data.storage import create_gold_snapshot_schema


class AcceptanceTests(unittest.TestCase):
    def fixture(self) -> tuple[Path, ClaimScope]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        db = root / "gold.sqlite"
        create_gold_snapshot_schema(db)
        connection = sqlite3.connect(db)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                "gold-acceptance-fixture",
                "2026-09-10T00:00:00Z",
                "gold",
                json.dumps({"tickers": ["ACB", "TCB"]}),
            ),
        )
        sources = [
            (
                "source-acb",
                "filing",
                "primary",
                "https://fixture.test/acb",
                "2026-09-10T00:00:00Z",
                "ACB.pdf",
                "hash-acb",
                "ACB",
                "test",
                "valid",
                None,
            ),
            (
                "source-tcb",
                "filing",
                "primary",
                "https://fixture.test/tcb",
                "2026-09-10T00:00:00Z",
                "TCB.pdf",
                "hash-tcb",
                "TCB",
                "test",
                "valid",
                None,
            ),
        ]
        connection.executemany("INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", sources)
        observations = [
            (
                "obs-acb-q1-roe",
                "ACB",
                "bank",
                "bank.roe",
                20.0,
                "%",
                "2024_Q1",
                "2024-03-31",
                "ttm",
                "source-acb",
                "page:10",
                "valid",
                None,
            ),
            (
                "obs-acb-q4-roe",
                "ACB",
                "bank",
                "bank.roe",
                22.0,
                "%",
                "2024_Q4",
                "2024-12-31",
                "ttm",
                "source-acb",
                "page:20",
                "valid",
                None,
            ),
            (
                "obs-tcb-q4-roe",
                "TCB",
                "bank",
                "bank.roe",
                15.0,
                "%",
                "2024_Q4",
                "2024-12-31",
                "ttm",
                "source-tcb",
                "page:30",
                "valid",
                None,
            ),
            (
                "obs-tcb-q1-roe",
                "TCB",
                "bank",
                "bank.roe",
                10.0,
                "%",
                "2024_Q1",
                "2024-03-31",
                "ttm",
                "source-tcb",
                "page:25",
                "valid",
                None,
            ),
        ]
        connection.executemany("INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", observations)
        evidence = [
            (
                "ev-acb-q1-roe",
                "source-acb",
                "ACB.pdf",
                10,
                "ROE",
                "2024_Q1",
                "ACB",
                "ROE was 20 percent.",
                1.0,
                "text_layer",
                1,
            ),
            (
                "ev-acb-q4-roe",
                "source-acb",
                "ACB.pdf",
                20,
                "ROE",
                "2024_Q4",
                "ACB",
                "ROE was 22 percent.",
                1.0,
                "text_layer",
                1,
            ),
            (
                "ev-tcb-q4-roe",
                "source-tcb",
                "TCB.pdf",
                30,
                "ROE",
                "2024_Q4",
                "TCB",
                "ROE was 15 percent.",
                1.0,
                "text_layer",
                1,
            ),
            (
                "ev-tcb-q1-roe",
                "source-tcb",
                "TCB.pdf",
                25,
                "ROE",
                "2024_Q1",
                "TCB",
                "ROE was 10 percent.",
                1.0,
                "text_layer",
                1,
            ),
        ]
        connection.executemany("INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", evidence)
        connection.commit()
        connection.close()
        return db, ClaimScope(
            entities=("ACB", "TCB"),
            periods=("2024_Q1", "2024_Q4"),
            metric_ids=("bank.roe",),
            comparison_universe="bank-peer-fixture",
        )

    def policy(self) -> AcceptancePolicy:
        return AcceptancePolicy(policy_version="test-acceptance-v1", provisional_threshold=0.75)

    def claim(
        self,
        *,
        entity: str = "ACB",
        period: str = "2024_Q4",
        value: float = 22.0,
        evidence: tuple[str, ...] = ("ev-acb-q4-roe",),
        source: tuple[str, ...] = ("source-acb",),
        ref_id: str = "obs-acb-q4-roe",
        ref_type: str = "observation",
    ) -> AtomicClaim:
        ref = ClaimDataRef(
            ref_id=ref_id,
            ref_type=ref_type,
            entity=entity,
            period=period,
            metric_id="bank.roe",
        )
        assertion = StructuredAssertion(
            assertion_id=f"assertion-{entity}-{period}",
            assertion_type=AssertionType.METRIC_VALUE,
            entity=entity,
            period=period,
            metric_id="bank.roe",
            asserted_value=value,
            unit="%",
            data_refs=(ref,),
        )
        return AtomicClaim(
            claim_id=f"claim-{entity}-{period}",
            claim_text=f"{entity} ROE in {period} was {value}%.",
            claim_type="numeric",
            title="ROE",
            interpretation="A directly observed profitability metric.",
            limitation="Fixture limitation.",
            scope=ClaimScope(
                entities=(entity,),
                periods=(period,),
                metric_ids=("bank.roe",),
            ),
            assertions=(assertion,),
            evidence_refs=evidence,
            source_refs=source,
            inference_type=InferenceType.FACT,
            support="evidence_backed" if evidence else "partially_supported",
        )

    def test_stage1_accepts_structured_numeric_claim(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(db, (self.claim(),), workload_scope, self.policy())
        self.assertTrue(result.passed)
        self.assertTrue(all(item.passed for item in result.gate_results.values()))
        self.assertEqual(result.gate_results["numeric_accuracy"].rate, 1.0)

    def test_numeric_accuracy_does_not_parse_claim_text(self):
        db, workload_scope = self.fixture()
        claim = self.claim()
        claim = claim.model_copy(update={"claim_text": "The prose deliberately contains no number."})
        result = validate_stage1_claims(db, (claim,), workload_scope, self.policy())
        self.assertTrue(result.passed)

    def test_numeric_mismatch_fails_without_prose_parsing(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(db, (self.claim(value=23.0),), workload_scope, self.policy())
        self.assertFalse(result.passed)
        self.assertFalse(result.gate_results["numeric_accuracy"].passed)
        self.assertIn("numeric_value_mismatch", " ".join(result.gate_results["numeric_accuracy"].violations))

    def test_legacy_reference_is_not_authoritative(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(
            db,
            (self.claim(ref_id="ACB|2024_Q4|bank.roe", ref_type="legacy"),),
            workload_scope,
            self.policy(),
        )
        self.assertFalse(result.passed)
        self.assertIn("legacy_reference", " ".join(result.gate_results["numeric_accuracy"].violations))

    def test_missing_evidence_fails_only_presence_gate_but_not_numeric_gate(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(db, (self.claim(evidence=()),), workload_scope, self.policy())
        self.assertFalse(result.passed)
        self.assertFalse(result.gate_results["critical_evidence_coverage"].passed)
        self.assertTrue(result.gate_results["numeric_accuracy"].passed)

    def test_invalid_reference_fails_reference_and_unaccepted_gates(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(
            db,
            (self.claim(ref_id="missing-observation"),),
            workload_scope,
            self.policy(),
        )
        self.assertFalse(result.gate_results["reference_validity"].passed)
        self.assertFalse(result.gate_results["fabricated_or_unaccepted_records"].passed)

    def test_claim_scope_is_generalized_and_validated_against_workload_scope(self):
        db, _workload_scope = self.fixture()
        result = validate_stage1_claims(
            db,
            (self.claim(),),
            ClaimScope(entities=("TCB",), periods=("2024_Q4",), metric_ids=("bank.roe",)),
            self.policy(),
        )
        self.assertFalse(result.gate_results["scope_compliance"].passed)

    def test_same_target_conflicting_values_are_deterministic_blockers(self):
        db, workload_scope = self.fixture()
        conflicting = self.claim(value=23.0).model_copy(update={"claim_id": "conflicting-claim"})
        result = validate_stage1_claims(db, (self.claim(), conflicting), workload_scope, self.policy())
        self.assertFalse(result.gate_results["blocking_contradictions"].passed)

    def test_cross_entity_divergence_is_not_automatically_contradiction(self):
        db, workload_scope = self.fixture()
        result = validate_stage1_claims(
            db,
            (
                self.claim(),
                self.claim(
                    entity="TCB",
                    value=15.0,
                    evidence=("ev-tcb-q4-roe",),
                    source=("source-tcb",),
                    ref_id="obs-tcb-q4-roe",
                ),
            ),
            workload_scope,
            self.policy(),
        )
        self.assertTrue(result.gate_results["blocking_contradictions"].passed)
        self.assertTrue(result.gate_results["blocking_contradictions"].deferred_to_critic)

    def test_comparison_and_trend_assertions_are_checked_against_gold(self):
        db, workload_scope = self.fixture()
        acb_q4 = ClaimDataRef(
            ref_id="obs-acb-q4-roe", ref_type="observation", entity="ACB",
            period="2024_Q4", metric_id="bank.roe",
        )
        tcb_q4 = ClaimDataRef(
            ref_id="obs-tcb-q4-roe", ref_type="observation", entity="TCB",
            period="2024_Q4", metric_id="bank.roe",
        )
        tcb_q1 = ClaimDataRef(
            ref_id="obs-tcb-q1-roe", ref_type="observation", entity="TCB",
            period="2024_Q1", metric_id="bank.roe",
        )
        comparison = AtomicClaim(
            claim_id="comparison-1", claim_text="ACB exceeds TCB.", claim_type="comparison",
            title="Peer comparison", interpretation="ACB is higher in the fixture.", limitation="Test only.",
            scope=ClaimScope(entities=("ACB", "TCB"), periods=("2024_Q4",), metric_ids=("bank.roe",)),
            assertions=(StructuredAssertion(
                assertion_id="comparison-assertion", assertion_type=AssertionType.COMPARISON,
                entity="ACB", period="2024_Q4", metric_id="bank.roe", asserted_value=22.0,
                unit="%", operator="gt", reference_ref=tcb_q4, data_refs=(acb_q4, tcb_q4),
            ),),
            evidence_refs=("ev-acb-q4-roe", "ev-tcb-q4-roe"),
            source_refs=("source-acb", "source-tcb"), inference_type=InferenceType.COMPARISON,
            support="evidence_backed",
        )
        trend = AtomicClaim(
            claim_id="trend-1", claim_text="TCB increased.", claim_type="trend",
            title="Trend", interpretation="The value rose over the fixture periods.", limitation="Test only.",
            scope=ClaimScope(entities=("TCB",), periods=("2024_Q1", "2024_Q4"), metric_ids=("bank.roe",)),
            assertions=(StructuredAssertion(
                assertion_id="trend-assertion", assertion_type=AssertionType.TREND,
                entity="TCB", period="2024_Q4", metric_id="bank.roe", operator="increase",
                reference_ref=tcb_q1, data_refs=(tcb_q4,),
            ),),
            evidence_refs=("ev-tcb-q1-roe", "ev-tcb-q4-roe"), source_refs=("source-tcb",),
            inference_type=InferenceType.TREND, support="evidence_backed",
        )
        result = validate_stage1_claims(db, (comparison, trend), workload_scope, self.policy())
        self.assertTrue(result.passed)

    def test_aggregate_assertion_recomputes_peer_median(self):
        db, workload_scope = self.fixture()
        refs = (
            ClaimDataRef(
                ref_id="obs-acb-q4-roe", ref_type="observation", entity="ACB",
                period="2024_Q4", metric_id="bank.roe",
            ),
            ClaimDataRef(
                ref_id="obs-tcb-q4-roe", ref_type="observation", entity="TCB",
                period="2024_Q4", metric_id="bank.roe",
            ),
        )
        claim = AtomicClaim(
            claim_id="aggregate-1", claim_text="Peer median is 18.5%.", claim_type="comparison",
            title="Peer median", interpretation="A deterministic median.", limitation="Test only.",
            scope=ClaimScope(
                entities=("ACB", "TCB"), periods=("2024_Q4",), metric_ids=("bank.roe",),
                comparison_universe="bank-peer-fixture",
            ),
            assertions=(StructuredAssertion(
                assertion_id="aggregate-assertion", assertion_type=AssertionType.AGGREGATE,
                entity="bank-peer-fixture", period="2024_Q4", metric_id="bank.roe",
                asserted_value=18.5, unit="%", operator="eq", data_refs=refs,
            ),),
            evidence_refs=("ev-acb-q4-roe", "ev-tcb-q4-roe"),
            source_refs=("source-acb", "source-tcb"), inference_type=InferenceType.COMPARISON,
            support="evidence_backed",
        )
        result = validate_stage1_claims(db, (claim,), workload_scope, self.policy())
        self.assertTrue(result.gate_results["numeric_accuracy"].passed)

    def test_quality_score_uses_configurable_dimensions(self):
        policy = self.policy()
        scores = {
            "groundedness": 1.0,
            "cross_level_integration": 0.5,
            "answer_coverage": 0.5,
            "logical_soundness": 1.0,
            "uncertainty_limitations": 0.0,
            "analytical_usefulness": 1.0,
        }
        self.assertEqual(quality_score(scores, policy.quality_weights), 0.7)

    def test_legacy_adapter_requires_enrichment_for_stage1(self):
        db, workload_scope = self.fixture()
        legacy = CompositeClaim(
            claim_id="legacy-1",
            claim_type="comparison",
            title="Legacy claim",
            claim="ACB ROE was 22%.",
            interpretation="Legacy interpretation.",
            limitation="Legacy limitation.",
            support="evidence_backed",
            data_refs=("ACB|2024_Q4|bank.roe",),
            evidence_ids=("ev-acb-q4-roe",),
            source_ids=("source-acb",),
        )
        untyped = legacy_composite_claim_to_atomic(legacy)
        self.assertEqual(untyped.assertions[0].assertion_type, AssertionType.REFERENCE_ONLY)
        self.assertFalse(
            validate_stage1_claims(db, (untyped,), workload_scope, self.policy()).passed
        )
        enriched = legacy_composite_claim_to_atomic(
            legacy,
            reference_values={
                "ACB|2024_Q4|bank.roe": {
                    "observation_id": "obs-acb-q4-roe",
                    "value": 22.0,
                    "unit": "%",
                }
            },
        )
        self.assertTrue(validate_stage1_claims(db, (enriched,), workload_scope, self.policy()).passed)
        projected = atomic_claim_to_legacy_composite_claim(enriched)
        self.assertEqual(projected.data_refs, ("ACB|2024_Q4|bank.roe",))

    def test_unresolved_issue_requires_allowed_data_reason(self):
        with self.assertRaises(ValueError):
            CritiqueIssue(
                issue_id="issue-1",
                issue_type=CritiqueIssueType.MISSING_EVIDENCE,
                severity=CritiqueSeverity.MAJOR,
                affected_agent="company",
                description="No evidence.",
                required_action=CritiqueAction.RETRIEVE_EVIDENCE,
                resolution_status=CritiqueIssueStatus.UNRESOLVED,
            )
        issue = CritiqueIssue(
            issue_id="issue-1",
            issue_type=CritiqueIssueType.MISSING_EVIDENCE,
            severity=CritiqueSeverity.MAJOR,
            affected_agent="company",
            description="The source is unavailable.",
            required_action=CritiqueAction.RETRIEVE_EVIDENCE,
            resolution_status=CritiqueIssueStatus.UNRESOLVED,
            unresolved_reason_code=UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
        )
        self.assertEqual(issue.unresolved_reason_code, UnresolvedReasonCode.EVIDENCE_UNAVAILABLE)

    def test_limited_acceptance_is_rejected_for_reasoning_failure(self):
        issue = CritiqueIssue(
            issue_id="issue-reasoning",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MAJOR,
            affected_agent="company",
            description="Available evidence was ignored.",
            required_action=CritiqueAction.REMOVE_CLAIM,
            resolution_status=CritiqueIssueStatus.UNRESOLVED,
            unresolved_reason_code=UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
        )
        gates = {
            gate_id: HardGateResult(gate_id=gate_id, passed=True, rate=1.0)
            for gate_id in (
                "numeric_accuracy", "reference_validity", "critical_evidence_coverage",
                "scope_compliance", "fabricated_or_unaccepted_records", "blocking_contradictions",
            )
        }
        with self.assertRaises(ValueError):
            AcceptanceRound(
                round_number=0, hard_gate_results=gates, critique_issues=(issue,),
                unresolved_issue_ids=("issue-reasoning",),
                unresolved_reason_codes=(UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,),
                quality_scores=QualityDimensionScores(
                    groundedness=1.0, cross_level_integration=1.0, answer_coverage=1.0,
                    logical_soundness=1.0, uncertainty_limitations=1.0, analytical_usefulness=1.0,
                ),
                quality_total=1.0, provisional_threshold=0.75,
                acceptance_decision=AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
            )

    def test_acceptance_state_persists_round_and_statement_mapping(self):
        policy = self.policy()
        gate_ids = (
            "numeric_accuracy",
            "reference_validity",
            "critical_evidence_coverage",
            "scope_compliance",
            "fabricated_or_unaccepted_records",
            "blocking_contradictions",
        )
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results={
                gate_id: HardGateResult(gate_id=gate_id, passed=True, rate=1.0)
                for gate_id in gate_ids
            },
            quality_scores=QualityDimensionScores(
                groundedness=1.0,
                cross_level_integration=1.0,
                answer_coverage=1.0,
                logical_soundness=1.0,
                uncertainty_limitations=1.0,
                analytical_usefulness=1.0,
            ),
            quality_total=1.0,
            provisional_threshold=policy.provisional_threshold,
            final_payload_version="payload-v1",
            acceptance_decision=AcceptanceDecision.ACCEPT,
        )
        state = ReportAcceptanceState(
            acceptance_model_version=ACCEPTANCE_MODEL_VERSION,
            run_id="run-1",
            policy=policy,
            rounds=(round_state,),
            final_payload_version="payload-v1",
            final_statement_links=(ReportStatementLink(statement_id="statement-1", claim_ids=("claim-1",)),),
            final_decision=AcceptanceDecision.ACCEPT,
        )
        self.assertEqual(state.rounds[0].round_number, 0)
        self.assertEqual(state.final_statement_links[0].claim_ids, ("claim-1",))


if __name__ == "__main__":
    unittest.main()
