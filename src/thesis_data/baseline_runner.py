"""Fail-closed execution boundary for one planned baseline job."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Mapping, Sequence

from .agent_runtime import AgentAdapter, RuntimeRunResult, run_agent_arm
from .baseline_plan import BaselineJob
from .experiment_contract import ExperimentRunConfig
from .question_set import QuestionType, load_question_set, question_set_sha256
from .schema import GoldConfig


class BaselineExecutionError(ValueError):
    """A planned job cannot be dispatched without changing its contract."""

    def __init__(self, blockers: Sequence[str]):
        self.blockers = tuple(blockers)
        super().__init__("baseline job rejected: " + ", ".join(self.blockers))


def _expected_metrics(question, question_set) -> tuple[str, ...]:
    if question.type is QuestionType.MACRO_TO_BANK:
        return question.bank_metric_ids
    if question.type is QuestionType.KNOWN_MISSING_OR_CONFLICT:
        return (question.target_cell.metric,)
    return question_set.scope.core_metrics


def _validate_job_contract(
    job: BaselineJob,
    run_config: ExperimentRunConfig,
    question_set_path: Path,
) -> object:
    blockers: list[str] = []
    if job.comparative_result:
        blockers.append("plan_job_marked_comparative")
    if job.snapshot_id != run_config.snapshot_id:
        blockers.append("snapshot_id_mismatch")
    if job.question_set_id != run_config.question_set_id:
        blockers.append("question_set_id_mismatch")
    if job.question_id != run_config.question_id:
        blockers.append("question_id_mismatch")
    if job.arm is not run_config.arm:
        blockers.append("arm_mismatch")
    try:
        actual_hash = question_set_sha256(question_set_path)
    except OSError:
        actual_hash = None
        blockers.append("question_set_hash_unavailable")
    if actual_hash is not None and actual_hash != job.question_set_sha256:
        blockers.append("question_set_hash_mismatch")

    try:
        question_set = load_question_set(question_set_path)
    except ValueError:
        question_set = None
        blockers.append("question_set_schema_invalid")

    question = None
    if question_set is not None:
        question = next(
            (candidate for candidate in question_set.questions if candidate.id == job.question_id),
            None,
        )
        if question is None:
            blockers.append("question_id_not_in_question_set")
        else:
            if question.issuer != job.issuer:
                blockers.append("job_issuer_mismatch")
            expected_periods = (
                question.periods
                if question.type is QuestionType.COMPANY_TREND
                else (question.period,)
            )
            if job.periods != expected_periods:
                blockers.append("job_periods_mismatch")
            expected_metrics = _expected_metrics(question, question_set)
            if job.metric_ids != expected_metrics:
                blockers.append("job_metric_ids_mismatch")
            if job.macro_indicator_ids != question.macro_indicator_ids:
                blockers.append("job_macro_indicator_ids_mismatch")

    if blockers:
        raise BaselineExecutionError(tuple(dict.fromkeys(blockers)))
    return question


def execute_baseline_job(
    db_path: Path,
    job: BaselineJob,
    run_config: ExperimentRunConfig,
    question_set_path: Path,
    gold_config: GoldConfig,
    adapter: AgentAdapter,
    *,
    verification_requests: Sequence[str] = (),
    deviation_thresholds: Mapping[str, float] | None = None,
) -> RuntimeRunResult:
    """Execute exactly one validated plan job through the guarded runtime.

    The caller supplies the adapter explicitly. This function has no provider
    or network behavior; the runtime's Gold and source-policy gates remain the
    authority for whether the database is eligible.
    """

    question = _validate_job_contract(job, run_config, question_set_path)
    # `_validate_job_contract` raises for a missing question, so this is only a
    # type narrowing guard for static checkers and future refactors.
    if question is None:
        raise BaselineExecutionError(("question_id_not_in_question_set",))
    result = run_agent_arm(
        db_path,
        run_config,
        question_set_path,
        gold_config,
        job.issuer,
        job.periods[-1],
        job.metric_ids,
        adapter,
        macro_indicator_ids=job.macro_indicator_ids,
        verification_requests=verification_requests,
        deviation_thresholds=deviation_thresholds,
        question_periods=job.periods,
    )
    return replace(result, job_id=job.job_id)
