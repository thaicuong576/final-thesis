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

    def record_call(
        self,
        role: str,
        latency_ms: int,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> None:
        self.calls.append(
            LLMCallRecord(
                role=role,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )

    @property
    def model_calls(self) -> int:
        return len(self.calls)

    @property
    def total_input_tokens(self) -> int | None:
        tokens = [c.input_tokens for c in self.calls if c.input_tokens is not None]
        return sum(tokens) if tokens else None

    @property
    def total_output_tokens(self) -> int | None:
        tokens = [c.output_tokens for c in self.calls if c.output_tokens is not None]
        return sum(tokens) if tokens else None


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
        response = self._target.create(*args, **kwargs)
        duration_ms = max(0, int((time.monotonic() - start) * 1000))
        input_tokens, output_tokens = _extract_usage(response)
        role = self._get_role()
        self._tracker.record_call(
            role=role,
            latency_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return response

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
        response = self._target.create(*args, **kwargs)
        duration_ms = max(0, int((time.monotonic() - start) * 1000))
        input_tokens, output_tokens = _extract_usage(response)
        role = self._get_role()
        self._tracker.record_call(
            role=role,
            latency_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return response

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
