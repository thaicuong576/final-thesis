"""Run a smoke job or the Gold-bound provider pilot with OpenAI tool calling."""

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

from thesis_data.baseline_batch_runner import preflight_baseline_plan_inputs
from thesis_data.baseline_plan import load_baseline_plan
from thesis_data.baseline_runner import execute_baseline_job
from thesis_data.openai_transport import OpenAIResponsesTransport
from thesis_data.provider_adapter import StructuredProviderAdapter
from thesis_data.provider_config import load_provider_config
from thesis_data.run_manifest import build_run_manifest, write_run_manifest
from thesis_data.schema import GoldConfig


DEFAULT_ROOT = PROJECT_ROOT
DEFAULT_DB = DEFAULT_ROOT / "data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite"
DEFAULT_PLAN = DEFAULT_ROOT / "experiments/runs/baseline-plan-core-gold-v1.json"
DEFAULT_QUESTIONS = DEFAULT_ROOT / "experiments/question-set-core-v1.json"
DEFAULT_CONFIG = DEFAULT_ROOT / "experiments/config/openai-gpt-5.6-luna.json"
DEFAULT_DOTENV = Path(r"D:\eddie-projects\personal-projects\mis-talent\.env")


def _load_key(dotenv_path: Path, env_name: str) -> str:
    """Read one key without logging the value or any other dotenv contents."""

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


def _gold_config(db_path: Path) -> GoldConfig:
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT config_json FROM snapshot_metadata WHERE status = 'gold' ORDER BY created_at_utc DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("Gold snapshot metadata not found")
    return GoldConfig.model_validate(json.loads(row[0]))


def _build_adapter(db_path: Path, config_path: Path, dotenv_path: Path):
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
    gold = _gold_config(db_path)
    transport = OpenAIResponsesTransport(client, db_path, tuple(gold.tickers), provider_config.max_tool_calls)
    return StructuredProviderAdapter(transport, provider_config), provider_config, gold


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--question-id", default="ACB_snapshot_q4")
    parser.add_argument(
        "--arm",
        choices=("single_agent", "hierarchical_no_critique", "hierarchical_bounded_critique"),
        default="single_agent",
        help="Arm to use in smoke mode; full mode always runs all arms.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dotenv", type=Path, default=DEFAULT_DOTENV)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--resume-dir",
        type=Path,
        default=None,
        help="Resume a prior full run directory and retry only jobs without a manifest.",
    )
    parser.add_argument("--run-id-prefix", default="provider-gpt-5.6-luna-v1")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapter, provider_config, gold = _build_adapter(args.db, args.config, args.dotenv)
    plan = load_baseline_plan(args.plan)
    selected_jobs = [job for job in plan.jobs if job.question_id == args.question_id]
    if not selected_jobs:
        raise RuntimeError(f"question not found in plan: {args.question_id}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.resume_dir or args.output_dir or (
        DEFAULT_ROOT / "experiments/outputs/provider" / f"{args.mode}-gpt-5.6-luna-{timestamp}"
    )
    if args.resume_dir is None and output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("refusing to overwrite non-empty provider output directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "full":
        audit = preflight_baseline_plan_inputs(
            args.db,
            args.plan,
            args.questions,
            gold,
            run_id_prefix=args.run_id_prefix,
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-tool-calling-v1",
            model_id=provider_config.model_id,
            source_policy_id=provider_config.source_policy_id,
            max_critique_attempts=2,
        )
        if not audit.eligible:
            raise RuntimeError("baseline preflight failed: " + ",".join(audit.blockers))
        from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig

        completed_job_ids = set()
        if args.resume_dir is not None and output_dir.exists():
            for existing in output_dir.glob("*.json"):
                if existing.name == "failures.json":
                    continue
                try:
                    existing_payload = json.loads(existing.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(existing_payload, dict) and isinstance(existing_payload.get("job_id"), str):
                    completed_job_ids.add(existing_payload["job_id"])
        manifests = []
        failures = []
        jobs_to_run = [job for job in plan.jobs if job.job_id not in completed_job_ids]
        for job in jobs_to_run:
            run_config = ExperimentRunConfig(
                run_id=f"{args.run_id_prefix}:{job.job_id}",
                snapshot_id=job.snapshot_id,
                question_set_id=job.question_set_id,
                question_id=job.question_id,
                rubric_version="rubric-v1",
                prompt_version="prompt-contract-tool-calling-v1",
                arm=job.arm,
                model_id=provider_config.model_id,
                source_policy_id=provider_config.source_policy_id,
                max_critique_attempts=2 if job.arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE else 0,
            )
            try:
                result = execute_baseline_job(
                    args.db, job, run_config, args.questions, gold, adapter
                )
                manifest = build_run_manifest(
                    result,
                    job.question_id,
                    job.metric_ids,
                    question_set_path=args.questions,
                    environment="provider_backed",
                    comparative_result=False,
                )
                prefix = "retry-" if args.resume_dir is not None else f"{len(manifests) + 1:03d}-"
                output = output_dir / f"{prefix}{job.job_id.replace(':', '__')}.json"
                write_run_manifest(manifest, output)
                manifests.append(manifest)
            except Exception as exc:
                blockers = getattr(exc, "blockers", None)
                failures.append(
                    {
                        "job_id": job.job_id,
                        "error_type": exc.__class__.__name__,
                        "blockers": list(blockers) if isinstance(blockers, (tuple, list)) else [exc.__class__.__name__],
                    }
                )
        (output_dir / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        total_manifest_count = len(completed_job_ids) + len(manifests)
        print(json.dumps({"mode": "full", "manifest_count": total_manifest_count, "failure_count": len(failures), "output_dir": str(output_dir)}))
        return 2 if failures else 0

    job = next((candidate for candidate in selected_jobs if candidate.arm.value == args.arm), selected_jobs[0])
    run_config_model = {
        "run_id": f"{args.run_id_prefix}:smoke:{job.job_id}",
        "snapshot_id": job.snapshot_id,
        "question_set_id": job.question_set_id,
        "question_id": job.question_id,
        "rubric_version": "rubric-v1",
        "prompt_version": "prompt-contract-tool-calling-v1",
        "arm": job.arm.value,
        "model_id": provider_config.model_id,
        "source_policy_id": provider_config.source_policy_id,
        "max_critique_attempts": 2 if job.arm.value == "hierarchical_bounded_critique" else 0,
    }
    from thesis_data.experiment_contract import ExperimentRunConfig

    result = execute_baseline_job(
        args.db,
        job,
        ExperimentRunConfig.model_validate(run_config_model),
        args.questions,
        gold,
        adapter,
    )
    manifest = build_run_manifest(
        result,
        job.question_id,
        job.metric_ids,
        question_set_path=args.questions,
        environment="provider_backed",
        comparative_result=False,
    )
    output = output_dir / "smoke.json"
    write_run_manifest(manifest, output)
    print(json.dumps({"mode": "smoke", "job_id": job.job_id, "manifest": str(output), "call_count": manifest.call_count}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        blockers = getattr(exc, "blockers", None)
        if isinstance(blockers, (tuple, list)):
            print(
                f"provider run rejected: {exc.__class__.__name__}: {','.join(str(item) for item in blockers)}",
                file=sys.stderr,
            )
        else:
            print(f"provider run rejected: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(2)
