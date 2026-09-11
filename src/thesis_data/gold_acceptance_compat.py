"""Compatibility entry point for the historical Gold acceptance fixture.

The generic acceptance core is intentionally unaware of this module. This
adapter owns only the legacy SQLite path and historical peer-median IDs needed
to replay pre-boundary benchmark tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .acceptance import validate_stage1_claims
from .acceptance_resolver import ProviderStage1DatasetResolver
from .dataset_contract import DatasetRef
from .dataset_provider import peer_benchmark_observation_id
from .gold_dataset_provider import GoldSqliteDatasetProvider
from .schema import AcceptancePolicy, AtomicClaim, ClaimScope, Stage1ValidationReport


PEER_MEDIAN_BENCHMARK_CONTRACT_VERSION = "peer-median-gold-v1"


def peer_median_benchmark_id(
    snapshot_id: str,
    comparison_universe: str,
    entities: Sequence[str],
    period: str,
    metric_id: str,
) -> str:
    """Build the historical benchmark identity used by legacy fixtures."""

    if not snapshot_id.strip() or not comparison_universe.strip():
        raise ValueError("snapshot_id and comparison_universe must be non-empty")
    canonical_entities = tuple(
        sorted(set(str(item).strip() for item in entities if str(item).strip()))
    )
    if not canonical_entities:
        raise ValueError("benchmark entities must not be empty")
    if not period.strip() or not metric_id.strip():
        raise ValueError("period and metric_id must be non-empty")
    return (
        f"peer-median/{PEER_MEDIAN_BENCHMARK_CONTRACT_VERSION}/"
        f"{snapshot_id}/{comparison_universe}/"
        f"{','.join(canonical_entities)}/{period}/{metric_id}"
    )


def _provider_universe_id(
    provider: GoldSqliteDatasetProvider,
    dataset_ref: DatasetRef,
    entity_ids: Sequence[str],
) -> str | None:
    """Resolve one historical peer set to one provider universe, fail closed."""

    requested = set(entity_ids)
    if not requested:
        return None
    catalog = provider.get_capabilities(dataset_ref)
    exact = [
        universe.peer_universe_id
        for universe in catalog.peer_universes
        if set(universe.entity_ids) == requested
    ]
    if len(exact) == 1:
        return exact[0]
    supersets = [
        universe.peer_universe_id
        for universe in catalog.peer_universes
        if requested.issubset(universe.entity_ids)
    ]
    return supersets[0] if len(supersets) == 1 else None


def _translate_benchmark_claim(
    claim: AtomicClaim,
    provider: GoldSqliteDatasetProvider,
    dataset_ref: DatasetRef,
) -> AtomicClaim:
    """Translate one valid historical benchmark contract to provider IDs.

    A malformed or fabricated historical ID is returned unchanged. It then
    reaches the generic resolver and fails as an unresolved benchmark rather
    than being repaired into a valid reference.
    """

    benchmark_assertions = [
        assertion for assertion in claim.assertions if assertion.benchmark_ref is not None
    ]
    if not benchmark_assertions or claim.scope.comparison_universe is None:
        return claim

    old_universe = claim.scope.comparison_universe
    provider_universe = _provider_universe_id(provider, dataset_ref, claim.scope.entities)
    if provider_universe is None:
        return claim

    for assertion in benchmark_assertions:
        ref = assertion.benchmark_ref
        assert ref is not None
        expected_old_id = peer_median_benchmark_id(
            dataset_ref.dataset_snapshot_id,
            old_universe,
            claim.scope.entities,
            ref.period,
            ref.metric_id,
        )
        if (
            ref.ref_id != expected_old_id
            or ref.entity != old_universe
            or ref.period not in claim.scope.periods
            or ref.metric_id not in claim.scope.metric_ids
        ):
            return claim

    def translate_assertion(assertion):
        ref = assertion.benchmark_ref
        if ref is None:
            return assertion
        translated_ref = ref.model_copy(
            update={
                "ref_id": peer_benchmark_observation_id(
                    dataset_ref,
                    provider_universe,
                    ref.period,
                    ref.metric_id,
                    claim.scope.entities,
                ),
                "entity": provider_universe,
            }
        )
        updates = {"benchmark_ref": translated_ref}
        if assertion.entity == old_universe:
            updates["entity"] = provider_universe
        return assertion.model_copy(update=updates)

    translated_scope = claim.scope.model_copy(
        update={"comparison_universe": provider_universe}
    )
    return claim.model_copy(
        update={
            "scope": translated_scope,
            "assertions": tuple(translate_assertion(item) for item in claim.assertions),
        }
    )


def _translate_workload_scope(
    workload_scope: ClaimScope,
    provider: GoldSqliteDatasetProvider,
    dataset_ref: DatasetRef,
) -> ClaimScope:
    if workload_scope.comparison_universe is None:
        return workload_scope
    provider_universe = _provider_universe_id(
        provider, dataset_ref, workload_scope.entities
    )
    if provider_universe is None:
        return workload_scope
    return workload_scope.model_copy(update={"comparison_universe": provider_universe})


def validate_gold_stage1_claims(
    db_path: Path,
    claims: Sequence[AtomicClaim],
    workload_scope: ClaimScope,
    policy: AcceptancePolicy,
    *,
    dataset_id: str = "gold-compatibility-v1",
) -> Stage1ValidationReport:
    """Replay historical Gold claims through the provider-neutral core."""

    provider = GoldSqliteDatasetProvider(db_path, dataset_id=dataset_id)
    dataset_ref = provider.current_dataset_ref()
    resolver = ProviderStage1DatasetResolver(provider, dataset_ref)
    translated_claims = tuple(
        _translate_benchmark_claim(claim, provider, dataset_ref) for claim in claims
    )
    translated_scope = _translate_workload_scope(workload_scope, provider, dataset_ref)
    return validate_stage1_claims(
        resolver,
        translated_claims,
        translated_scope,
        policy,
    )
