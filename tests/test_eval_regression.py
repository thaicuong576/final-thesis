"""Tests for evaluation regression gate (scripts/eval_regression.py)."""

import json
from pathlib import Path
import time
import pytest

from scripts.eval_regression import (
    check_mutation_catch_rates,
    check_sentence_verdicts,
    run_eval_regression,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "experiments" / "er9" / "runs"
BASELINE_PATH = ROOT / "experiments" / "mut1" / "baseline.json"


def test_eval_regression_passes_on_current_baseline():
    """Verify regression gate passes on committed ER-9 runs and baseline."""
    assert RUNS_DIR.exists()
    assert BASELINE_PATH.exists()
    exit_code = run_eval_regression(RUNS_DIR, BASELINE_PATH, seed=42)
    assert exit_code == 0


def test_eval_regression_execution_time_under_60_seconds():
    """Requirement 4: It must run offline in < 60 s."""
    start = time.time()
    exit_code = run_eval_regression(RUNS_DIR, BASELINE_PATH, seed=42)
    elapsed = time.time() - start
    assert exit_code == 0
    assert elapsed < 60.0, f"Gate took {elapsed:.2f}s, exceeding 60s limit"


def test_gate_fails_when_accepted_verdict_flipped_in_fixture(tmp_path: Path):
    """Requirement 5: the gate fails when a verdict is flipped in a fixture."""
    # Load original baseline and flip one accepted sentence verdict
    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline_data = json.load(f)

    # Find first accepted sentence and flip verdict_ok to False
    flipped = False
    for item in baseline_data.get("sentence_verdicts", []):
        if not item.get("is_dropped"):
            item["verdict_ok"] = False
            flipped = True
            break
    assert flipped, "Expected at least one accepted sentence in baseline"

    bad_baseline = tmp_path / "baseline_flipped.json"
    with open(bad_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    ok, failures = check_sentence_verdicts(RUNS_DIR, bad_baseline)
    assert not ok
    assert len(failures) > 0
    assert any("verdict flipped" in fail for fail in failures)

    exit_code = run_eval_regression(RUNS_DIR, bad_baseline, seed=42)
    assert exit_code != 0


def test_gate_fails_when_dropped_verdict_flipped_in_fixture(tmp_path: Path):
    """Verify gate fails when a verifier-dropped sentence verdict is flipped in fixture."""
    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline_data = json.load(f)

    # Find a verifier-dropped sentence (recorded_audit_reason != 'unresolved_critique')
    flipped = False
    for item in baseline_data.get("sentence_verdicts", []):
        if item.get("is_dropped") and item.get("recorded_audit_reason") != "unresolved_critique":
            item["verdict_ok"] = True  # Flip to ok=True
            flipped = True
            break
    assert flipped, "Expected at least one verifier-dropped sentence in baseline"

    bad_baseline = tmp_path / "baseline_dropped_flipped.json"
    with open(bad_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    ok, failures = check_sentence_verdicts(RUNS_DIR, bad_baseline)
    assert not ok
    assert len(failures) > 0
    assert any("verdict flipped" in fail for fail in failures)


def test_gate_fails_when_catch_rate_falls_below_baseline(tmp_path: Path):
    """Requirement 4: Exit non-zero if any operator's catch rate falls below committed baseline."""
    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline_data = json.load(f)

    # Set impossible catch rate for an operator (e.g. period requires 1.0, current is ~0.83)
    baseline_data["operator_catch_rates"]["period"] = 1.0

    bad_baseline = tmp_path / "baseline_high_target.json"
    with open(bad_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    ok, failures = check_mutation_catch_rates(RUNS_DIR, bad_baseline, seed=42)
    assert not ok
    assert any("Catch rate regression for operator 'period'" in fail for fail in failures)

    exit_code = run_eval_regression(RUNS_DIR, bad_baseline, seed=42)
    assert exit_code != 0
