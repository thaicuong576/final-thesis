"""Execute a validated baseline plan without bypassing input or provenance gates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Mapping, Sequence

from .agent_runtime import AgentAdapter
from .baseline_plan import BaselineJob, BaselinePlan, audit_baseline_plan, load_baseline_plan
from .baseline_runner import BaselineExecutionError, execute_baseline_job
from .experiment_contract import ExperimentArm, ExperimentRunConfig, audit_experiment_inputs
from .provider_config import (
    ProviderBoundaryError,
    ProviderExecutionConfig,
    validate_provider_config_for_run,
)
from .run_manifest import ExperimentRunManifest, build_run_manifest, write_run_manifest
from .schema import GoldConfig


class BaselineBatchExecutionError(ValueError):
    """A complete plan cannot be executed without changing its contract."""

    def __init__(self, blockers: Sequence[str]):
        self.blockers = tuple(blockers)
        super().__init__("baseline plan rejected: " + ", ".join(self.blockers))


@dataclass(frozen=True)
class BaselineBatchResult:
    """The manifests produced by one validated plan execution."""

    output_dir: Path
    manifests: tuple[ExperimentRunManifest, ...]


@dataclass(frozen=True)
class BaselinePlanInputAudit:
    """Read-only result of checking every plan job before adapter dispatch."""

    eligible: bool
    blockers: tuple[str, ...]
    snapshot_id: str | None
    job_count: int


def _manifest_filename(index: int, job: BaselineJob) -> str:
    safe_job_id = job.job_id.replace(":", "__").replace("/", "_").replace("\\", "_")
    return f"{index:03d}-{safe_job_id}.json"


def _run_config_for_job(
    job: BaselineJob,
    *,
    run_id_prefix: str,
    rubric_version: str,
    prompt_version: str,
    model_id: str,
    source_policy_id: str,
    max_critique_attempts: int,
) -> ExperimentRunConfig:
    configured_attempts = (
        max_critique_attempts
        if job.arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE
        else 0
    )
    return ExperimentRunConfig(
        run_id=f"{run_id_prefix}:{job.job_id}",
        snapshot_id=job.snapshot_id,
        question_set_id=job.question_set_id,
        question_id=job.question_id,
        rubric_version=rubric_version,
        prompt_version=prompt_version,
        arm=job.arm,
        model_id=model_id,
        source_policy_id=source_policy_id,
        max_critique_attempts=configured_attempts,
    )


def _preflight_job_inputs(
    db_path: Path,
    plan: BaselinePlan,
    question_set_path: Path,
    gold_config: GoldConfig,
    *,
    run_id_prefix: str,
    rubric_version: str,
    prompt_version: str = "prompt-contract-v1",
    model_id: str,
    source_policy_id: str,
    max_critique_attempts: int,
) -> tuple[str, ...]:
    """Return every job's input blockers before any dispatch."""

    blockers: list[str] = []
    for job in plan.jobs:
        try:
            run_config = _run_config_for_job(
                job,
                run_id_prefix=run_id_prefix,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                model_id=model_id,
                source_policy_id=source_policy_id,
                max_critique_attempts=max_critique_attempts,
            )
            audit = audit_experiment_inputs(
                db_path,
                run_config,
                question_set_path,
                gold_config,
            )
        except ValueError as exc:
            blockers.append(f"job_input_failed:{job.job_id}:{exc}")
            continue
        if not audit.eligible:
            blockers.extend(
                f"job_input_failed:{job.job_id}:{blocker}"
                for blocker in audit.blockers
            )
    return tuple(dict.fromkeys(blockers))


def preflight_baseline_plan_inputs(
    db_path: Path,
    plan_path: Path,
    question_set_path: Path,
    gold_config: GoldConfig,
    *,
    run_id_prefix: str,
    rubric_version: str,
    prompt_version: str = "prompt-contract-v1",
    model_id: str,
    source_policy_id: str,
    max_critique_attempts: int = 2,
) -> BaselinePlanInputAudit:
    """Audit a complete plan and its Gold inputs without calling an adapter."""

    if not run_id_prefix:
        return BaselinePlanInputAudit(False, ("run_id_prefix_missing",), None, 0)
    if plan_path.exists() and not plan_path.is_file():
        return BaselinePlanInputAudit(False, ("plan_not_a_file",), None, 0)
    try:
        plan = load_baseline_plan(plan_path)
    except ValueError as exc:
        return BaselinePlanInputAudit(False, (f"plan_invalid:{exc}",), None, 0)

    structural_audit = audit_baseline_plan(plan_path, question_set_path)
    blockers = list(structural_audit.blockers)
    if plan.snapshot_id == "PENDING_GOLD_SNAPSHOT":
        blockers.append("snapshot_placeholder")
    if not blockers:
        blockers.extend(
            _preflight_job_inputs(
                db_path,
                plan,
                question_set_path,
                gold_config,
                run_id_prefix=run_id_prefix,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                model_id=model_id,
                source_policy_id=source_policy_id,
                max_critique_attempts=max_critique_attempts,
            )
        )
    return BaselinePlanInputAudit(
        eligible=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        snapshot_id=plan.snapshot_id,
        job_count=len(plan.jobs),
    )


