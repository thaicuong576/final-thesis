"""Cost and token usage tracking for LLM client invocations.

Collects real model calls, latency, input tokens, and output tokens from
client response usage metadata without heuristic estimations.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMCallRecord:
    role: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    cost: float | None = None
    is_retry: bool = False
    is_discarded: bool = False


def _extract_cost(response: Any) -> float | None:
    """Provider-reported cost of one call (a non-standard ``usage.cost`` field some
    OpenAI-compatible proxies return). Never estimated; None when absent."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return None
    cost = usage.get("cost") if isinstance(usage, dict) else getattr(usage, "cost", None)
    if cost is None and not isinstance(usage, dict):
        cost = (getattr(usage, "model_extra", None) or {}).get("cost")
    return float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None


def _extract_usage(response: Any) -> tuple[int | None, int | None]:
    """Extract exact token counts from OpenAI client response usage.

    Never estimates missing tokens. Returns None when usage is unavailable.
    """
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return None, None

    input_tokens = None
    output_tokens = None

    if hasattr(usage, "input_tokens"):
        input_tokens = usage.input_tokens
    elif hasattr(usage, "prompt_tokens"):
        input_tokens = usage.prompt_tokens
    elif isinstance(usage, dict):
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))

    if hasattr(usage, "output_tokens"):
        output_tokens = usage.output_tokens
    elif hasattr(usage, "completion_tokens"):
        output_tokens = usage.completion_tokens
    elif isinstance(usage, dict):
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))

    if isinstance(input_tokens, (int, float)):
        input_tokens = int(input_tokens)
    else:
        input_tokens = None

    if isinstance(output_tokens, (int, float)):
        output_tokens = int(output_tokens)
    else:
        output_tokens = None

    return input_tokens, output_tokens


class LLMUsageTracker:
    """Aggregates LLM calls and token counts across all active specialists and orchestrators."""

    def __init__(self) -> None:
        self.calls: list[LLMCallRecord] = []
        self.retries: list[dict[str, Any]] = []

    def record_call(
        self,
        role: str,
        latency_ms: int,
        input_tokens: int | None,
        output_tokens: int | None,
        cost: float | None = None,
        *,
        is_retry: bool = False,
        is_discarded: bool = False,
    ) -> None:
        self.calls.append(
            LLMCallRecord(
                role=role,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                is_retry=is_retry,
                is_discarded=is_discarded,
            )
        )

    def record_retry(
        self,
        *,
        role: str,
        reason: str,
        attempt: int = 1,
    ) -> None:
        self.retries.append({
            "role": role,
            "reason": reason,
            "attempt": attempt,
            "timestamp": time.time(),
        })

    def discard_last_call(self, *, reason: str = "") -> None:
        if self.calls:
            last = self.calls.pop()
            self.calls.append(
                LLMCallRecord(
                    role=last.role,
                    latency_ms=last.latency_ms,
                    input_tokens=last.input_tokens,
                    output_tokens=last.output_tokens,
                    cost=last.cost,
                    is_retry=last.is_retry,
                    is_discarded=True,
                )
            )
            self.record_retry(role=last.role, reason=reason or "discarded_last_call")

    @property
    def model_calls(self) -> int:
        return len([c for c in self.calls if not c.is_discarded])

    @property
    def total_retries(self) -> int:
        return len(self.retries)

    @property
    def total_input_tokens(self) -> int | None:
        tokens = [c.input_tokens for c in self.calls if not c.is_discarded and c.input_tokens is not None]
        return sum(tokens) if tokens else None

    @property
    def total_output_tokens(self) -> int | None:
        tokens = [c.output_tokens for c in self.calls if not c.is_discarded and c.output_tokens is not None]
        return sum(tokens) if tokens else None

    @property
    def total_cost(self) -> float | None:
        costs = [c.cost for c in self.calls if not c.is_discarded and c.cost is not None]
        return sum(costs) if costs else None


class _TrackingCallable:
    def __init__(
        self,
        target_fn: Callable[..., Any],
        tracker: LLMUsageTracker,
        get_role: Callable[[], str],
    ) -> None:
        self._target_fn = target_fn
        self._tracker = tracker
        self._get_role = get_role

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = self._target_fn(*args, **kwargs)
        duration_ms = max(0, int((time.monotonic() - start) * 1000))
        input_tokens, output_tokens = _extract_usage(response)
        role = self._get_role()
        self._tracker.record_call(
            role=role,
            latency_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=_extract_cost(response),
        )
        return response


