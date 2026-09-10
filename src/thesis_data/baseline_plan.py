"""Deterministic, non-executing plans for the three baseline arms."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .experiment_contract import ExperimentArm
from .question_set import QuestionType, load_question_set, question_set_sha256
from .workload_contract import AnalysisTask, WorkloadTier


class BaselinePlanStatus(StrEnum):
    PLANNED_NOT_EXECUTED = "planned_not_executed"


class BaselineJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    question_id: str = Field(min_length=1)
    arm: ExperimentArm
    issuer: str = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    macro_indicator_ids: tuple[str, ...] = Field(default_factory=tuple)
    comparative_result: Literal[False] = False


class BaselinePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    status: BaselinePlanStatus
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    comparative_result: Literal[False] = False
    jobs: list[BaselineJob] = Field(min_length=1)


class ComplexityPlanStatus(StrEnum):
    PLANNED_NOT_EXECUTED = "planned_not_executed"


class ComplexityJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    question_id: str = Field(min_length=1)
    arm: ExperimentArm
    workload_tier: WorkloadTier
    issuers: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    analysis_tasks: tuple[AnalysisTask, ...] = Field(min_length=1)
    model_id: str = Field(min_length=1)
    max_total_calls: int = Field(ge=1, le=32)
    worker_parallelism: int | None = Field(default=None, ge=1, le=4)
    comparative_result: Literal[False] = False


class ComplexityPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    status: ComplexityPlanStatus
    snapshot_id: str = Field(min_length=1)
    question_set_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_id: str = Field(min_length=1)
    tier_1_reference_question_set_id: str = Field(min_length=1)
    tier_1_reference_plan_path: str = Field(min_length=1)
    total_call_ceilings: dict[str, int] = Field(min_length=1)
    comparative_result: Literal[False] = False
    jobs: list[ComplexityJob] = Field(min_length=1)


def load_complexity_question_set(path: Path):
    """Load a question set that contains only frozen composite workloads."""

    question_set = load_question_set(path)
    if not question_set.questions or any(
        question.type is not QuestionType.COMPOSITE_WORKLOAD
        or question.workload is None
        for question in question_set.questions
    ):
        raise ValueError("complexity question set must contain only composite workloads")
    return question_set


def build_complexity_plan(
    question_set,
    question_set_path: Path,
    arms: tuple[ExperimentArm, ...],
    snapshot_id: str,
    model_id: str,
    *,
    total_call_ceilings: dict[str, int],
    tier_1_reference_question_set_id: str = "pilot-2024-bank-core-qa-v1",
    tier_1_reference_plan_path: str = "experiments/runs/baseline-plan-core-gold-v1.json",
) -> ComplexityPlan:
    """Build a frozen three-arm plan for composite workload scaling."""

    if not arms or len(set(arms)) != len(arms):
        raise ValueError("arms must be non-empty and unique")
    if not snapshot_id or not model_id:
        raise ValueError("snapshot_id and model_id must not be empty")
    digest = question_set_sha256(question_set_path)
    jobs: list[ComplexityJob] = []
    for question in question_set.questions:
        workload = question.workload
        if workload is None:
            raise ValueError(f"question {question.id} has no composite workload")
        tier = workload.tier.value
        ceiling = total_call_ceilings.get(tier)
        if not isinstance(ceiling, int) or ceiling < 1 or ceiling > 32:
            raise ValueError(f"missing or invalid call ceiling for {tier}")
        for arm in arms:
            jobs.append(
                ComplexityJob(
                    job_id=f"{question.id}:{arm.value}",
                    snapshot_id=snapshot_id,
                    question_set_id=question_set.question_set_id,
                    question_set_sha256=digest,
                    question_id=question.id,
                    arm=arm,
                    workload_tier=workload.tier,
                    issuers=workload.issuers,
                    periods=workload.periods,
                    metric_ids=workload.metric_ids,
                    analysis_tasks=workload.analysis_tasks,
                    model_id=model_id,
                    max_total_calls=ceiling,
                    worker_parallelism=2 if arm is not ExperimentArm.SINGLE_AGENT else 1,
                )
            )
    return ComplexityPlan(
        schema_version=1,
        status=ComplexityPlanStatus.PLANNED_NOT_EXECUTED,
        snapshot_id=snapshot_id,
        question_set_id=question_set.question_set_id,
        question_set_sha256=digest,
        model_id=model_id,
        tier_1_reference_question_set_id=tier_1_reference_question_set_id,
        tier_1_reference_plan_path=tier_1_reference_plan_path,
        total_call_ceilings=dict(total_call_ceilings),
        jobs=jobs,
    )


def load_complexity_plan(path: Path) -> ComplexityPlan:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ComplexityPlan.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid complexity plan: {path}") from exc


def audit_complexity_plan(
    plan_path: Path,
    question_set_path: Path,
) -> BaselinePlanAudit:
    """Audit composite job identity, hashes, scope, arms, and budgets."""

    blockers: list[str] = []
    try:
        plan = load_complexity_plan(plan_path)
    except ValueError as exc:
        return BaselinePlanAudit(False, (f"plan_invalid:{exc}",), 0, 0, None, None)
    try:
        question_set = load_complexity_question_set(question_set_path)
    except ValueError as exc:
        return BaselinePlanAudit(
            False,
            (f"question_set_invalid:{exc}",),
            0,
            len(plan.jobs),
            plan.snapshot_id,
            plan.question_set_id,
        )
    actual_hash = question_set_sha256(question_set_path)
    if plan.question_set_sha256 != actual_hash:
        blockers.append("plan_question_set_hash_mismatch")
    if plan.question_set_id != question_set.question_set_id:
        blockers.append("plan_question_set_id_mismatch")
    if any(job.question_set_sha256 != actual_hash for job in plan.jobs):
        blockers.append("job_question_set_hash_mismatch")
    if any(job.model_id != plan.model_id for job in plan.jobs):
        blockers.append("job_model_id_mismatch")

    questions_by_id = {question.id: question for question in question_set.questions}
    expected_ids = {
        f"{question.id}:{arm.value}"
        for question in question_set.questions
        for arm in ExperimentArm
    }
    actual_ids = [job.job_id for job in plan.jobs]
    if len(set(actual_ids)) != len(actual_ids):
        blockers.append("duplicate_job_id")
    blockers.extend(f"missing_job:{job_id}" for job_id in sorted(expected_ids - set(actual_ids)))
    blockers.extend(f"unexpected_job:{job_id}" for job_id in sorted(set(actual_ids) - expected_ids))
    for job in plan.jobs:
        question = questions_by_id.get(job.question_id)
        if question is None or question.workload is None:
            blockers.append(f"job_question_id_invalid:{job.job_id}")
            continue
        workload = question.workload
        if job.arm.value not in {arm.value for arm in ExperimentArm}:
            blockers.append(f"job_arm_invalid:{job.job_id}")
        if job.snapshot_id != plan.snapshot_id:
            blockers.append(f"job_snapshot_id_mismatch:{job.job_id}")
        for field in ("workload_tier", "issuers", "periods", "metric_ids", "analysis_tasks"):
            expected = workload.tier if field == "workload_tier" else getattr(workload, field)
            actual = getattr(job, field)
            if actual != expected:
                blockers.append(f"job_{field}_mismatch:{job.job_id}")
        if job.max_total_calls != plan.total_call_ceilings.get(workload.tier.value):
            blockers.append(f"job_call_ceiling_mismatch:{job.job_id}")
        expected_parallelism = 1 if job.arm is ExperimentArm.SINGLE_AGENT else 2
        if job.worker_parallelism is not None and job.worker_parallelism != expected_parallelism:
            blockers.append(f"job_worker_parallelism_mismatch:{job.job_id}")
    return BaselinePlanAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        question_count=len(question_set.questions),
        job_count=len(plan.jobs),
        snapshot_id=plan.snapshot_id,
        question_set_id=plan.question_set_id,
    )


@dataclass(frozen=True)
class BaselinePlanAudit:
    eligible: bool
    blockers: tuple[str, ...]
    question_count: int
    job_count: int
    snapshot_id: str | None
    question_set_id: str | None


def _job_metrics(question, question_set) -> tuple[str, ...]:
    if question.type is QuestionType.MACRO_TO_BANK:
        return question.bank_metric_ids
    if question.type is QuestionType.KNOWN_MISSING_OR_CONFLICT:
        return (question.target_cell.metric,)
    return question_set.scope.core_metrics


def _job_periods(question) -> tuple[str, ...]:
    if question.type is QuestionType.COMPANY_TREND:
        return question.periods
    return (question.period,)


def build_baseline_plan(
    question_set,
    question_set_path: Path,
    snapshot_id: str,
) -> BaselinePlan:
    """Expand each typed question into one deterministic job per arm.

    This function only plans work. It does not open a database, call an agent,
    promote data, or mark a run as comparative.
    """

    if not snapshot_id:
        raise ValueError("snapshot_id must not be empty")
    digest = question_set_sha256(question_set_path)
    jobs: list[BaselineJob] = []
    for question in question_set.questions:
        periods = _job_periods(question)
        metrics = _job_metrics(question, question_set)
        for arm in ExperimentArm:
            jobs.append(
                BaselineJob(
                    job_id=f"{question.id}:{arm.value}",
                    snapshot_id=snapshot_id,
                    question_set_id=question_set.question_set_id,
                    question_set_sha256=digest,
                    question_id=question.id,
                    arm=arm,
                    issuer=question.issuer,
                    periods=periods,
                    metric_ids=metrics,
                    macro_indicator_ids=question.macro_indicator_ids,
                )
            )
    return BaselinePlan(
        schema_version=1,
        status=BaselinePlanStatus.PLANNED_NOT_EXECUTED,
        snapshot_id=snapshot_id,
        question_set_id=question_set.question_set_id,
        question_set_sha256=digest,
        jobs=jobs,
    )


def build_baseline_plan_from_file(question_set_path: Path, snapshot_id: str) -> BaselinePlan:
    """Load a typed question set and create a deterministic pre-Gold plan."""

    return build_baseline_plan(
        load_question_set(question_set_path),
        question_set_path,
        snapshot_id,
    )


def load_baseline_plan(path: Path) -> BaselinePlan:
    """Load and validate a serialized baseline plan without modifying it."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load baseline plan: {path}") from exc
    try:
        return BaselinePlan.model_validate(payload)
    except ValueError as exc:
        raise ValueError(f"invalid baseline plan {path}: {exc}") from exc