def execute_baseline_plan(
    db_path: Path,
    plan_path: Path,
    question_set_path: Path,
    gold_config: GoldConfig,
    adapter: AgentAdapter,
    output_dir: Path,
    *,
    run_id_prefix: str,
    rubric_version: str,
    prompt_version: str = "prompt-contract-v1",
    model_id: str,
    source_policy_id: str,
    max_critique_attempts: int = 2,
    environment: Literal["offline_fixture", "provider_backed"] = "provider_backed",
    provider_config: ProviderExecutionConfig | None = None,
    comparative_result: bool = False,
    verification_requests: Sequence[str] = (),
    deviation_thresholds: Mapping[str, float] | None = None,
    recorded_at_utc: datetime | None = None,
) -> BaselineBatchResult:
    """Execute every job in a preflighted plan and write immutable manifests.

    The function deliberately requires an already promoted snapshot ID and an
    injected adapter. It does not discover providers, fetch data, or substitute
    fallback facts. Each job still passes through the one-job Gold and source
    policy gates before its adapter is called.
    """

    if not run_id_prefix:
        raise BaselineBatchExecutionError(("run_id_prefix_missing",))
    if plan_path.exists() and not plan_path.is_file():
        raise BaselineBatchExecutionError(("plan_not_a_file",))
    try:
        plan = load_baseline_plan(plan_path)
    except ValueError as exc:
        raise BaselineBatchExecutionError((f"plan_invalid:{exc}",)) from exc

    if environment == "offline_fixture" and comparative_result:
        raise BaselineBatchExecutionError(("offline_comparative_result_forbidden",))
    if environment == "provider_backed" and provider_config is None:
        raise BaselineBatchExecutionError(("provider_config_required",))
    if provider_config is not None:
        if provider_config.environment != environment:
            raise BaselineBatchExecutionError(("provider_config_environment_mismatch",))
        provider_blockers: list[str] = []
        for job in plan.jobs:
            run_config = _run_config_for_job(
                job,
                run_id_prefix=run_id_prefix,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                model_id=model_id,
                source_policy_id=source_policy_id,
                max_critique_attempts=max_critique_attempts,
            )
            try:
                validate_provider_config_for_run(provider_config, run_config)
            except ProviderBoundaryError as exc:
                provider_blockers.extend(
                    f"provider_config_failed:{job.job_id}:{blocker}"
                    for blocker in exc.blockers
                )
        if provider_blockers:
            raise BaselineBatchExecutionError(tuple(dict.fromkeys(provider_blockers)))
    if output_dir.exists():
        if not output_dir.is_dir():
            raise BaselineBatchExecutionError(("output_not_a_directory",))
        if any(output_dir.iterdir()):
            raise BaselineBatchExecutionError(("output_directory_not_empty",))

    input_audit = preflight_baseline_plan_inputs(
        db_path,
        plan_path,
        question_set_path,
        gold_config,
        run_id_prefix=run_id_prefix,
        rubric_version=rubric_version,
        prompt_version=prompt_version,
        model_id=model_id,
        source_policy_id=source_policy_id,
        max_critique_attempts=max_critique_attempts,
    )
    if not input_audit.eligible:
        raise BaselineBatchExecutionError(input_audit.blockers)

    manifests: list[ExperimentRunManifest] = []
    for job in plan.jobs:
        try:
            run_config = _run_config_for_job(
                job,
                run_id_prefix=run_id_prefix,
                rubric_version=rubric_version,
                prompt_version=prompt_version,
                model_id=model_id,
                source_policy_id=source_policy_id,
                max_critique_attempts=max_critique_attempts,
            )
            result = execute_baseline_job(
                db_path,
                job,
                run_config,
                question_set_path,
                gold_config,
                adapter,
                verification_requests=verification_requests,
                deviation_thresholds=deviation_thresholds,
            )
            manifests.append(
                build_run_manifest(
                    result,
                    job.question_id,
                    job.metric_ids,
                    question_set_path=question_set_path,
                    environment=environment,
                    comparative_result=comparative_result,
                    recorded_at_utc=recorded_at_utc,
                )
            )
        except BaselineExecutionError as exc:
            raise BaselineBatchExecutionError(
                (f"job_failed:{job.job_id}", *exc.blockers)
            ) from exc
        except ValueError as exc:
            raise BaselineBatchExecutionError(
                (f"job_failed:{job.job_id}:{exc}",)
            ) from exc

    for index, (job, manifest) in enumerate(zip(plan.jobs, manifests), start=1):
        write_run_manifest(manifest, output_dir / _manifest_filename(index, job))

    return BaselineBatchResult(
        output_dir=output_dir.resolve(),
        manifests=tuple(manifests),
    )
