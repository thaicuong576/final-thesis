"""Configuration boundary for a future provider-backed agent adapter.

This module describes how a provider may be configured without creating a
provider client or reading a secret.  Network access remains the responsibility
of the caller that explicitly injects an adapter into the guarded runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .experiment_contract import ExperimentRunConfig


class ProviderBoundaryError(ValueError):
    """A provider configuration cannot be used for the selected run."""

    def __init__(self, blockers: tuple[str, ...] | list[str]):
        self.blockers = tuple(blockers)
        super().__init__("provider configuration rejected: " + ", ".join(self.blockers))


class ProviderExecutionConfig(BaseModel):
    """Secret-free settings shared by a future provider adapter.

    ``api_key_env_var`` is only the name of a local environment variable; the
    secret value must never appear in this model or in a committed config file.
    This model intentionally has no client factory and performs no I/O.
    """

    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    source_policy_id: str = Field(min_length=1)
    environment: Literal["offline_fixture", "provider_backed"]
    retrieval_mode: Literal["prefetched", "tool_calling"] = "prefetched"
    max_tool_calls: int = Field(default=8, ge=1, le=32)
    network_access: Literal["disabled", "enabled"] = "disabled"
    api_key_env_var: str | None = None
    endpoint_env_var: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium"
    # GPT-5.6 Luna supports up to 128K output tokens. Keep the boundary in
    # sync with the provider so large, strictly structured composite payloads
    # can be tested without silently truncating the final JSON object.
    max_output_tokens: int = Field(default=4096, ge=1, le=128000)
    max_context_chars: int = Field(default=180000, ge=1000, le=2_000_000)
    timeout_seconds: float = Field(default=60.0, gt=0.0, le=300.0)
    telemetry_required: bool = True

    @field_validator("api_key_env_var", "endpoint_env_var")
    @classmethod
    def validate_env_var_name(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            raise ValueError("environment variable reference must be an uppercase name")
        return value

    @model_validator(mode="after")
    def enforce_network_boundary(self) -> "ProviderExecutionConfig":
        blockers: list[str] = []
        if self.environment == "provider_backed":
            if self.network_access != "enabled":
                blockers.append("provider_network_access_required")
            if self.api_key_env_var is None:
                blockers.append("api_key_env_var_required")
        if self.environment == "offline_fixture" and self.network_access == "enabled":
            blockers.append("offline_network_forbidden")
        if blockers:
            raise ValueError(";".join(blockers))
        return self


def load_provider_config(path: Path) -> ProviderExecutionConfig:
    """Load a secret-free provider config without opening a provider client."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProviderExecutionConfig.model_validate(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderBoundaryError(("provider_config_unreadable",)) from exc
    except ValueError as exc:
        raise ProviderBoundaryError(("provider_config_invalid",)) from exc


def validate_provider_config_for_run(
    provider_config: ProviderExecutionConfig,
    run_config: ExperimentRunConfig,
) -> None:
    """Ensure provider settings cannot silently change the experiment contract."""

    blockers: list[str] = []
    if provider_config.model_id != run_config.model_id:
        blockers.append("model_id_mismatch")
    if provider_config.source_policy_id != run_config.source_policy_id:
        blockers.append("source_policy_id_mismatch")
    if blockers:
        raise ProviderBoundaryError(blockers)
