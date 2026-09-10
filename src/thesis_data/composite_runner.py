"""Fair three-arm controller for composite multi-workload experiments."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from typing import Any, Mapping, Protocol, Sequence

from .agent_runtime import AgentCallTelemetry, AgentToolCall
from .anomaly import AnomalyTrigger
from .composite_schema import CompositeAnalysisPayload
from .composite_transport import CompositeProviderResponse, _validate_composite_payload
from .context_budget import compact_composite_context
from .experiment_contract import ExperimentArm, ExperimentRunConfig
from .workload_contract import CompositeWorkloadSpec


class CompositeAdapter(Protocol):
    def complete(
        self,
        spec: CompositeWorkloadSpec,
        role: str,
        question_prompt: str = "",
        prepared_context: Mapping[str, Any] | None = None,
    ) -> CompositeProviderResponse | CompositeAnalysisPayload:
        """Return one typed response for one isolated composite stage."""


@dataclass(frozen=True)
class CompositeCallRecord:
    role: str
    attempt: int
    telemetry: AgentCallTelemetry
    tool_calls: tuple[AgentToolCall, ...] = ()
    payload: CompositeAnalysisPayload | None = None


@dataclass(frozen=True)
class CompositeArmRunResult:
    arm: ExperimentArm
    workload: CompositeWorkloadSpec
    final_payload: CompositeAnalysisPayload | None
    run_config: ExperimentRunConfig | None = None
    calls: tuple[CompositeCallRecord, ...] = ()
    telemetry: tuple[AgentCallTelemetry, ...] = ()
    critique_requests: tuple[str, ...] = ()
    arm_sop: tuple[str, ...] = ()
    failure_status: str | None = None
    failure_blockers: tuple[str, ...] = ()
    wall_clock_latency_ms: float | None = None
    peak_context_chars: int | None = None
    context_budget_chars: int | None = None

    @property
    def call_count(self) -> int:
        return len(self.calls)


def build_arm_sop(arm: ExperimentArm, spec: CompositeWorkloadSpec) -> tuple[str, ...]:
    """Return the pre-registered stage names for one arm."""

    if arm is ExperimentArm.SINGLE_AGENT:
        return ("decompose", "retrieve", "validate", "assemble", "synthesize")
    if arm is ExperimentArm.HIERARCHICAL_NO_CRITIQUE:
        return ("decompose", "company", "sector", "orchestrator", "assemble", "synthesize")
    if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE:
        return (
            "decompose",
            "company",
            "sector",
            "orchestrator",
            "verification",
            "assemble",
            "synthesize",
        )
    raise ValueError(f"unsupported experiment arm: {arm}")


def bounded_verification_requests(
    spec: CompositeWorkloadSpec,
    payload: CompositeAnalysisPayload,
    triggers: Sequence[str | AnomalyTrigger],
    max_attempts: int,
) -> tuple[str, ...]:
    """Select only deterministic trigger-backed verification requests."""

    if payload.question_id != spec.question_id:
        raise ValueError("payload does not belong to workload")
    if max_attempts <= 0:
        return ()
    selected: list[str] = []
    for trigger in triggers:
        request = (
            trigger.verification_request
            if isinstance(trigger, AnomalyTrigger)
            else str(trigger)
        ).strip()
        if request and request not in selected:
            selected.append(request)
        if len(selected) >= max_attempts:
            break
    return tuple(selected)


def _response_parts(
    response: CompositeProviderResponse | CompositeAnalysisPayload,
) -> tuple[CompositeAnalysisPayload, AgentCallTelemetry, tuple[AgentToolCall, ...]]:
    if isinstance(response, CompositeProviderResponse):
        return response.payload, response.telemetry, tuple(response.tool_calls)
    if isinstance(response, CompositeAnalysisPayload):
        return response, AgentCallTelemetry(), ()
    raise TypeError(f"adapter returned {type(response).__name__}, expected composite response")


def _failure_kind(exc: Exception) -> str:
    blockers = getattr(exc, "blockers", None)
    if isinstance(blockers, (tuple, list)) and any(
        str(item).startswith(("provider_", "context_budget", "tool_call_budget"))
        for item in blockers
    ):
        return "provider_failed"
    return "payload_validation_failed" if blockers else "provider_failed"


def run_composite_arm(
    spec: CompositeWorkloadSpec,
    arm_config: ExperimentRunConfig,
    adapter: CompositeAdapter,
    *,
    question_prompt: str = "Execute the declared composite workload.",
    triggers: Sequence[str | AnomalyTrigger] = (),
) -> CompositeArmRunResult:
    """Run one arm under a shared workload and total-call ceiling.

    A failed worker is recorded as a failed run; its output is never silently
    repaired or promoted as the arm's final composite answer.
    """

    sop = build_arm_sop(arm_config.arm, spec)
    if arm_config.question_id != spec.question_id:
        return CompositeArmRunResult(
            arm_config.arm, spec, None, arm_sop=sop,
            failure_status="workload_binding_failed",
            failure_blockers=("question_id_mismatch",),
        )
    if arm_config.max_total_calls <= 0:
        return CompositeArmRunResult(
            arm_config.arm, spec, None, arm_sop=sop,
            failure_status="call_budget_invalid",
            failure_blockers=("max_total_calls_required",),
        )

    calls: list[CompositeCallRecord] = []
    telemetry: list[AgentCallTelemetry] = []
    critique_requests: tuple[str, ...] = ()
    failure_status: str | None = None
    failure_blockers: tuple[str, ...] = ()
    final_payload: CompositeAnalysisPayload | None = None
    started = monotonic()
    peak_context_chars: int | None = None
    context_budget_chars: int | None = None

    def dispatch(
        role: str,
        attempt: int = 0,
        prompt_override: str | None = None,
        prepared_context: Mapping[str, Any] | None = None,
    ) -> CompositeAnalysisPayload | None:
        nonlocal failure_status, failure_blockers
        if len(calls) >= arm_config.max_total_calls:
            failure_status = "call_budget_exhausted"
            failure_blockers = ("max_total_calls_reached",)
            return None
        try:
            response = adapter.complete(
                spec,
                role,
                question_prompt if prompt_override is None else prompt_override,
                prepared_context,
            )
            payload, call_telemetry, tool_calls = _response_parts(response)
            _validate_composite_payload(payload, spec, role)
        except Exception as exc:
            blockers = getattr(exc, "blockers", None)
            failure_status = _failure_kind(exc)
            failure_blockers = tuple(blockers) if isinstance(blockers, (tuple, list)) else (exc.__class__.__name__,)
            return None
        calls.append(CompositeCallRecord(role, attempt, call_telemetry, tool_calls, payload))
        telemetry.append(call_telemetry)
        nonlocal peak_context_chars, context_budget_chars
        if call_telemetry.context_chars is not None:
            peak_context_chars = max(peak_context_chars or 0, call_telemetry.context_chars)
        if call_telemetry.context_budget_chars is not None:
            context_budget_chars = call_telemetry.context_budget_chars
        return payload

    def invoke(role: str, attempt: int = 0, prompt_override: str | None = None,
               prepared_context: Mapping[str, Any] | None = None) -> CompositeCallRecord:
        response = adapter.complete(
            spec,
            role,
            question_prompt if prompt_override is None else prompt_override,
            prepared_context,
        )
        payload, call_telemetry, tool_calls = _response_parts(response)
        _validate_composite_payload(payload, spec, role)
        return CompositeCallRecord(role, attempt, call_telemetry, tool_calls, payload)

    def append_record(record: CompositeCallRecord) -> CompositeAnalysisPayload:
        nonlocal peak_context_chars, context_budget_chars
        calls.append(record)
        telemetry.append(record.telemetry)
        if record.telemetry.context_chars is not None:
            peak_context_chars = max(peak_context_chars or 0, record.telemetry.context_chars)
        if record.telemetry.context_budget_chars is not None:
            context_budget_chars = record.telemetry.context_budget_chars
        if record.payload is None:
            raise ValueError("composite call record has no payload")
        return record.payload

    if arm_config.arm is ExperimentArm.SINGLE_AGENT:
        final_payload = dispatch("single_agent")
    else:
        worker_payloads: dict[str, Any] = {}
        worker_roles = ("company", "sector")
        if arm_config.worker_parallelism > 1:
            with ThreadPoolExecutor(max_workers=min(arm_config.worker_parallelism, len(worker_roles))) as pool:
                futures = {role: pool.submit(invoke, role) for role in worker_roles}
                for role in worker_roles:
                    try:
                        worker_payload = append_record(futures[role].result())
                    except Exception as exc:
                        failure_status = _failure_kind(exc)
                        blockers = getattr(exc, "blockers", None)
                        failure_blockers = tuple(blockers) if isinstance(blockers, (tuple, list)) else (exc.__class__.__name__,)
                        break
                    worker_payloads[role] = worker_payload.model_dump(mode="json")
        else:
            for role in worker_roles:
                worker_payload = dispatch(role)
                if worker_payload is None:
                    break
                worker_payloads[role] = worker_payload.model_dump(mode="json")
        if failure_status is None:
            try:
                compact_workers = compact_composite_context(
                    {"worker_payloads": worker_payloads},
                    max_chars=arm_config.max_context_chars,
                )
            except Exception as exc:
                failure_status = "context_budget_failed"
                blockers = getattr(exc, "blockers", None)
                failure_blockers = tuple(blockers) if isinstance(blockers, (tuple, list)) else (exc.__class__.__name__,)
            else:
                final_payload = dispatch(
                    "orchestrator",
                    prepared_context=compact_workers,
                )
        if (
            arm_config.arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE
            and failure_status is None
            and final_payload is not None
        ):
            critique_requests = bounded_verification_requests(
                spec,
                final_payload,
                triggers,
                arm_config.max_critique_attempts,
            )
            for attempt, request in enumerate(critique_requests, start=1):
                try:
                    verification_context = compact_composite_context(
                        {"orchestrator_payload": final_payload.model_dump(mode="json")},
                        max_chars=arm_config.max_context_chars,
                    )
                except Exception as exc:
                    failure_status = "context_budget_failed"
                    blockers = getattr(exc, "blockers", None)
                    failure_blockers = tuple(blockers) if isinstance(blockers, (tuple, list)) else (exc.__class__.__name__,)
                    break
                if dispatch(
                    "verification",
                    attempt,
                    prompt_override=request,
                    prepared_context=verification_context,
                ) is None:
                    break

    return CompositeArmRunResult(
        arm=arm_config.arm,
        workload=spec,
        final_payload=final_payload if failure_status is None else None,
        run_config=arm_config,
        calls=tuple(calls),
        telemetry=tuple(telemetry),
        critique_requests=critique_requests,
        arm_sop=sop,
        failure_status=failure_status,
        failure_blockers=failure_blockers,
        wall_clock_latency_ms=(monotonic() - started) * 1000,
        peak_context_chars=peak_context_chars,
        context_budget_chars=context_budget_chars,
    )
