"""Provider-neutral response parsing for the guarded agent runtime.

This module owns only the boundary between a future provider transport and the
typed thesis payload contract. It does not create a provider client, resolve
secrets, or perform network I/O. A caller must inject a transport explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Any, Protocol

from pydantic import ValidationError

from .agent_runtime import (
    AgentCallRequest,
    AgentCallTelemetry,
    AgentCompletion,
    AgentToolCall,
)
from .composite_schema import CompositeAnalysisPayload
from .composite_transport import CompositeProviderResponse
from .provider_config import ProviderExecutionConfig
from .prompting import render_agent_prompt
from .prompting import render_composite_prompt
from .schema import AgentPayload, AgentStatus, EvidenceSnippet


class ProviderAdapterError(ValueError):
    """A provider transport response cannot cross the typed runtime boundary."""

    def __init__(self, blockers: tuple[str, ...] | list[str]):
        self.blockers = tuple(blockers)
        super().__init__("provider adapter rejected response: " + ", ".join(self.blockers))


@dataclass(frozen=True)
class ProviderResponse:
    """The narrow result a provider transport must return.

    ``payload`` may be an already typed payload, a JSON object, or a JSON
    string. Telemetry is deliberately typed before entering the runtime so
    provider-specific measurements cannot bypass the finite-value checks in
    :class:`AgentCallTelemetry`.
    """

    payload: AgentPayload | Mapping[str, Any] | str
    telemetry: AgentCallTelemetry | None = None
    effective_context: Mapping[str, Any] | None = None
    tool_calls: tuple[AgentToolCall, ...] = ()


class ProviderTransport(Protocol):
    """Dependency-injected transport; the implementation owns all I/O."""

    def complete(
        self,
        request: AgentCallRequest,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
    ) -> ProviderResponse:
        """Return one response for one request and its canonical prompt."""


class CompositeProviderTransport(Protocol):
    def complete_composite(
        self,
        spec: Any,
        role: str,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
        prepared_context: Mapping[str, Any] | None = None,
    ) -> CompositeProviderResponse:
        """Return one typed composite response."""


def _parse_payload(raw_payload: AgentPayload | Mapping[str, Any] | str) -> AgentPayload:
    if isinstance(raw_payload, AgentPayload):
        return raw_payload

    if isinstance(raw_payload, str):
        try:
            decoded: Any = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ProviderAdapterError(("provider_response_json_invalid",)) from exc
        raw_payload = decoded

    if not isinstance(raw_payload, Mapping):
        raise ProviderAdapterError(("provider_payload_schema_invalid",))

    try:
        return AgentPayload.model_validate(dict(raw_payload))
    except (TypeError, ValidationError) as exc:
        raise ProviderAdapterError(("provider_payload_schema_invalid",)) from exc


def _canonicalize_tool_evidence(
    payload: AgentPayload,
    effective_context: Mapping[str, Any] | None,
) -> AgentPayload:
    """Bind cited evidence objects to the exact objects returned by Gold tools."""

    if not effective_context or not payload.evidence:
        return payload
    evidence_by_id: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            candidate = value.get("evidence_id")
            if isinstance(candidate, str) and candidate:
                evidence_by_id[candidate] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(effective_context)
    canonical: list[EvidenceSnippet] = []
    unbound_count = 0
    for evidence in payload.evidence:
        expected = evidence_by_id.get(evidence.evidence_id)
        if expected is None:
            unbound_count += 1
        else:
            try:
                canonical.append(EvidenceSnippet.model_validate(expected))
            except ValueError as exc:
                raise ProviderAdapterError(("provider_tool_evidence_invalid",)) from exc
    quality_flags = list(payload.quality_flags)
    if unbound_count and "unbound_evidence_dropped" not in quality_flags:
        quality_flags.append("unbound_evidence_dropped")
    return payload.model_copy(update={"evidence": canonical, "quality_flags": quality_flags})


def _canonicalize_tool_provenance(
    payload: AgentPayload,
    effective_context: Mapping[str, Any] | None,
) -> AgentPayload:
    """Drop model-invented IDs while retaining only IDs returned by Gold tools."""

    if not effective_context:
        return payload
    allowed_observations: set[str] = set()
    allowed_sources: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, target in (("observation_ids", allowed_observations), ("source_ids", allowed_sources)):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    target.add(candidate)
                elif isinstance(candidate, list):
                    target.update(item for item in candidate if isinstance(item, str) and item)
            candidate = value.get("source_id")
            if isinstance(candidate, str) and candidate:
                allowed_sources.add(candidate)
            candidate = value.get("observation_id")
            if isinstance(candidate, str) and candidate:
                allowed_observations.add(candidate)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(effective_context)
    quality_flags = list(payload.quality_flags)
    observation_ids = [item for item in payload.observation_ids if item in allowed_observations]
    source_ids = [item for item in payload.source_ids if item in allowed_sources]
    if len(observation_ids) != len(payload.observation_ids):
        quality_flags.append("unbound_observation_ids_dropped")
    if len(source_ids) != len(payload.source_ids):
        quality_flags.append("unbound_source_ids_dropped")
    metrics = dict(payload.metrics)
    benchmarks = dict(payload.sector_benchmarks)
    if (metrics or benchmarks) and not (observation_ids or source_ids or payload.evidence):
        metrics = {key: None for key in metrics}
        benchmarks = {key: None for key in benchmarks}
        quality_flags.append("unbound_numeric_claims_dropped")
        status = AgentStatus.PARTIAL
    else:
        status = payload.status
    return payload.model_copy(
        update={
            "observation_ids": observation_ids,
            "source_ids": source_ids,
            "metrics": metrics,
            "sector_benchmarks": benchmarks,
            "quality_flags": list(dict.fromkeys(quality_flags)),
            "status": status,
        }
    )


class StructuredProviderAdapter:
    """Adapt one injected transport to the runtime's ``AgentAdapter`` shape."""

    def __init__(
        self,
        transport: ProviderTransport,
        config: ProviderExecutionConfig,
    ) -> None:
        self._transport = transport
        self._config = config
        self.retrieval_mode = config.retrieval_mode

    def complete(self, request: AgentCallRequest) -> AgentCompletion:
        rendered_prompt = render_agent_prompt(request)
        try:
            response = self._transport.complete(request, rendered_prompt, self._config)
        except Exception as exc:
            # Do not copy provider exception text into experiment artifacts:
            # it may contain endpoint, request, or secret-related details.
            blockers = getattr(exc, "blockers", None)
            raise ProviderAdapterError(
                blockers if isinstance(blockers, (tuple, list)) else ("provider_transport_failed",)
            ) from exc

        if not isinstance(response, ProviderResponse):
            raise ProviderAdapterError(("provider_response_type_invalid",))

        payload = _parse_payload(response.payload)
        payload = _canonicalize_tool_evidence(payload, response.effective_context)
        payload = _canonicalize_tool_provenance(payload, response.effective_context)
        if response.telemetry is None:
            if self._config.telemetry_required:
                raise ProviderAdapterError(("provider_telemetry_required",))
            telemetry = AgentCallTelemetry()
        elif not isinstance(response.telemetry, AgentCallTelemetry):
            raise ProviderAdapterError(("provider_telemetry_invalid",))
        else:
            telemetry = response.telemetry

        return AgentCompletion(
            payload=payload,
            telemetry=telemetry,
            effective_context=(
                dict(response.effective_context)
                if response.effective_context is not None
                else None
            ),
            tool_calls=tuple(response.tool_calls),
        )


