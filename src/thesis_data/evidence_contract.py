"""Minimal generic document contract for pre-extracted evidence."""

from __future__ import annotations

import re
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


DOCUMENT_CONTRACT_VERSION = "document-contract-v1"
_WINDOWS_PATH = re.compile(r"[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"\\\\")
_PRIVATE_UNIX_PATH = re.compile(r"(?:^|\s)/(?:Users|home|mnt|tmp)(?:/|$)", re.IGNORECASE)
_RELATIVE_PATH = re.compile(r"(?:^|\s)[.]{1,2}[\\/]")
_FORBIDDEN_PATH_KEYS = {"local_path", "file_path", "filepath", "path"}


def _contains_local_path(value: Any, *, key: str | None = None) -> bool:
    if key is not None and key.lower() in _FORBIDDEN_PATH_KEYS:
        return True
    if isinstance(value, Mapping):
        return any(
            _contains_local_path(child, key=str(child_key))
            for child_key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_local_path(child) for child in value)
    if isinstance(value, str):
        return any(
            pattern.search(value)
            for pattern in (_WINDOWS_PATH, _UNC_PATH, _PRIVATE_UNIX_PATH, _RELATIVE_PATH)
        )
    return False


class DatasetDocument(BaseModel):
    """Immutable document metadata linked to one canonical dataset snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = DOCUMENT_CONTRACT_VERSION
    document_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_snapshot_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publisher: str | None = Field(default=None, min_length=1)
    content_hash: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_document_contract(self) -> "DatasetDocument":
        if self.contract_version != DOCUMENT_CONTRACT_VERSION:
            raise ValueError("unsupported document contract version")
        if "/" in self.source_ref or "\\" in self.source_ref:
            raise ValueError("document source_ref must be an opaque reference")
        if (
            _contains_local_path(self.title)
            or _contains_local_path(self.publisher)
            or _contains_local_path(self.metadata)
        ):
            raise ValueError("document metadata must not contain local paths")
        return self
