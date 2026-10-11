#!/usr/bin/env python3
"""Evaluation regression gate for narrative verification.

Verifies:
1. Re-verifies every sentence stored in ER-9 runs (both accepted and dropped)
   and ensures no verdict has flipped compared to recorded baselines.
2. Re-runs the full mutation suite and verifies no operator's catch rate has
   regressed below the committed baseline in experiments/mut1/baseline.json.
3. Exits non-zero on any regression or flipped verdict. Completes offline in < 60s.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.er8_score import build_verification_context_for_run, extract_sentences_from_report_spec
from scripts.verifier_mutation import run_mutation_evaluation
from thesis_data.narrative_verification import (
    NarrativeSentence,
    SentenceVerdict,
    verify_sentence,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_regression")


def check_sentence_verdicts(
    runs_dir: Path,
    baseline_path: Path,
) -> tuple[bool, list[str]]:
    """Re-verify every sentence stored in the ER-9 runs against recorded verdicts."""
    failures: list[str] = []
    if not baseline_path.exists():
        return False, [f"Baseline file not found at {baseline_path}"]

    with open(baseline_path, encoding="utf-8") as f:
        baseline_data = json.load(f)

    # Build lookup of recorded verdicts: key = (run_id, sentence_id, is_dropped, text)
    baseline_verdicts: dict[tuple[str, str, bool, str], dict[str, Any]] = {}
    for entry in baseline_data.get("sentence_verdicts", []):
        key = (
            entry.get("run_id", ""),
            entry.get("sentence_id", ""),
            entry.get("is_dropped", False),
            entry.get("text", "").strip(),
        )
        baseline_verdicts[key] = entry

    run_files = sorted(runs_dir.glob("*.json"))
    if not run_files:
        return False, [f"No run files found in {runs_dir}"]

    sentences_checked = 0
    for rf in run_files:
        with open(rf, encoding="utf-8") as f:
            run_data = json.load(f)

        run_id = run_data.get("run_id", rf.stem)
        resp = run_data.get("response") or {}
        facts_data = resp.get("facts") or []
        plan_data = resp.get("analysis_plan") or run_data.get("plan") or {}
        ctx = build_verification_context_for_run(facts_data, plan_data)

        # 1. Accepted sentences
        accepted = extract_sentences_from_report_spec(resp.get("report_spec"))
        for s in accepted:
            sentences_checked += 1
            s_id = s.get("sentence_id", "")
            text = s.get("text", "")
            f_ids = tuple(s.get("fact_ids", ()))
            ns = NarrativeSentence(
                sentence_id=s_id,
                author=s.get("author", "orchestrator"),
                text=text,
                fact_ids=f_ids,
                source=s.get("source", "model"),
                revision=s.get("revision", 0),
            )
            v = verify_sentence(ns, ctx)
            if not v.ok:
                failures.append(
                    f"[{run_id}] Accepted sentence '{s_id}' failed verification: "
                    f"reason_code='{v.reason_code}', reason='{v.reason}'"
                )

            key = (run_id, s_id, False, text.strip())
            if key in baseline_verdicts:
                expected = baseline_verdicts[key]
                if v.ok != expected.get("verdict_ok"):
                    failures.append(
                        f"[{run_id}] Accepted sentence '{s_id}' verdict flipped: "
                        f"current ok={v.ok}, expected ok={expected.get('verdict_ok')}"
                    )

        # 2. Dropped sentences
        audit = resp.get("narrative_audit") or {}
        for d in audit.get("sentences_dropped", []):
            sentences_checked += 1
            d_id = d.get("sentence_id", "")
            text = d.get("text", "")
            f_ids = tuple(d.get("fact_ids", ()))
            rec_code = d.get("reason_code")
            ns_drop = NarrativeSentence(
                sentence_id=d_id,
                author=d.get("author", "orchestrator"),
                text=text,
                fact_ids=f_ids,
                source="dropped",
                revision=0,
            )
            v_drop = verify_sentence(ns_drop, ctx)

            # If dropped by verifier (not semantic critic unresolved_critique), must remain not ok
            if rec_code != "unresolved_critique" and v_drop.ok:
                failures.append(
                    f"[{run_id}] Verifier-dropped sentence '{d_id}' unexpectedly passed verification: "
                    f"recorded reason was '{rec_code}'"
                )

            key = (run_id, d_id, True, text.strip())
            if key in baseline_verdicts:
                expected = baseline_verdicts[key]
                if v_drop.ok != expected.get("verdict_ok"):
                    failures.append(
                        f"[{run_id}] Dropped sentence '{d_id}' verdict flipped: "
                        f"current ok={v_drop.ok}, expected ok={expected.get('verdict_ok')}"
                    )

    logger.info("Sentence verdicts gate: %d sentences checked, %d failures", sentences_checked, len(failures))
    return len(failures) == 0, failures


def check_mutation_catch_rates(
    runs_dir: Path,
    baseline_path: Path,
    seed: int = 42,
) -> tuple[bool, list[str]]:
    """Re-run mutation evaluation and check catch rates against baseline."""
    failures: list[str] = []
    if not baseline_path.exists():
        return False, [f"Baseline file not found at {baseline_path}"]

    with open(baseline_path, encoding="utf-8") as f:
        baseline_data = json.load(f)

    baseline_rates: dict[str, float] = baseline_data.get("operator_catch_rates", {})
    if not baseline_rates:
        return False, ["No operator catch rates found in baseline.json"]

    # Run evaluation in-memory
    current_results = run_mutation_evaluation(runs_dir=runs_dir, seed=seed)
    current_ops = current_results.get("operators", {})

    for op, target_rate in baseline_rates.items():
        if op not in current_ops:
            failures.append(f"Operator '{op}' missing from current mutation evaluation results")
            continue
        current_rate = current_ops[op]["rate"]
        # Allow small floating point tolerance
        if current_rate < target_rate - 1e-4:
            failures.append(
                f"Catch rate regression for operator '{op}': "
                f"current={current_rate:.4f} ({current_ops[op]['caught']}/{current_ops[op]['n']}) "
                f"< baseline={target_rate:.4f}"
            )
        else:
            logger.info("Operator %-20s: %.4f >= baseline %.4f [OK]", op, current_rate, target_rate)

    return len(failures) == 0, failures


def run_eval_regression(
    runs_dir: Path,
    baseline_path: Path,
    seed: int = 42,
) -> int:
    """Run full evaluation regression gate. Returns 0 on success, 1 on failure."""
    start_time = time.time()
    logger.info("Starting eval regression gate (timeout target: < 60s)...")

    # Part 1: Sentence verdicts check
    v_ok, v_failures = check_sentence_verdicts(runs_dir, baseline_path)

    # Part 2: Mutation catch rates check
    m_ok, m_failures = check_mutation_catch_rates(runs_dir, baseline_path, seed=seed)

    elapsed = time.time() - start_time
    logger.info("Eval regression gate finished in %.2f s", elapsed)

    if elapsed > 60.0:
        logger.warning("Execution time exceeded 60s target (took %.2fs)", elapsed)

    if not v_ok or not m_ok:
        print("\n=== EVAL REGRESSION GATE FAILED ===", file=sys.stderr)
        for err in v_failures + m_failures:
            print(f"  [ERROR] {err}", file=sys.stderr)
        return 1

    print(f"\n=== EVAL REGRESSION GATE PASSED (in {elapsed:.2f} s) ===")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation regression gate.")
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=ROOT / "experiments" / "er9" / "runs",
        help="Path to ER-9 runs directory",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "experiments" / "mut1" / "baseline.json",
        help="Path to baseline.json file",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for mutation generator",
    )
    args = parser.parse_args()

    exit_code = run_eval_regression(
        runs_dir=args.runs_dir,
        baseline_path=args.baseline,
        seed=args.seed,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
