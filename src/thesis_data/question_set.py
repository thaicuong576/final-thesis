"""Typed, fail-closed contracts for versioned evaluation question sets."""

from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .workload_contract import CompositeWorkloadSpec


PERIOD_PATTERN = r"^\d{4}_Q[1-4]$"
QuestionSetHashMode = Literal[
    "raw_file_bytes_sha256",
    "canonical_lf_utf8_sha256",
]
RAW_FILE_BYTES_HASH_MODE: QuestionSetHashMode = "raw_file_bytes_sha256"
CANONICAL_LF_UTF8_HASH_MODE: QuestionSetHashMode = "canonical_lf_utf8_sha256"


class QuestionType(StrEnum):
    COMPANY_SNAPSHOT = "company_snapshot"
    COMPANY_TREND = "company_trend"
    PEER_COMPARISON = "peer_comparison"
    MACRO_TO_BANK = "macro_to_bank"
    KNOWN_MISSING_OR_CONFLICT = "known_missing_or_conflict"
    ANOMALY_REVIEW = "anomaly_review"
    COMPOSITE_WORKLOAD = "composite_workload"


class QuestionScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuers: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    core_metrics: tuple[str, ...] = Field(min_length=1)
    conditional_metrics: tuple[str, ...] = Field(default_factory=tuple)


class TargetCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer: str = Field(min_length=1)
    period: str = Field(pattern=PERIOD_PATTERN)
    metric: str = Field(min_length=1)


class EvaluationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    issuer: str | None = Field(default=None, min_length=1)
    type: QuestionType
    period: str | None = Field(default=None, pattern=PERIOD_PATTERN)
    periods: tuple[str, ...] = Field(default_factory=tuple)
    peer_set: tuple[str, ...] = Field(default_factory=tuple)
    macro_indicator_ids: tuple[str, ...] = Field(default_factory=tuple)
    bank_metric_ids: tuple[str, ...] = Field(default_factory=tuple)
    causal_claim_policy: str | None = None
    target_cell: TargetCell | None = None
    case_kind: str | None = None
    trigger_ids: tuple[str, ...] = Field(default_factory=tuple)
    workload: CompositeWorkloadSpec | None = None
    prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "EvaluationQuestion":
        if self.type is QuestionType.COMPOSITE_WORKLOAD:
            if self.workload is None:
                raise ValueError("composite_workload requires workload")
            if self.workload.question_id != self.id:
                raise ValueError("workload.question_id must match question id")
            if self.period is not None or self.periods:
                raise ValueError("composite_workload uses periods from workload")
            if self.issuer is not None:
                raise ValueError("composite_workload must not declare a single issuer")
            return self
        if self.issuer is None:
            raise ValueError(f"{self.type.value} requires issuer")
        if self.type is QuestionType.COMPANY_TREND:
            if self.period is not None or len(self.periods) < 2:
                raise ValueError("company_trend requires periods and no period")
        elif self.period is None:
            raise ValueError(f"{self.type.value} requires period")

        if self.type is QuestionType.PEER_COMPARISON:
            if len(self.peer_set) < 2 or self.issuer not in self.peer_set:
                raise ValueError("peer_comparison requires peer_set containing issuer")

        if self.type is QuestionType.MACRO_TO_BANK:
            if not self.macro_indicator_ids:
                raise ValueError("macro_indicator_ids are required for macro_to_bank")
            if not self.bank_metric_ids:
                raise ValueError("bank_metric_ids are required for macro_to_bank")
            if self.causal_claim_policy != "association_only":
                raise ValueError("macro_to_bank requires causal_claim_policy=association_only")

        if self.type is QuestionType.KNOWN_MISSING_OR_CONFLICT:
            if self.target_cell is None:
                raise ValueError("target_cell is required for known_missing_or_conflict")
            if self.case_kind not in {"known_missing", "known_conflict"}:
                raise ValueError("known_missing_or_conflict requires a known_missing or known_conflict case_kind")
            if self.target_cell.issuer != self.issuer or self.target_cell.period != self.period:
                raise ValueError("target_cell must match the question issuer and period")

        if self.type is QuestionType.ANOMALY_REVIEW and not self.trigger_ids:
            raise ValueError("anomaly_review requires trigger_ids")

        return self


class QuestionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    question_set_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    scope: QuestionScope
    questions: list[EvaluationQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope_and_ids(self) -> "QuestionSet":
        question_ids = [question.id for question in self.questions]
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("question IDs must be unique")

        allowed_metrics = set(self.scope.core_metrics) | set(self.scope.conditional_metrics)
        allowed_issuers = set(self.scope.issuers)
        allowed_periods = set(self.scope.periods)
        for question in self.questions:
            if question.type is QuestionType.COMPOSITE_WORKLOAD:
                workload = question.workload
                if workload is None:
                    raise ValueError(f"question {question.id} composite workload is missing")
                if any(issuer not in allowed_issuers for issuer in workload.issuers):
                    raise ValueError(f"question {question.id} workload issuer is outside scope")
                if any(period not in allowed_periods for period in workload.periods):
                    raise ValueError(f"question {question.id} workload period is outside scope")
                if any(issuer not in allowed_issuers for issuer in workload.peer_tickers):
                    raise ValueError(f"question {question.id} workload peer is outside scope")
                if any(metric not in allowed_metrics for metric in workload.metric_ids):
                    raise ValueError(f"question {question.id} workload metric is outside scope")
                continue
            if question.issuer not in allowed_issuers:
                raise ValueError(f"question {question.id} issuer is outside scope")
            if question.period is not None and question.period not in allowed_periods:
                raise ValueError(f"question {question.id} period is outside scope")
            if any(period not in allowed_periods for period in question.periods):
                raise ValueError(f"question {question.id} periods are outside scope")
            if any(issuer not in allowed_issuers for issuer in question.peer_set):
                raise ValueError(f"question {question.id} peer_set is outside scope")
            if any(metric not in allowed_metrics for metric in question.bank_metric_ids):
                raise ValueError(f"question {question.id} bank_metric_ids are outside scope")
            if question.target_cell is not None:
                if question.target_cell.issuer not in allowed_issuers:
                    raise ValueError(f"question {question.id} target_cell issuer is outside scope")
                if question.target_cell.period not in allowed_periods:
                    raise ValueError(f"question {question.id} target_cell period is outside scope")
                if question.target_cell.metric not in allowed_metrics:
                    raise ValueError(f"question {question.id} target_cell metric is outside scope")
        return self


def load_question_set(path: Path) -> QuestionSet:
    """Load and validate a question set without mutating the input file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load question set: {path}") from exc
    try:
        return QuestionSet.model_validate(payload)
    except ValueError as exc:
        raise ValueError(f"invalid question set {path}: {exc}") from exc


def question_set_sha256(
    path: Path,
    *,
    hash_mode: QuestionSetHashMode = RAW_FILE_BYTES_HASH_MODE,
) -> str:
    """Hash a question set using an explicit byte or canonical text mode."""

    content = path.read_bytes()
    if hash_mode == CANONICAL_LF_UTF8_HASH_MODE:
        text = content.decode("utf-8", errors="strict")
        content = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    elif hash_mode != RAW_FILE_BYTES_HASH_MODE:
        raise ValueError(f"unsupported question-set hash mode: {hash_mode}")
    return sha256(content).hexdigest()
