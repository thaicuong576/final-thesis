"""Bounded CSV staging for the application onboarding boundary.

This module only turns immutable CSV bytes into a deterministic preview.  It
does not infer financial meaning or create canonical observations; explicit
mapping and normalization live in :mod:`onboarding_validation`.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
import re
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from .onboarding_contract import RawDatasetDescriptor, StagedField


_DECIMAL_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
class CsvStagedDataset(BaseModel):
    """Deterministic, in-memory result of parsing one CSV byte sequence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_descriptor: RawDatasetDescriptor
    headers: tuple[str, ...] = Field(min_length=1)
    staged_fields: tuple[StagedField, ...] = Field(min_length=1)
    rows: tuple[tuple[str, ...], ...] = Field(default_factory=tuple)
    row_count: int = Field(ge=0)

    @property
    def raw_rows(self) -> tuple[tuple[str, ...], ...]:
        """Alias making the preserved raw-row payload explicit to callers."""

        return self.rows


def _infer_type(values: tuple[str, ...]) -> str:
    non_empty = tuple(value.strip() for value in values if value.strip())
    if not non_empty:
        return "empty"
    if all(value.isdigit() or (value.startswith(("+", "-")) and value[1:].isdigit()) for value in non_empty):
        return "integer"
    if all(_DECIMAL_PATTERN.fullmatch(value) for value in non_empty):
        return "number"
    return "string"


def _staged_fields(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> tuple[StagedField, ...]:
    result: list[StagedField] = []
    for index, field_name in enumerate(headers):
        values = tuple(row[index] for row in rows)
        samples = tuple(value for value in values if value.strip())[:5]
        result.append(
            StagedField(
                field_name=field_name,
                inferred_data_type=_infer_type(values),
                sample_values=samples,
                null_count=sum(1 for value in values if not value.strip()),
            )
        )
    return tuple(result)


def stage_csv_bytes(
    content: bytes,
    *,
    raw_dataset_id: str,
    original_name: str,
    ingested_at: datetime | None = None,
) -> CsvStagedDataset:
    """Parse UTF-8 CSV bytes into a deterministic staging result.

    The descriptor hash is calculated from the exact bytes supplied by the
    caller.  No path is accepted or persisted as application identity.
    """

    if not isinstance(content, bytes):
        raise TypeError("CSV staging requires source bytes")
    if "/" in raw_dataset_id or "\\" in raw_dataset_id:
        raise ValueError("raw_dataset_id must not contain path separators")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be valid UTF-8") from exc

    descriptor = RawDatasetDescriptor(
        raw_dataset_id=raw_dataset_id,
        source_type="csv",
        original_name=original_name,
        content_hash=sha256(content).hexdigest(),
        ingested_at=ingested_at or datetime.now(timezone.utc),
    )
    reader = csv.reader(StringIO(text, newline=""), strict=True)
    try:
        first_row = next(reader, None)
        if first_row is None or not first_row:
            raise ValueError("CSV header is required")
        headers = tuple(first_row)
        if any(not header.strip() for header in headers):
            raise ValueError("CSV header fields must be non-empty")
        if len(headers) != len(set(headers)):
            raise ValueError("duplicate CSV header fields are not supported")

        rows: list[tuple[str, ...]] = []
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != len(headers):
                raise ValueError("CSV row has a different number of fields than the header")
            rows.append(tuple(row))
    except csv.Error as exc:
        raise ValueError("malformed CSV") from exc

    frozen_rows = tuple(rows)
    staged = CsvStagedDataset(
        raw_descriptor=descriptor,
        headers=headers,
        staged_fields=_staged_fields(headers, frozen_rows),
        rows=frozen_rows,
        row_count=len(frozen_rows),
    )
    return staged
