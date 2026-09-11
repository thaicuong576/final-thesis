"""Provider protocol for the application dataset boundary.

The protocol intentionally accepts dataset identities instead of database
paths.  Storage-specific knowledge belongs in a concrete adapter.
"""

from __future__ import annotations

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
