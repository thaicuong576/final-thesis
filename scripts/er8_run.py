#!/usr/bin/env python3
"""ER-8 Evaluation Run Harness: in-process A/B/C execution over hash-bound Gold v5 snapshot.

Arms:
  - single_agent (Arm A): Direct composition from deterministic facts, no specialist findings, no critic.
  - hierarchical_no_critique (Arm B): Query-adaptive specialists + verifier + orchestrator compose, no critic.
  - hierarchical_with_critique (Arm C): Specialists + verifier + orchestrator compose + semantic critic & revision.

Constraints:
  - planner_mode="rules_only" ensures identical frozen plans across all 3 arms for the same task.
  - Plan hashes are recorded and verified equal across arms of the same task.
  - Temporary copy of Gold v5 SQLite is used (never writes to original Gold file).
  - Scope authority sidecar is explicitly configured.
  - Token budget guard stops execution when accumulated input+output tokens exceed --max-tokens.
  - Retries max 2 times only for network errors / rate limits.
  - Errored or blocked runs are preserved in the denominator.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging
import os
import random
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# Pre-load environment variables from .env before importing thesis_api/settings
env_path = ROOT / ".env"
if not env_path.exists():
    root_candidate = ROOT.parent.parent / ".env"
    if root_candidate.exists():
        env_path = root_candidate
if env_path.exists():
    load_dotenv(env_path)

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from thesis_api.schemas import AnalysisRequest, AnalysisResponse
from thesis_api.service import AnalysisEngine
from thesis_api.settings import Settings

logger = logging.getLogger(__name__)

GOLD_RAW_BYTES_SHA256 = "1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73"
GOLD_SNAPSHOT_ID = "gold-bank-2025-expanded-v5-evidence"
GOLD_RELATIVE_CANDIDATES = [
    ROOT / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    ROOT.parents[1] / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    ROOT.parent / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/gold-bank-2025-expanded-v5-evidence.sqlite"),
]

ER9_DATASET_RAW_BYTES_SHA256 = "2a18845feb8dddd83ace39a4ea56fc5d5fbe4a3cb0fcccdfce374a48627f560a"
ER9_DATASET_SNAPSHOT_ID = "snapshot-42a105f6d7978ef00e972dae40d3f4050dba6102e7b33611a60c521b6f2ce54e"
ER9_RELATIVE_CANDIDATES = [
    ROOT / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
    ROOT.parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
    ROOT.parent / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
    Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
]

ARMS = ("single_agent", "hierarchical_no_critique", "hierarchical_with_critique")


def canonical_lf_utf8_sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    text = content.decode("utf-8", errors="strict")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _relpath_str(p: Path) -> str:
    """Return path relative to repo root using POSIX forward slashes, or as_posix() if outside."""
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def verify_dataset_snapshot(
    db_path: Path,
    expected_hash: str | None = None,
    expected_snapshot_id: str | None = None,
) -> None:
    """Verify raw file SHA-256 and internal snapshot ID, raising ValueError on mismatch."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database snapshot not found: {db_path}")

    if expected_hash:
        raw_hash = hashlib.sha256(db_path.read_bytes()).hexdigest().lower()
        if raw_hash != expected_hash.lower():
            raise ValueError(
                f"Supplied dataset SHA-256 mismatch for {db_path}: {raw_hash} != {expected_hash.lower()}"
            )

    if expected_snapshot_id:
        conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
        found_id = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            if "dataset_metadata" in tables:
                cur.execute("SELECT dataset_snapshot_id FROM dataset_metadata LIMIT 1")
                row = cur.fetchone()
                if row:
                    found_id = row[0]
            elif "snapshot_metadata" in tables:
                cur.execute("SELECT snapshot_id FROM snapshot_metadata LIMIT 1")
                row = cur.fetchone()
                if row:
                    found_id = row[0]
        finally:
            conn.close()

        if found_id != expected_snapshot_id:
            raise ValueError(
                f"Supplied dataset snapshot_id mismatch for {db_path}: expected '{expected_snapshot_id}', got '{found_id}'"
            )


