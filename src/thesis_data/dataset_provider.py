"""Provider protocol for the application dataset boundary.

The protocol intentionally accepts dataset identities instead of database
paths.  Storage-specific knowledge belongs in a concrete adapter.
"""

from __future__ import annotations

import hashlib
import json
from statistics import median
from typing import Protocol, Sequence, runtime_checkable

from .dataset_contract import (
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEvidence,
    DatasetRef,
    DatasetSource,
)
from .schema import QualityStatus


class DatasetProviderError(ValueError):
    """The provider cannot satisfy a dataset-bound request."""


def peer_benchmark_observation_id(
    dataset_ref: DatasetRef,
    peer_universe_id: str,
    period_id: str,
    metric_id: str,
    peer_entity_ids: Sequence[str],
) -> str:
    """Build an identity that changes when the effective peer scope changes."""

    scope_digest = hashlib.sha256(
        json.dumps(tuple(sorted(peer_entity_ids)), separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return (
        f"benchmark:{dataset_ref.dataset_id}:{dataset_ref.dataset_snapshot_id}:"
        f"{peer_universe_id}:{period_id}:{metric_id}:scope-{scope_digest}"
    )


def aggregate_peer_median(
    *,
    dataset_ref: DatasetRef,
    peer_universe_id: str,
    period_id: str,
    metric_id: str,
    peer_entity_ids: Sequence[str],
    member_observations: Sequence[CanonicalObservation],
) -> CanonicalObservation:
    """Build a provider-neutral peer median with explicit coverage lineage.

    ``input_observation_ids`` and ``eligible_peer_entity_ids`` contain exactly
    the accepted observations used by the median. Metadata retains the
    requested peer set separately from the eligible numeric denominator, plus
    each member's observed or missing status so callers can explain the
    denominator without treating the peer sample as a sector total.
    """

    effective_peer_entity_ids = tuple(peer_entity_ids)
    if not effective_peer_entity_ids:
        raise DatasetProviderError("peer benchmark requires at least one peer entity")
    if len(effective_peer_entity_ids) != len(set(effective_peer_entity_ids)):
        raise DatasetProviderError("peer benchmark entity IDs must be unique")

    observations_by_entity: dict[str, CanonicalObservation] = {}
    for item in member_observations:
        if (
            item.dataset_id != dataset_ref.dataset_id
            or item.dataset_snapshot_id != dataset_ref.dataset_snapshot_id
            or item.period_id != period_id
            or item.metric_id != metric_id
            or item.entity_id not in effective_peer_entity_ids
        ):
            raise DatasetProviderError("peer benchmark input does not match requested scope")
        if item.entity_id in observations_by_entity:
            raise DatasetProviderError("ambiguous peer member observation")
        observations_by_entity[item.entity_id] = item

    accepted: list[CanonicalObservation] = []
    missing_members: list[dict[str, str | None]] = []
    member_records: list[dict[str, object]] = []
    for entity_id in effective_peer_entity_ids:
        item = observations_by_entity.get(entity_id)
        if item is None:
            missing_members.append(
                {
                    "entity_id": entity_id,
                    "observation_id": None,
                    "validation_status": None,
                    "reason": "NO_OBSERVATION_FOUND",
                }
            )
            member_records.append(
                {
                    "entity_id": entity_id,
                    "observation_id": None,
                    "validation_status": None,
                    "accepted": False,
                    "reason": "NO_OBSERVATION_FOUND",
                    "reporting_scope": None,
                    "scope_authority": None,
                }
            )
            continue

        is_accepted = item.validation_status is QualityStatus.VALID and item.value is not None
        member_records.append(
            {
                "entity_id": entity_id,
                "observation_id": item.observation_id,
                "validation_status": item.validation_status.value,
                "accepted": is_accepted,
                "reason": None if is_accepted else (
                    item.missing_reason or f"STATUS_{item.validation_status.value.upper()}"
                ),
                "reporting_scope": item.reporting_scope,
                "scope_authority": item.metadata.get("reporting_scope_authority"),
            }
        )
        if is_accepted:
            accepted.append(item)
        else:
            missing_members.append(
                {
                    "entity_id": entity_id,
                    "observation_id": item.observation_id,
                    "validation_status": item.validation_status.value,
                    "reason": item.missing_reason or f"STATUS_{item.validation_status.value.upper()}",
                }
            )

    benchmark_id = peer_benchmark_observation_id(
        dataset_ref,
        peer_universe_id,
        period_id,
        metric_id,
        effective_peer_entity_ids,
    )
    eligible_peer_entity_ids = [item.entity_id for item in accepted]
    metadata = {
        "benchmark_method": "peer_median_v1",
        "aggregation_method": "peer_median_v1",
        "aggregation_version": "peer_median_v1",
        "peer_universe_id": peer_universe_id,
        "requested_peer_entity_ids": list(effective_peer_entity_ids),
        "eligible_peer_entity_ids": eligible_peer_entity_ids,
        "requested_denominator": len(effective_peer_entity_ids),
        "eligible_denominator": len(eligible_peer_entity_ids),
        "member_observation_ids": [
            record["observation_id"]
            for record in member_records
            if record["observation_id"] is not None
        ],
        "peer_member_observations": member_records,
        "missing_members": missing_members,
    }
    if not accepted:
        return CanonicalObservation(
            observation_id=benchmark_id,
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            entity_id=peer_universe_id,
            period_id=period_id,
            metric_id=metric_id,
            validation_status=QualityStatus.MISSING,
            missing_reason="all_values_missing",
            metadata=metadata,
        )

    units = {item.unit for item in accepted}
    if any(not isinstance(item.unit, str) or not item.unit.strip() for item in accepted):
        raise DatasetProviderError("peer benchmark inputs require non-null units")
    if len(units) != 1:
        raise DatasetProviderError("peer benchmark inputs have incompatible units")
    period_bases = {item.period_basis for item in accepted}
    if any(
        not isinstance(item.period_basis, str) or not item.period_basis.strip()
        for item in accepted
    ):
        raise DatasetProviderError("peer benchmark inputs require non-null period bases")
    if len(period_bases) != 1:
        raise DatasetProviderError("peer benchmark inputs have incompatible period bases")
    reporting_scopes = {item.reporting_scope for item in accepted}
    if any(
        not isinstance(item.reporting_scope, str) or not item.reporting_scope.strip()
        for item in accepted
    ):
        raise DatasetProviderError(
            "peer benchmark inputs require verified reporting scopes"
        )
    if len(reporting_scopes) != 1:
        raise DatasetProviderError("peer benchmark inputs have incompatible reporting scopes")

    return CanonicalObservation(
        observation_id=benchmark_id,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        entity_id=peer_universe_id,
        period_id=period_id,
        metric_id=metric_id,
        value=float(median(item.value for item in accepted)),
        unit=accepted[0].unit,
        period_basis=accepted[0].period_basis,
        reporting_scope=accepted[0].reporting_scope,
        validation_status=QualityStatus.VALID,
        derivation_method="peer_median_v1",
        input_observation_ids=tuple(item.observation_id for item in accepted),
        metadata=metadata,
    )


@runtime_checkable
class FinancialDatasetProvider(Protocol):
    """Bounded read interface consumed by application runtime code."""

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        ...

    def get_metric(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        ...

    def get_entity_metrics(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        ...

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        ...

    def get_evidence(
        self,
        dataset_ref: DatasetRef,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        ...

    def resolve_evidence(
        self,
        dataset_ref: DatasetRef,
        evidence_id: str,
    ) -> DatasetEvidence | None:
        """Resolve one exact evidence resource within the dataset snapshot."""
        ...

    def get_source(
        self,
        dataset_ref: DatasetRef,
        source_ref: str,
    ) -> DatasetSource | None:
        ...

    def get_macro_observation(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        ...

    def resolve_observation(
        self,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        ...
