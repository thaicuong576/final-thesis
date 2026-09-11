"""Application analysis-request contract and capability-bound validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .dataset_contract import DatasetCapabilityCatalog, DatasetRef


def _unique_non_empty(values: tuple[str, ...], field_name: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain non-empty identifiers")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")


class AnalysisRequest(BaseModel):
    """A user/application request, independent of experiment question sets."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_snapshot_id: str = Field(min_length=1)
    target_entity_ids: tuple[str, ...] = Field(min_length=1)
    period_ids: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    macro_metric_ids: tuple[str, ...] = Field(default_factory=tuple)
    peer_universe_id: str | None = Field(default=None, min_length=1)
    peer_entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    objective: str = Field(min_length=1)
    causal_claim_policy: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_request_shape(self) -> "AnalysisRequest":
        for field_name in (
            "target_entity_ids",
            "period_ids",
            "metric_ids",
            "macro_metric_ids",
            "peer_entity_ids",
        ):
            _unique_non_empty(getattr(self, field_name), field_name)
        if not set(self.macro_metric_ids).issubset(self.metric_ids):
            raise ValueError("macro metrics must be included in metric_ids")
        if self.peer_entity_ids and self.peer_universe_id is None:
            raise ValueError("explicit peer entities require peer_universe_id")
        return self

    @property
    def dataset_ref(self) -> DatasetRef:
        return DatasetRef(
            dataset_id=self.dataset_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
        )


class AnalysisRequestValidationError(ValueError):
    """The request crosses the discovered dataset capability boundary."""


def validate_analysis_request(
    request: AnalysisRequest,
    capability_catalog: DatasetCapabilityCatalog,
) -> None:
    """Fail closed without touching a database or provider implementation."""

    blockers: list[str] = []
    if request.dataset_id != capability_catalog.dataset_ref.dataset_id:
        blockers.append("dataset_id_mismatch")
    if request.dataset_snapshot_id != capability_catalog.dataset_ref.dataset_snapshot_id:
        blockers.append("dataset_snapshot_id_mismatch")
    blockers.extend(
        f"unsupported_entity:{entity_id}"
        for entity_id in request.target_entity_ids
        if entity_id not in capability_catalog.entity_ids
    )
    blockers.extend(
        f"unsupported_period:{period_id}"
        for period_id in request.period_ids
        if period_id not in capability_catalog.period_ids
    )
    blockers.extend(
        f"unsupported_metric:{metric_id}"
        for metric_id in request.metric_ids
        if metric_id not in capability_catalog.metric_ids
    )
    blockers.extend(
        f"unsupported_macro_metric:{metric_id}"
        for metric_id in request.macro_metric_ids
        if metric_id not in capability_catalog.macro_metric_ids
    )
    if request.peer_universe_id is not None:
        universe = capability_catalog.peer_universe(request.peer_universe_id)
        if universe is None:
            blockers.append(f"unsupported_peer_universe:{request.peer_universe_id}")
        else:
            blockers.extend(
                f"unsupported_peer_entity:{entity_id}"
                for entity_id in request.peer_entity_ids
                if entity_id not in universe.entity_ids
            )
    if blockers:
        raise AnalysisRequestValidationError(";".join(dict.fromkeys(blockers)))
