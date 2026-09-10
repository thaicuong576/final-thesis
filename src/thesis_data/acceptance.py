"""Versioned acceptance contracts and deterministic Stage-1 validation.

This module deliberately stops before model-based critique or revision.  It
owns the mechanical integrity layer and compatibility adapters for the legacy
composite claim shape.  Semantic evidence entailment, unsupported inference,
and cross-level contradiction remain deferred to the future critic.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
from statistics import median
from typing import Any, Mapping, Sequence

from .composite_schema import CompositeClaim
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
    QualityWeights,
    Stage1ValidationReport,
    StructuredAssertion,
    UnresolvedReasonCode,
)


ACCEPTANCE_MODEL_VERSION = "report-acceptance-v1"
LEGACY_CLAIM_ADAPTER_VERSION = "legacy-composite-claim-to-atomic-v1"


@dataclass(frozen=True)
class _ResolvedReference:
    ref: ClaimDataRef
    value: float | None
    unit: str | None
    quality_status: str
    source_id: str | None
    source_tier: str | None


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

    The old contract stores refs as ``ticker|period|metric`` strings and does
    not carry structured numeric values.  When ``reference_values`` is
    supplied, the adapter enriches those refs with Gold values.  Otherwise it
    emits explicit ``reference_only``/``legacy`` assertions; Stage-1 correctly
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
    return round(
        float(scores["groundedness"]) * weights.groundedness
        + float(scores["cross_level_integration"]) * weights.cross_level_integration
        + float(scores["answer_coverage"]) * weights.answer_coverage
        + float(scores["logical_soundness"]) * weights.logical_soundness
        + float(scores["uncertainty_limitations"]) * weights.uncertainty_limitations
        + float(scores["analytical_usefulness"]) * weights.analytical_usefulness,
        12,
    )


def _open_gold(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    required = {"metric_observations", "source_records", "evidence_snippets"}
    tables = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = sorted(required - tables)
    if missing:
        connection.close()
        raise ValueError("Gold database missing required tables: " + ",".join(missing))
    return connection


def _accepted_tier(policy: AcceptancePolicy) -> set[str]:
    return {item.value if hasattr(item, "value") else str(item) for item in policy.accepted_source_tiers}


def _observation_reference(
    connection: sqlite3.Connection,
    ref: ClaimDataRef,
    policy: AcceptancePolicy,
) -> tuple[_ResolvedReference | None, list[str]]:
    if ref.ref_type == "legacy":
        return None, [f"legacy_reference:{ref.ref_id}"]
    if ref.ref_type == "benchmark":
        return None, []
    if ref.ref_type == "derived_metric":
        rows = connection.execute(
            """
            SELECT derived_id, ticker, metric, value, unit, period, quality_status
            FROM derived_metrics
            WHERE derived_id = ?
            """,
            (ref.ref_id,),
        ).fetchall()
        if len(rows) != 1:
            return None, [f"derived_reference_missing_or_ambiguous:{ref.ref_id}"]
        row = rows[0]
        violations: list[str] = []
        if row["ticker"] != ref.entity or row["period"] != ref.period or row["metric"] != ref.metric_id:
            violations.append(f"reference_scope_mismatch:{ref.ref_id}")
        if row["quality_status"] != "valid":
            violations.append(f"derived_reference_unaccepted:{ref.ref_id}")
        return (
            _ResolvedReference(ref, row["value"], row["unit"], row["quality_status"], None, None),
            violations,
        )

    rows = connection.execute(
        """
        SELECT metric.observation_id, metric.ticker, metric.metric, metric.value,
               metric.unit, metric.period, metric.quality_status, metric.source_id,
               source.source_tier, source.quality_status AS source_quality_status
        FROM metric_observations AS metric
        LEFT JOIN source_records AS source ON source.source_id = metric.source_id
        WHERE metric.observation_id = ?
        """,
        (ref.ref_id,),
    ).fetchall()
    if len(rows) != 1:
        return None, [f"observation_reference_missing_or_ambiguous:{ref.ref_id}"]
    row = rows[0]
    violations = []
    if row["ticker"] != ref.entity or row["period"] != ref.period or row["metric"] != ref.metric_id:
        violations.append(f"reference_scope_mismatch:{ref.ref_id}")
    if ref.ref_type == "observation" and row["quality_status"] != "valid":
        violations.append(f"observation_reference_unaccepted:{ref.ref_id}")
    if ref.ref_type == "missing_cell" and row["quality_status"] not in {"missing", "invalid", "conflicting", "pending_validation"}:
        violations.append(f"missing_cell_reference_not_missing:{ref.ref_id}")
    if row["source_quality_status"] != "valid" and ref.ref_type == "observation":
        violations.append(f"observation_source_unaccepted:{ref.ref_id}")
    if (
        ref.ref_type == "observation"
        and row["source_tier"] not in _accepted_tier(policy)
    ):
        violations.append(f"observation_source_tier_not_allowed:{ref.ref_id}")
    return (
        _ResolvedReference(
            ref,
            row["value"],
            row["unit"],
            row["quality_status"],
            row["source_id"],
            row["source_tier"],
        ),
        violations,
    )


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
    connection: sqlite3.Connection,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
) -> list[str]:
    if not claim.critical and claim.claim_type not in policy.critical_claim_types:
        return []
    violations: list[str] = []
    if not claim.evidence_refs:
        return [f"critical_claim_evidence_missing:{claim.claim_id}"]
    allowed_tiers = _accepted_tier(policy)
    declared_sources = set(claim.source_refs)
    for evidence_id in claim.evidence_refs:
        rows = connection.execute(
            """
            SELECT evidence.evidence_id, evidence.source_id, evidence.ticker,
                   evidence.period, source.quality_status, source.source_tier
            FROM evidence_snippets AS evidence
            LEFT JOIN source_records AS source ON source.source_id = evidence.source_id
            WHERE evidence.evidence_id = ?
            """,
            (evidence_id,),
        ).fetchall()
        if len(rows) != 1:
            violations.append(f"evidence_reference_missing_or_ambiguous:{claim.claim_id}:{evidence_id}")
            continue
        row = rows[0]
        if row["quality_status"] != "valid":
            violations.append(f"evidence_source_unaccepted:{claim.claim_id}:{evidence_id}")
        if row["source_tier"] not in allowed_tiers:
            violations.append(f"evidence_source_tier_not_allowed:{claim.claim_id}:{evidence_id}")
        if row["ticker"] is not None and row["ticker"] not in claim.scope.entities:
            violations.append(f"evidence_entity_outside_scope:{claim.claim_id}:{evidence_id}")
        if row["period"] is not None and row["period"] not in claim.scope.periods:
            violations.append(f"evidence_period_outside_scope:{claim.claim_id}:{evidence_id}")
        if row["ticker"] is None and row["period"] is None:
            violations.append(f"evidence_scope_missing:{claim.claim_id}:{evidence_id}")
        if declared_sources and row["source_id"] not in declared_sources:
            violations.append(f"evidence_source_not_declared:{claim.claim_id}:{evidence_id}")
    return violations


def _all_direct_references(claim: AtomicClaim) -> list[ClaimDataRef]:
    refs: list[ClaimDataRef] = []
    for assertion in claim.assertions:
        refs.extend(assertion.data_refs)
        if assertion.reference_ref is not None:
            refs.append(assertion.reference_ref)
        if assertion.benchmark_ref is not None:
            refs.append(assertion.benchmark_ref)
    return refs


def _reference_violations(
    connection: sqlite3.Connection,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[str]:
    violations: list[str] = []
    seen: set[tuple[str, str]] = set()
    for claim in claims:
        for ref in _all_direct_references(claim):
            key = (ref.ref_type, ref.ref_id)
            if key in seen:
                continue
            seen.add(key)
            if ref.ref_type == "benchmark":
                if not ref.ref_id.strip():
                    violations.append("benchmark_reference_empty")
                continue
            _resolved, ref_violations = _observation_reference(connection, ref, policy)
            violations.extend(f"{claim.claim_id}:{item}" for item in ref_violations)
    for claim in claims:
        for source_id in claim.source_refs:
            rows = connection.execute(
                "SELECT source_id, source_tier, quality_status FROM source_records WHERE source_id = ?",
                (source_id,),
            ).fetchall()
            if len(rows) != 1:
                violations.append(f"source_reference_missing_or_ambiguous:{claim.claim_id}:{source_id}")
                continue
            row = rows[0]
            if row["quality_status"] != "valid":
                violations.append(f"source_reference_unaccepted:{claim.claim_id}:{source_id}")
            if row["source_tier"] not in _accepted_tier(policy):
                violations.append(f"source_reference_tier_not_allowed:{claim.claim_id}:{source_id}")
    return violations


def _resolve_data_refs(
    connection: sqlite3.Connection,
    refs: Sequence[ClaimDataRef],
    policy: AcceptancePolicy,
) -> tuple[list[_ResolvedReference], list[str]]:
    resolved: list[_ResolvedReference] = []
    violations: list[str] = []
    for ref in refs:
        if ref.ref_type == "benchmark":
            continue
        item, item_violations = _observation_reference(connection, ref, policy)
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


def _numeric_violations(
    connection: sqlite3.Connection,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
) -> list[str]:
    violations: list[str] = []
    for assertion in claim.assertions:
        resolved, ref_violations = _resolve_data_refs(connection, assertion.data_refs, policy)
        if ref_violations:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}" for item in ref_violations
            )
            continue
        if assertion.assertion_type is AssertionType.REFERENCE_ONLY:
            violations.append(f"numeric_assertion_unmaterialized:{claim.claim_id}:{assertion.assertion_id}")
            continue
        if assertion.assertion_type is AssertionType.MISSINGNESS:
            expected_missing = assertion.operator is AssertionOperator.MISSING
            actual_missing = bool(resolved) and resolved[0].quality_status != "valid"
            if expected_missing != actual_missing:
                violations.append(f"missingness_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            continue

        if assertion.assertion_type is AssertionType.AGGREGATE:
            values = [float(item.value) for item in resolved if item.value is not None]
            if not values:
                violations.append(f"numeric_aggregate_unavailable:{claim.claim_id}:{assertion.assertion_id}")
                continue
            if assertion.unit is not None and any(item.unit != assertion.unit for item in resolved):
                violations.append(f"numeric_aggregate_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
                continue
            if assertion.operator is not AssertionOperator.EQ or assertion.asserted_value is None:
                violations.append(f"numeric_aggregate_operator_unsupported:{claim.claim_id}:{assertion.assertion_id}")
                continue
            expected = float(median(values))
            if not _number_equal(float(assertion.asserted_value), expected, policy.numeric_tolerance):
                violations.append(f"numeric_aggregate_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            continue

        lhs = _find_entity_value(assertion, resolved)
        if lhs is None:
            violations.append(f"numeric_lhs_missing:{claim.claim_id}:{assertion.assertion_id}")
            continue
        if assertion.unit is not None and lhs.unit != assertion.unit:
            violations.append(f"numeric_unit_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            continue
        if assertion.asserted_value is not None and not _number_equal(
            float(assertion.asserted_value), float(lhs.value), policy.numeric_tolerance
        ):
            violations.append(f"numeric_value_mismatch:{claim.claim_id}:{assertion.assertion_id}")
            continue

        if assertion.assertion_type is AssertionType.METRIC_VALUE:
            continue
        if assertion.operator is None:
            violations.append(f"numeric_operator_missing:{claim.claim_id}:{assertion.assertion_id}")
            continue
        rhs: float | None = None
        if assertion.reference_ref is not None:
            reference, reference_violations = _observation_reference(
                connection, assertion.reference_ref, policy
            )
            if reference_violations or reference is None or reference.value is None:
                violations.extend(
                    f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                    for item in reference_violations or ["numeric_reference_unavailable"]
                )
                continue
            rhs = float(reference.value)
        elif assertion.benchmark_ref is not None:
            benchmark_values = [float(item.value) for item in resolved if item.value is not None]
            if not benchmark_values:
                violations.append(f"numeric_benchmark_unavailable:{claim.claim_id}:{assertion.assertion_id}")
                continue
            rhs = float(median(benchmark_values))
        else:
            violations.append(f"numeric_comparison_reference_missing:{claim.claim_id}:{assertion.assertion_id}")
            continue

        if not _operator_holds(assertion.operator, float(lhs.value), rhs, policy.numeric_tolerance):
            violations.append(f"numeric_operator_mismatch:{claim.claim_id}:{assertion.assertion_id}")
    return violations


def _deterministic_contradiction_violations(
    claims: Sequence[AtomicClaim],
    tolerance: float,
) -> list[str]:
    grouped: dict[tuple[str, str, str, str], list[tuple[str, float]]] = {}
    for claim in claims:
        for assertion in claim.assertions:
            if assertion.assertion_type is not AssertionType.METRIC_VALUE:
                continue
            if assertion.asserted_value is None or assertion.unit is None:
                continue
            key = (assertion.entity, assertion.period, assertion.metric_id, assertion.unit)
            grouped.setdefault(key, []).append((claim.claim_id, float(assertion.asserted_value)))
    violations: list[str] = []
    for key, values in grouped.items():
        baseline = values[0][1]
        if any(not _number_equal(value, baseline, tolerance) for _claim_id, value in values[1:]):
            claim_ids = ",".join(claim_id for claim_id, _value in values)
            violations.append(f"deterministic_claim_value_conflict:{'|'.join(key)}:{claim_ids}")
    return violations


def validate_stage1_claims(
    db_path: Path,
    claims: Sequence[AtomicClaim],
    workload_scope: ClaimScope,
    policy: AcceptancePolicy,
) -> Stage1ValidationReport:
    """Run all currently deterministic Stage-1 integrity gates.

    Semantic evidence entailment and semantic contradiction are intentionally
    not guessed here.  The contradiction gate covers mechanically compatible
    duplicate numeric assertions and marks the result as deferred to the
    future critic.
    """

    normalized_claims = tuple(claims)
    claim_count = max(1, len(normalized_claims))
    connection = _open_gold(db_path)
    try:
        scope_violations = [
            item
            for claim in normalized_claims
            for item in (
                _claim_scope_violations(workload_scope, claim.scope, f"claim:{claim.claim_id}")
                + _assertion_scope_violations(claim)
            )
        ]
        reference_violations = _reference_violations(connection, normalized_claims, policy)
        evidence_violations = [
            item for claim in normalized_claims for item in _evidence_violations(connection, claim, policy)
        ]
        numeric_violations = [
            item for claim in normalized_claims for item in _numeric_violations(connection, claim, policy)
        ]
    finally:
        connection.close()

    assertion_count = max(1, sum(len(claim.assertions) for claim in normalized_claims))
    reference_count = max(1, sum(len(_all_direct_references(claim)) for claim in normalized_claims))
    critical_claim_count = max(
        1,
        sum(
            1
            for claim in normalized_claims
            if claim.critical or claim.claim_type in policy.critical_claim_types
        ),
    )
    contradiction_violations = _deterministic_contradiction_violations(
        normalized_claims, policy.numeric_tolerance
    )

    def gate(
        gate_id: str,
        violations: Sequence[str],
        denominator: int,
        *,
        deferred_to_critic: bool = False,
    ) -> HardGateResult:
        unique_violations = tuple(dict.fromkeys(str(item) for item in violations))
        rate = max(0.0, 1.0 - (len(unique_violations) / float(denominator)))
        return HardGateResult(
            gate_id=gate_id,
            passed=not unique_violations,
            rate=rate,
            required_rate=1.0,
            violations=unique_violations,
            deferred_to_critic=deferred_to_critic,
        )

    gates = {
        "numeric_accuracy": gate("numeric_accuracy", numeric_violations, assertion_count),
        "reference_validity": gate("reference_validity", reference_violations, reference_count),
        "critical_evidence_coverage": gate(
            "critical_evidence_coverage", evidence_violations, critical_claim_count
        ),
        "scope_compliance": gate("scope_compliance", scope_violations, claim_count),
        "fabricated_or_unaccepted_records": gate(
            "fabricated_or_unaccepted_records", reference_violations, reference_count
        ),
        "blocking_contradictions": gate(
            "blocking_contradictions",
            contradiction_violations,
            max(1, len(normalized_claims)),
            deferred_to_critic=True,
        ),
    }
    return Stage1ValidationReport(
        passed=all(item.passed for item in gates.values()),
        gate_results=gates,
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
