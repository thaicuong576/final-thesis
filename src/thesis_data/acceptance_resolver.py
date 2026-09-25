"""Provider-neutral resolution boundary for Stage-1 claim references.

This module retrieves canonical dataset resources only.  Acceptance policy and
hard-gate decisions remain in the acceptance layer that consumes the results.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .dataset_contract import (
    CanonicalObservation,
    DatasetEvidence,
    DatasetRef,
    DatasetSource,
)
from .dataset_provider import DatasetProviderError, FinancialDatasetProvider
from .schema import ClaimDataRef


class Stage1DatasetResolver(Protocol):
    """Canonical resource lookup required by deterministic Stage-1 checks."""

    @property
    def dataset_ref(self) -> DatasetRef:
        ...

    def resolve_observation_ref(
        self,
        ref: ClaimDataRef,
    ) -> CanonicalObservation | None:
        ...

    def resolve_observation_id(
        self,
        observation_id: str,
    ) -> CanonicalObservation | None:
        """Resolve one exact observation ID inside this resolver's snapshot."""
        ...

    def resolve_benchmark(
        self,
        *,
        peer_universe_id: str,
        peer_entity_ids: Sequence[str],
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation:
        ...

    def resolve_source(self, source_ref: str) -> DatasetSource | None:
        ...

    def resolve_evidence(self, evidence_id: str) -> DatasetEvidence | None:
        ...


class ProviderStage1DatasetResolver:
    """Resolve Stage-1 references through one dataset-bound provider."""

    def __init__(
        self,
        provider: FinancialDatasetProvider,
        dataset_ref: DatasetRef,
    ) -> None:
        self._provider = provider
        self._dataset_ref = dataset_ref

    @property
    def dataset_ref(self) -> DatasetRef:
        return self._dataset_ref

    def _bound_observation(
        self,
        observation: CanonicalObservation | None,
    ) -> CanonicalObservation | None:
        if observation is None:
            return None
        if (
            observation.dataset_id != self._dataset_ref.dataset_id
            or observation.dataset_snapshot_id != self._dataset_ref.dataset_snapshot_id
        ):
            raise DatasetProviderError(
                "resolved observation does not match resolver dataset reference"
            )
        return observation

    def resolve_observation_ref(
        self,
        ref: ClaimDataRef,
    ) -> CanonicalObservation | None:
        """Resolve all supported observation-like refs by their exact ID."""

        if ref.ref_type == "legacy":
            return None
        if ref.ref_type not in {
            "observation",
            "macro_observation",
            "derived_metric",
            "missing_cell",
        }:
            return None
        observation = self._bound_observation(
            self._provider.resolve_observation(self._dataset_ref, ref.ref_id)
        )
        return observation

    def resolve_observation_id(
        self,
        observation_id: str,
    ) -> CanonicalObservation | None:
        """Resolve a lineage input by its exact provider identity."""

        observation = self._provider.resolve_observation(
            self._dataset_ref,
            observation_id,
        )
        return self._bound_observation(observation)

    def resolve_benchmark(
        self,
        *,
        peer_universe_id: str,
        peer_entity_ids: Sequence[str],
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation:
        """Resolve one provider-derived benchmark for the exact requested scope."""

        observations = self._provider.get_peer_benchmark(
            self._dataset_ref,
            peer_universe_id,
            period_id,
            (metric_id,),
            peer_entity_ids=tuple(peer_entity_ids),
        )
        if len(observations) != 1:
            raise DatasetProviderError(
                "provider returned missing or ambiguous benchmark resolution"
            )
        observation = self._bound_observation(observations[0])
        assert observation is not None
        if (
            observation.entity_id != peer_universe_id
            or observation.period_id != period_id
            or observation.metric_id != metric_id
        ):
            raise DatasetProviderError(
                "resolved benchmark does not match requested scope"
            )
        return observation

    def resolve_source(self, source_ref: str) -> DatasetSource | None:
        return self._provider.get_source(self._dataset_ref, source_ref)

    def resolve_evidence(self, evidence_id: str) -> DatasetEvidence | None:
        return self._provider.resolve_evidence(self._dataset_ref, evidence_id)