class StructuredCompositeProviderAdapter:
    """Provider-neutral boundary for typed composite responses."""

    def __init__(
        self,
        transport: CompositeProviderTransport,
        config: ProviderExecutionConfig,
        prompt_version: str = "composite-prompt-v1",
    ) -> None:
        self._transport = transport
        self._config = config
        self._prompt_version = prompt_version
        self.retrieval_mode = config.retrieval_mode

    def complete(
        self,
        spec: Any,
        role: str,
        question_prompt: str = "",
        prepared_context: Mapping[str, Any] | None = None,
    ) -> CompositeProviderResponse:
        rendered_prompt = render_composite_prompt(
            spec,
            role,
            self._prompt_version,
            question_prompt or "Execute the declared composite workload.",
            prepared_context=prepared_context,
            max_context_chars=self._config.max_context_chars,
        )
        try:
            if prepared_context is None:
                response = self._transport.complete_composite(
                    spec, role, rendered_prompt, self._config
                )
            else:
                response = self._transport.complete_composite(
                    spec,
                    role,
                    rendered_prompt,
                    self._config,
                    prepared_context=prepared_context,
                )
        except Exception as exc:
            blockers = getattr(exc, "blockers", None)
            raise ProviderAdapterError(
                blockers if isinstance(blockers, (tuple, list)) else ("provider_transport_failed",)
            ) from exc
        if not isinstance(response, CompositeProviderResponse):
            raise ProviderAdapterError(("composite_provider_response_type_invalid",))
        if not isinstance(response.payload, CompositeAnalysisPayload):
            raise ProviderAdapterError(("composite_provider_payload_schema_invalid",))
        if not isinstance(response.telemetry, AgentCallTelemetry):
            raise ProviderAdapterError(("provider_telemetry_invalid",))
        if self._config.telemetry_required and response.telemetry.status != "provided":
            raise ProviderAdapterError(("provider_telemetry_required",))
        return response
