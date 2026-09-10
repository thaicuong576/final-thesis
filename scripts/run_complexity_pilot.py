"""Run the frozen composite workload pilot with OpenAI tool calling."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.baseline_gate import audit_baseline_inputs  # noqa: E402
from thesis_data.baseline_plan import audit_complexity_plan, load_complexity_plan  # noqa: E402
from thesis_data.composite_runner import run_composite_arm  # noqa: E402
from thesis_data.composite_transport import OpenAICompositeTransport  # noqa: E402
from thesis_data.comparative_gate import audit_comparative_definition_gate  # noqa: E402
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig  # noqa: E402
from thesis_data.provider_adapter import StructuredCompositeProviderAdapter  # noqa: E402
from thesis_data.provider_config import load_provider_config  # noqa: E402
from thesis_data.question_set import load_question_set  # noqa: E402
from thesis_data.run_manifest import build_composite_run_manifest, write_run_manifest  # noqa: E402
from thesis_data.schema import GoldConfig  # noqa: E402


DEFAULT_ROOT = PROJECT_ROOT
DEFAULT_DB = DEFAULT_ROOT / "data/processed/gold-bank-2025-pilot-v1-adjudated-v2.sqlite"
DEFAULT_PLAN = DEFAULT_ROOT / "experiments/runs/complexity-plan-gold-v1.json"
DEFAULT_QUESTIONS = DEFAULT_ROOT / "experiments/question-set-complexity-v1.json"
DEFAULT_CONFIG = DEFAULT_ROOT / "experiments/config/openai-gpt-5.6-luna.json"
DEFAULT_DOTENV = Path(r"D:\eddie-projects\personal-projects\mis-talent\.env")
DEFAULT_DEFINITION_MANIFEST = DEFAULT_ROOT / "data/manifests/gold-bank-2025-expansion-v3/comparative-definition-gate-v1.json"


def ensure_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError("refusing to overwrite non-empty provider output directory")
    path.mkdir(parents=True, exist_ok=True)


def select_complexity_jobs(plan, *, mode: str, question_id: str | None, arm: str):
    """Select jobs without letting a full-mode retry silently run all arms."""

    selected_jobs = list(plan.jobs)
    if question_id:
        selected_jobs = [job for job in selected_jobs if job.question_id == question_id]
    if mode == "smoke":
        selected_jobs = [job for job in selected_jobs if job.arm.value == arm][:1]
    elif question_id:
        selected_jobs = [job for job in selected_jobs if job.arm.value == arm]
    return selected_jobs


def _load_key(dotenv_path: Path, env_name: str) -> str:
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError("external dotenv file is unreadable") from exc
    prefix = env_name + "="
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or not candidate.startswith(prefix):
            continue
        value = candidate[len(prefix):].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            return value
    raise RuntimeError(f"{env_name} not found in external dotenv file")


def _gold_snapshot(db_path: Path) -> tuple[str, GoldConfig]:
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT snapshot_id, config_json FROM snapshot_metadata WHERE status = 'gold' ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("Gold snapshot metadata not found")
    return str(row[0]), GoldConfig.model_validate(json.loads(row[1]))


def _validate_plan_snapshot(plan_snapshot_id: str, gold_snapshot_id: str) -> None:
    """Reject a plan that is not bound to the selected Gold snapshot."""

    if plan_snapshot_id != gold_snapshot_id:
        raise RuntimeError(
            "Gold preflight failed: plan snapshot_id does not match the selected Gold snapshot "
            f"({plan_snapshot_id} != {gold_snapshot_id})"
        )


def _build_adapter(
    db_path: Path,
    config_path: Path,
    dotenv_path: Path,
    prompt_version: str,
):
    provider_config = load_provider_config(config_path)
    if provider_config.provider_id != "openai" or provider_config.model_id != "gpt-5.6-luna":
        raise RuntimeError("provider config must use exact openai/gpt-5.6-luna target")
    api_key = _load_key(dotenv_path, provider_config.api_key_env_var or "OPENAI_API_KEY")
    os.environ[provider_config.api_key_env_var or "OPENAI_API_KEY"] = api_key
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is not installed") from exc
    client = OpenAI(api_key=api_key, timeout=provider_config.timeout_seconds, max_retries=0)
    transport = OpenAICompositeTransport(client, db_path, provider_config.max_tool_calls)
    adapter = StructuredCompositeProviderAdapter(
        transport,
        provider_config,
        prompt_version=prompt_version,
    )
    return adapter, provider_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--question-id", default=None)
    parser.add_argument("--arm", choices=tuple(arm.value for arm in ExperimentArm), default="single_agent")
    parser.add_argument("--db", type=Path, default=DEFAULT_ROOT / "data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dotenv", type=Path, default=DEFAULT_DOTENV)
    parser.add_argument(
        "--definition-manifest",
        type=Path,
        default=None,
        help="versioned cross-issuer metric-definition manifest; required for the five-issuer scaling plan",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--run-id-prefix", default="complexity-gpt-5.6-luna-v1")
    parser.add_argument("--prompt-version", default="composite-prompt-tool-calling-v3")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    plan = load_complexity_plan(args.plan)
    question_set = load_question_set(args.questions)
    audit = audit_complexity_plan(args.plan, args.questions)
    if not audit.eligible:
        raise RuntimeError("complexity plan preflight failed: " + ",".join(audit.blockers))
    gold_snapshot_id, stored_gold_config = _gold_snapshot(args.db)
    _validate_plan_snapshot(plan.snapshot_id, gold_snapshot_id)
    # Validate the question-set scope against the Gold DB, rather than merely
    # validating the DB against its own metadata. This prevents a structurally
    # valid plan for five issuers from running against a three-issuer snapshot.
    requested_gold = GoldConfig(
        tickers=tuple(question_set.scope.issuers),
        periods=tuple(question_set.scope.periods),
        required_metrics=tuple(question_set.scope.core_metrics),
        min_manual_labels=stored_gold_config.min_manual_labels,
        min_independent_checkers=stored_gold_config.min_independent_checkers,
        min_metric_coverage=stored_gold_config.min_metric_coverage,
    )
    gold_audit = audit_baseline_inputs(args.db, requested_gold)
    if not gold_audit.eligible:
        raise RuntimeError("Gold preflight failed: " + ",".join(gold_audit.blockers))
    definition_manifest = args.definition_manifest
    if definition_manifest is None and "5issuer" in plan.question_set_id:
        definition_manifest = DEFAULT_DEFINITION_MANIFEST
    if definition_manifest is not None:
        definition_audit = audit_comparative_definition_gate(
            args.db, definition_manifest, requested_gold
        )
        if not definition_audit.eligible:
            raise RuntimeError(
                "Comparative definition preflight failed: "
                + ",".join(definition_audit.blockers)
            )
    adapter, provider_config = _build_adapter(
        args.db, args.config, args.dotenv, args.prompt_version
    )

    selected_jobs = select_complexity_jobs(
        plan, mode=args.mode, question_id=args.question_id, arm=args.arm
    )
    if not selected_jobs:
        raise RuntimeError("no complexity jobs selected")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (DEFAULT_ROOT / "experiments/outputs/provider" / f"complexity-gpt-5.6-luna-{timestamp}")
    ensure_output_dir(output_dir)
    questions_by_id = {question.id: question for question in question_set.questions}
    failures: list[dict[str, object]] = []
    manifest_count = 0
    for job in selected_jobs:
        question = questions_by_id[job.question_id]
        workload = question.workload
        if workload is None:
            raise RuntimeError(f"missing workload: {job.question_id}")
        arm = job.arm
        config = ExperimentRunConfig(
            run_id=f"{args.run_id_prefix}:{job.job_id}",
            snapshot_id=job.snapshot_id,
            question_set_id=job.question_set_id,
            question_id=job.question_id,
            rubric_version="rubric-v1",
            prompt_version=args.prompt_version,
            arm=arm,
            model_id=provider_config.model_id,
            source_policy_id=provider_config.source_policy_id,
            max_critique_attempts=2 if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE else 0,
            max_total_calls=job.max_total_calls,
            worker_parallelism=job.worker_parallelism or 1,
            max_context_chars=provider_config.max_context_chars,
        )
        triggers = (
            ("pre_registered_missing_conflict_and_anomaly_check",)
            if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE
            and "missing_conflict" in {task.value for task in workload.analysis_tasks}
            else ()
        )
        result = run_composite_arm(
            workload,
            config,
            adapter,
            question_prompt=question.prompt,
            triggers=triggers,
        )
        manifest = build_composite_run_manifest(
            result,
            question_set_path=args.questions,
            job_id=job.job_id,
            environment="provider_backed",
            comparative_result=False,
        )
        output = output_dir / f"{job.job_id.replace(':', '__')}.json"
        write_run_manifest(manifest, output)
        manifest_count += 1
        if result.failure_status:
            failures.append({
                "job_id": job.job_id,
                "failure_status": result.failure_status,
                "blockers": list(result.failure_blockers),
            })
    (output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"mode": args.mode, "manifest_count": manifest_count, "failure_count": len(failures), "output_dir": str(output_dir)}))
    return 2 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        blockers = getattr(exc, "blockers", None)
        if isinstance(blockers, (tuple, list)):
            print(f"complexity run rejected: {exc.__class__.__name__}: {','.join(str(item) for item in blockers)}", file=sys.stderr)
        else:
            detail = " ".join(str(exc).split())
            suffix = f": {detail}" if detail else ""
            print(f"complexity run rejected: {exc.__class__.__name__}{suffix}", file=sys.stderr)
        raise SystemExit(2)
