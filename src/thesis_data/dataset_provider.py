"""Provider protocol for the application dataset boundary.

The protocol intentionally accepts dataset identities instead of database
paths.  Storage-specific knowledge belongs in a concrete adapter.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol, Sequence, runtime_checkable

from .dataset_contract import (
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEvidence,
    DatasetRef,
    DatasetSource,
)


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
