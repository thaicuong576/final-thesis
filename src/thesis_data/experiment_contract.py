"""Contracts and fail-closed input checks for comparative experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import sqlite3

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .baseline_gate import audit_baseline_inputs
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
    """Require primary, valid, period-aligned macro facts for macro questions."""

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
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if {"macro_observations", "source_records"} - tables:
            for period in periods:
                for indicator in macro_indicator_ids:
                    blockers.append(f"missing_accepted_macro_observation:{period}:{indicator}")
            return blockers
        for period in periods:
            for indicator in macro_indicator_ids:
                macro_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM macro_observations AS macro
                    JOIN source_records AS source ON source.source_id = macro.source_id
                    WHERE macro.indicator = ?
                      AND macro.period = ?
                      AND macro.quality_status = 'valid'
                      AND macro.value IS NOT NULL
                      AND source.quality_status = 'valid'
                      AND source.source_tier = 'primary'
                    """,
                    (indicator, period),
                ).fetchone()[0]
                if not macro_count:
                    blockers.append(f"missing_accepted_macro_observation:{period}:{indicator}")
    finally:
        connection.close()
    return blockers


def audit_experiment_inputs(
    db_path: Path,
    run_config: ExperimentRunConfig,
    question_set_path: Path,
    gold_config: GoldConfig,
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
        blockers.extend(_macro_question_blockers(db_path, selected_question))

    return ExperimentInputAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        snapshot_id=baseline.snapshot_id,
        question_set_id=question_set_id,
        question_count=question_count,
    )