def find_dataset_path(
    explicit_path: Path | None = None,
    *,
    candidates: Sequence[Path] = (),
    expected_hash: str | None = None,
    expected_snapshot_id: str | None = None,
    verify_integrity: bool = True,
) -> Path:
    if explicit_path and explicit_path.exists():
        if verify_integrity:
            verify_dataset_snapshot(explicit_path, expected_hash, expected_snapshot_id)
        return explicit_path
    if explicit_path and not explicit_path.exists():
        raise FileNotFoundError(f"Specified dataset path does not exist: {explicit_path}")

    for candidate in candidates:
        if candidate.exists():
            try:
                if verify_integrity:
                    verify_dataset_snapshot(candidate, expected_hash, expected_snapshot_id)
                return candidate
            except (ValueError, FileNotFoundError):
                continue
    raise FileNotFoundError("Could not find verified SQLite database matching expected hash and snapshot ID.")


def find_gold_path(explicit_path: Path | None = None, *, verify_hash: bool = True) -> Path:
    return find_dataset_path(
        explicit_path,
        candidates=GOLD_RELATIVE_CANDIDATES,
        expected_hash=GOLD_RAW_BYTES_SHA256 if verify_hash else None,
        expected_snapshot_id=GOLD_SNAPSHOT_ID if verify_hash else None,
        verify_integrity=verify_hash,
    )


def find_gold_path_or_none(explicit_path: Path | None = None, *, verify_hash: bool = True) -> Path | None:
    try:
        return find_gold_path(explicit_path, verify_hash=verify_hash)
    except (FileNotFoundError, ValueError):
        return None


def check_live_model_preflight(model: str | None = None) -> None:
    """Pre-flight check: send a minimal request to the model before running evaluation.

    If it fails, abort with a clear error message instead of failing all 36 runs.
    """
    settings = Settings()
    if not settings.openai_api_key or not settings.openai_api_key.strip():
        raise SystemExit(
            "ERROR: OPENAI_API_KEY is not set or empty in environment / .env. "
            "Cannot run real model evaluation."
        )
    eff_model = model or settings.openai_model
    logger.info("Running preflight check against model '%s' (base_url=%s)...", eff_model, settings.openai_base_url)
    try:
        from thesis_api.llm import get_llm_client
        client = get_llm_client(settings)
        client.chat.completions.create(
            model=eff_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        logger.info("Preflight check succeeded. Model '%s' is responsive.", eff_model)
    except Exception as exc:
        raise SystemExit(
            f"ERROR: Live model preflight check failed for model '{eff_model}' (base_url={settings.openai_base_url}): {exc}\n"
            f"Aborting evaluation run before starting runs."
        ) from exc


class _DummyChatCompletions:
    def __init__(self, prompt_tokens: int = 350, completion_tokens: int = 90) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def create(self, *args: Any, **kwargs: Any) -> Any:
        from types import SimpleNamespace
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=SimpleNamespace(prompt_tokens=self.prompt_tokens, completion_tokens=self.completion_tokens),
        )


class _DummyClient:
    def __init__(self, prompt_tokens: int = 350, completion_tokens: int = 90) -> None:
        from types import SimpleNamespace
        self.chat = SimpleNamespace(completions=_DummyChatCompletions(prompt_tokens, completion_tokens))


