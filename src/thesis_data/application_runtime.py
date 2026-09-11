"""Application runtime context bound to a dataset provider and request."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analysis_request import AnalysisRequest, validate_analysis_request
from .dataset_contract import DatasetCapabilityCatalog, DatasetRef
from .dataset_provider import FinancialDatasetProvider
from .runtime_events import RuntimeEvent, RuntimeEventSink, RuntimeEventType


@dataclass
class ApplicationRuntimeContext:
    """The minimum application context needed by future agents."""

    analysis_request: AnalysisRequest
    dataset_ref: DatasetRef
    capability_catalog: DatasetCapabilityCatalog
    provider: FinancialDatasetProvider
    event_sink: RuntimeEventSink | None = None
    run_id: str | None = None
    _next_sequence: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.dataset_ref != self.analysis_request.dataset_ref:
            raise ValueError("application context dataset_ref does not match analysis request")
        if self.capability_catalog.dataset_ref != self.dataset_ref:
            raise ValueError("capability catalog dataset_ref does not match context")
        validate_analysis_request(self.analysis_request, self.capability_catalog)
        if self.run_id is None:
            self.run_id = self.analysis_request.request_id

    @classmethod
    def from_request(
        cls,
        request: AnalysisRequest,
        provider: FinancialDatasetProvider,
        *,
        event_sink: RuntimeEventSink | None = None,
    ) -> "ApplicationRuntimeContext":
        dataset_ref = request.dataset_ref
        catalog = provider.get_capabilities(dataset_ref)
        return cls(
            analysis_request=request,
            dataset_ref=dataset_ref,
            capability_catalog=catalog,
            provider=provider,
            event_sink=event_sink,
        )

    def emit(
        self,
        event_type: RuntimeEventType,
        actor: str,
        *,
        task_id: str | None = None,
        artifact_refs: tuple[str, ...] = (),
        summary: str | None = None,
        public_payload: dict[str, Any] | None = None,
    ) -> RuntimeEvent | None:
        if self.event_sink is None:
            self._next_sequence += 1
            return None
        event = RuntimeEvent(
            event_id=f"{self.run_id}:event:{self._next_sequence}",
            run_id=self.run_id or self.analysis_request.request_id,
            sequence=self._next_sequence,
            event_type=event_type,
            actor=actor,
            task_id=task_id,
            artifact_refs=artifact_refs,
            summary=summary,
            public_payload=public_payload or {},
        )
        self.event_sink.emit(event)
        self._next_sequence += 1
        return event

    def assign_task(self, task_id: str, actor: str, summary: str | None = None) -> None:
        self.emit(
            RuntimeEventType.TASK_ASSIGNED,
            actor,
            task_id=task_id,
            summary=summary,
        )

    def start_agent(self, task_id: str, actor: str) -> None:
        self.emit(RuntimeEventType.AGENT_STARTED, actor, task_id=task_id)

    def record_agent_output(
        self,
        task_id: str,
        actor: str,
        *,
        artifact_refs: tuple[str, ...] = (),
        summary: str | None = None,
    ) -> None:
        self.emit(
            RuntimeEventType.AGENT_OUTPUT_CREATED,
            actor,
            task_id=task_id,
            artifact_refs=artifact_refs,
            summary=summary,
        )
