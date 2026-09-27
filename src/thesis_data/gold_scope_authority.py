"""Explicit, hash-verified reporting-scope authority for an immutable Gold DB."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SHA256_LENGTH = 64


def canonical_lf_utf8_sha256(path: Path) -> str:
    """Hash tracked UTF-8 text using the repository's canonical line endings."""

    text = path.read_bytes().decode("utf-8", errors="strict")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


class GoldObservationScopeEntry(BaseModel):
    """One exact accepted Gold observation and its reviewed reporting scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1)
    review_target_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    period_basis: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    reporting_scope: Literal["consolidated"]
    review_status: Literal["accepted"]
    checker_ids: tuple[str, ...] = Field(min_length=2)
    checker_scope_confirmations: tuple[str, ...] = Field(min_length=2)
    adjudicator_id: str = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("authority values must be finite")
        return value

    @model_validator(mode="after")
    def validate_reviewers(self) -> "GoldObservationScopeEntry":
        if len(self.checker_ids) != len(set(self.checker_ids)):
            raise ValueError("scope authority requires distinct reviewers")
        if any(not reviewer.strip() for reviewer in self.checker_ids):
            raise ValueError("scope authority reviewer IDs must be non-empty")
        if len(self.checker_scope_confirmations) != len(self.checker_ids):
            raise ValueError("each reviewer must have an explicit scope confirmation")
        if any(scope != self.reporting_scope for scope in self.checker_scope_confirmations):
            raise ValueError("reviewer scope confirmations must match the authority scope")
        return self


class GoldObservationScopeAuthority(BaseModel):
    """Hash-pinned, snapshot-bound scope authority materialized from review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["gold-observation-scope-authority-v1"]
    authority_id: str = Field(min_length=1)
    authority_ref: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    gold_snapshot_sha256: str
    source_review_ledger_ref: str = Field(min_length=1)
    source_review_ledger_raw_file_bytes_sha256: str
    source_authority_manifest_ref: str = Field(min_length=1)
    source_authority_manifest_canonical_lf_utf8_sha256: str
    authority_refs: tuple[str, ...] = Field(min_length=1)
    entries: tuple[GoldObservationScopeEntry, ...] = Field(min_length=1)

    @field_validator(
        "gold_snapshot_sha256",
        "source_review_ledger_raw_file_bytes_sha256",
        "source_authority_manifest_canonical_lf_utf8_sha256",
    )
    @classmethod
    def hashes_must_be_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != _SHA256_LENGTH or any(
            char not in "0123456789abcdef" for char in normalized
        ):
            raise ValueError("authority hash must be a 64-character SHA-256")
        return normalized

    @model_validator(mode="after")
    def validate_unique_observations(self) -> "GoldObservationScopeAuthority":
        observation_ids = [entry.observation_id for entry in self.entries]
        target_ids = [entry.review_target_id for entry in self.entries]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("scope authority observation IDs must be unique")
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("scope authority review target IDs must be unique")
        if len(self.authority_refs) != len(set(self.authority_refs)):
            raise ValueError("scope authority references must be unique")
        required_authority_refs = {
            "docs/DECISIONS.md#D-063",
            "docs/DECISIONS.md#D-072",
        }
        if not required_authority_refs.issubset(self.authority_refs):
            raise ValueError("scope authority must reference Gold decisions D-063 and D-072")
        return self


@dataclass(frozen=True)
class VerifiedGoldObservationScopeAuthority:
    """A sidecar parsed only after its expected canonical hash was checked."""

    authority: GoldObservationScopeAuthority
    canonical_sha256: str

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        expected_canonical_sha256: str,
    ) -> "VerifiedGoldObservationScopeAuthority":
        path = Path(path)
        actual = canonical_lf_utf8_sha256(path)
        expected = expected_canonical_sha256.lower()
        if actual != expected:
            raise ValueError("reporting-scope authority SHA-256 does not match expected value")
        payload = json.loads(path.read_text(encoding="utf-8"))
        authority = GoldObservationScopeAuthority.model_validate(payload)
        if Path(authority.authority_ref).name != path.name:
            raise ValueError("scope authority path does not match its declared artifact ref")
        return cls(authority=authority, canonical_sha256=actual)

    @property
    def authority_ref(self) -> str:
        return self.authority.authority_ref

    @property
    def dataset_id(self) -> str:
        return self.authority.dataset_id

    @property
    def snapshot_id(self) -> str:
        return self.authority.snapshot_id

    @property
    def entries_by_observation_id(self) -> dict[str, GoldObservationScopeEntry]:
        return {entry.observation_id: entry for entry in self.authority.entries}
