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
    QualityDimensionScores,
    QualityWeights,
    Stage1ValidationReport,
    StructuredAssertion,
    UnresolvedReasonCode,
)


ACCEPTANCE_MODEL_VERSION = "report-acceptance-v1"
LEGACY_CLAIM_ADAPTER_VERSION = "legacy-composite-claim-to-atomic-v1"
PEER_MEDIAN_BENCHMARK_CONTRACT_VERSION = "peer-median-gold-v1"
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


@dataclass(frozen=True)
class _UnitEvaluation:
    """One evaluation unit and its item-level violations."""

    key: str
    violations: tuple[str, ...] = ()


def peer_median_benchmark_id(
    snapshot_id: str,
    comparison_universe: str,
    entities: Sequence[str],
    period: str,
    metric_id: str,
) -> str:
    """Build the versioned identity for a Gold-derived peer median.

    The MVP has no benchmark table.  A benchmark is therefore valid only when
    its ID is this exact identity for the current Gold snapshot, comparison
    universe, canonical peer set, period, and metric.  The median itself is
    recomputed from the assertion's typed Gold observation refs.
    """

    if not snapshot_id.strip() or not comparison_universe.strip():
        raise ValueError("snapshot_id and comparison_universe must be non-empty")
    canonical_entities = tuple(sorted(set(str(item).strip() for item in entities if str(item).strip())))
    if not canonical_entities:
        raise ValueError("benchmark entities must not be empty")
    if not period.strip() or not metric_id.strip():
        raise ValueError("period and metric_id must be non-empty")
    return (
        f"peer-median/{PEER_MEDIAN_BENCHMARK_CONTRACT_VERSION}/"
        f"{snapshot_id}/{comparison_universe}/"
        f"{','.join(canonical_entities)}/{period}/{metric_id}"
    )


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
    return QualityDimensionScores(**scores).weighted_total(weights)


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


