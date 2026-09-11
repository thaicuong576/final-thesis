"""Dataset-aware, request-bounded tools for the application path.

This module has no SQLite or path knowledge.  It only delegates to the
``FinancialDatasetProvider`` held by ``ApplicationRuntimeContext``.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .application_runtime import ApplicationRuntimeContext
from .dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetEvidence,
    DatasetSource,
    SupportedOperation,
)
from .dataset_provider import DatasetProviderError
from .runtime_events import RuntimeEventType


class DatasetToolError(ValueError):
    """A generic dataset tool request cannot cross the application boundary."""


class _ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetMetricArguments(_ToolArguments):
    entity_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)


class GetEntityMetricsArguments(_ToolArguments):
    entity_id: str = Field(min_length=1)
    period_ids: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)


class GetPeerBenchmarkArguments(_ToolArguments):
    peer_universe_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)


class GetEvidenceArguments(_ToolArguments):
    source_refs: tuple[str, ...] = Field(min_length=1)
    entity_id: str | None = Field(default=None, min_length=1)
    period_id: str | None = Field(default=None, min_length=1)
    metric_id: str | None = Field(default=None, min_length=1)


class GetSourceArguments(_ToolArguments):
    source_ref: str = Field(min_length=1)


class GetMacroObservationArguments(GetMetricArguments):
    pass


class ResolveObservationArguments(_ToolArguments):
    observation_id: str = Field(min_length=1)


_ARGUMENT_MODELS: dict[str, type[_ToolArguments]] = {
    SupportedOperation.GET_METRIC.value: GetMetricArguments,
    SupportedOperation.GET_ENTITY_METRICS.value: GetEntityMetricsArguments,
    SupportedOperation.GET_PEER_BENCHMARK.value: GetPeerBenchmarkArguments,
    SupportedOperation.GET_EVIDENCE.value: GetEvidenceArguments,
    SupportedOperation.GET_SOURCE.value: GetSourceArguments,
    SupportedOperation.GET_MACRO_OBSERVATION.value: GetMacroObservationArguments,
    SupportedOperation.RESOLVE_OBSERVATION.value: ResolveObservationArguments,
}


_ENTITY_TO_METRIC_LEVEL = {
    "company": AnalyticalLevel.COMPANY,
    "sector": AnalyticalLevel.SECTOR,
    "macro": AnalyticalLevel.MACRO,
}


@dataclass(frozen=True)
class DatasetToolExecution:
    operation: str
    output: Any
    result_sha256: str


class DatasetToolRuntime:
    """Execute generic read tools against one bounded application request."""

    def __init__(
        self,
        context: ApplicationRuntimeContext,
        *,
        actor: str = "application",
        task_id: str | None = None,
    ) -> None:
        self.context = context
        self.actor = actor
        self.task_id = task_id
        self._discovered_source_refs: set[str] = set()

    @property
    def discovered_source_refs(self) -> frozenset[str]:
        return frozenset(self._discovered_source_refs)

    def definitions(self) -> list[dict[str, Any]]:
        """Return provider-neutral strict tool definitions for a model adapter."""

        supported = {
            item.value for item in self.context.capability_catalog.supported_operations
        }
        return [
            {
                "type": "function",
                "name": operation,
                "description": f"Read {operation} within the declared dataset request.",
                "parameters": {
                    key: value
                    for key, value in _ARGUMENT_MODELS[operation].model_json_schema().items()
                    if key != "title"
                },
                "strict": True,
            }
            for operation in _ARGUMENT_MODELS
            if operation in supported
        ]

    def _ensure_period(self, period_id: str) -> None:
        if period_id not in self.context.analysis_request.period_ids:
            raise DatasetToolError("period outside analysis request")

    def _ensure_periods(self, period_ids: Sequence[str]) -> None:
        if not set(period_ids).issubset(self.context.analysis_request.period_ids):
            raise DatasetToolError("period outside analysis request")

    def _ensure_metric(self, metric_id: str) -> None:
        if metric_id not in self.context.analysis_request.metric_ids:
            raise DatasetToolError("metric outside analysis request")

    def _ensure_metrics(self, metric_ids: Sequence[str]) -> None:
        if not set(metric_ids).issubset(self.context.analysis_request.metric_ids):
            raise DatasetToolError("metric outside analysis request")

    def _catalog_metric(self, metric_id: str):
        metric = next(
            (item for item in self.context.capability_catalog.metrics if item.metric_id == metric_id),
            None,
        )
        if metric is None:
            raise DatasetToolError("metric is not in dataset capabilities")
        return metric

    def _catalog_entity(self, entity_id: str):
        entity = next(
            (item for item in self.context.capability_catalog.entities if item.entity_id == entity_id),
            None,
        )
        if entity is None:
            raise DatasetToolError("entity is not in dataset capabilities")
        return entity

    def _ensure_metric_level(self, entity_id: str, metric_id: str) -> None:
        metric = self._catalog_metric(metric_id)
        entity = self._catalog_entity(entity_id)
        required_level = _ENTITY_TO_METRIC_LEVEL.get(entity.entity_type.value)
        if required_level is not None and metric.analytical_level is not required_level:
            raise DatasetToolError("metric analytical level is incompatible with entity")

    def _ensure_metrics_for_entity(
        self,
        entity_id: str,
        metric_ids: Sequence[str],
    ) -> None:
        self._ensure_metrics(metric_ids)
        for metric_id in metric_ids:
            self._ensure_metric_level(entity_id, metric_id)

    def _ensure_company_peer_metrics(self, metric_ids: Sequence[str]) -> None:
        self._ensure_metrics(metric_ids)
        for metric_id in metric_ids:
            metric = self._catalog_metric(metric_id)
            if metric.analytical_level is not AnalyticalLevel.COMPANY:
                raise DatasetToolError("peer benchmark requires company-level metrics")

    def _ensure_entity(self, entity_id: str, metric_id: str) -> None:
        self._ensure_metric(metric_id)
        self._ensure_metric_level(entity_id, metric_id)
        if entity_id in self.context.analysis_request.target_entity_ids:
            return
        catalog_entity = self._catalog_entity(entity_id)
        if (
            catalog_entity.entity_type.value == AnalyticalLevel.MACRO.value
            and metric_id in self.context.analysis_request.macro_metric_ids
        ):
            return
        raise DatasetToolError("entity outside analysis request")

    def _ensure_target_entity(self, entity_id: str) -> None:
        if entity_id not in self.context.analysis_request.target_entity_ids:
            raise DatasetToolError("entity outside analysis request")

    def _ensure_peer_universe(self, peer_universe_id: str):
        if peer_universe_id != self.context.analysis_request.peer_universe_id:
            raise DatasetToolError("peer universe outside analysis request")
        universe = self.context.capability_catalog.peer_universe(peer_universe_id)
        if universe is None:
            raise DatasetToolError("unknown peer universe")
        try:
            effective_peer_entity_ids = universe.effective_entity_ids(
                self.context.analysis_request.peer_entity_ids
            )
        except ValueError as exc:
            raise DatasetToolError(str(exc)) from exc
        for entity_id in effective_peer_entity_ids:
            entity = self._catalog_entity(entity_id)
            if entity.entity_type.value != AnalyticalLevel.COMPANY.value:
                raise DatasetToolError("peer benchmark requires company peer entities")
        return universe

    def _ensure_sources(self, source_refs: Sequence[str]) -> None:
        if not set(source_refs).issubset(self._discovered_source_refs):
            raise DatasetToolError("evidence source outside discovered request scope")

    def _remember_observation(self, observation: CanonicalObservation | None) -> None:
        if observation is not None and observation.source_ref:
            self._discovered_source_refs.add(observation.source_ref)

    def get_metric(
        self,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._ensure_entity(entity_id, metric_id)
        self._ensure_period(period_id)
        self._ensure_metric(metric_id)
        observation = self.context.provider.get_metric(
            self.context.dataset_ref,
            entity_id,
            period_id,
            metric_id,
        )
        self._remember_observation(observation)
        return observation

    def get_entity_metrics(
        self,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        self._ensure_target_entity(entity_id)
        self._ensure_periods(period_ids)
        self._ensure_metrics_for_entity(entity_id, metric_ids)
        observations = self.context.provider.get_entity_metrics(
            self.context.dataset_ref,
            entity_id,
            period_ids,
            metric_ids,
        )
        for observation in observations:
            self._remember_observation(observation)
        return observations

    def get_peer_benchmark(
        self,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        self._ensure_peer_universe(peer_universe_id)
        self._ensure_period(period_id)
        self._ensure_company_peer_metrics(metric_ids)
        return self.context.provider.get_peer_benchmark(
            self.context.dataset_ref,
            peer_universe_id,
            period_id,
            metric_ids,
            peer_entity_ids=(self.context.analysis_request.peer_entity_ids or None),
        )

    def get_evidence(
        self,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        self._ensure_sources(source_refs)
        if entity_id is not None:
            if metric_id is None:
                if entity_id not in self.context.analysis_request.target_entity_ids:
                    macro_entity = next(
                        (
                            item
                            for item in self.context.capability_catalog.entities
                            if item.entity_id == entity_id
                            and item.entity_type.value == AnalyticalLevel.MACRO.value
                        ),
                        None,
                    )
                    if macro_entity is None:
                        raise DatasetToolError("entity outside analysis request")
            else:
                self._ensure_entity(entity_id, metric_id)
        elif metric_id is None or metric_id not in self.context.analysis_request.macro_metric_ids:
            raise DatasetToolError("company evidence requires a scoped entity")
        if period_id is not None:
            self._ensure_period(period_id)
        if metric_id is not None:
            self._ensure_metric(metric_id)
        evidence = self.context.provider.get_evidence(
            self.context.dataset_ref,
            source_refs,
            entity_id,
            period_id,
            metric_id,
        )
        self._discovered_source_refs.update(item.source_ref for item in evidence)
        return evidence

    def get_source(self, source_ref: str) -> DatasetSource | None:
        self._ensure_sources((source_ref,))
        return self.context.provider.get_source(self.context.dataset_ref, source_ref)

    def get_macro_observation(
        self,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        if metric_id not in self.context.analysis_request.macro_metric_ids:
            raise DatasetToolError("macro metric outside analysis request")
        self._ensure_entity(entity_id, metric_id)
        self._ensure_period(period_id)
        observation = self.context.provider.get_macro_observation(
            self.context.dataset_ref,
            entity_id,
            period_id,
            metric_id,
        )
        self._remember_observation(observation)
        return observation

    def resolve_observation(self, observation_id: str) -> CanonicalObservation | None:
        observation = self.context.provider.resolve_observation(
            self.context.dataset_ref,
            observation_id,
        )
        if observation is None:
            return None
        self._ensure_entity(observation.entity_id, observation.metric_id)
        self._ensure_period(observation.period_id)
        self._ensure_metric(observation.metric_id)
        self._remember_observation(observation)
        return observation

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, tuple):
            return [DatasetToolRuntime._serialize(item) for item in value]
        if isinstance(value, list):
            return [DatasetToolRuntime._serialize(item) for item in value]
        if isinstance(value, dict):
            return {key: DatasetToolRuntime._serialize(item) for key, item in value.items()}
        return value

    def execute(self, name: str, raw_arguments: dict[str, Any]) -> DatasetToolExecution:
        if name not in _ARGUMENT_MODELS:
            self.context.emit(
                RuntimeEventType.RUN_BLOCKED,
                self.actor,
                task_id=self.task_id,
                summary="unsupported dataset tool",
                public_payload={"operation": "unknown", "status": "blocked"},
            )
            raise DatasetToolError("unsupported dataset tool")
        supported = {
            item.value for item in self.context.capability_catalog.supported_operations
        }
        if name not in supported:
            self.context.emit(
                RuntimeEventType.RUN_BLOCKED,
                self.actor,
                task_id=self.task_id,
                summary="dataset tool is not supported by catalog",
                public_payload={"operation": name, "status": "blocked"},
            )
            raise DatasetToolError("dataset tool is not supported by catalog")
        self.context.emit(
            RuntimeEventType.TOOL_STARTED,
            self.actor,
            task_id=self.task_id,
            public_payload={"operation": name},
        )
        try:
            arguments = _ARGUMENT_MODELS[name].model_validate(raw_arguments)
            if name == SupportedOperation.GET_METRIC.value:
                output = self.get_metric(
                    arguments.entity_id, arguments.period_id, arguments.metric_id
                )
            elif name == SupportedOperation.GET_ENTITY_METRICS.value:
                output = self.get_entity_metrics(
                    arguments.entity_id, arguments.period_ids, arguments.metric_ids
                )
            elif name == SupportedOperation.GET_PEER_BENCHMARK.value:
                output = self.get_peer_benchmark(
                    arguments.peer_universe_id, arguments.period_id, arguments.metric_ids
                )
            elif name == SupportedOperation.GET_EVIDENCE.value:
                output = self.get_evidence(
                    arguments.source_refs,
                    arguments.entity_id,
                    arguments.period_id,
                    arguments.metric_id,
                )
            elif name == SupportedOperation.GET_SOURCE.value:
                output = self.get_source(arguments.source_ref)
            elif name == SupportedOperation.GET_MACRO_OBSERVATION.value:
                output = self.get_macro_observation(
                    arguments.entity_id, arguments.period_id, arguments.metric_id
                )
            else:
                output = self.resolve_observation(arguments.observation_id)
            serialized = self._serialize(output)
            encoded = json.dumps(
                serialized,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            self.context.emit(
                RuntimeEventType.TOOL_COMPLETED,
                self.actor,
                task_id=self.task_id,
                public_payload={"operation": name, "status": "success"},
            )
            return DatasetToolExecution(
                operation=name,
                output=serialized,
                result_sha256=sha256(encoded.encode("utf-8")).hexdigest(),
            )
        except DatasetToolError:
            self.context.emit(
                RuntimeEventType.RUN_BLOCKED,
                self.actor,
                task_id=self.task_id,
                summary="dataset tool request blocked",
                public_payload={"operation": name, "status": "blocked"},
            )
            raise
        except DatasetProviderError as exc:
            self.context.emit(
                RuntimeEventType.RUN_FAILED,
                self.actor,
                task_id=self.task_id,
                summary="dataset provider failed",
                public_payload={"operation": name, "status": "failed"},
            )
            raise DatasetToolError("dataset provider failed") from exc
        except ValueError as exc:
            self.context.emit(
                RuntimeEventType.RUN_BLOCKED,
                self.actor,
                task_id=self.task_id,
                summary="tool arguments or scope were invalid",
                public_payload={"operation": name, "status": "blocked"},
            )
            raise DatasetToolError("dataset tool request is invalid") from exc