class _TrackingResponsesNamespace:
    def __init__(
        self,
        responses_target: Any,
        tracker: LLMUsageTracker,
        get_role: Callable[[], str],
    ) -> None:
        self._target = responses_target
        self._tracker = tracker
        self._get_role = get_role

    def create(self, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        is_stream = bool(kwargs.get("stream"))
        response = self._target.create(*args, **kwargs)
        if not is_stream:
            duration_ms = max(0, int((time.monotonic() - start) * 1000))
            input_tokens, output_tokens = _extract_usage(response)
            role = self._get_role()
            self._tracker.record_call(
                role=role,
                latency_ms=duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=_extract_cost(response),
            )
            return response

        role = self._get_role()
        tracker = self._tracker

        def _stream_generator() -> Any:
            completed_resp = None
            try:
                for event in response:
                    if getattr(event, "type", None) == "response.completed":
                        completed_resp = getattr(event, "response", None)
                    yield event
                duration_ms = max(0, int((time.monotonic() - start) * 1000))
                input_tokens, output_tokens = _extract_usage(completed_resp)
                tracker.record_call(
                    role=role,
                    latency_ms=duration_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=_extract_cost(completed_resp),
                )
            except Exception as stream_err:
                tracker.record_retry(
                    role=role,
                    reason=f"stream_failed: {type(stream_err).__name__}",
                )
                raise

        return _stream_generator()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _TrackingChatCompletionsNamespace:
    def __init__(
        self,
        completions_target: Any,
        tracker: LLMUsageTracker,
        get_role: Callable[[], str],
    ) -> None:
        self._target = completions_target
        self._tracker = tracker
        self._get_role = get_role

    def create(self, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        is_stream = bool(kwargs.get("stream"))
        response = self._target.create(*args, **kwargs)
        if not is_stream:
            duration_ms = max(0, int((time.monotonic() - start) * 1000))
            input_tokens, output_tokens = _extract_usage(response)
            role = self._get_role()
            self._tracker.record_call(
                role=role,
                latency_ms=duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=_extract_cost(response),
            )
            return response

        role = self._get_role()
        tracker = self._tracker

        def _stream_generator() -> Any:
            last_chunk = None
            try:
                for chunk in response:
                    last_chunk = chunk
                    yield chunk
                duration_ms = max(0, int((time.monotonic() - start) * 1000))
                input_tokens, output_tokens = _extract_usage(last_chunk)
                tracker.record_call(
                    role=role,
                    latency_ms=duration_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=_extract_cost(last_chunk),
                )
            except Exception as stream_err:
                tracker.record_retry(
                    role=role,
                    reason=f"stream_failed: {type(stream_err).__name__}",
                )
                raise

        return _stream_generator()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _TrackingChatNamespace:
    def __init__(
        self,
        chat_target: Any,
        tracker: LLMUsageTracker,
        get_role: Callable[[], str],
    ) -> None:
        self._target = chat_target
        self._tracker = tracker
        self._get_role = get_role

    @property
    def completions(self) -> _TrackingChatCompletionsNamespace:
        return _TrackingChatCompletionsNamespace(
            self._target.completions,
            self._tracker,
            self._get_role,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class TrackingClient:
    """Transparent proxy around an OpenAI client intercepting create calls for telemetry."""

    def __init__(
        self,
        target_client: Any,
        tracker: LLMUsageTracker,
        *,
        default_role: str = "orchestrator",
        role_getter: Callable[[], str] | None = None,
    ) -> None:
        self._target_client = target_client
        self._tracker = tracker
        self._role_getter = role_getter or (lambda: default_role)

    @property
    def responses(self) -> Any:
        target = getattr(self._target_client, "responses", None)
        if target is not None:
            return _TrackingResponsesNamespace(target, self._tracker, self._role_getter)
        return None

    @property
    def chat(self) -> Any:
        target = getattr(self._target_client, "chat", None)
        if target is not None:
            return _TrackingChatNamespace(target, self._tracker, self._role_getter)
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target_client, name)


def wrap_llm_client(
    client: Any,
    tracker: LLMUsageTracker,
    *,
    default_role: str = "orchestrator",
    role_getter: Callable[[], str] | None = None,
) -> Any:
    """Wrap client with TrackingClient if client is provided and not already wrapped."""
    if client is None:
        return None
    if isinstance(client, TrackingClient):
        return client
    return TrackingClient(
        client,
        tracker,
        default_role=default_role,
        role_getter=role_getter,
    )
