"""Public, secret-safe runtime observability events."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


RUNTIME_EVENT_CONTRACT_VERSION = "runtime-events-v1"


class RuntimeEventType(StrEnum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    AGENT_STARTED = "AGENT_STARTED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    AGENT_OUTPUT_CREATED = "AGENT_OUTPUT_CREATED"
    REVIEW_ISSUE_CREATED = "REVIEW_ISSUE_CREATED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    REVISION_COMPLETED = "REVISION_COMPLETED"
    SYNTHESIS_COMPLETED = "SYNTHESIS_COMPLETED"
    REPORT_ACCEPTED = "REPORT_ACCEPTED"
    RUN_BLOCKED = "RUN_BLOCKED"
    RUN_FAILED = "RUN_FAILED"


_FORBIDDEN_KEYS = {
    "apikey",
    "api_key",
    "password",
    "secret",
    "access_token",
    "api_token",
    "credential",
    "local_path",
    "db_path",
    "file_path",
    "token",
    "chain_of_thought",
    "hidden_reasoning",
    "private_reasoning",
    "reasoning",
    "thoughts",
}
_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"^\\\\")
_UNIX_PRIVATE_PATH = re.compile(r"^(?:/Users/|/home/|/tmp/|/var/|/mnt/)", re.IGNORECASE)
_RELATIVE_LOCAL_PATH = re.compile(
    r"^(?:\.{0,2}[\\/]|(?:data|src|tests|legacy|docs|tmp)[\\/])",
    re.IGNORECASE,
)


def _contains_forbidden_public_data(value: Any, *, key: str | None = None) -> bool:
    if key is not None:
        normalized = key.lower()
        if normalized in _FORBIDDEN_KEYS or any(
            marker in normalized
            for marker in ("chain_of_thought", "hidden_reasoning", "private_reasoning")
        ):
            return True
    if isinstance(value, Mapping):
        return any(
            _contains_forbidden_public_data(child, key=str(child_key))
            for child_key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_public_data(child) for child in value)
    if isinstance(value, str):
        return bool(
            _WINDOWS_PATH.match(value)
            or _UNC_PATH.match(value)
            or _UNIX_PRIVATE_PATH.match(value)
            or _RELATIVE_LOCAL_PATH.match(value)
        )
    return False


class RuntimeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = RUNTIME_EVENT_CONTRACT_VERSION
    event_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: RuntimeEventType
    actor: str = Field(min_length=1)
    task_id: str | None = Field(default=None, min_length=1)
    artifact_refs: tuple[str, ...] = Field(default_factory=tuple)
    summary: str | None = None
    public_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_public_boundary(self) -> "RuntimeEvent":
        if self.contract_version != RUNTIME_EVENT_CONTRACT_VERSION:
            raise ValueError("unsupported runtime event contract version")
        if any(_contains_forbidden_public_data(value) for value in self.artifact_refs):
            raise ValueError("artifact_refs must not contain local paths or secrets")
        if self.summary is not None and _contains_forbidden_public_data(self.summary):
            raise ValueError("summary must not contain local paths or private reasoning")
        if _contains_forbidden_public_data(self.public_payload):
            raise ValueError("public_payload contains private reasoning, secret, or local path")
        return self


@runtime_checkable
class RuntimeEventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None:
        ...


class InMemoryRuntimeEventRecorder:
    """Deterministic test sink that enforces contiguous event sequence."""

    def __init__(self, run_id: str) -> None:
        if not run_id.strip():
            raise ValueError("run_id must be non-empty")
        self.run_id = run_id
        self._events: list[RuntimeEvent] = []

    def emit(self, event: RuntimeEvent) -> None:
        if event.run_id != self.run_id:
            raise ValueError("event run_id does not match recorder")
        expected_sequence = len(self._events) + 1
        if event.sequence != expected_sequence:
            raise ValueError("runtime event sequence must be contiguous")
        self._events.append(event)

    @property
    def events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)
