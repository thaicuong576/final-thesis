"""Contracts and fail-closed input checks for comparative experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .baseline_gate import audit_baseline_inputs
from .macro_gold import macro_cell_availability
from .schema import GoldConfig
from .question_set import load_question_set


class ExperimentArm(StrEnum):
    SINGLE_AGENT = "single_agent"
    HIERARCHICAL_NO_CRITIQUE = "hierarchical_no_critique"
    HIERARCHICAL_BOUNDED_CRITIQUE = "hierarchical_bounded_critique"


class ExperimentRunConfig(BaseModel):
    """Immutable configuration fields that must be shared across arms."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    arm: ExperimentArm
    model_id: str = Field(min_length=1)
    source_policy_id: str = Field(min_length=1)
    max_critique_attempts: int = Field(default=0, ge=0, le=2)
    max_total_calls: int = Field(default=0, ge=0, le=32)
    worker_parallelism: int = Field(default=1, ge=1, le=4)
    max_context_chars: int = Field(default=180000, ge=1000, le=2_000_000)

    @model_validator(mode="after")
    def enforce_arm_budget(self) -> "ExperimentRunConfig":
        if self.arm is not ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE and self.max_critique_attempts:
            raise ValueError("only hierarchical_bounded_critique may use critique attempts")
        return self


@dataclass(frozen=True)
class ExperimentInputAudit:
    eligible: bool
    blockers: tuple[str, ...]
    snapshot_id: str | None
    question_set_id: str | None
    question_count: int


def _load_question_set(
    path: Path,
) -> tuple[str | None, int, list[str], dict | None, set[str], dict[str, dict]]:
    if not path.exists():
        return None, 0, ["question_set_missing"], None, set(), {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, 0, ["question_set_invalid_json"], None, set(), {}
    schema_blockers: list[str] = []
    try:
        load_question_set(path)
    except ValueError:
        schema_blockers.append("question_set_schema_invalid")
    question_set_id = payload.get("question_set_id")
    questions = payload.get("questions")
    scope = payload.get("scope")
    blockers: list[str] = schema_blockers
    if not isinstance(question_set_id, str) or not question_set_id:
        blockers.append("question_set_id_missing")
        question_set_id = None
    if not isinstance(scope, dict):
        blockers.append("question_scope_missing")
        scope = None
    if not isinstance(questions, list) or not questions:
        blockers.append("question_set_empty")
        return question_set_id, 0, blockers, scope, set(), {}
    question_ids = [item.get("id") for item in questions if isinstance(item, dict)]
    valid_question_ids: set[str] = set()
    question_by_id: dict[str, dict] = {}
    if len(question_ids) != len(questions) or any(not isinstance(value, str) or not value for value in question_ids):
        blockers.append("question_ids_invalid")
    elif len(set(question_ids)) != len(question_ids):
        blockers.append("duplicate_question_ids")
    else:
        valid_question_ids = set(question_ids)
        question_by_id = {item["id"]: item for item in questions}
    return question_set_id, len(questions), blockers, scope, valid_question_ids, question_by_id


def _macro_question_blockers(db_path: Path, question: dict) -> list[str]:
    """Allow accepted valid or accepted missing V2 macro cells.

    Legacy macro rows and pending/fallback/conflicting rows remain blocked.  An
    accepted missing cell is executable input, but its missingness must be
    surfaced by the Macro Agent rather than replaced with a value.
    """

    macro_indicator_ids = question.get("macro_indicator_ids")
    blockers: list[str] = []
    if not isinstance(macro_indicator_ids, list) or not macro_indicator_ids or any(
        not isinstance(indicator, str) or not indicator for indicator in macro_indicator_ids
    ):
        blockers.append("macro_question_indicators_missing")
    periods = question.get("periods")
    if periods is None:
        period = question.get("period")
        periods = [period] if isinstance(period, str) and period else []
    if not isinstance(periods, list) or not periods or any(
        not isinstance(period, str) or not period for period in periods
    ):
        blockers.append("macro_question_periods_missing")
    if (
        not isinstance(macro_indicator_ids, list)
        or not macro_indicator_ids
        or not all(isinstance(indicator, str) and indicator for indicator in macro_indicator_ids)
        or not isinstance(periods, list)
        or not periods
        or not all(isinstance(period, str) and period for period in periods)
    ):
        return blockers

    if not db_path.exists():
        return blockers
    for period in periods:
        for indicator in macro_indicator_ids:
            availability = macro_cell_availability(db_path, indicator, period)
            if availability.status not in {"valid", "missing"}:
                blockers.append(f"missing_accepted_macro_observation:{period}:{indicator}")
                if availability.reason:
                    blockers.append(f"macro_cell_blocked:{period}:{indicator}:{availability.reason}")
    return blockers


def audit_experiment_inputs(
    db_path: Path,
    run_config: ExperimentRunConfig,
    question_set_path: Path,
    gold_config: GoldConfig,
    macro_indicator_ids: tuple[str, ...] | None = None,
) -> ExperimentInputAudit:
    """Validate all inputs before an experiment runner can call an agent arm."""

    baseline = audit_baseline_inputs(db_path, gold_config)
    blockers = list(baseline.blockers)
    if baseline.snapshot_id != run_config.snapshot_id:
        blockers.append("snapshot_id_mismatch")

    (
        question_set_id,
        question_count,
        question_blockers,
        question_scope,
        question_ids,
        question_by_id,
    ) = _load_question_set(question_set_path)
    blockers.extend(question_blockers)
    if question_set_id is not None and question_set_id != run_config.question_set_id:
        blockers.append("question_set_id_mismatch")
    if question_ids and run_config.question_id not in question_ids:
        blockers.append("question_id_not_in_question_set")
    if question_scope is not None:
        expected_scope = {
            "issuers": list(gold_config.tickers),
            "periods": list(gold_config.periods),
            "core_metrics": list(gold_config.required_metrics),
        }
        if any(question_scope.get(key) != value for key, value in expected_scope.items()):
            blockers.append("question_scope_mismatch")

    selected_question = question_by_id.get(run_config.question_id)
    if selected_question and selected_question.get("type") == "macro_to_bank":
        # When the runtime supplies its own macro list, request binding is
        # validated immediately afterwards.  Avoid masking a declared-scope
        # mismatch with a data blocker; direct callers retain the strict gate.
        declared = tuple(selected_question.get("macro_indicator_ids") or ())
        if macro_indicator_ids is None or macro_indicator_ids == declared:
            blockers.extend(_macro_question_blockers(db_path, selected_question))

    return ExperimentInputAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        snapshot_id=baseline.snapshot_id,
        question_set_id=question_set_id,
        question_count=question_count,
    )
