"""Versioned acceptance contracts and deterministic Stage-1 validation.

This module deliberately stops before model-based critique or revision.  It
owns the mechanical integrity layer and compatibility adapters for the legacy
composite claim shape.  Semantic evidence entailment, unsupported inference,
and cross-level contradiction remain deferred to the future critic.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from .analysis_plan import AnalysisPlan, AnalysisAgent, RequirementType
from .composite_schema import CompositeClaim
from .acceptance_resolver import Stage1DatasetResolver
from .dataset_contract import CanonicalObservation, DatasetSource
from .schema import (
    AcceptancePolicy,
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    CritiqueIssue,
    CritiqueIssueStatus,
    HardGateResult,
    InferenceType,
    QualityDimensionScores,
    QualityWeights,
    Stage1ValidationReport,
    StructuredAssertion,
    UnresolvedReasonCode,
)


ACCEPTANCE_MODEL_VERSION = "report-acceptance-v1"
LEGACY_CLAIM_ADAPTER_VERSION = "legacy-composite-claim-to-atomic-v1"
_NUMERIC_ASSERTION_TYPES = frozenset(
    {
        AssertionType.METRIC_VALUE,
        AssertionType.COMPARISON,
        AssertionType.TREND,
        AssertionType.AGGREGATE,
    }
)


@dataclass(frozen=True)
class _ResolvedReference:
    ref: ClaimDataRef
    value: float | None
    unit: str | None
    quality_status: str
    source_id: str | None
    source_tier: str | None
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class _UnitEvaluation:
    """One evaluation unit and its item-level violations."""

    key: str
    violations: tuple[str, ...] = ()


def _legacy_inference_type(claim_type: str) -> InferenceType:
    normalized = claim_type.strip().lower()
    if "trend" in normalized:
        return InferenceType.TREND
    if "comparison" in normalized or "peer" in normalized:
        return InferenceType.COMPARISON
    if "causal" in normalized:
        return InferenceType.CAUSAL
    if "association" in normalized:
        return InferenceType.ASSOCIATION
    if "interpret" in normalized:
        return InferenceType.INTERPRETATION
    return InferenceType.FACT


def legacy_composite_claim_to_atomic(
    claim: CompositeClaim | Mapping[str, Any],
    *,
    reference_values: Mapping[str, Mapping[str, Any]] | None = None,
    comparison_universe: str | None = None,
) -> AtomicClaim:
    """Adapt a legacy ``CompositeClaim`` without making it publishable.

    The old contract stores refs as ``entity|period|metric`` strings and does
    not carry structured numeric values. When ``reference_values`` is supplied,
    the adapter enriches those refs with canonical values. Otherwise it emits
    explicit ``reference_only``/``legacy`` assertions; Stage-1 correctly
    rejects those as not yet authoritative instead of silently trusting them.
    """

    raw = claim.model_dump(mode="json") if isinstance(claim, CompositeClaim) else dict(claim)
    raw_refs = raw.get("data_refs") or []
    assertions: list[StructuredAssertion] = []
    parsed_refs: list[tuple[str, str, str]] = []
    for raw_ref in raw_refs:
        ref_text = str(raw_ref)
        parts = ref_text.split("|", 2)
        if len(parts) != 3 or any(not part for part in parts):
            raise ValueError(f"legacy data ref must be ticker|period|metric: {ref_text}")
        entity, period, metric_id = parts
        parsed_refs.append((entity, period, metric_id))
        lookup = (reference_values or {}).get(ref_text, {})
        observation_id = lookup.get("observation_id")
        ref_type = "observation" if observation_id else "legacy"
        ref_id = str(observation_id or ref_text)
        data_ref = ClaimDataRef(
            ref_id=ref_id,
            ref_type=ref_type,
            entity=entity,
            period=period,
            metric_id=metric_id,
        )
        value = lookup.get("value")
        unit = lookup.get("unit")
        if value is not None and unit:
            assertion_type = AssertionType.METRIC_VALUE
        else:
            assertion_type = AssertionType.REFERENCE_ONLY
            value = None
            unit = None
        assertions.append(
            StructuredAssertion(
                assertion_id=f"{raw.get('claim_id', 'legacy-claim')}:{len(assertions) + 1}",
                assertion_type=assertion_type,
                entity=entity,
                period=period,
                metric_id=metric_id,
                asserted_value=value,
                unit=unit,
                data_refs=(data_ref,),
            )
        )

    if not parsed_refs:
        raise ValueError("legacy composite claim must contain at least one data ref")
    entities = tuple(dict.fromkeys(item[0] for item in parsed_refs))
    periods = tuple(dict.fromkeys(item[1] for item in parsed_refs))
    metric_ids = tuple(dict.fromkeys(item[2] for item in parsed_refs))
    return AtomicClaim(
        claim_id=str(raw["claim_id"]),
        claim_text=str(raw.get("claim") or raw.get("title") or raw["claim_id"]),
        claim_type=str(raw["claim_type"]),
        title=str(raw.get("title") or raw["claim_id"]),
        interpretation=str(raw.get("interpretation") or "Legacy claim adaptation."),
        limitation=str(raw.get("limitation") or "Legacy claim requires structured assertion enrichment."),
        scope=ClaimScope(
            entities=entities,
            periods=periods,
            metric_ids=metric_ids,
            comparison_universe=comparison_universe,
        ),
        assertions=tuple(assertions),
        evidence_refs=tuple(raw.get("evidence_ids") or ()),
        source_refs=tuple(raw.get("source_ids") or ()),
        inference_type=_legacy_inference_type(str(raw["claim_type"])),
        support=str(raw.get("support") or "partially_supported"),
        priority=str(raw.get("priority") or "normal"),
        origin=str(raw.get("origin") or "model"),
    )


def atomic_claim_to_legacy_composite_claim(claim: AtomicClaim) -> CompositeClaim:
    """Project an atomic claim to the old report/provider contract.

    This adapter is intentionally lossy: the legacy shape cannot represent
    assertion IDs, scope objects, operators, or typed references.  New
    acceptance-aware consumers must use ``AtomicClaim`` instead.
    """

    data_refs = tuple(
        f"{ref.entity}|{ref.period}|{ref.metric_id}"
        for assertion in claim.assertions
        for ref in assertion.data_refs
        if ref.ref_type != "legacy"
    )
    if not data_refs:
        data_refs = tuple(
            f"{claim.scope.entities[0]}|{claim.scope.periods[0]}|{claim.scope.metric_ids[0]}"
            for _ in (0,)
        )
    return CompositeClaim(
        claim_id=claim.claim_id,
        claim_type=claim.claim_type,
        priority=claim.priority,
        title=claim.title,
        claim=claim.claim_text,
        interpretation=claim.interpretation,
        limitation=claim.limitation,
        support=claim.support,
        data_refs=data_refs,
        evidence_ids=claim.evidence_refs,
        source_ids=claim.source_refs,
    )


def quality_score(scores: Mapping[str, float], weights: QualityWeights) -> float:
    """Compute the configurable Stage-2 weighted score without judging it."""

    required = {
        "groundedness",
        "cross_level_integration",
        "answer_coverage",
        "logical_soundness",
        "uncertainty_limitations",
        "analytical_usefulness",
    }
    if set(scores) != required:
        raise ValueError("quality scores must contain exactly the six configured dimensions")
    if any(not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0 for value in scores.values()):
        raise ValueError("quality scores must be finite values in [0, 1]")
    return QualityDimensionScores(**scores).weighted_total(weights)


def _accepted_tier(policy: AcceptancePolicy) -> set[str]:
    return {item.value if hasattr(item, "value") else str(item) for item in policy.accepted_source_tiers}


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _source_reference_violations(
    resolver: Stage1DatasetResolver,
    source_ref: str | None,
    policy: AcceptancePolicy,
    prefix: str,
) -> tuple[DatasetSource | None, list[str]]:
    if not source_ref:
        return None, [f"{prefix}_missing"]
    try:
        source = resolver.resolve_source(source_ref)
    except ValueError:
        source = None
    if source is None:
        return None, [f"{prefix}_unresolved:{source_ref}"]
    violations: list[str] = []
    if _status_value(source.validation_status) != "valid":
        violations.append(f"{prefix}_unaccepted:{source_ref}")
    if _status_value(source.source_tier) not in _accepted_tier(policy):
        violations.append(f"{prefix}_tier_not_allowed:{source_ref}")
    return source, violations


def _resolved_reference(
    ref: ClaimDataRef,
    observation: CanonicalObservation,
    source: DatasetSource | None,
) -> _ResolvedReference:
    return _ResolvedReference(
        ref=ref,
        value=observation.value,
        unit=observation.unit,
        quality_status=_status_value(observation.validation_status),
        source_id=source.source_ref if source is not None else observation.source_ref,
        source_tier=_status_value(source.source_tier) if source is not None else None,
        metadata=observation.metadata,
    )


def _source_locator(observation: CanonicalObservation) -> str | None:
    locator = observation.source_locator
    if not isinstance(locator, str) or not locator.strip():
        return None
    return locator.strip()


def _primary_source_locator_violations(
    resolver: Stage1DatasetResolver,
    *,
    source_ref: str | None,
    locator: str | None,
    policy: AcceptancePolicy,
    prefix: str,
) -> tuple[DatasetSource | None, list[str]]:
    source, violations = _source_reference_violations(
        resolver, source_ref, policy, prefix
    )
    if source is not None and _status_value(source.source_tier) != "primary":
        violations.append(f"{prefix}_tier_not_primary:{source.source_ref}")
    if locator is None or not locator.strip():
        violations.append(f"{prefix}_locator_missing:{source_ref or 'unknown'}")
    return source, violations


def _derived_lineage_violations(
    resolver: Stage1DatasetResolver,
    observation: CanonicalObservation,
    policy: AcceptancePolicy,
    *,
    ref_id: str,
    required_formula_version: str | None,
) -> tuple[list[str], set[str]]:
    """Validate provider-resolved derivation lineage and its primary-backed leaves."""

    violations: list[str] = []
    source_refs: set[str] = set()
    if required_formula_version is not None:
        if not required_formula_version.strip():
            violations.append(f"derived_formula_version_missing:{ref_id}")
        elif observation.derivation_method != required_formula_version:
            violations.append(f"derived_formula_version_mismatch:{ref_id}")
    elif observation.derivation_method is None or not observation.derivation_method.strip():
        violations.append(f"derived_formula_version_missing:{ref_id}")
    if observation.source_ref is not None:
        violations.append(f"derived_source_ref_unexpected:{ref_id}")
    if not observation.input_observation_ids:
        violations.append(f"derived_inputs_missing:{ref_id}")

    visited: set[str] = set()

    def visit_input(observation_id: str, ancestors: frozenset[str]) -> None:
        if observation_id in ancestors:
            violations.append(f"derived_input_cycle:{ref_id}:{observation_id}")
            return
        if observation_id in visited:
            return
        visited.add(observation_id)
        try:
            item = resolver.resolve_observation_id(observation_id)
        except (AttributeError, TypeError, ValueError):
            item = None
        if item is None:
            violations.append(f"derived_input_missing_or_ambiguous:{ref_id}:{observation_id}")
            return
        if item.observation_id != observation_id:
            violations.append(f"derived_input_id_mismatch:{ref_id}:{observation_id}")
            return
        if _status_value(item.validation_status) != "valid":
            violations.append(f"derived_input_unaccepted:{ref_id}:{observation_id}")
            return
        if item.value is None or not math.isfinite(float(item.value)):
            violations.append(f"derived_input_value_missing:{ref_id}:{observation_id}")
        if item.unit is None or not item.unit.strip():
            violations.append(f"derived_input_unit_missing:{ref_id}:{observation_id}")
        if not item.entity_id.strip() or not item.period_id.strip():
            violations.append(f"derived_input_scope_missing:{ref_id}:{observation_id}")

        if item.source_ref:
            if item.derivation_method is not None or item.input_observation_ids:
                violations.append(f"derived_input_provenance_ambiguous:{ref_id}:{observation_id}")
            source, source_violations = _primary_source_locator_violations(
                resolver,
                source_ref=item.source_ref,
                locator=_source_locator(item),
                policy=policy,
                prefix="derived_input_source",
            )
            violations.extend(source_violations)
            if source is not None:
                source_refs.add(source.source_ref)
            return

        if item.derivation_method is None or not item.derivation_method.strip():
            violations.append(f"derived_input_source_missing:{ref_id}:{observation_id}")
            return
        if not item.input_observation_ids:
            violations.append(f"derived_input_lineage_missing:{ref_id}:{observation_id}")
            return
        for nested_id in item.input_observation_ids:
            visit_input(nested_id, ancestors | {observation_id})

    for input_id in observation.input_observation_ids:
        visit_input(input_id, frozenset({observation.observation_id}))
    return list(dict.fromkeys(violations)), source_refs


def _benchmark_reference_violations(
    resolver: Stage1DatasetResolver,
    claim: AtomicClaim,
    assertion: StructuredAssertion,
    ref: ClaimDataRef,
) -> list[str]:
    """Validate a benchmark against requested scope and accepted peer inputs.

    Claim scope and the benchmark identity bind the requested peer universe.
    ``data_refs`` and ``input_observation_ids`` bind only the eligible members
    that actually contribute numeric values. Missing requested members remain
    explicit through per-member records and reasons.
    """

    violations: list[str] = []
    if assertion.assertion_type not in {
        AssertionType.AGGREGATE,
        AssertionType.COMPARISON,
    }:
        violations.append(f"benchmark_contract_unsupported_assertion_type:{ref.ref_id}")
    if claim.scope.comparison_universe is None:
        violations.append(f"benchmark_comparison_universe_missing:{ref.ref_id}")
    elif ref.entity != claim.scope.comparison_universe:
        violations.append(f"benchmark_comparison_universe_mismatch:{ref.ref_id}")

    input_refs = assertion.data_refs
    if not input_refs:
        violations.append(f"benchmark_inputs_missing:{ref.ref_id}")
    else:
        if any(item.ref_type != "observation" for item in input_refs):
            violations.append(f"benchmark_inputs_not_observations:{ref.ref_id}")
        if any(item.period != ref.period or item.metric_id != ref.metric_id for item in input_refs):
            violations.append(f"benchmark_input_scope_mismatch:{ref.ref_id}")
    if claim.scope.comparison_universe is None:
        return violations
    try:
        benchmark = resolver.resolve_benchmark(
            peer_universe_id=claim.scope.comparison_universe,
            peer_entity_ids=claim.scope.entities,
            period_id=ref.period,
            metric_id=ref.metric_id,
        )
    except (TypeError, ValueError):
        benchmark = None
    if benchmark is None or benchmark.observation_id != ref.ref_id:
        violations.append(f"benchmark_reference_unresolved:{ref.ref_id}")
    else:
        if (
            benchmark.entity_id != ref.entity
            or benchmark.period_id != ref.period
            or benchmark.metric_id != ref.metric_id
        ):
            violations.append(f"benchmark_scope_mismatch:{ref.ref_id}")
        metadata = benchmark.metadata
        if metadata.get("aggregation_version") != "peer_median_v1":
            violations.append(f"benchmark_aggregation_version_unsupported:{ref.ref_id}")
        if metadata.get("peer_universe_id") != claim.scope.comparison_universe:
            violations.append(f"benchmark_peer_universe_mismatch:{ref.ref_id}")

        requested_ids = metadata.get("requested_peer_entity_ids")
        eligible_ids = metadata.get("eligible_peer_entity_ids")
        if not isinstance(requested_ids, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in requested_ids
        ):
            requested_ids = ()
            violations.append(f"benchmark_requested_peer_set_missing:{ref.ref_id}")
        if len(set(requested_ids)) != len(requested_ids):
            violations.append(f"benchmark_requested_peer_set_ambiguous:{ref.ref_id}")
        if set(requested_ids) != set(claim.scope.entities) or len(requested_ids) != len(
            claim.scope.entities
        ):
            violations.append(f"benchmark_requested_peer_set_mismatch:{ref.ref_id}")

        if not isinstance(eligible_ids, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in eligible_ids
        ):
            eligible_ids = ()
            violations.append(f"benchmark_eligible_peer_set_missing:{ref.ref_id}")
        if len(set(eligible_ids)) != len(eligible_ids):
            violations.append(f"benchmark_eligible_peer_set_ambiguous:{ref.ref_id}")

        observation_refs = [item for item in input_refs if item.ref_type == "observation"]
        input_ids = [item.ref_id for item in observation_refs]
        input_entities = [item.entity for item in observation_refs]
        if len(set(input_ids)) != len(input_ids) or len(set(input_entities)) != len(
            input_entities
        ):
            violations.append(f"benchmark_inputs_ambiguous:{ref.ref_id}")
        if set(eligible_ids) != set(input_entities) or len(eligible_ids) != len(
            input_entities
        ):
            violations.append(f"benchmark_eligible_peer_set_mismatch:{ref.ref_id}")
        if set(input_ids) != set(benchmark.input_observation_ids) or len(input_ids) != len(
            benchmark.input_observation_ids
        ):
            violations.append(f"benchmark_input_provenance_mismatch:{ref.ref_id}")

        missing_members = metadata.get("missing_members")
        if not isinstance(missing_members, (list, tuple)) or any(
            not isinstance(item, Mapping) for item in missing_members
        ):
            missing_members = ()
            violations.append(f"benchmark_missing_member_records_missing:{ref.ref_id}")
        missing_entities = [item.get("entity_id") for item in missing_members]
        valid_missing_entities = [
            item for item in missing_entities if isinstance(item, str) and item.strip()
        ]
        expected_missing_entities = set(requested_ids) - set(eligible_ids)
        if (
            len(valid_missing_entities) != len(missing_entities)
            or len(set(valid_missing_entities)) != len(valid_missing_entities)
            or set(valid_missing_entities) != expected_missing_entities
            or any(
                not isinstance(item.get("reason"), str) or not item["reason"].strip()
                for item in missing_members
            )
        ):
            violations.append(f"benchmark_missing_member_coverage_mismatch:{ref.ref_id}")

        requested_denominator = metadata.get("requested_denominator")
        eligible_denominator = metadata.get("eligible_denominator")
        if (
            isinstance(requested_denominator, bool)
            or not isinstance(requested_denominator, int)
            or requested_denominator != len(requested_ids)
        ):
            violations.append(f"benchmark_requested_denominator_mismatch:{ref.ref_id}")
        if (
            isinstance(eligible_denominator, bool)
            or not isinstance(eligible_denominator, int)
            or eligible_denominator != len(eligible_ids)
        ):
            violations.append(f"benchmark_eligible_denominator_mismatch:{ref.ref_id}")

        member_records = metadata.get("peer_member_observations")
        if not isinstance(member_records, (list, tuple)) or any(
            not isinstance(item, Mapping) for item in member_records
        ):
            member_records = ()
            violations.append(f"benchmark_member_records_missing:{ref.ref_id}")
        member_entities = [item.get("entity_id") for item in member_records]
        valid_member_entities = [
            item for item in member_entities if isinstance(item, str) and item.strip()
        ]
        if (
            len(valid_member_entities) != len(member_entities)
            or len(set(valid_member_entities)) != len(valid_member_entities)
            or set(valid_member_entities) != set(requested_ids)
            or len(valid_member_entities) != len(requested_ids)
        ):
            violations.append(f"benchmark_member_records_mismatch:{ref.ref_id}")
        eligible_entity_set = set(eligible_ids)
        for item in member_records:
            member_id = item.get("entity_id")
            is_eligible = isinstance(member_id, str) and member_id in eligible_entity_set
            if item.get("accepted") is not is_eligible:
                violations.append(f"benchmark_member_acceptance_mismatch:{ref.ref_id}")
            if is_eligible and item.get("reporting_scope") != benchmark.reporting_scope:
                violations.append(f"benchmark_member_scope_mismatch:{ref.ref_id}")
            if not is_eligible and (
                not isinstance(item.get("reason"), str) or not item["reason"].strip()
            ):
                violations.append(f"benchmark_member_missing_reason:{ref.ref_id}")

        if _status_value(benchmark.validation_status) != "valid":
            violations.append(f"benchmark_unaccepted:{ref.ref_id}")
        if benchmark.value is None or benchmark.unit is None:
            violations.append(f"benchmark_value_unavailable:{ref.ref_id}")
        if not isinstance(benchmark.period_basis, str) or not benchmark.period_basis.strip():
            violations.append(f"benchmark_period_basis_unavailable:{ref.ref_id}")
        if not isinstance(benchmark.reporting_scope, str) or not benchmark.reporting_scope.strip():
            violations.append(f"benchmark_reporting_scope_unavailable:{ref.ref_id}")
        if not benchmark.derivation_method or not benchmark.input_observation_ids:
            violations.append(f"benchmark_derivation_provenance_missing:{ref.ref_id}")
        if benchmark.source_ref is not None:
            violations.append(f"benchmark_source_must_be_derived:{ref.ref_id}")
    return violations


def _observation_reference(
    resolver: Stage1DatasetResolver,
    ref: ClaimDataRef,
    policy: AcceptancePolicy,
    *,
    require_primary_numeric_source: bool = False,
) -> tuple[_ResolvedReference | None, list[str]]:
    if ref.ref_type == "legacy":
        return None, [f"legacy_reference:{ref.ref_id}"]
    if ref.ref_type == "benchmark":
        return None, []
    try:
        observation = resolver.resolve_observation_ref(ref)
    except (TypeError, ValueError):
        observation = None
    if observation is None:
        return None, [f"{ref.ref_type}_reference_missing_or_ambiguous:{ref.ref_id}"]

    violations: list[str] = []
    if observation.observation_id != ref.ref_id:
        violations.append(f"reference_id_mismatch:{ref.ref_id}")
    if (
        observation.entity_id != ref.entity
        or observation.period_id != ref.period
        or observation.metric_id != ref.metric_id
    ):
        violations.append(f"reference_scope_mismatch:{ref.ref_id}")

    status = _status_value(observation.validation_status)
    source: DatasetSource | None = None
    if ref.ref_type == "missing_cell":
        accepted_missing = (
            status == "missing"
            and observation.value is None
            and observation.missing_reason == "DATA_UNAVAILABLE"
        )
        if not accepted_missing:
            violations.append(f"missing_cell_reference_not_missing:{ref.ref_id}")
    elif status == "valid":
        if observation.value is None or observation.unit is None:
            violations.append(f"{ref.ref_type}_value_or_unit_missing:{ref.ref_id}")
        if ref.ref_type == "derived_metric":
            if observation.source_ref is not None or not observation.derivation_method or not observation.input_observation_ids:
                violations.append(f"derived_reference_provenance_invalid:{ref.ref_id}")
        else:
            if not observation.source_ref:
                violations.append(f"{ref.ref_type}_source_missing:{ref.ref_id}")
            else:
                if require_primary_numeric_source:
                    source, source_violations = _primary_source_locator_violations(
                        resolver,
                        source_ref=observation.source_ref,
                        locator=_source_locator(observation),
                        policy=policy,
                        prefix=f"{ref.ref_type}_source",
                    )
                else:
                    source, source_violations = _source_reference_violations(
                        resolver,
                        observation.source_ref,
                        policy,
                        f"{ref.ref_type}_source",
                    )
                    if (
                        ref.ref_type == "macro_observation"
                        and not _source_locator(observation)
                    ):
                        source_violations.append(
                            f"macro_observation_provenance_incomplete:{ref.ref_id}"
                        )
                violations.extend(source_violations)
    elif ref.ref_type == "macro_observation":
        accepted_missing = (
            status == "missing"
            and observation.value is None
            and observation.missing_reason == "DATA_UNAVAILABLE"
            and bool(observation.metadata.get("adjudication_ref"))
        )
        if not accepted_missing:
            violations.append(f"macro_observation_unaccepted:{ref.ref_id}")
    elif ref.ref_type == "observation":
        violations.append(f"observation_reference_unaccepted:{ref.ref_id}")
    elif status != "valid":
        violations.append(f"{ref.ref_type}_reference_unaccepted:{ref.ref_id}")

    return _resolved_reference(ref, observation, source), violations


def _claim_scope_violations(parent: ClaimScope, child: ClaimScope, prefix: str) -> list[str]:
    violations: list[str] = []
    if not set(child.entities).issubset(parent.entities):
        violations.append(f"{prefix}:entities_outside_workload")
    if not set(child.periods).issubset(parent.periods):
        violations.append(f"{prefix}:periods_outside_workload")
    if not set(child.metric_ids).issubset(parent.metric_ids):
        violations.append(f"{prefix}:metrics_outside_workload")
    if child.comparison_universe is not None and child.comparison_universe != parent.comparison_universe:
        violations.append(f"{prefix}:comparison_universe_mismatch")
    return violations


def _assertion_scope_violations(claim: AtomicClaim) -> list[str]:
    violations: list[str] = []
    allowed_entities = set(claim.scope.entities)
    if claim.scope.comparison_universe:
        allowed_entities.add(claim.scope.comparison_universe)
    for assertion in claim.assertions:
        if assertion.entity not in allowed_entities:
            violations.append(f"assertion_entity_outside_scope:{claim.claim_id}:{assertion.assertion_id}")
        if assertion.period not in claim.scope.periods:
            violations.append(f"assertion_period_outside_scope:{claim.claim_id}:{assertion.assertion_id}")
        if assertion.metric_id not in claim.scope.metric_ids:
            violations.append(f"assertion_metric_outside_scope:{claim.claim_id}:{assertion.assertion_id}")
        for ref in assertion.data_refs:
            if ref.entity not in allowed_entities:
                violations.append(f"data_ref_entity_outside_scope:{claim.claim_id}:{ref.ref_id}")
            if ref.period not in claim.scope.periods:
                violations.append(f"data_ref_period_outside_scope:{claim.claim_id}:{ref.ref_id}")
            if ref.metric_id not in claim.scope.metric_ids:
                violations.append(f"data_ref_metric_outside_scope:{claim.claim_id}:{ref.ref_id}")
        for ref in (assertion.reference_ref, assertion.benchmark_ref):
            if ref is None:
                continue
            if ref.entity not in allowed_entities:
                violations.append(f"assertion_ref_entity_outside_scope:{claim.claim_id}:{ref.ref_id}")
            if ref.period not in claim.scope.periods:
                violations.append(f"assertion_ref_period_outside_scope:{claim.claim_id}:{ref.ref_id}")
            if ref.metric_id not in claim.scope.metric_ids:
                violations.append(f"assertion_ref_metric_outside_scope:{claim.claim_id}:{ref.ref_id}")
    return violations


def _evidence_violations(
    resolver: Stage1DatasetResolver,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
) -> list[str]:
    if not claim.critical and claim.claim_type not in policy.critical_claim_types:
        return []

    has_numeric_assertion = any(
        assertion.assertion_type in _NUMERIC_ASSERTION_TYPES
        for assertion in claim.assertions
    )
    if has_numeric_assertion:
        numeric_only_claim = (
            all(
                assertion.assertion_type in _NUMERIC_ASSERTION_TYPES
                for assertion in claim.assertions
            )
            and claim.inference_type in {
                InferenceType.FACT,
                InferenceType.COMPARISON,
                InferenceType.TREND,
            }
        )
        if numeric_only_claim and claim.evidence_refs:
            # AtomicClaim currently has no reviewed observation-to-snippet link.
            # A related document with the same source or period cannot stand in
            # for that link, so numeric-only claims must use their typed data refs.
            return list(dict.fromkeys(
                [f"numeric_document_evidence_unlinked:{claim.claim_id}"]
                + _document_evidence_violations(resolver, claim, policy)
            ))
        if numeric_only_claim:
            return _structured_numeric_evidence_violations(resolver, claim, policy)
        # A mixed or causal statement still needs genuine document evidence for
        # its narrative inference. Numeric assertions are checked independently.
        return _document_evidence_violations(resolver, claim, policy)

    return _document_evidence_violations(resolver, claim, policy)


def _document_evidence_violations(
    resolver: Stage1DatasetResolver,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
) -> list[str]:
    violations: list[str] = []
    if not claim.evidence_refs:
        return [f"critical_claim_evidence_missing:{claim.claim_id}"]
    declared_sources = set(claim.source_refs)
    for evidence_id in claim.evidence_refs:
        try:
            evidence = resolver.resolve_evidence(evidence_id)
        except (TypeError, ValueError):
            evidence = None
        if evidence is None:
            violations.append(f"evidence_reference_missing_or_ambiguous:{claim.claim_id}:{evidence_id}")
            continue
        _source, source_violations = _source_reference_violations(
            resolver, evidence.source_ref, policy, "evidence_source"
        )
        violations.extend(
            f"{item}:{claim.claim_id}:{evidence_id}" for item in source_violations
        )
        if evidence.entity_id is not None and evidence.entity_id not in claim.scope.entities:
            violations.append(f"evidence_entity_outside_scope:{claim.claim_id}:{evidence_id}")
        if evidence.period_id is not None and evidence.period_id not in claim.scope.periods:
            violations.append(f"evidence_period_outside_scope:{claim.claim_id}:{evidence_id}")
        if evidence.metric_id is not None and evidence.metric_id not in claim.scope.metric_ids:
            violations.append(f"evidence_metric_outside_scope:{claim.claim_id}:{evidence_id}")
        if evidence.entity_id is None and evidence.period_id is None:
            violations.append(f"evidence_scope_missing:{claim.claim_id}:{evidence_id}")
        if declared_sources and evidence.source_ref not in declared_sources:
            violations.append(f"evidence_source_not_declared:{claim.claim_id}:{evidence_id}")
    return violations


def _structured_numeric_evidence_violations(
    resolver: Stage1DatasetResolver,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
) -> list[str]:
    """Require numeric evidence to resolve wholly through provider observations."""

    violations: list[str] = []
    resolved_source_refs: set[str] = set()
    for assertion in claim.assertions:
        violations.extend(
            _numeric_assertion_violations(resolver, claim, policy, assertion)
        )
        refs = list(assertion.data_refs)
        if assertion.reference_ref is not None:
            refs.append(assertion.reference_ref)
        for ref in refs:
            if ref.ref_type == "benchmark":
                continue
            resolved, _ref_violations = _observation_reference(
                resolver,
                ref,
                policy,
                require_primary_numeric_source=True,
            )
            if resolved is not None and resolved.source_id:
                resolved_source_refs.add(resolved.source_id)
            if ref.ref_type != "derived_metric":
                continue
            try:
                derived = resolver.resolve_observation_ref(ref)
            except (TypeError, ValueError):
                derived = None
            if derived is None:
                continue
            asserted_value_ref = (
                ref in assertion.data_refs
                and ref.entity == assertion.entity
                and ref.period == assertion.period
                and ref.metric_id == assertion.metric_id
            )
            lineage_violations, lineage_source_refs = _derived_lineage_violations(
                resolver,
                derived,
                policy,
                ref_id=ref.ref_id,
                required_formula_version=(
                    assertion.formula_version or "" if asserted_value_ref else None
                ),
            )
            violations.extend(lineage_violations)
            resolved_source_refs.update(lineage_source_refs)
    for source_ref in sorted(resolved_source_refs - set(claim.source_refs)):
        violations.append(f"numeric_source_not_declared:{claim.claim_id}:{source_ref}")
    return list(dict.fromkeys(violations))


def _reference_evaluations(
    resolver: Stage1DatasetResolver,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[_UnitEvaluation]:
    """Evaluate each typed reference occurrence as one denominator unit.

    A single reference can emit multiple diagnostic messages, but its pass/fail
    status is counted once.  Source IDs are included because they are also
    persisted provenance references and are resolved deterministically here.
    """

    evaluations: list[_UnitEvaluation] = []
    for claim_index, claim in enumerate(claims):
        for assertion in claim.assertions:
            refs: list[tuple[str, ClaimDataRef]] = [
                (f"data:{index}", ref)
                for index, ref in enumerate(assertion.data_refs)
            ]
            if assertion.reference_ref is not None:
                refs.append(("reference", assertion.reference_ref))
            if assertion.benchmark_ref is not None:
                refs.append(("benchmark", assertion.benchmark_ref))
            for role, ref in refs:
                if ref.ref_type == "benchmark":
                    ref_violations = _benchmark_reference_violations(
                        resolver, claim, assertion, ref
                    )
                else:
                    _resolved, ref_violations = _observation_reference(
                        resolver,
                        ref,
                        policy,
                        require_primary_numeric_source=(
                            assertion.assertion_type in _NUMERIC_ASSERTION_TYPES
                        ),
                    )
                    if ref.ref_type == "derived_metric":
                        try:
                            derived = resolver.resolve_observation_ref(ref)
                        except (TypeError, ValueError):
                            derived = None
                        if derived is not None:
                            is_asserted_value = (
                                role.startswith("data:")
                                and assertion.assertion_type in _NUMERIC_ASSERTION_TYPES
                                and ref.entity == assertion.entity
                                and ref.period == assertion.period
                                and ref.metric_id == assertion.metric_id
                            )
                            lineage_violations, lineage_sources = _derived_lineage_violations(
                                resolver,
                                derived,
                                policy,
                                ref_id=ref.ref_id,
                                required_formula_version=(
                                    (assertion.formula_version or "")
                                    if is_asserted_value
                                    else None
                                ),
                            )
                            ref_violations.extend(lineage_violations)
                            for source_ref in sorted(lineage_sources - set(claim.source_refs)):
                                ref_violations.append(
                                    f"derived_input_source_not_declared:{ref.ref_id}:{source_ref}"
                                )
                evaluations.append(
                    _UnitEvaluation(
                        key=f"claim:{claim_index}:{claim.claim_id}:{assertion.assertion_id}:{role}:{ref.ref_id}",
                        violations=tuple(
                            dict.fromkeys(
                                f"{claim.claim_id}:{item}" for item in ref_violations
                            )
                        ),
                    )
                )
        for source_index, source_id in enumerate(claim.source_refs):
            _source, source_violations = _source_reference_violations(
                resolver, source_id, policy, "source_reference"
            )
            source_violations = [f"{item}:{claim.claim_id}" for item in source_violations]
            evaluations.append(
                _UnitEvaluation(
                    key=f"claim:{claim_index}:{claim.claim_id}:source:{source_index}:{source_id}",
                    violations=tuple(dict.fromkeys(source_violations)),
                )
            )
    return evaluations


def _resolve_data_refs(
    resolver: Stage1DatasetResolver,
    refs: Sequence[ClaimDataRef],
    policy: AcceptancePolicy,
) -> tuple[list[_ResolvedReference], list[str]]:
    resolved: list[_ResolvedReference] = []
    violations: list[str] = []
    for ref in refs:
        if ref.ref_type == "benchmark":
            continue
        item, item_violations = _observation_reference(
            resolver,
            ref,
            policy,
            require_primary_numeric_source=True,
        )
        violations.extend(item_violations)
        if item is not None:
            resolved.append(item)
    return resolved, violations


def _number_equal(left: float, right: float, tolerance: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)


def _operator_holds(operator: AssertionOperator, left: float, right: float, tolerance: float) -> bool:
    if operator is AssertionOperator.EQ:
        return _number_equal(left, right, tolerance)
    if operator is AssertionOperator.GT:
        return left > right + tolerance
    if operator is AssertionOperator.GTE:
        return left >= right - tolerance
    if operator is AssertionOperator.LT:
        return left < right - tolerance
    if operator is AssertionOperator.LTE:
        return left <= right + tolerance
    if operator is AssertionOperator.INCREASE:
        return left > right + tolerance
    if operator is AssertionOperator.DECREASE:
        return left < right - tolerance
    raise ValueError(f"operator is not numeric: {operator}")


def _find_entity_value(
    assertion: StructuredAssertion,
    resolved: Sequence[_ResolvedReference],
) -> _ResolvedReference | None:
    for item in resolved:
        if (
            item.ref.entity == assertion.entity
            and item.ref.period == assertion.period
            and item.ref.metric_id == assertion.metric_id
            and item.value is not None
        ):
            return item
    return None


def _numeric_assertion_violations(
    resolver: Stage1DatasetResolver,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
    assertion: StructuredAssertion,
) -> list[str]:
    violations: list[str] = []
    resolved, ref_violations = _resolve_data_refs(resolver, assertion.data_refs, policy)
    if ref_violations:
        violations.extend(
            f"{claim.claim_id}:{assertion.assertion_id}:{item}" for item in ref_violations
        )
        return violations

    for ref in assertion.data_refs:
        if ref.ref_type != "derived_metric":
            continue
        asserted_value_ref = (
            ref.entity == assertion.entity
            and ref.period == assertion.period
            and ref.metric_id == assertion.metric_id
        )
        try:
            derived = resolver.resolve_observation_ref(ref)
        except (TypeError, ValueError):
            derived = None
        if derived is None:
            continue
        lineage_violations, _lineage_sources = _derived_lineage_violations(
            resolver,
            derived,
            policy,
            ref_id=ref.ref_id,
            required_formula_version=(
                (assertion.formula_version or "") if asserted_value_ref else None
            ),
        )
        violations.extend(
            f"{claim.claim_id}:{assertion.assertion_id}:{item}"
            for item in lineage_violations
        )
    if violations:
        return list(dict.fromkeys(violations))

    if assertion.assertion_type is AssertionType.AGGREGATE:
        if assertion.benchmark_ref is None:
            violations.append(
                f"numeric_benchmark_reference_missing:{claim.claim_id}:{assertion.assertion_id}"
            )
            return violations
        benchmark_violations = _benchmark_reference_violations(
            resolver, claim, assertion, assertion.benchmark_ref
        )
        if benchmark_violations:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                for item in benchmark_violations
            )
            return violations
        try:
            benchmark = resolver.resolve_benchmark(
                peer_universe_id=claim.scope.comparison_universe or "",
                peer_entity_ids=claim.scope.entities,
                period_id=assertion.benchmark_ref.period,
                metric_id=assertion.benchmark_ref.metric_id,
            )
        except (TypeError, ValueError):
            benchmark = None
        if benchmark is None or benchmark.value is None:
            violations.append(f"numeric_aggregate_unavailable:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        if assertion.unit is not None and any(item.unit != assertion.unit for item in resolved):
            violations.append(f"numeric_aggregate_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        if assertion.operator is not AssertionOperator.EQ or assertion.asserted_value is None:
            violations.append(
                f"numeric_aggregate_operator_unsupported:{claim.claim_id}:{assertion.assertion_id}"
            )
            return violations
        if assertion.unit is not None and benchmark.unit != assertion.unit:
            violations.append(f"numeric_aggregate_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        expected = float(benchmark.value)
        if not _number_equal(float(assertion.asserted_value), expected, policy.numeric_tolerance):
            violations.append(f"numeric_aggregate_mismatch:{claim.claim_id}:{assertion.assertion_id}")
        return violations

    lhs = _find_entity_value(assertion, resolved)
    if lhs is None:
        violations.append(f"numeric_lhs_missing:{claim.claim_id}:{assertion.assertion_id}")
        return violations
    if assertion.unit is not None and lhs.unit != assertion.unit:
        violations.append(f"numeric_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
        return violations
    if assertion.asserted_value is not None and not _number_equal(
        float(assertion.asserted_value), float(lhs.value), policy.numeric_tolerance
    ):
        violations.append(f"numeric_value_mismatch:{claim.claim_id}:{assertion.assertion_id}")
        return violations

    if assertion.assertion_type is AssertionType.METRIC_VALUE:
        return violations
    if assertion.operator is None:
        violations.append(f"numeric_operator_missing:{claim.claim_id}:{assertion.assertion_id}")
        return violations
    rhs: float | None = None
    if assertion.reference_ref is not None:
        reference, reference_violations = _observation_reference(
            resolver, assertion.reference_ref, policy
        )
        if reference_violations or reference is None or reference.value is None:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                for item in reference_violations or ["numeric_reference_unavailable"]
            )
            return violations
        rhs = float(reference.value)
    elif assertion.benchmark_ref is not None:
        benchmark_violations = _benchmark_reference_violations(
            resolver, claim, assertion, assertion.benchmark_ref
        )
        if benchmark_violations:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                for item in benchmark_violations
            )
            return violations
        try:
            benchmark = resolver.resolve_benchmark(
                peer_universe_id=claim.scope.comparison_universe or "",
                peer_entity_ids=claim.scope.entities,
                period_id=assertion.benchmark_ref.period,
                metric_id=assertion.benchmark_ref.metric_id,
            )
        except (TypeError, ValueError):
            benchmark = None
        if benchmark is None or benchmark.value is None:
            violations.append(f"numeric_benchmark_unavailable:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        if assertion.unit is not None and benchmark.unit != assertion.unit:
            violations.append(f"numeric_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        rhs = float(benchmark.value)
    else:
        violations.append(
            f"numeric_comparison_reference_missing:{claim.claim_id}:{assertion.assertion_id}"
        )
        return violations

    if not _operator_holds(assertion.operator, float(lhs.value), rhs, policy.numeric_tolerance):
        violations.append(f"numeric_operator_mismatch:{claim.claim_id}:{assertion.assertion_id}")
    return violations


def _scope_evaluations(
    claims: Sequence[AtomicClaim],
    workload_scope: ClaimScope,
) -> list[_UnitEvaluation]:
    """Evaluate one scope bundle per claim, including all nested assertions."""

    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}",
            violations=tuple(
                dict.fromkeys(
                    _claim_scope_violations(workload_scope, claim.scope, f"claim:{claim.claim_id}")
                    + _assertion_scope_violations(claim)
                )
            ),
        )
        for index, claim in enumerate(claims)
    ]


def _evidence_evaluations(
    resolver: Stage1DatasetResolver,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[_UnitEvaluation]:
    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}",
            violations=tuple(dict.fromkeys(_evidence_violations(resolver, claim, policy))),
        )
        for index, claim in enumerate(claims)
        if claim.critical or claim.claim_type in policy.critical_claim_types
    ]


def _numeric_evaluations(
    resolver: Stage1DatasetResolver,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[_UnitEvaluation]:
    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}:{assertion.assertion_id}",
            violations=tuple(
                dict.fromkeys(_numeric_assertion_violations(resolver, claim, policy, assertion))
            ),
        )
        for index, claim in enumerate(claims)
        for assertion in claim.assertions
        if assertion.assertion_type in _NUMERIC_ASSERTION_TYPES
    ]


def _deterministic_contradiction_evaluations(
    claims: Sequence[AtomicClaim],
    tolerance: float,
) -> list[_UnitEvaluation]:
    grouped: dict[tuple[str, str, str, str], list[tuple[str, float]]] = {}
    for claim in claims:
        for assertion in claim.assertions:
            if assertion.assertion_type is not AssertionType.METRIC_VALUE:
                continue
            if assertion.asserted_value is None or assertion.unit is None:
                continue
            key = (assertion.entity, assertion.period, assertion.metric_id, assertion.unit)
            grouped.setdefault(key, []).append((claim.claim_id, float(assertion.asserted_value)))
    claim_violations: dict[str, list[str]] = {}
    for key, values in grouped.items():
        baseline = values[0][1]
        if any(not _number_equal(value, baseline, tolerance) for _claim_id, value in values[1:]):
            claim_ids = ",".join(claim_id for claim_id, _value in values)
            violation = f"deterministic_claim_value_conflict:{'|'.join(key)}:{claim_ids}"
            for claim_id, _value in values:
                claim_violations.setdefault(claim_id, []).append(violation)
    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}",
            violations=tuple(dict.fromkeys(claim_violations.get(claim.claim_id, []))),
        )
        for index, claim in enumerate(claims)
    ]


def _evaluation_summary(
    evaluations: Sequence[_UnitEvaluation],
    extra_violations: Sequence[str] = (),
) -> tuple[int, int, tuple[str, ...]]:
    """Return counts by evaluation unit and retain diagnostics separately."""

    violations = tuple(
        dict.fromkeys(
            str(item)
            for evaluation in evaluations
            for item in evaluation.violations
        )
    )
    violations = tuple(dict.fromkeys((*violations, *(str(item) for item in extra_violations))))
    return (
        len(evaluations),
        sum(1 for evaluation in evaluations if not evaluation.violations),
        violations,
    )


def _company_trend_coverage_evaluations(
    resolver: Stage1DatasetResolver,
    claims: Sequence[AtomicClaim],
    workload_scope: ClaimScope,
    plan: AnalysisPlan | None,
) -> list[_UnitEvaluation]:
    """Require every cell in a frozen multi-period Company scope exactly once.

    This remains dormant for legacy callers, single-period plans and peer scopes.
    Company trend plans have one entity and one or more company metrics over an
    ordered multi-period scope; their expected facts are the full typed matrix,
    independent of how many factual requirements or claims the producer emits.
    Planned trend assertions are checked separately and never fill a matrix cell.
    """

    if (
        plan is None
        or len(plan.scope.periods) < 2
        or len(plan.scope.entities) != 1
        or not plan.scope.company_metric_ids
        or plan.scope.comparison_universe
    ):
        return []

    target_entity = plan.scope.entities[0]
    expected_cells = tuple(
        (target_entity, metric_id, period)
        for metric_id in plan.scope.company_metric_ids
        for period in plan.scope.periods
    )
    expected_cell_set = set(expected_cells)
    violations: list[str] = []

    if resolver.dataset_ref != plan.dataset_ref:
        violations.append("company_metric_period_plan_dataset_mismatch")
    if (
        set(workload_scope.entities) != set(plan.scope.entities)
        or set(workload_scope.periods) != set(plan.scope.periods)
        or not set(plan.scope.company_metric_ids).issubset(workload_scope.metric_ids)
        or workload_scope.comparison_universe is not None
    ):
        violations.append("company_metric_period_plan_scope_mismatch")

    facts_by_cell: dict[tuple[str, str, str], list[StructuredAssertion]] = {}
    trend_assertions: list[tuple[str, StructuredAssertion]] = []
    for claim in claims:
        for assertion in claim.assertions:
            if assertion.assertion_type in {
                AssertionType.METRIC_VALUE,
                AssertionType.MISSINGNESS,
            }:
                cell = (assertion.entity, assertion.metric_id, assertion.period)
                facts_by_cell.setdefault(cell, []).append(assertion)
            elif assertion.assertion_type is AssertionType.TREND:
                trend_assertions.append((claim.claim_id, assertion))

    evaluations: list[_UnitEvaluation] = []
    for cell in expected_cells:
        entity, metric_id, period = cell
        key = f"company_metric_period:{entity}|{metric_id}|{period}"
        assertions = facts_by_cell.get(cell, [])
        cell_violations: list[str] = []
        if not assertions:
            cell_violations.append(f"company_metric_period_missing:{entity}|{metric_id}|{period}")
        elif len(assertions) != 1:
            cell_violations.append(f"company_metric_period_duplicate:{entity}|{metric_id}|{period}")
        else:
            assertion = assertions[0]
            if assertion.assertion_type is AssertionType.METRIC_VALUE:
                if assertion.asserted_value is None or assertion.unit is None:
                    cell_violations.append(
                        f"company_metric_period_numeric_value_invalid:{entity}|{metric_id}|{period}"
                    )
                if (
                    len(assertion.data_refs) != 1
                    or assertion.data_refs[0].ref_type
                    not in {"observation", "derived_metric"}
                    or (
                        assertion.data_refs
                        and (
                            assertion.data_refs[0].entity,
                            assertion.data_refs[0].metric_id,
                            assertion.data_refs[0].period,
                        )
                        != cell
                    )
                    or assertion.reference_ref is not None
                    or assertion.benchmark_ref is not None
                ):
                    cell_violations.append(
                        f"company_metric_period_numeric_lineage_mismatch:{entity}|{metric_id}|{period}"
                    )
            else:
                missing_ref = (
                    assertion.data_refs[0]
                    if len(assertion.data_refs) == 1
                    else None
                )
                if (
                    assertion.operator is not AssertionOperator.MISSING
                    or assertion.asserted_value is not None
                    or missing_ref is None
                    or missing_ref.ref_type != "missing_cell"
                    or (missing_ref.entity, missing_ref.metric_id, missing_ref.period)
                    != cell
                    or assertion.reference_ref is not None
                    or assertion.benchmark_ref is not None
                ):
                    cell_violations.append(
                        f"company_metric_period_missingness_invalid:{entity}|{metric_id}|{period}"
                    )
                elif missing_ref is not None:
                    try:
                        observation = resolver.resolve_observation_ref(missing_ref)
                    except (TypeError, ValueError):
                        observation = None
                    if (
                        observation is None
                        or _status_value(observation.validation_status) != "missing"
                        or observation.value is not None
                        or not isinstance(observation.missing_reason, str)
                        or not observation.missing_reason.strip()
                    ):
                        cell_violations.append(
                            f"company_metric_period_missingness_unaccepted:{entity}|{metric_id}|{period}"
                        )
        evaluations.append(
            _UnitEvaluation(key=key, violations=tuple(dict.fromkeys(cell_violations)))
        )

    for cell in sorted(set(facts_by_cell) - expected_cell_set):
        evaluations.append(
            _UnitEvaluation(
                key=f"company_metric_period_extra:{'|'.join(cell)}",
                violations=(f"company_metric_period_extra:{'|'.join(cell)}",),
            )
        )

    planned_trends = tuple(
        requirement
        for requirement in plan.requirements
        if requirement.requirement_type is RequirementType.TREND
        and AnalysisAgent.COMPANY in requirement.required_agents
        and tuple(requirement.periods) == tuple(plan.scope.periods)
    )
    for claim_id, assertion in trend_assertions:
        planned = any(
            assertion.entity in requirement.entities
            and assertion.metric_id in requirement.metric_ids
            and assertion.period in requirement.periods
            for requirement in planned_trends
        )
        if not planned:
            evaluations.append(
                _UnitEvaluation(
                    key=f"company_trend_unplanned:{claim_id}:{assertion.assertion_id}",
                    violations=(
                        f"company_trend_assertion_unplanned:{claim_id}:{assertion.assertion_id}",
                    ),
                )
            )

    if violations:
        evaluations.append(
            _UnitEvaluation(
                key="company_metric_period_plan",
                violations=tuple(dict.fromkeys(violations)),
            )
        )
    return evaluations


def validate_stage1_claims(
    resolver: Stage1DatasetResolver,
    claims: Sequence[AtomicClaim],
    workload_scope: ClaimScope,
    policy: AcceptancePolicy,
    *,
    plan: AnalysisPlan | None = None,
) -> Stage1ValidationReport:
    """Run all currently deterministic Stage-1 integrity gates.

    Semantic evidence entailment and semantic contradiction are intentionally
    not guessed here.  The contradiction gate covers mechanically compatible
    duplicate numeric assertions and marks the result as deferred to the
    future critic.
    """

    normalized_claims = tuple(claims)
    integrity_violations = ("empty_claim_set",) if not normalized_claims else ()
    scope_evaluations = _scope_evaluations(normalized_claims, workload_scope)
    company_trend_coverage = _company_trend_coverage_evaluations(
        resolver, normalized_claims, workload_scope, plan
    )
    reference_evaluations = _reference_evaluations(resolver, normalized_claims, policy)
    evidence_evaluations = _evidence_evaluations(resolver, normalized_claims, policy)
    numeric_evaluations = _numeric_evaluations(resolver, normalized_claims, policy)

    contradiction_evaluations = _deterministic_contradiction_evaluations(
        normalized_claims, policy.numeric_tolerance
    )

    def gate(
        gate_id: str,
        evaluations: Sequence[_UnitEvaluation],
        *,
        extra_violations: Sequence[str] = (),
        evaluation_unit: str,
        deferred_to_critic: bool = False,
    ) -> HardGateResult:
        evaluated_count, passed_count, unique_violations = _evaluation_summary(
            evaluations, extra_violations
        )
        rate = passed_count / evaluated_count if evaluated_count else 0.0
        return HardGateResult(
            gate_id=gate_id,
            passed=not unique_violations,
            rate=rate,
            required_rate=1.0 if evaluated_count else 0.0,
            evaluation_unit=evaluation_unit,
            evaluated_count=evaluated_count,
            passed_count=passed_count,
            violations=unique_violations,
            deferred_to_critic=deferred_to_critic,
        )

    gates = {
        "numeric_accuracy": gate(
            "numeric_accuracy", numeric_evaluations, evaluation_unit="numeric_assertion"
        ),
        "reference_validity": gate(
            "reference_validity", reference_evaluations, evaluation_unit="reference"
        ),
        "critical_evidence_coverage": gate(
            "critical_evidence_coverage", evidence_evaluations, evaluation_unit="critical_claim"
        ),
        "scope_compliance": gate(
            "scope_compliance",
            (*scope_evaluations, *company_trend_coverage),
            extra_violations=integrity_violations,
            evaluation_unit="claim_scope_or_company_metric_period_cell",
        ),
        "fabricated_or_unaccepted_records": gate(
            "fabricated_or_unaccepted_records", reference_evaluations, evaluation_unit="reference"
        ),
        "blocking_contradictions": gate(
            "blocking_contradictions",
            contradiction_evaluations,
            extra_violations=integrity_violations,
            evaluation_unit="claim",
            deferred_to_critic=True,
        ),
    }
    return Stage1ValidationReport(
        passed=all(item.passed for item in gates.values()) and not integrity_violations,
        gate_results=gates,
        integrity_violations=integrity_violations,
    )


def allowed_limited_acceptance_reason(code: UnresolvedReasonCode) -> bool:
    """Make the ACCEPT_WITH_LIMITATIONS allow-list explicit and auditable."""

    return code in {
        UnresolvedReasonCode.DATA_UNAVAILABLE,
        UnresolvedReasonCode.DATA_INSUFFICIENT_FOR_SCOPE,
        UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
        UnresolvedReasonCode.EVIDENCE_INSUFFICIENT_FOR_SCOPE,
        UnresolvedReasonCode.PERIOD_NOT_COVERED,
    }