def _gold_snapshot_id(connection: sqlite3.Connection) -> str | None:
    """Return the sole Gold snapshot identity used by benchmark resolution."""

    try:
        rows = connection.execute(
            "SELECT snapshot_id, status FROM snapshot_metadata"
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    if len(rows) != 1 or rows[0]["status"] != "gold":
        return None
    return str(rows[0]["snapshot_id"])


def _benchmark_reference_violations(
    connection: sqlite3.Connection,
    claim: AtomicClaim,
    assertion: StructuredAssertion,
    ref: ClaimDataRef,
) -> list[str]:
    """Validate the MVP's deterministic Gold-derived peer-median contract."""

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

    snapshot_id = _gold_snapshot_id(connection)
    if snapshot_id is None:
        violations.append(f"benchmark_snapshot_missing_or_ambiguous:{ref.ref_id}")
    else:
        expected_id = peer_median_benchmark_id(
            snapshot_id,
            claim.scope.comparison_universe or ref.entity,
            claim.scope.entities,
            ref.period,
            ref.metric_id,
        )
        if ref.ref_id != expected_id:
            violations.append(f"benchmark_reference_unresolved:{ref.ref_id}")

    input_refs = assertion.data_refs
    if not input_refs:
        violations.append(f"benchmark_inputs_missing:{ref.ref_id}")
    else:
        if any(item.ref_type != "observation" for item in input_refs):
            violations.append(f"benchmark_inputs_not_observations:{ref.ref_id}")
        if {item.entity for item in input_refs} != set(claim.scope.entities):
            violations.append(f"benchmark_peer_set_mismatch:{ref.ref_id}")
        if len(input_refs) != len(claim.scope.entities):
            violations.append(f"benchmark_inputs_not_one_per_peer:{ref.ref_id}")
        if any(item.period != ref.period or item.metric_id != ref.metric_id for item in input_refs):
            violations.append(f"benchmark_input_scope_mismatch:{ref.ref_id}")
    return violations


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


def _reference_evaluations(
    connection: sqlite3.Connection,
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
                        connection, claim, assertion, ref
                    )
                else:
                    _resolved, ref_violations = _observation_reference(connection, ref, policy)
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
            rows = connection.execute(
                "SELECT source_id, source_tier, quality_status FROM source_records WHERE source_id = ?",
                (source_id,),
            ).fetchall()
            source_violations: list[str] = []
            if len(rows) != 1:
                source_violations.append(
                    f"source_reference_missing_or_ambiguous:{claim.claim_id}:{source_id}"
                )
            else:
                row = rows[0]
                if row["quality_status"] != "valid":
                    source_violations.append(
                        f"source_reference_unaccepted:{claim.claim_id}:{source_id}"
                    )
                if row["source_tier"] not in _accepted_tier(policy):
                    source_violations.append(
                        f"source_reference_tier_not_allowed:{claim.claim_id}:{source_id}"
                    )
            evaluations.append(
                _UnitEvaluation(
                    key=f"claim:{claim_index}:{claim.claim_id}:source:{source_index}:{source_id}",
                    violations=tuple(dict.fromkeys(source_violations)),
                )
            )
    return evaluations


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


def _numeric_assertion_violations(
    connection: sqlite3.Connection,
    claim: AtomicClaim,
    policy: AcceptancePolicy,
    assertion: StructuredAssertion,
) -> list[str]:
    violations: list[str] = []
    resolved, ref_violations = _resolve_data_refs(connection, assertion.data_refs, policy)
    if ref_violations:
        violations.extend(
            f"{claim.claim_id}:{assertion.assertion_id}:{item}" for item in ref_violations
        )
        return violations

    if assertion.assertion_type is AssertionType.AGGREGATE:
        if assertion.benchmark_ref is None:
            violations.append(
                f"numeric_benchmark_reference_missing:{claim.claim_id}:{assertion.assertion_id}"
            )
            return violations
        benchmark_violations = _benchmark_reference_violations(
            connection, claim, assertion, assertion.benchmark_ref
        )
        if benchmark_violations:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                for item in benchmark_violations
            )
            return violations
        values = [float(item.value) for item in resolved if item.value is not None]
        if not values:
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
        expected = float(median(values))
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
            connection, assertion.reference_ref, policy
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
            connection, claim, assertion, assertion.benchmark_ref
        )
        if benchmark_violations:
            violations.extend(
                f"{claim.claim_id}:{assertion.assertion_id}:{item}"
                for item in benchmark_violations
            )
            return violations
        benchmark_values = [float(item.value) for item in resolved if item.value is not None]
        if not benchmark_values:
            violations.append(f"numeric_benchmark_unavailable:{claim.claim_id}:{assertion.assertion_id}")
            return violations
        rhs = float(median(benchmark_values))
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
    connection: sqlite3.Connection,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[_UnitEvaluation]:
    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}",
            violations=tuple(dict.fromkeys(_evidence_violations(connection, claim, policy))),
        )
        for index, claim in enumerate(claims)
        if claim.critical or claim.claim_type in policy.critical_claim_types
    ]


def _numeric_evaluations(
    connection: sqlite3.Connection,
    claims: Sequence[AtomicClaim],
    policy: AcceptancePolicy,
) -> list[_UnitEvaluation]:
    return [
        _UnitEvaluation(
            key=f"claim:{index}:{claim.claim_id}:{assertion.assertion_id}",
            violations=tuple(
                dict.fromkeys(_numeric_assertion_violations(connection, claim, policy, assertion))
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
    integrity_violations = ("empty_claim_set",) if not normalized_claims else ()
    connection = _open_gold(db_path)
    try:
        scope_evaluations = _scope_evaluations(normalized_claims, workload_scope)
        reference_evaluations = _reference_evaluations(connection, normalized_claims, policy)
        evidence_evaluations = _evidence_evaluations(connection, normalized_claims, policy)
        numeric_evaluations = _numeric_evaluations(connection, normalized_claims, policy)
    finally:
        connection.close()

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
            scope_evaluations,
            extra_violations=integrity_violations,
            evaluation_unit="claim_scope_bundle",
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
