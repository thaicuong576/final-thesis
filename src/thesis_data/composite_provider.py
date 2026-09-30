"""Composite dataset provider combining an accepted base provider with an upload snapshot.

Enables analytical execution over a user-supplied bank alongside the Gold benchmark peer group,
while strictly keeping the peer group and peer median frozen to the Gold entities.
"""

from __future__ import annotations

from typing import Sequence

from .dataset_contract import (
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEvidence,
    DatasetRef,
    DatasetSource,
)
from .dataset_provider import DatasetProviderError, FinancialDatasetProvider, peer_benchmark_observation_id


class CompositeDatasetProvider:
    """Read interface combining a base (Gold) provider with a validated user upload snapshot."""

    def __init__(
        self,
        base_provider: FinancialDatasetProvider,
        upload_provider: FinancialDatasetProvider,
        *,
        uploaded_entity_id: str,
    ) -> None:
        self._base_provider = base_provider
        self._upload_provider = upload_provider
        self._base_ref = base_provider.current_dataset_ref()
        self._upload_ref = upload_provider.current_dataset_ref()
        self._uploaded_entity_id = uploaded_entity_id.strip().upper()

        self._composite_ref = DatasetRef(
            dataset_id=self._base_ref.dataset_id,
            dataset_snapshot_id=f"{self._base_ref.dataset_snapshot_id}+upload-{self._upload_ref.dataset_snapshot_id}",
        )

    @property
    def base_ref(self) -> DatasetRef:
        return self._base_ref

    @property
    def upload_ref(self) -> DatasetRef:
        return self._upload_ref

    @property
    def uploaded_entity_id(self) -> str:
        return self._uploaded_entity_id

    def current_dataset_ref(self) -> DatasetRef:
        return self._composite_ref

    def _validate_ref(self, dataset_ref: DatasetRef) -> None:
        if dataset_ref != self._composite_ref:
            raise DatasetProviderError(
                f"Dataset reference {dataset_ref} does not match composite reference {self._composite_ref}"
            )

    def _wrap_obs(self, obs: CanonicalObservation | None) -> CanonicalObservation | None:
        if obs is None:
            return None
        if hasattr(obs, "model_copy"):
            return obs.model_copy(
                update={
                    "dataset_id": self._composite_ref.dataset_id,
                    "dataset_snapshot_id": self._composite_ref.dataset_snapshot_id,
                }
            )
        import copy
        obs_copy = copy.copy(obs)
        obs_copy.dataset_id = self._composite_ref.dataset_id
        obs_copy.dataset_snapshot_id = self._composite_ref.dataset_snapshot_id
        return obs_copy

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        self._validate_ref(dataset_ref)
        base_caps = self._base_provider.get_capabilities(self._base_ref)
        upload_caps = self._upload_provider.get_capabilities(self._upload_ref)

        # Merge entities: Gold entities + uploaded entity (never duplicated)
        existing_entity_ids = {e.entity_id for e in base_caps.entities}
        merged_entities = list(base_caps.entities)
        for e in upload_caps.entities:
            if e.entity_id not in existing_entity_ids:
                merged_entities.append(e)

        # Merge periods
        existing_period_ids = {p.period_id for p in base_caps.periods}
        merged_periods = list(base_caps.periods)
        for p in upload_caps.periods:
            if p.period_id not in existing_period_ids:
                merged_periods.append(p)

        # Merge metrics
        existing_metric_ids = {m.metric_id for m in base_caps.metrics}
        merged_metrics = list(base_caps.metrics)
        for m in upload_caps.metrics:
            if m.metric_id not in existing_metric_ids:
                merged_metrics.append(m)

        # Sources
        merged_sources = tuple(dict.fromkeys(base_caps.source_refs + upload_caps.source_refs))

        # Peer universe: STRICTLY base peer universes. Uploaded entity is NEVER added to peer universe!
        return DatasetCapabilityCatalog(
            dataset_ref=self._composite_ref,
            entities=tuple(merged_entities),
            periods=tuple(merged_periods),
            metrics=tuple(merged_metrics),
            peer_universes=base_caps.peer_universes,
            source_refs=merged_sources,
            supported_operations=base_caps.supported_operations,
        )

    def get_metric(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        if entity_id.strip().upper() == self._uploaded_entity_id:
            obs = self._upload_provider.get_metric(self._upload_ref, entity_id, period_id, metric_id)
        else:
            obs = self._base_provider.get_metric(self._base_ref, entity_id, period_id, metric_id)
        return self._wrap_obs(obs)

    def get_entity_metrics(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        self._validate_ref(dataset_ref)
        if entity_id.strip().upper() == self._uploaded_entity_id:
            obs_list = self._upload_provider.get_entity_metrics(
                self._upload_ref, entity_id, period_ids, metric_ids
            )
        else:
            obs_list = self._base_provider.get_entity_metrics(
                self._base_ref, entity_id, period_ids, metric_ids
            )
        return tuple(self._wrap_obs(o) for o in obs_list if o is not None)

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        """Aggregate peer median from base provider only."""
        self._validate_ref(dataset_ref)
        benchmarks = self._base_provider.get_peer_benchmark(
            self._base_ref,
            peer_universe_id,
            period_id,
            metric_ids,
            peer_entity_ids=peer_entity_ids,
        )
        wrapped: list[CanonicalObservation] = []
        for b in benchmarks:
            if b is not None:
                wb = self._wrap_obs(b)
                effective_peers = tuple(
                    b.metadata.get("requested_peer_entity_ids")
                    or (universe.effective_entity_ids(peer_entity_ids) if (universe := self._base_provider.get_capabilities(self._base_ref).peer_universe(peer_universe_id)) else ())
                )
                new_id = peer_benchmark_observation_id(
                    self._composite_ref,
                    peer_universe_id,
                    period_id,
                    b.metric_id,
                    effective_peers,
                )
                if hasattr(wb, "model_copy"):
                    wb = wb.model_copy(update={"observation_id": new_id})
                else:
                    wb.observation_id = new_id
                wrapped.append(wb)
        return tuple(wrapped)

    def get_evidence(
        self,
        dataset_ref: DatasetRef,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        self._validate_ref(dataset_ref)
        if entity_id and entity_id.strip().upper() == self._uploaded_entity_id:
            return self._upload_provider.get_evidence(
                self._upload_ref, source_refs, entity_id, period_id, metric_id
            )
        results: list[DatasetEvidence] = []
        try:
            results.extend(
                self._base_provider.get_evidence(
                    self._base_ref, source_refs, entity_id, period_id, metric_id
                )
            )
        except Exception:
            pass
        try:
            results.extend(
                self._upload_provider.get_evidence(
                    self._upload_ref, source_refs, entity_id, period_id, metric_id
                )
            )
        except Exception:
            pass
        return tuple(results)

    def resolve_evidence(
        self,
        dataset_ref: DatasetRef,
        evidence_id: str,
    ) -> DatasetEvidence | None:
        self._validate_ref(dataset_ref)
        ev = self._upload_provider.resolve_evidence(self._upload_ref, evidence_id)
        if ev is not None:
            return ev
        return self._base_provider.resolve_evidence(self._base_ref, evidence_id)

    def get_source(
        self,
        dataset_ref: DatasetRef,
        source_ref: str,
    ) -> DatasetSource | None:
        self._validate_ref(dataset_ref)
        src = self._upload_provider.get_source(self._upload_ref, source_ref)
        if src is not None:
            return src
        return self._base_provider.get_source(self._base_ref, source_ref)

    def get_macro_observation(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        obs = self._base_provider.get_macro_observation(self._base_ref, entity_id, period_id, metric_id)
        return self._wrap_obs(obs)

    def resolve_observation(
        self,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        obs = self._upload_provider.resolve_observation(self._upload_ref, observation_id)
        if obs is not None:
            return self._wrap_obs(obs)
        obs = self._base_provider.resolve_observation(self._base_ref, observation_id)
        return self._wrap_obs(obs)
