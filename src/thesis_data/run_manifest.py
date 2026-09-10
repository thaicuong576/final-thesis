"""Versioned run manifests for reproducible, source-grounded agent calls."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_runtime import AgentCallTelemetry, RuntimeRunResult
from .composite_runner import CompositeArmRunResult
from .prompting import render_agent_prompt
from .prompting import render_composite_prompt
from .workload_contract import WorkloadTier


class RunCallTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1)
    attempt: int = Field(ge=0)
    periods: list[str] = Field(default_factory=list)
    context_sha256: str = Field(min_length=64, max_length=64)
    prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    payload_agent_id: str = Field(min_length=1)
    payload_status: str = Field(min_length=1)
    telemetry_status: Literal["provided", "unavailable"] = "unavailable"
    latency_ms: float | None = Field(default=None, ge=0.0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_estimate: float | None = Field(default=None, ge=0.0)
    context_chars: int | None = Field(default=None, ge=0)
    context_budget_chars: int | None = Field(default=None, ge=0)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentRunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=2, ge=1)
    environment: Literal["offline_fixture", "provider_backed"]
    comparative_result: bool
    run_id: str = Field(min_length=1)
    job_id: str | None = None
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    question_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    arm: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    source_policy_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    period: str = Field(min_length=1)
    periods: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(min_length=1)
    input_observation_ids: list[str] = Field(default_factory=list)
    input_source_ids: list[str] = Field(default_factory=list)
    input_evidence_ids: list[str] = Field(default_factory=list)
    input_context_sha256: str = Field(min_length=64, max_length=64)
    anomaly_triggers: list[dict[str, Any]] = Field(default_factory=list)
    call_count: int = Field(ge=0)
    calls: list[RunCallTrace]
    payloads: list[dict[str, Any]]
    recorded_at_utc: datetime
    workload_tier: WorkloadTier | None = None
    complexity_vector: dict[str, int] | None = None
    arm_sop: list[str] = Field(default_factory=list)
    subreport_count: int = Field(default=0, ge=0)
    total_tool_calls: int = Field(default=0, ge=0)
    total_input_tokens: int | None = Field(default=None, ge=0)
    total_output_tokens: int | None = Field(default=None, ge=0)
    total_cost_estimate: float | None = Field(default=None, ge=0.0)
    total_latency_ms: float | None = Field(default=None, ge=0.0)
    wall_clock_latency_ms: float | None = Field(default=None, ge=0.0)
    peak_context_chars: int | None = Field(default=None, ge=0)
    context_budget_chars: int | None = Field(default=None, ge=0)
    critique_count: int = Field(default=0, ge=0)
    failure_status: str | None = None
    failure_blockers: list[str] = Field(default_factory=list)
    final_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def trace_counts_match(self) -> "ExperimentRunManifest":
        if self.call_count != len(self.calls) or self.call_count != len(self.payloads):
            raise ValueError("call_count must match calls and payloads")
        if self.environment == "offline_fixture" and self.comparative_result:
            raise ValueError("offline fixture runs cannot be marked comparative results")
        return self


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_ids(value: Any, key: str, found: set[str]) -> None:
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            found.add(candidate)
        elif isinstance(candidate, list):
            found.update(item for item in candidate if isinstance(item, str) and item)
        for child in value.values():
            _collect_ids(child, key, found)
    elif isinstance(value, list):
        for child in value:
            _collect_ids(child, key, found)


def _prepared_context(context: dict[str, Any]) -> Any:
    if "shared_facts" in context:
        return context["shared_facts"]
    if "facts" in context:
        return context["facts"]
    return context


def build_run_manifest(
    result: RuntimeRunResult,
    question_id: str,
    metric_ids: Sequence[str],
    *,
    question_set_path: Path,
    environment: Literal["offline_fixture", "provider_backed"] = "offline_fixture",
    comparative_result: bool = False,
    recorded_at_utc: datetime | None = None,
) -> ExperimentRunManifest:
    """Capture immutable run inputs, provenance IDs, calls, and payloads."""
    if not question_id:
        raise ValueError("question_id must not be empty")
    normalized_metrics = [metric for metric in metric_ids if metric]
    if not normalized_metrics:
        raise ValueError("metric_ids must not be empty")
    if len(result.calls) != len(result.payloads):
        raise ValueError("runtime result calls and payloads must have equal lengths")
    telemetry = result.telemetry
    if not telemetry:
        telemetry = tuple(AgentCallTelemetry() for _ in result.calls)
    if len(result.calls) != len(telemetry):
        raise ValueError("runtime result calls and telemetry must have equal lengths")
    effective_contexts = result.effective_contexts or tuple(call.context for call in result.calls)
    if len(effective_contexts) != len(result.calls):
        raise ValueError("runtime result calls and effective contexts must have equal lengths")
    tool_calls = result.tool_calls or tuple(() for _ in result.calls)
    if len(tool_calls) != len(result.calls):
        raise ValueError("runtime result calls and tool calls must have equal lengths")

    observation_ids: set[str] = set()
    source_ids: set[str] = set()
    evidence_ids: set[str] = set()
    traces: list[RunCallTrace] = []
    for call, payload, call_telemetry, effective_context, call_tools in zip(
        result.calls, result.payloads, telemetry, effective_contexts, tool_calls
    ):
        _collect_ids(effective_context, "observation_ids", observation_ids)
        _collect_ids(effective_context, "source_ids", source_ids)
        _collect_ids(effective_context, "evidence_ids", evidence_ids)
        _collect_ids(effective_context, "evidence_id", evidence_ids)
        traces.append(
            RunCallTrace(
                role=call.role,
                attempt=call.attempt,
                periods=list(call.periods or (call.period,)),
                context_sha256=_canonical_sha256(call.context),
                prompt_sha256=sha256(
                    render_agent_prompt(call).encode("utf-8")
                ).hexdigest(),
                payload_agent_id=payload.agent_id,
                payload_status=payload.status.value,
                telemetry_status=call_telemetry.status,
                latency_ms=call_telemetry.latency_ms,
                input_tokens=call_telemetry.input_tokens,
                output_tokens=call_telemetry.output_tokens,
                cost_estimate=call_telemetry.cost_estimate,
                tool_calls=[
                    {
                        "name": item.name,
                        "arguments": item.arguments,
                        "result_sha256": item.result_sha256,
                        "status": item.status,
                        "valid_count": item.valid_count,
                        "missing_count": item.missing_count,
                        "conflict_count": item.conflict_count,
                    }
                    for item in call_tools
                ],
            )
        )

    prepared = _prepared_context(effective_contexts[0]) if effective_contexts else {}
    config = result.run_config
    if question_id != config.question_id:
        raise ValueError("question_id does not match run config")
    if any(call.prompt_version != config.prompt_version for call in result.calls):
        raise ValueError("call prompt_version does not match run config")
    return ExperimentRunManifest(
        environment=environment,
        comparative_result=comparative_result,
        run_id=config.run_id,
        job_id=result.job_id,
        snapshot_id=config.snapshot_id,
        question_set_id=config.question_set_id,
        question_set_sha256=_file_sha256(question_set_path),
        question_id=question_id,
        rubric_version=config.rubric_version,
        prompt_version=config.prompt_version,
        arm=config.arm.value,
        model_id=config.model_id,
        source_policy_id=config.source_policy_id,
        ticker=result.calls[0].ticker if result.calls else "unknown",
        period=result.calls[0].period if result.calls else "unknown",
        periods=(
            list(result.calls[0].periods or (result.calls[0].period,))
            if result.calls
            else []
        ),
        metric_ids=normalized_metrics,
        input_observation_ids=sorted(observation_ids),
        input_source_ids=sorted(source_ids),
        input_evidence_ids=sorted(evidence_ids),
        input_context_sha256=_canonical_sha256(prepared),
        anomaly_triggers=[trigger.as_dict() for trigger in result.anomaly_triggers],
        call_count=result.call_count,
        calls=traces,
        payloads=[payload.model_dump(mode="json") for payload in result.payloads],
        recorded_at_utc=recorded_at_utc or datetime.now(timezone.utc),
    )


def write_run_manifest(manifest: ExperimentRunManifest, output_path: Path) -> None:
    """Write one immutable manifest without overwriting an existing run."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite run manifest: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_composite_run_manifest(
    result: CompositeArmRunResult,
    *,
    question_set_path: Path,
    job_id: str | None = None,
    environment: Literal["offline_fixture", "provider_backed"] = "offline_fixture",
    comparative_result: bool = False,
    recorded_at_utc: datetime | None = None,
) -> ExperimentRunManifest:
    """Persist a composite run with additive, secret-safe telemetry fields."""

    config = result.workload
    run_config = getattr(result, "run_config", None)
    if run_config is None:
        raise ValueError("composite result must carry run configuration")
    if run_config.question_id != config.question_id:
        raise ValueError("composite question_id does not match run config")

    observation_ids: set[str] = set()
    source_ids: set[str] = set()
    evidence_ids: set[str] = set()
    traces: list[RunCallTrace] = []
    payloads: list[dict[str, Any]] = []
    scope_context = {
        "question_id": config.question_id,
        "tier": config.tier.value,
        "issuers": list(config.issuers),
        "periods": list(config.periods),
        "metric_ids": list(config.metric_ids),
        "analysis_tasks": [task.value for task in config.analysis_tasks],
    }
    for call in result.calls:
        payload = call.payload
        if payload is None:
            continue
        payload_json = payload.model_dump(mode="json")
        payloads.append(payload_json)
        _collect_ids(payload_json, "observation_ids", observation_ids)
        _collect_ids(payload_json, "source_ids", source_ids)
        _collect_ids(payload_json, "evidence_ids", evidence_ids)
        _collect_ids(payload_json, "evidence_id", evidence_ids)
        call_context = {**scope_context, "role": call.role, "attempt": call.attempt}
        traces.append(
            RunCallTrace(
                role=call.role,
                attempt=call.attempt,
                periods=list(config.periods),
                context_sha256=_canonical_sha256(call_context),
                prompt_sha256=sha256(
                    render_composite_prompt(
                        config,
                        call.role,
                        run_config.prompt_version,
                    ).encode("utf-8")
                ).hexdigest(),
                payload_agent_id=payload.agent_id,
                payload_status=payload.status.value,
                telemetry_status=call.telemetry.status,
                latency_ms=call.telemetry.latency_ms,
                input_tokens=call.telemetry.input_tokens,
                output_tokens=call.telemetry.output_tokens,
                cost_estimate=call.telemetry.cost_estimate,
                context_chars=call.telemetry.context_chars,
                context_budget_chars=call.telemetry.context_budget_chars,
                tool_calls=[
                    {
                        "name": item.name,
                        "arguments": item.arguments,
                        "result_sha256": item.result_sha256,
                        "status": item.status,
                        "valid_count": item.valid_count,
                        "missing_count": item.missing_count,
                        "conflict_count": item.conflict_count,
                    }
                    for item in call.tool_calls
                ],
            )
        )

    input_tokens = [call.telemetry.input_tokens for call in result.calls if call.telemetry.input_tokens is not None]
    output_tokens = [call.telemetry.output_tokens for call in result.calls if call.telemetry.output_tokens is not None]
    costs = [call.telemetry.cost_estimate for call in result.calls if call.telemetry.cost_estimate is not None]
    latencies = [call.telemetry.latency_ms for call in result.calls if call.telemetry.latency_ms is not None]
    final_payload = (
        result.final_payload.model_dump(mode="json")
        if result.final_payload is not None
        else None
    )
    return ExperimentRunManifest(
        environment=environment,
        comparative_result=comparative_result,
        run_id=run_config.run_id,
        job_id=job_id,
        snapshot_id=run_config.snapshot_id,
        question_set_id=run_config.question_set_id,
        question_set_sha256=_file_sha256(question_set_path),
        question_id=config.question_id,
        rubric_version=run_config.rubric_version,
        prompt_version=run_config.prompt_version,
        arm=run_config.arm.value,
        model_id=run_config.model_id,
        source_policy_id=run_config.source_policy_id,
        ticker=config.issuers[0],
        period=config.periods[0],
        periods=list(config.periods),
        metric_ids=list(config.metric_ids),
        input_observation_ids=sorted(observation_ids),
        input_source_ids=sorted(source_ids),
        input_evidence_ids=sorted(evidence_ids),
        input_context_sha256=_canonical_sha256(scope_context),
        call_count=len(result.calls),
        calls=traces,
        payloads=payloads,
        recorded_at_utc=recorded_at_utc or datetime.now(timezone.utc),
        workload_tier=config.tier,
        complexity_vector=config.complexity_vector.model_dump(mode="json"),
        arm_sop=list(result.arm_sop),
        subreport_count=len(result.final_payload.subreports) if result.final_payload else 0,
        total_tool_calls=sum(len(call.tool_calls) for call in result.calls),
        total_input_tokens=sum(input_tokens) if input_tokens else None,
        total_output_tokens=sum(output_tokens) if output_tokens else None,
        total_cost_estimate=sum(costs) if costs else None,
        total_latency_ms=sum(latencies) if latencies else None,
        wall_clock_latency_ms=result.wall_clock_latency_ms,
        peak_context_chars=result.peak_context_chars,
        context_budget_chars=result.context_budget_chars,
        critique_count=len(result.critique_requests),
        failure_status=result.failure_status,
        failure_blockers=list(result.failure_blockers),
        final_payload=final_payload,
    )


RunManifest = ExperimentRunManifest
