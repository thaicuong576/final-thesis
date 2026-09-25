"""Small non-SQLite provider used for application boundary tests and demos."""

from __future__ import annotations

from typing import Iterable, Sequence

from .dataset_contract import (
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEvidence,
    DatasetRef,
    DatasetSource,
)
from .dataset_provider import DatasetProviderError, aggregate_peer_median
from .schema import QualityStatus


class InMemoryFinancialDatasetProvider:
    """Deterministic provider implementation with no filesystem dependency."""

    def __init__(
        self,
        catalog: DatasetCapabilityCatalog,
        *,
        observations: Iterable[CanonicalObservation] = (),
        sources: Iterable[DatasetSource] = (),
        evidence: Iterable[DatasetEvidence] = (),
    ) -> None:
        self._catalog = catalog
        self._observations = tuple(observations)
        self._sources = {item.source_ref: item for item in sources}
        self._evidence = tuple(evidence)
        self._validate_payload_identity()

    def _validate_ref(self, dataset_ref: DatasetRef) -> None:
        if dataset_ref != self._catalog.dataset_ref:
            raise DatasetProviderError("dataset reference does not match in-memory provider")

    def _validate_payload_identity(self) -> None:
        ref = self._catalog.dataset_ref
        for observation in self._observations:
            if (
                observation.dataset_id != ref.dataset_id
                or observation.dataset_snapshot_id != ref.dataset_snapshot_id
            ):
                raise ValueError("in-memory observation has mismatched dataset identity")

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        self._validate_ref(dataset_ref)
        return self._catalog

    def get_metric(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        matches = [
            item
            for item in self._observations
            if item.entity_id == entity_id
            and item.period_id == period_id
            and item.metric_id == metric_id
        ]
        if len(matches) > 1:
            raise DatasetProviderError("ambiguous in-memory observation")
        return matches[0] if matches else None

    def get_entity_metrics(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        self._validate_ref(dataset_ref)
        result = [
            item
            for item in self._observations
            if item.entity_id == entity_id
            and item.period_id in period_ids
            and item.metric_id in metric_ids
        ]
        return tuple(sorted(result, key=lambda item: (item.period_id, item.metric_id)))

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        self._validate_ref(dataset_ref)
        universe = self._catalog.peer_universe(peer_universe_id)
        if universe is None:
            raise DatasetProviderError("unknown in-memory peer universe")
        try:
            effective_peer_entity_ids = universe.effective_entity_ids(peer_entity_ids)
        except ValueError as exc:
            raise DatasetProviderError(str(exc)) from exc
        for metric_id in metric_ids:
            metric = next(
                (item for item in self._catalog.metrics if item.metric_id == metric_id),
                None,
            )
            if metric is None or metric.analytical_level.value != "company":
                raise DatasetProviderError("peer benchmark requires company-level metrics")
        result: list[CanonicalObservation] = []
        for metric_id in metric_ids:
            member_observations = [
                item
                for item in self._observations
                if item.entity_id in effective_peer_entity_ids
                and item.period_id == period_id
                and item.metric_id == metric_id
            ]
            result.append(
                aggregate_peer_median(
                    dataset_ref=dataset_ref,
                    peer_universe_id=peer_universe_id,
                    period_id=period_id,
                    metric_id=metric_id,
                    peer_entity_ids=effective_peer_entity_ids,
                    member_observations=member_observations,
                )
            )
        return tuple(result)

    def get_evidence(
        self,
        dataset_ref: DatasetRef,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        self._validate_ref(dataset_ref)
        return tuple(
            item
            for item in self._evidence
            if item.source_ref in source_refs
            and (entity_id is None or item.entity_id == entity_id)
            and (period_id is None or item.period_id == period_id)
            and (metric_id is None or item.metric_id == metric_id)
        )

    def resolve_evidence(
        self,
        dataset_ref: DatasetRef,
        evidence_id: str,
    ) -> DatasetEvidence | None:
        """Resolve one exact evidence resource from the in-memory snapshot."""

        self._validate_ref(dataset_ref)
        matches = [item for item in self._evidence if item.evidence_id == evidence_id]
        if len(matches) > 1:
            raise DatasetProviderError("ambiguous in-memory evidence ID")
        return matches[0] if matches else None

    def get_source(
        self,
        dataset_ref: DatasetRef,
        source_ref: str,
    ) -> DatasetSource | None:
        self._validate_ref(dataset_ref)
        return self._sources.get(source_ref)

    def get_macro_observation(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        return self.get_metric(dataset_ref, entity_id, period_id, metric_id)

    def resolve_observation(
        self,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        matches = [item for item in self._observations if item.observation_id == observation_id]
        if len(matches) > 1:
            raise DatasetProviderError("ambiguous in-memory observation ID")
        return matches[0] if matches else None