def audit_baseline_plan(
    plan_path: Path,
    question_set_path: Path,
) -> BaselinePlanAudit:
    """Check every serialized plan job against the current typed question set."""

    blockers: list[str] = []
    try:
        plan = load_baseline_plan(plan_path)
    except ValueError as exc:
        return BaselinePlanAudit(
            eligible=False,
            blockers=(f"plan_invalid:{exc}",),
            question_count=0,
            job_count=0,
            snapshot_id=None,
            question_set_id=None,
        )

    try:
        question_set = load_question_set(question_set_path)
    except ValueError as exc:
        return BaselinePlanAudit(
            eligible=False,
            blockers=(f"question_set_invalid:{exc}",),
            question_count=0,
            job_count=len(plan.jobs),
            snapshot_id=plan.snapshot_id,
            question_set_id=plan.question_set_id,
        )

    try:
        actual_hash = question_set_sha256(question_set_path)
    except OSError:
        actual_hash = None
        blockers.append("question_set_hash_unavailable")
    if actual_hash is not None:
        if plan.question_set_sha256 != actual_hash:
            blockers.append("plan_question_set_hash_mismatch")
        if any(job.question_set_sha256 != actual_hash for job in plan.jobs):
            blockers.append("job_question_set_hash_mismatch")

    if plan.question_set_id != question_set.question_set_id:
        blockers.append("plan_question_set_id_mismatch")

    questions_by_id = {question.id: question for question in question_set.questions}
    expected_jobs: dict[str, tuple[object, ExperimentArm]] = {}
    for question in question_set.questions:
        for arm in ExperimentArm:
            expected_jobs[f"{question.id}:{arm.value}"] = (question, arm)

    actual_job_ids = [job.job_id for job in plan.jobs]
    if len(set(actual_job_ids)) != len(actual_job_ids):
        blockers.append("duplicate_job_id")
    expected_ids = set(expected_jobs)
    actual_ids = set(actual_job_ids)
    blockers.extend(
        f"missing_job:{job_id}" for job_id in sorted(expected_ids - actual_ids)
    )
    blockers.extend(
        f"unexpected_job:{job_id}" for job_id in sorted(actual_ids - expected_ids)
    )

    for job in plan.jobs:
        if job.snapshot_id != plan.snapshot_id:
            blockers.append(f"job_snapshot_id_mismatch:{job.job_id}")
        if job.question_set_id != plan.question_set_id:
            blockers.append(f"job_question_set_id_mismatch:{job.job_id}")
        expected = expected_jobs.get(job.job_id)
        if expected is None:
            continue
        question, arm = expected
        if job.arm is not arm:
            blockers.append(f"job_arm_mismatch:{job.job_id}")
        if job.issuer != question.issuer:
            blockers.append(f"job_issuer_mismatch:{job.job_id}")
        expected_periods = _job_periods(question)
        if job.periods != expected_periods:
            blockers.append(f"job_periods_mismatch:{job.job_id}")
        expected_metrics = _job_metrics(question, question_set)
        if job.metric_ids != expected_metrics:
            blockers.append(f"job_metric_ids_mismatch:{job.job_id}")
        if job.macro_indicator_ids != question.macro_indicator_ids:
            blockers.append(f"job_macro_indicator_ids_mismatch:{job.job_id}")

    # Accessing this map also makes the intended question identity explicit in
    # the audit even when a malformed job carries an unknown question ID.
    for job in plan.jobs:
        if job.question_id not in questions_by_id:
            blockers.append(f"job_question_id_not_in_question_set:{job.job_id}")

    return BaselinePlanAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        question_count=len(question_set.questions),
        job_count=len(plan.jobs),
        snapshot_id=plan.snapshot_id,
        question_set_id=plan.question_set_id,
    )
