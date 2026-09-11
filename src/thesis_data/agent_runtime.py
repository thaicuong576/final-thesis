"""Guarded, adapter-based dispatch scaffold for the three experiment arms.

This module deliberately does not know how to call an LLM. The caller injects an
adapter so tests can run offline and future model providers cannot bypass the
snapshot, scope, or critique-budget checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import math
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence

from .experiment_contract import (
    ExperimentArm,
    ExperimentRunConfig,
    audit_experiment_inputs,
)
from .anomaly import AnomalyTrigger, detect_anomaly_triggers
from .query import (
    EvidenceQuery,
    get_company_metrics,
    get_evidence,
    get_macro_context,
    get_macro_evidence,
    get_sector_benchmarks,
)
from .schema import AgentPayload, AgentStatus, GoldConfig
from .question_set import QuestionType, load_question_set


@dataclass(frozen=True)
class AgentCallRequest:
    role: str
    ticker: str
    period: str
    context: dict[str, Any]
    attempt: int = 0
    periods: tuple[str, ...] = ()
    metric_ids: tuple[str, ...] = ()
    macro_indicator_ids: tuple[str, ...] = ()
    question_id: str = ""
    question_type: str = ""
    question_prompt: str = ""
    prompt_version: str = ""
    peer_tickers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.prompt_version, str) or not self.prompt_version.strip():
            raise ValueError("prompt_version must be non-empty")


@dataclass(frozen=True)
class AgentCallTelemetry:
    """Provider-supplied call measurements; unavailable values stay null."""

    status: Literal["provided", "unavailable"] = "unavailable"
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_estimate: float | None = None
    context_chars: int | None = None
    context_budget_chars: int | None = None

    def __post_init__(self) -> None:
        if self.status == "unavailable" and any(
            value is not None
            for value in (
                self.latency_ms,
                self.input_tokens,
                self.output_tokens,
                self.cost_estimate,
                self.context_chars,
                self.context_budget_chars,
            )
        ):
            raise ValueError("unavailable telemetry cannot include measurements")
        for name, value in (
            ("latency_ms", self.latency_ms),
            ("cost_estimate", self.cost_estimate),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative finite number")
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("context_chars", self.context_chars),
            ("context_budget_chars", self.context_budget_chars),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class AgentCompletion:
    payload: AgentPayload
    telemetry: AgentCallTelemetry = AgentCallTelemetry()
    effective_context: dict[str, Any] | None = None
    tool_calls: tuple["AgentToolCall", ...] = ()


@dataclass(frozen=True)
class AgentToolCall:
    """Secret-safe trace of one validated local tool execution."""

    name: str
    arguments: dict[str, Any]
    result_sha256: str
    status: Literal["success", "rejected", "failed"] = "success"
    valid_count: int = 0
    missing_count: int = 0
    conflict_count: int = 0

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.arguments, dict):
            raise ValueError("tool trace name and arguments are required")
        if len(self.result_sha256) != 64:
            raise ValueError("tool trace result_sha256 must be a SHA-256 digest")
        for name, value in (
            ("valid_count", self.valid_count),
            ("missing_count", self.missing_count),
            ("conflict_count", self.conflict_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


class AgentAdapter(Protocol):
    def complete(self, request: AgentCallRequest) -> AgentPayload | AgentCompletion:
        """Return a payload, optionally with provider telemetry."""


@dataclass(frozen=True)
class RuntimeRunResult:
    run_config: ExperimentRunConfig
    payloads: tuple[AgentPayload, ...]
    calls: tuple[AgentCallRequest, ...]
    anomaly_triggers: tuple[AnomalyTrigger, ...] = ()
    telemetry: tuple[AgentCallTelemetry, ...] = ()
    effective_contexts: tuple[dict[str, Any], ...] = ()
    tool_calls: tuple[tuple[AgentToolCall, ...], ...] = ()
    job_id: str | None = None

    @property
    def call_count(self) -> int:
        return len(self.calls)


class ExperimentInputError(ValueError):
    def __init__(self, blockers: Sequence[str]):
        self.blockers = tuple(blockers)
        super().__init__("experiment inputs rejected: " + ", ".join(self.blockers))


class AgentOutputError(ValueError):
    def __init__(self, blockers: Sequence[str]):
        self.blockers = tuple(blockers)
        super().__init__("agent output rejected: " + ", ".join(self.blockers))


def _source_tiers_for_policy(source_policy_id: str) -> tuple[str, ...]:
    """Resolve the small, explicit source-policy vocabulary fail-closed."""

    primary_only_policies = {
        "primary-only-v1",
        "fixture-primary-only-v1",
        "offline-fixture-primary-only-v1",
    }
    if source_policy_id in primary_only_policies:
        return ("primary",)
    raise ExperimentInputError((f"unknown_source_policy:{source_policy_id}",))


def _validate_question_request(
    question_set_path: Path,
    question_id: str,
    ticker: str,
    period: str,
    metric_ids: Sequence[str],
    macro_indicator_ids: Sequence[str] = (),
    question_periods: Sequence[str] | None = None,
) -> Any:
    """Keep the runtime request bound to the selected question's target."""

    try:
        question_set = load_question_set(question_set_path)
    except ValueError as exc:
        raise ExperimentInputError(("question_set_schema_invalid",)) from exc

    question = next(
        (candidate for candidate in question_set.questions if candidate.id == question_id),
        None,
    )
    if question is None:
        raise ExperimentInputError(("question_id_not_in_question_set",))

    blockers: list[str] = []
    if question.issuer != ticker:
        blockers.append("question_issuer_mismatch")
    requested_periods = tuple(question_periods) if question_periods is not None else (period,)
    if not requested_periods or any(not item for item in requested_periods):
        blockers.append("question_periods_invalid")
    allowed_periods = (
        question.periods
        if question.type is QuestionType.COMPANY_TREND
        else (question.period,) if question.period is not None else ()
    )
    if period not in allowed_periods:
        blockers.append("question_period_mismatch")
    if question.type is QuestionType.COMPANY_TREND:
        if question_periods is None:
            blockers.append("question_requires_multi_period_runtime")
        elif requested_periods != question.periods:
            blockers.append("question_periods_mismatch")
    elif requested_periods != (period,):
        blockers.append("question_periods_mismatch")
    allowed_metrics = set(question_set.scope.core_metrics) | set(
        question_set.scope.conditional_metrics
    )
    blockers.extend(
        f"metric_outside_question_scope:{metric}"
        for metric in metric_ids
        if metric not in allowed_metrics
    )
    if (
        question.type is QuestionType.MACRO_TO_BANK
        and tuple(macro_indicator_ids) != question.macro_indicator_ids
    ):
        blockers.append("macro_indicator_scope_mismatch")
    if blockers:
        raise ExperimentInputError(tuple(blockers))
    return question