class DryRunOfflineWriter:
    """Offline test double for writer when --dry-run is active."""

    def __init__(self, tracker: Any = None) -> None:
        self.tracker = tracker
        self.client = _DummyClient(prompt_tokens=300, completion_tokens=80)
        self.write_findings_calls: list[dict] = []
        self.compose_report_calls: list[dict] = []
        self.rewrite_sentence_calls: list[dict] = []

    def write_findings(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]] = (),
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]:
        self.write_findings_calls.append(dict(role=role, question=question, question_type=question_type))
        if hasattr(self, "client") and hasattr(self.client, "chat"):
            self.client.chat.completions.create(model="dummy", messages=[])
        elif self.tracker is not None:
            self.tracker.record_call(role=role, latency_ms=15, input_tokens=250, output_tokens=80)

        results = []
        for f in facts[:max_sentences]:
            fid = f.get("fact_id", "")
            mota = f.get("mo_ta") or "Chỉ tiêu"
            hienthi = f.get("hien_thi") or str(f.get("value", ""))
            results.append({
                "text": f"{mota} đạt {hienthi}.",
                "fact_ids": [fid],
            })
        return results

    def compose_report(
        self,
        *,
        question: str,
        question_type: str,
        sentences: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        signals: Sequence[Mapping[str, Any]] | None = None,
        findings: Sequence[Mapping[str, Any]] | None = None,
        facts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.compose_report_calls.append(dict(question=question, question_type=question_type))
        if hasattr(self, "client") and hasattr(self.client, "chat"):
            self.client.chat.completions.create(model="dummy", messages=[])
        elif self.tracker is not None:
            self.tracker.record_call(role="orchestrator", latency_ms=25, input_tokens=400, output_tokens=120)

        if question_type == "lookup":
            val_fid = facts[0]["fact_id"] if facts else "f-1"
            return {
                "kind": "answer_card",
                "blocks": [
                    {
                        "type": "answer",
                        "value_fact_id": val_fid,
                        "sentences": [
                            {"sentence_id": s["sentence_id"]}
                            for s in sentences[:1]
                        ] if sentences else [],
                    }
                ],
            }

        blocks: list[dict[str, Any]] = []
        if sentences:
            blocks.append({
                "type": "headline",
                "sentence": {"sentence_id": sentences[0]["sentence_id"]},
            })
        elif facts:
            f0 = facts[0]
            blocks.append({
                "type": "headline",
                "sentence": {
                    "text": f"{f0.get('mo_ta', 'Chỉ tiêu')} đạt {f0.get('hien_thi', '')}.",
                    "fact_ids": [f0["fact_id"]],
                },
            })

        for idx, ds in enumerate(datasets_summary[:2], start=1):
            chart = ds.get("allowed_charts", ["rank_heatmap"])[0] if ds.get("allowed_charts") else "rank_heatmap"
            fid = facts[0]["fact_id"] if facts else "f-1"
            blocks.append({
                "type": "figure",
                "figure_no": idx,
                "chart": chart,
                "dataset_id": ds["dataset_id"],
                "title": ds["title"],
                "takeaway": {
                    "text": f"{ds['title']} thể hiện dữ liệu phân tích.",
                    "fact_ids": [fid],
                },
            })

        if len(sentences) > 1:
            blocks.append({
                "type": "key_points",
                "items": [
                    {
                        "title": "Nhận định chính",
                        "sentences": [
                            {"sentence_id": s["sentence_id"]}
                            for s in sentences[1:4]
                        ],
                    }
                ],
            })

        if findings:
            fnd = findings[0]
            fid = fnd.get("fact_ids", [facts[0]["fact_id"] if facts else "f-1"])[0]
            blocks.append({
                "type": "callout",
                "tone": "notice",
                "title": fnd.get("text", "Phát hiện liên tầng"),
                "sentences": [
                    {
                        "text": f"{fnd.get('text', 'Phát hiện')} được ghi nhận từ dữ liệu.",
                        "fact_ids": [fid],
                    }
                ],
            })

        return {
            "kind": "note",
            "blocks": blocks,
        }

    def rewrite_sentence(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        self.rewrite_sentence_calls.append(dict(role=role, question=question, sentence=sentence, issue=issue))
        if hasattr(self, "client") and hasattr(self.client, "chat"):
            self.client.chat.completions.create(model="dummy", messages=[])
        elif self.tracker is not None:
            self.tracker.record_call(role=role, latency_ms=15, input_tokens=150, output_tokens=50)
        if facts:
            f = facts[0]
            mota = f.get("mo_ta") or "Chỉ tiêu"
            hienthi = f.get("hien_thi") or str(f.get("value", ""))
            return {
                "text": f"{mota} ghi nhận {hienthi}.",
                "fact_ids": [f["fact_id"]],
            }
        return {
            "text": "Dữ liệu được cập nhật phù hợp.",
            "fact_ids": [],
        }


class DryRunOfflineCritic:
    """Offline test double for critic when --dry-run is active."""

    def __init__(self, tracker: Any = None) -> None:
        self.tracker = tracker
        self.client = _DummyClient(prompt_tokens=450, completion_tokens=90)
        self.calls = 0

    def evaluate(self, *, plan: Any, claims: Sequence[Any], stage1_report: Any, round_context: Any) -> Any:
        from thesis_data.schema import (
            CritiqueAction,
            CritiqueIssue,
            CritiqueIssueStatus,
            CritiqueIssueType,
            CritiqueSeverity,
        )
        from thesis_data.semantic_evaluation import (
            ApplicableLinkResult,
            SemanticDimension,
            SemanticDimensionApplicability,
            SemanticDimensionResult,
            StructuredCriticResult,
            expected_dimension_applicability,
        )

        del stage1_report
        self.calls += 1
        if hasattr(self, "client") and hasattr(self.client, "chat"):
            self.client.chat.completions.create(model="dummy", messages=[])
        elif self.tracker is not None:
            self.tracker.record_call(role="critic", latency_ms=30, input_tokens=450, output_tokens=90)

        claim_ids = tuple(claim.claim_id for claim in claims)
        issues: list[CritiqueIssue] = []

        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(
                SemanticDimensionResult(
                    dimension=dimension,
                    applicability=applicability,
                    score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                    rationale="Dry-run offline critic fixture acceptance.",
                    supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
                )
            )

        return StructuredCriticResult(
            evaluator_version="dryrun-offline-er-critic-v1",
            dimension_scores=tuple(dimensions),
            critique_issues=tuple(issues),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
        )


def _is_network_or_rate_limit_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    patterns = ("ratelimit", "connection", "timeout", "network", "429", "503", "502", "reset", "closed")
    return any(p in name or p in msg for p in patterns)


def _compute_plan_hash(plan: Any) -> str:
    if plan is None:
        return "none"
    d = plan.model_dump(mode="json", exclude_none=True) if hasattr(plan, "model_dump") else dict(plan)
    # known_limitations is appended by the runtime after execution and differs by arm;
    # it is not part of the frozen plan the arms must share.
    d = {k: v for k, v in d.items() if k != "known_limitations"}
    canonical = json.dumps(d, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_DEFAULT = object()


def run_evaluation(
    *,
    dry_run: bool = False,
    reps: int = 1,
    seed: int = 20260930,
    max_tokens: int = 3000000,
    only_tasks: Sequence[str] | None = None,
    gold_path: Path | None = None,
    dataset_path: Path | None = None,
    authority_path: Any = _DEFAULT,
    questions_path: Path | None = None,
    task_specs_path: Path | None = None,
    expected_coverage_path: Path | None = None,
    output_dir: Path | None = None,
    model: str | None = None,
    concurrency: int = 1,
    resume: bool = False,
    expected_raw_sha256: str | None = None,
    expected_snapshot_id: str | None = None,
    run_id_prefix: str = "er8",
    manifest_id: str | None = None,
    arms: Sequence[str] | None = None,
) -> dict[str, Any]:
    effective_dataset = dataset_path or gold_path

    effective_arms = tuple(arms) if arms is not None else ARMS
    for a in effective_arms:
        if a not in ARMS:
            raise ValueError(f"Invalid arm '{a}'. Allowed arms: {ARMS}")

    if run_id_prefix == "er9":
        if output_dir is None:
            output_dir = (ROOT / "experiments" / "er9" / "dry-run") if dry_run else (ROOT / "experiments" / "er9")
        eff_expected_hash = expected_raw_sha256 or ER9_DATASET_RAW_BYTES_SHA256
        eff_expected_snapshot_id = expected_snapshot_id or ER9_DATASET_SNAPSHOT_ID
        verified_dataset = find_dataset_path(
            effective_dataset,
            candidates=ER9_RELATIVE_CANDIDATES,
            expected_hash=eff_expected_hash,
            expected_snapshot_id=eff_expected_snapshot_id,
            verify_integrity=True,
        )
        if authority_path is _DEFAULT:
            authority_path = None
        questions_path = questions_path or (ROOT / "data" / "evaluation" / "er9-questions-v1.jsonl")
        task_specs_path = task_specs_path or (ROOT / "data" / "evaluation" / "er9-task-specs-v1.json")
        if expected_coverage_path is None:
            if "redteam" in str(questions_path):
                rt_cov = ROOT / "data" / "evaluation" / "redteam-expected-coverage-v1.json"
                expected_coverage_path = rt_cov if rt_cov.exists() else None
            else:
                expected_coverage_path = ROOT / "data" / "evaluation" / "er9-expected-coverage-v1.json"
        manifest_id = manifest_id or ("redteam-evaluation-manifest-v1" if "redteam" in str(questions_path) else "er9-evaluation-manifest-v1")
    else:
        if output_dir is None:
            output_dir = (ROOT / "experiments" / "er8" / "dry-run") if dry_run else (ROOT / "experiments" / "er8")
        eff_expected_hash = expected_raw_sha256 or GOLD_RAW_BYTES_SHA256
        eff_expected_snapshot_id = expected_snapshot_id or GOLD_SNAPSHOT_ID
        should_verify = not dry_run or (effective_dataset is None) or (expected_raw_sha256 is not None)
        verified_dataset = find_dataset_path(
            effective_dataset,
            candidates=GOLD_RELATIVE_CANDIDATES,
            expected_hash=eff_expected_hash,
            expected_snapshot_id=eff_expected_snapshot_id,
            verify_integrity=should_verify,
        )
        if authority_path is _DEFAULT:
            authority_path = ROOT / "data" / "evaluation" / "gold-v5-reporting-scope-authority-v1.json"
        questions_path = questions_path or (ROOT / "data" / "evaluation" / "er8-questions-v2.jsonl")
        task_specs_path = task_specs_path or (ROOT / "data" / "evaluation" / "er8-task-specs-v2.json")
        expected_coverage_path = expected_coverage_path or (ROOT / "data" / "evaluation" / "er8-expected-coverage-v2.json")
        manifest_id = manifest_id or "er8-evaluation-manifest-v2"

    output_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    runs_dbs_dir = output_dir / "runs_dbs"
    runs_dbs_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        check_live_model_preflight(model=model)

    # Hashes of input files
    q_content = questions_path.read_bytes()
    specs_content = task_specs_path.read_bytes()
    cov_content = expected_coverage_path.read_bytes() if (expected_coverage_path and expected_coverage_path.exists()) else None
    questions_hash = canonical_lf_utf8_sha256(q_content)
    specs_hash = canonical_lf_utf8_sha256(specs_content)
    cov_hash = canonical_lf_utf8_sha256(cov_content) if cov_content else None

    # Load questions
    all_questions: list[dict[str, str]] = []
    for line in questions_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        all_questions.append(json.loads(line))

    if only_tasks:
        only_set = set(only_tasks)
        all_questions = [q for q in all_questions if q["task_id"] in only_set]

    # Build planned run matrix
    planned_runs = []
    for rep in range(reps):
        for q in all_questions:
            for arm in effective_arms:
                planned_runs.append({
                    "task_id": q["task_id"],
                    "question_text": q["question_text"],
                    "arm": arm,
                    "rep": rep,
                })

    # Shuffle execution order deterministically with seed
    rng = random.Random(seed)
    rng.shuffle(planned_runs)

    # Copy dataset to temporary file
    temp_dir = tempfile.mkdtemp(prefix=f"{run_id_prefix}-db-")
    temp_db = Path(temp_dir) / f"{run_id_prefix}_ro_snapshot.sqlite"
    shutil.copyfile(verified_dataset, temp_db)

    accumulated_tokens = 0
    budget_exceeded = False
    budget_lock = threading.Lock()
    run_records: list[dict[str, Any]] = []

    # If dry-run, install socket guard to forbid any accidental network requests
    if dry_run:
        from tests.socket_guard import install_socket_guard
        install_socket_guard()

    try:
        def execute_single_run(order: int, plan_item: dict[str, Any]) -> dict[str, Any]:
            nonlocal accumulated_tokens, budget_exceeded

            tid = plan_item["task_id"]
            q_text = plan_item["question_text"]
            arm = plan_item["arm"]
            rep = plan_item["rep"]

            run_id = f"{run_id_prefix}-{tid}-{arm}-r{rep}"
            run_file = runs_dir / f"{run_id}.json"

            # Resume check
            if resume and run_file.exists():
                try:
                    existing = json.loads(run_file.read_text(encoding="utf-8"))
                    existing_status = existing.get("status")
                    if existing_status in ("completed", "accepted_with_limitations", "blocked"):
                        logger.info("Resuming run %s: already has status %s", run_id, existing_status)
                        with budget_lock:
                            existing_tokens = (existing.get("tokens") or {}).get("total_tokens", 0)
                            accumulated_tokens += existing_tokens
                            if accumulated_tokens >= max_tokens:
                                budget_exceeded = True
                        return existing
                except Exception as exc:
                    logger.warning("Could not read existing run file %s for resume: %s. Re-running.", run_file, exc)

            with budget_lock:
                if budget_exceeded or accumulated_tokens >= max_tokens:
                    budget_exceeded = True
                    logger.warning("Token budget exceeded (%d >= %d). Aborting run %s.", accumulated_tokens, max_tokens, run_id)
                    aborted_record = {
                        "run_id": run_id,
                        "task_id": tid,
                        "arm": arm,
                        "rep": rep,
                        "order": order,
                        "status": "aborted_budget",
                        "plan": None,
                        "plan_hash": None,
                        "model": model or ("offline-stub" if dry_run else "unconfigured"),
                        "duration_ms": 0,
                        "model_calls": 0,
                        "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "retries": [],
                        "response": None,
                        "trace": [],
                    }
                    run_file.write_text(json.dumps(aborted_record, indent=2, ensure_ascii=False), encoding="utf-8")
                    return aborted_record

            run_db_path = runs_dbs_dir / f"{run_id}.sqlite"
            settings_kwargs: dict[str, Any] = {
                "app_name": f"{run_id_prefix}-evaluation-harness",
                "sqlite_db_path": str(temp_db),
                "analysis_runs_db_path": str(run_db_path),
                "planner_mode": "rules_only",
                "analysis_arm": arm,
            }
            if authority_path:
                settings_kwargs["gold_scope_authority_path"] = str(authority_path)
            if model:
                settings_kwargs["openai_model"] = model
            if dry_run:
                settings_kwargs["openai_api_key"] = "dry-run-key"

            settings = Settings(**settings_kwargs)
            writer_double = DryRunOfflineWriter() if dry_run else None
            critic_double = DryRunOfflineCritic() if dry_run else None

            # Retry loop: max 2 retries (3 attempts total) ONLY for network/rate-limit errors
            max_attempts = 3
            attempt = 0
            retries_info: list[dict[str, Any]] = []
            final_resp: AnalysisResponse | None = None
            final_err: str | None = None
            t_start = time.monotonic()

            while attempt < max_attempts:
                attempt += 1
                try:
                    engine = AnalysisEngine(
                        temp_db,
                        settings,
                        semantic_critic=critic_double,
                        analysis_writer=writer_double,
                    )
                    final_resp = engine.analyze(AnalysisRequest(query=q_text))
                    break
                except Exception as exc:
                    if _is_network_or_rate_limit_error(exc) and attempt < max_attempts:
                        delay = attempt * 2
                        logger.warning("Attempt %d for run %s failed with network/rate limit error: %s. Retrying in %ds...", attempt, run_id, exc, delay)
                        retries_info.append({"attempt": attempt, "error": str(exc), "delay_s": delay})
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Run %s failed with non-retryable error or exhausted retries: %s", run_id, exc)
                        final_err = f"{type(exc).__name__}: {exc}"
                        break

            duration_ms = max(0, int((time.monotonic() - t_start) * 1000))

            # Extract metrics and traces
            if final_resp is not None:
                status = final_resp.status
                plan_obj = final_resp.analysis_plan
                plan_hash = _compute_plan_hash(plan_obj)
                plan_dump = plan_obj.model_dump(mode="json", exclude_none=True) if plan_obj else None

                tracker = getattr(final_resp, "_tracker", None)
                model_calls = tracker.model_calls if tracker else 0
                in_tok = tracker.total_input_tokens if tracker else 0
                out_tok = tracker.total_output_tokens if tracker else 0
                in_tok = in_tok or 0
                out_tok = out_tok or 0
                tot_tok = in_tok + out_tok

                trace_steps = getattr(final_resp, "_trace_steps", []) or []
                trace_dump = [
                    s.model_dump(mode="json", exclude_none=False) if hasattr(s, "model_dump") else s
                    for s in trace_steps
                ]

                resp_dump = final_resp.model_dump(mode="json", exclude_none=False)
            else:
                status = "error"
                plan_dump = None
                plan_hash = "none"
                model_calls = 0
                in_tok = 0
                out_tok = 0
                tot_tok = 0
                trace_dump = []
                resp_dump = {"status": "error", "error": {"code": "execution_failed", "message": final_err or "Unknown execution error"}}

            with budget_lock:
                accumulated_tokens += tot_tok
                if accumulated_tokens >= max_tokens:
                    budget_exceeded = True

            record = {
                "run_id": run_id,
                "task_id": tid,
                "arm": arm,
                "rep": rep,
                "order": order,
                "status": status,
                "plan": plan_dump,
                "plan_hash": plan_hash,
                "model": model or ("offline-stub" if dry_run else getattr(settings, "openai_model", "unknown")),
                "duration_ms": duration_ms,
                "model_calls": model_calls,
                "tokens": {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "total_tokens": tot_tok,
                },
                "retries": retries_info,
                "response": resp_dump,
                "trace": trace_dump,
            }

            run_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            return record

        effective_concurrency = max(1, concurrency)
        if effective_concurrency == 1:
            for order, plan_item in enumerate(planned_runs, start=1):
                rec = execute_single_run(order, plan_item)
                run_records.append(rec)
        else:
            with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
                futures = [
                    executor.submit(execute_single_run, order, plan_item)
                    for order, plan_item in enumerate(planned_runs, start=1)
                ]
                for f in futures:
                    run_records.append(f.result())

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Consolidated runs.sqlite
    runs_sqlite_path = output_dir / "runs.sqlite"
    try:
        from thesis_api.database import ensure_analysis_runs_table
        ensure_analysis_runs_table(runs_sqlite_path)
        conn_all = sqlite3.connect(runs_sqlite_path)
        for single_db in sorted(runs_dbs_dir.glob("*.sqlite")):
            try:
                conn_all.execute(f"ATTACH DATABASE '{single_db.resolve().as_posix()}' AS single_run")
                conn_all.execute("INSERT OR REPLACE INTO analysis_runs SELECT * FROM single_run.analysis_runs")
                conn_all.commit()
                conn_all.execute("DETACH DATABASE single_run")
            except Exception as e:
                logger.warning("Could not merge run db %s: %s", single_db, e)
        conn_all.close()
    except Exception as e:
        logger.warning("Could not build consolidated runs.sqlite: %s", e)

    # Cross-arm plan hash verification
    # For each (task_id, rep), verify plan hashes of the 3 arms are equal
    plan_hash_mismatches = 0
    grouped_runs: dict[tuple[str, int], dict[str, str]] = {}
    for r in run_records:
        if r["status"] != "aborted_budget" and r["plan_hash"] != "none":
            k = (r["task_id"], r["rep"])
            if k not in grouped_runs:
                grouped_runs[k] = {}
            grouped_runs[k][r["arm"]] = r["plan_hash"]

    for (t_id, rep_no), arm_hashes in grouped_runs.items():
        if len(arm_hashes) > 1 and len(set(arm_hashes.values())) > 1:
            plan_hash_mismatches += 1
            logger.error("Plan hash mismatch for task %s rep %d across arms: %s", t_id, rep_no, arm_hashes)
            for r in run_records:
                if r["task_id"] == t_id and r["rep"] == rep_no:
                    r["plan_hash_valid"] = False
        else:
            for r in run_records:
                if r["task_id"] == t_id and r["rep"] == rep_no:
                    r["plan_hash_valid"] = True

    # Build manifest
    completed_runs = sum(1 for r in run_records if r["status"] == "completed")
    error_runs = sum(1 for r in run_records if r["status"] == "error")
    aborted_runs = sum(1 for r in run_records if r["status"] == "aborted_budget")

    manifest = {
        "manifest_id": manifest_id,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": seed,
        "reps": reps,
        "concurrency": effective_concurrency,
        "arms": list(effective_arms),
        "max_tokens_budget": max_tokens,
        "accumulated_tokens": accumulated_tokens,
        "budget_exceeded": budget_exceeded,
        "dry_run": dry_run,
        "model": model or ("offline-stub" if dry_run else (os.environ.get("OPENAI_MODEL") or "unconfigured")),
        "gold_snapshot_bytes_sha256": eff_expected_hash,
        "dataset_snapshot_bytes_sha256": eff_expected_hash,
        "dataset_snapshot_id": eff_expected_snapshot_id,
        "questions_file": _relpath_str(questions_path),
        "questions_canonical_lf_utf8_sha256": questions_hash,
        "task_specs_file": _relpath_str(task_specs_path),
        "task_specs_canonical_lf_utf8_sha256": specs_hash,
        "expected_coverage_file": _relpath_str(expected_coverage_path) if (expected_coverage_path and expected_coverage_path.exists()) else None,
        "expected_coverage_canonical_lf_utf8_sha256": cov_hash,
        "total_planned_runs": len(planned_runs),
        "total_executed_runs": len(run_records),
        "completed_runs": completed_runs,
        "error_runs": error_runs,
        "aborted_budget_runs": aborted_runs,
        "plan_hash_mismatches": plan_hash_mismatches,
        "runs": [
            {
                "run_id": r["run_id"],
                "task_id": r["task_id"],
                "arm": r["arm"],
                "rep": r["rep"],
                "order": r["order"],
                "status": r["status"],
                "plan_hash": r["plan_hash"],
                "plan_hash_valid": r.get("plan_hash_valid", True),
                "duration_ms": r["duration_ms"],
                "model_calls": r["model_calls"],
                "total_tokens": r["tokens"]["total_tokens"],
                "file": f"runs/{r['run_id']}.json",
            }
            for r in run_records
        ],
    }

    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest written to: {manifest_file}")
    print(f"Summary: Planned={len(planned_runs)}, Executed={len(run_records)}, Completed={completed_runs}, Error={error_runs}, Aborted={aborted_runs}")
    print(f"Total tokens: {accumulated_tokens} / {max_tokens} (Budget exceeded: {budget_exceeded})")
    print(f"Plan hash mismatches: {plan_hash_mismatches}")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="ER-8 / ER-9 Evaluation Run Harness")
    parser.add_argument("--dry-run", action="store_true", help="Run offline using mock doubles, no external network")
    parser.add_argument("--reps", type=int, default=1, help="Repetitions per task-arm (default: 1)")
    parser.add_argument("--seed", type=int, default=20260930, help="Random seed for execution order (default: 20260930)")
    parser.add_argument("--max-tokens", type=int, default=3000000, help="Maximum accumulated token budget (default: 3000000)")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated task IDs to run (e.g. T01,T02)")
    parser.add_argument("--gold-path", type=Path, default=None, help="Path to verified Gold SQLite snapshot (deprecated alias for --dataset-path)")
    parser.add_argument("--dataset-path", type=Path, default=None, help="Path to verified SQLite snapshot")
    parser.add_argument("--expected-hash", type=str, default=None, help="Expected raw file SHA-256")
    parser.add_argument("--expected-snapshot-id", type=str, default=None, help="Expected snapshot_id in dataset metadata")
    parser.add_argument("--authority-path", type=Path, default=None, help="Path to scope authority sidecar (None for ER-9)")
    parser.add_argument("--questions", type=Path, default=None, help="Path to questions JSONL file")
    parser.add_argument("--specs", type=Path, default=None, help="Path to task specs JSON file")
    parser.add_argument("--coverage", type=Path, default=None, help="Path to expected coverage JSON file")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--model", type=str, default=None, help="OpenAI model name override")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent workers (default: 1)")
    parser.add_argument("--resume", action="store_true", help="Skip runs whose files already exist with status completed/blocked")
    parser.add_argument("--run-id-prefix", type=str, default=None, help="Run ID prefix (er8 or er9)")
    parser.add_argument("--er9", action="store_true", help="Preset: run ER-9 on the ten-bank quarterly operational snapshot")
    parser.add_argument("--arms", type=str, default=None, help=f"Comma-separated arms to run (default: all three; options: {','.join(ARMS)})")

    args = parser.parse_args()

    only_tasks = [t.strip() for t in args.only.split(",")] if args.only else None
    run_id_prefix = args.run_id_prefix or ("er9" if args.er9 else "er8")
    arms = [a.strip() for a in args.arms.split(",") if a.strip()] if args.arms else None
    if arms:
        for a in arms:
            if a not in ARMS:
                parser.error(f"Invalid arm '{a}'. Allowed arms: {', '.join(ARMS)}")

    run_evaluation(
        dry_run=args.dry_run,
        reps=args.reps,
        seed=args.seed,
        max_tokens=args.max_tokens,
        only_tasks=only_tasks,
        gold_path=args.gold_path,
        dataset_path=args.dataset_path,
        authority_path=args.authority_path if args.authority_path is not None else (_DEFAULT if not args.er9 else None),
        questions_path=args.questions,
        task_specs_path=args.specs,
        expected_coverage_path=args.coverage,
        output_dir=args.output_dir,
        model=args.model,
        concurrency=args.concurrency,
        resume=args.resume,
        expected_raw_sha256=args.expected_hash,
        expected_snapshot_id=args.expected_snapshot_id,
        run_id_prefix=run_id_prefix,
        arms=arms,
    )


if __name__ == "__main__":
    main()