def _context_provenance(
    value: Any,
    observation_ids: set[str],
    source_ids: set[str],
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    if isinstance(value, dict):
        for key, target in (
            ("observation_ids", observation_ids),
            ("source_ids", source_ids),
        ):
            candidate = value.get(key)
            if isinstance(candidate, list):
                target.update(item for item in candidate if isinstance(item, str) and item)
        evidence_id = value.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id:
            evidence_by_id[evidence_id] = dict(value)
            evidence_source_id = value.get("source_id")
            if isinstance(evidence_source_id, str) and evidence_source_id:
                source_ids.add(evidence_source_id)
        source_id = value.get("source_id")
        if isinstance(source_id, str) and source_id:
            source_ids.add(source_id)
        for child in value.values():
            _context_provenance(child, observation_ids, source_ids, evidence_by_id)
    elif isinstance(value, list):
        for child in value:
            _context_provenance(child, observation_ids, source_ids, evidence_by_id)


def _validate_payload_provenance(
    payload: AgentPayload, context: dict[str, Any]
) -> None:
    allowed_observation_ids: set[str] = set()
    allowed_source_ids: set[str] = set()
    evidence_by_id: dict[str, dict[str, Any]] = {}
    _context_provenance(
        context,
        allowed_observation_ids,
        allowed_source_ids,
        evidence_by_id,
    )
    blockers: list[str] = []
    blockers.extend(
        f"observation_id_not_in_context:{observation_id}"
        for observation_id in payload.observation_ids
        if observation_id not in allowed_observation_ids
    )
    blockers.extend(
        f"source_id_not_in_context:{source_id}"
        for source_id in payload.source_ids
        if source_id not in allowed_source_ids
    )
    for evidence in payload.evidence:
        expected = evidence_by_id.get(evidence.evidence_id)
        if expected is None:
            blockers.append(f"evidence_id_not_in_context:{evidence.evidence_id}")
            continue
        if evidence.model_dump(mode="json") != expected:
            blockers.append(f"evidence_payload_mismatch:{evidence.evidence_id}")
    if blockers:
        raise AgentOutputError(tuple(dict.fromkeys(blockers)))


def _validate_payload_request_binding(
    payload: AgentPayload, request: AgentCallRequest
) -> None:
    """Reject a valid-looking payload that answers another target or period."""

    blockers: list[str] = []
    if payload.agent_id != request.role:
        blockers.append("payload_agent_id_mismatch")
    # Macro workers may intentionally return ticker=None because their context
    # is indicator-scoped rather than issuer-scoped. Every other role must
    # return the concrete issuer that was requested for this call.
    if request.role == "macro":
        ticker_mismatch = payload.ticker is not None and payload.ticker != request.ticker
    else:
        ticker_mismatch = payload.ticker != request.ticker
    if ticker_mismatch:
        blockers.append("payload_ticker_mismatch")
    if payload.period != request.period:
        blockers.append("payload_period_mismatch")

    requested_periods = request.periods or (request.period,)
    metric_scope = (
        set(request.macro_indicator_ids)
        if request.role == "macro"
        else set(request.metric_ids)
    )
    benchmark_scope = set() if request.role == "macro" else set(request.metric_ids)
    allowed_metric_fields = metric_scope | benchmark_scope
    observed_metric_fields = (
        set(payload.metrics)
        | set(payload.sector_benchmarks)
        | set(payload.metric_units)
        | set(payload.metric_periods)
    )
    blockers.extend(
        f"payload_metric_outside_request:{metric}"
        for metric in sorted(observed_metric_fields - allowed_metric_fields)
    )
    published_metric_fields = set(payload.metrics) | set(payload.sector_benchmarks)
    blockers.extend(
        f"payload_metric_unit_missing:{metric}"
        for metric in sorted(published_metric_fields - set(payload.metric_units))
    )
    blockers.extend(
        f"payload_metric_period_missing:{metric}"
        for metric in sorted(published_metric_fields - set(payload.metric_periods))
    )
    blockers.extend(
        f"payload_metric_period_outside_request:{metric}"
        for metric, metric_period in sorted(payload.metric_periods.items())
        if metric in allowed_metric_fields and metric_period not in requested_periods
    )
    numeric_metric_published = any(
        value is not None
        for value in (*payload.metrics.values(), *payload.sector_benchmarks.values())
    )
    if numeric_metric_published and not (
        payload.observation_ids or payload.source_ids or payload.evidence
    ):
        blockers.append("payload_numeric_metric_without_provenance")
    if blockers:
        raise AgentOutputError(tuple(dict.fromkeys(blockers)))


def _empty_macro_payload(period: str) -> AgentPayload:
    return AgentPayload(
        agent_id="macro",
        status=AgentStatus.PARTIAL,
        period=period,
        findings=["macro_context_not_requested"],
    )


def _prepare_period_context(
    db_path: Path,
    ticker: str,
    period: str,
    metric_ids: Sequence[str],
    macro_indicator_ids: Sequence[str],
    peer_tickers: Sequence[str],
    source_tiers: Sequence[str],
) -> dict[str, Any]:
    company = get_company_metrics(
        db_path,
        ticker,
        period,
        metric_ids,
        source_tiers=source_tiers,
    )
    sector = get_sector_benchmarks(
        db_path,
        "bank",
        period,
        metric_ids,
        tickers=peer_tickers,
        source_tiers=source_tiers,
    )
    macro = (
        get_macro_context(
            db_path,
            period,
            macro_indicator_ids,
            source_tiers=source_tiers,
        )
        if macro_indicator_ids
        else _empty_macro_payload(period)
    )
    company_source_ids = sorted(set(company.source_ids + sector.source_ids))
    evidence = get_evidence(
        db_path,
        company_source_ids,
        EvidenceQuery(ticker=ticker, period=period),
        source_tiers=source_tiers,
    )
    if macro.source_ids:
        typed_macro_evidence = [
            snippet
            for indicator_id in macro_indicator_ids
            for snippet in get_macro_evidence(
                db_path,
                sorted(set(macro.source_ids)),
                indicator_id,
                period,
                source_tiers=source_tiers,
            )
        ]
        if typed_macro_evidence:
            evidence.extend(typed_macro_evidence)
        else:
            # Compatibility fallback for pre-V2 fixtures only.  The typed
            # macro acceptance resolver never uses this path.
            evidence.extend(
                get_evidence(
                    db_path,
                    sorted(set(macro.source_ids)),
                    EvidenceQuery(period=period),
                    source_tiers=source_tiers,
                )
            )
    evidence_by_id = {snippet.evidence_id: snippet for snippet in evidence}
    return {
        "company": company.model_dump(mode="json"),
        "sector": sector.model_dump(mode="json"),
        "macro": macro.model_dump(mode="json"),
        "evidence": [
            evidence_by_id[evidence_id].model_dump(mode="json")
            for evidence_id in sorted(evidence_by_id)
        ],
    }


def _prepare_context(
    db_path: Path,
    ticker: str,
    periods: Sequence[str],
    metric_ids: Sequence[str],
    macro_indicator_ids: Sequence[str],
    peer_tickers: Sequence[str],
    source_tiers: Sequence[str],
) -> dict[str, Any]:
    normalized_periods = tuple(periods)
    if not normalized_periods:
        raise ValueError("periods must not be empty")
    prepared = {
        period: _prepare_period_context(
            db_path,
            ticker,
            period,
            metric_ids,
            macro_indicator_ids,
            peer_tickers,
            source_tiers,
        )
        for period in normalized_periods
    }
    if len(normalized_periods) == 1:
        return prepared[normalized_periods[0]]
    return {
        "period_order": list(normalized_periods),
        "periods": prepared,
    }


def _detect_context_anomalies(
    facts: dict[str, Any],
    periods: Sequence[str],
    metric_ids: Sequence[str],
    deviation_thresholds: Mapping[str, float] | None,
) -> tuple[AnomalyTrigger, ...]:
    if len(periods) == 1:
        return detect_anomaly_triggers(
            facts,
            metric_ids,
            deviation_thresholds=deviation_thresholds,
        )

    period_contexts = facts.get("periods")
    if not isinstance(period_contexts, dict):
        raise ValueError("multi-period facts must include period contexts")
    triggers: list[AnomalyTrigger] = []
    for period in periods:
        period_facts = period_contexts.get(period)
        if not isinstance(period_facts, dict):
            raise ValueError(f"missing prepared context for period: {period}")
        for trigger in detect_anomaly_triggers(
            period_facts,
            metric_ids,
            deviation_thresholds=deviation_thresholds,
        ):
            triggers.append(
                AnomalyTrigger(
                    rule_id=trigger.rule_id,
                    metric_id=trigger.metric_id,
                    description=f"{period}: {trigger.description}",
                    affected_agents=trigger.affected_agents,
                    verification_request=f"{period}: {trigger.verification_request}",
                )
            )
    return tuple(triggers)


def run_agent_arm(
    db_path: Path,
    run_config: ExperimentRunConfig,
    question_set_path: Path,
    gold_config: GoldConfig,
    ticker: str,
    period: str,
    metric_ids: Sequence[str],
    adapter: AgentAdapter,
    *,
    macro_indicator_ids: Sequence[str] = (),
    verification_requests: Sequence[str] = (),
    deviation_thresholds: Mapping[str, float] | None = None,
    question_periods: Sequence[str] | None = None,
) -> RuntimeRunResult:
    """Prepare accepted facts and dispatch one configured arm.

    The function is intentionally a dispatch scaffold: it returns worker
    payloads and call traces, while final natural-language synthesis belongs to
    the injected adapter or a later orchestrator layer.
    """

    input_audit = audit_experiment_inputs(
        db_path,
        run_config,
        question_set_path,
        gold_config,
        macro_indicator_ids=tuple(macro_indicator_ids),
    )
    if not input_audit.eligible:
        raise ExperimentInputError(input_audit.blockers)

    question = _validate_question_request(
        question_set_path,
        run_config.question_id,
        ticker,
        period,
        metric_ids,
        macro_indicator_ids=macro_indicator_ids,
        question_periods=question_periods,
    )
    source_tiers = _source_tiers_for_policy(run_config.source_policy_id)
    requested_periods = (
        tuple(question_periods) if question_periods is not None else (period,)
    )

    tool_calling = getattr(adapter, "retrieval_mode", "prefetched") == "tool_calling"
    if tool_calling:
        facts = {
            "retrieval_mode": "closed_world_tool_calling",
            "snapshot_id": run_config.snapshot_id,
            "source_policy_id": run_config.source_policy_id,
            "tool_scope": "role_isolated_read_only_gold",
        }
    else:
        facts = _prepare_context(
            db_path,
            ticker,
            requested_periods,
            metric_ids,
            macro_indicator_ids,
            question.peer_set
            if question.type is QuestionType.PEER_COMPARISON
            else gold_config.tickers,
            source_tiers,
        )
    anomaly_triggers = (
        _detect_context_anomalies(
            facts,
            requested_periods,
            metric_ids,
            deviation_thresholds,
        )
        if run_config.arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE and not tool_calling
        else ()
    )
    calls: list[AgentCallRequest] = []
    payloads: list[AgentPayload] = []
    telemetry: list[AgentCallTelemetry] = []
    effective_contexts: list[dict[str, Any]] = []
    tool_call_traces: list[tuple[AgentToolCall, ...]] = []

    def dispatch(role: str, context: dict[str, Any], attempt: int = 0) -> AgentPayload:
        # Give the adapter an isolated copy and validate against an untouched
        # trace copy. Otherwise a mutable adapter could add invented
        # provenance to request.context before the guard runs.
        trace_request = AgentCallRequest(
            role,
            ticker,
            period,
            deepcopy(context),
            attempt,
            periods=requested_periods,
            metric_ids=tuple(metric_ids),
            macro_indicator_ids=tuple(macro_indicator_ids),
            question_id=question.id,
            question_type=question.type.value,
            question_prompt=question.prompt,
            prompt_version=run_config.prompt_version,
            peer_tickers=(
                tuple(question.peer_set)
                if question.type is QuestionType.PEER_COMPARISON
                else tuple(gold_config.tickers)
            ),
        )
        request = AgentCallRequest(
            role,
            ticker,
            period,
            deepcopy(trace_request.context),
            attempt,
            periods=trace_request.periods,
            metric_ids=trace_request.metric_ids,
            macro_indicator_ids=trace_request.macro_indicator_ids,
            question_id=trace_request.question_id,
            question_type=trace_request.question_type,
            question_prompt=trace_request.question_prompt,
            prompt_version=trace_request.prompt_version,
            peer_tickers=trace_request.peer_tickers,
        )
        completion = adapter.complete(request)
        if isinstance(completion, AgentCompletion):
            payload = completion.payload
            call_telemetry = completion.telemetry
            completion_context = completion.effective_context
            completion_tool_calls = completion.tool_calls
        else:
            payload = completion
            call_telemetry = AgentCallTelemetry()
            completion_context = None
            completion_tool_calls = ()
        if not isinstance(payload, AgentPayload):
            raise TypeError(f"adapter returned {type(payload).__name__}, expected AgentPayload")
        effective_context = deepcopy(trace_request.context)
        if completion_context:
            effective_context["tool_results"] = deepcopy(completion_context)
        _validate_payload_request_binding(payload, trace_request)
        _validate_payload_provenance(payload, effective_context)
        calls.append(trace_request)
        payloads.append(payload)
        telemetry.append(call_telemetry)
        effective_contexts.append(effective_context)
        tool_call_traces.append(tuple(completion_tool_calls))
        return payload

    if run_config.arm is ExperimentArm.SINGLE_AGENT:
        dispatch("single_agent", facts)
        return RuntimeRunResult(
            run_config,
            tuple(payloads),
            tuple(calls),
            telemetry=tuple(telemetry),
            effective_contexts=tuple(effective_contexts),
            tool_calls=tuple(tool_call_traces),
        )

    worker_payloads: dict[str, AgentPayload] = {}
    for role in ("macro", "sector", "company"):
        worker_payloads[role] = dispatch(
            role,
            {"shared_facts": facts, "focus": role},
        )

    dispatch(
        "orchestrator",
        {"facts": facts, "workers": {key: value.model_dump(mode="json") for key, value in worker_payloads.items()}},
    )

    if run_config.arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE:
        requests = tuple(verification_requests)
        if not requests:
            requests = tuple(trigger.verification_request for trigger in anomaly_triggers)
        if not requests and tool_calling:
            requests = (
                "Verify the requested numeric claims, missing cells, conflicts, "
                "and their evidence against the Gold snapshot.",
            )
        for attempt, request_text in enumerate(
            requests[: run_config.max_critique_attempts],
            start=1,
        ):
            dispatch(
                "verification",
                {
                    "request": request_text,
                    "facts": facts,
                    "workers": {key: value.model_dump(mode="json") for key, value in worker_payloads.items()},
                },
                attempt=attempt,
            )

    return RuntimeRunResult(
        run_config,
        tuple(payloads),
        tuple(calls),
        anomaly_triggers,
        tuple(telemetry),
        tuple(effective_contexts),
        tuple(tool_call_traces),
    )
