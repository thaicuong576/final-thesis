#!/usr/bin/env python3
"""Deterministic scoring for ER-8 evaluation runs.

Calculates deterministic evaluation metrics per PR-8 §5 from run files:
  1. Completion (answered: status 'completed' or 'accepted_with_limitations'; clean_completion counts only 'completed'; R1/R2 succeed by rejection).
  2. Numeric correctness (all numbers in final sentences match cited facts; facts match Gold v5).
     Uses thesis_data.narrative_verification.verify_sentence for exact grounding and tolerance.
  3. Observation traceability (input_observation_ids resolve to Gold v5 locators).
  4. Coverage (required cells in expected-coverage covered by facts or declared missing).
  5. Missingness handling (T03 and ACB Q1 in T08 properly handle missing data, no fabricated numbers).
  6. Correct rejection (R1 and R2 rejected before model execution with expected error codes).
  7. Sentence quality (discard rate from narrative verifier, count of accepted sentences).
  8. Cross-level findings (count of cross-level insights in report).
  9. Latency, model calls, token costs, revision rounds.

Outputs:
  experiments/er8/scores/deterministic.csv (or dry-run/scores/deterministic.csv)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.er8_run import find_gold_path, find_gold_path_or_none
from thesis_api.metric_presentation import METRIC_PRESENTATIONS
from thesis_data.narrative_verification import (
    NarrativeSentence,
    SentenceVerdict,
    VerificationContext,
    verify_sentence,
)
from thesis_data.report_facts import Fact

logger = logging.getLogger(__name__)


def load_dataset_observations(db_path: Path) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]

    if "observations" in tables:
        c.execute(
            "SELECT observation_id, entity_id, period_id, metric_id, value, unit, validation_status, source_ref, source_locator "
            "FROM observations"
        )
    elif "metric_observations" in tables:
        c.execute(
            "SELECT observation_id, ticker, period, metric, value, unit, quality_status, source_id, source_locator "
            "FROM metric_observations"
        )
    else:
        conn.close()
        return {}

    rows = c.fetchall()
    conn.close()

    result = {}
    for r in rows:
        result[r[0]] = {
            "observation_id": r[0],
            "ticker": r[1],
            "period": r[2],
            "metric": r[3],
            "value": r[4],
            "unit": r[5],
            "quality_status": r[6],
            "source_id": r[7],
            "source_locator": r[8],
        }
    return result


def load_gold_observations(gold_path: Path) -> dict[str, dict[str, Any]]:
    return load_dataset_observations(gold_path)


def matches_number(num: float, candidates: Sequence[float], tol: float = 0.05) -> bool:
    """Check if number matches any candidate value within tolerance."""
    for c in candidates:
        if c is None:
            continue
        # Check absolute tolerance
        if abs(num - c) <= tol:
            return True
        # Check percentage/decimal scaling (e.g. 0.015 vs 1.5)
        if abs(num - (c * 100.0)) <= tol or abs((num * 100.0) - c) <= tol:
            return True
    return False


def extract_sentences_from_report_spec(report_spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract all text sentences and their cited fact_ids from a ReportSpec dictionary."""
    if not report_spec or not isinstance(report_spec, dict):
        return []
    sentences = []
    blocks = report_spec.get("blocks", [])
    for blk in blocks:
        if not isinstance(blk, dict):
            continue
        b_type = blk.get("type")
        if b_type == "headline":
            s = blk.get("sentence")
            if s and isinstance(s, dict):
                sentences.append(s)
        elif b_type == "answer":
            for s in blk.get("sentences", []):
                if isinstance(s, dict):
                    sentences.append(s)
        elif b_type == "figure":
            t = blk.get("takeaway")
            if t and isinstance(t, dict):
                sentences.append(t)
        elif b_type == "key_points":
            for item in blk.get("items", []):
                if isinstance(item, dict):
                    for s in item.get("sentences", []):
                        if isinstance(s, dict):
                            sentences.append(s)
        elif b_type == "callout":
            for s in blk.get("sentences", []):
                if isinstance(s, dict):
                    sentences.append(s)
        elif b_type == "section":
            for s in blk.get("sentences", []):
                if isinstance(s, dict):
                    sentences.append(s)
    return sentences


def build_verification_context_for_run(
    facts_data: Sequence[dict[str, Any]],
    plan_data: dict[str, Any] | None,
) -> VerificationContext:
    facts_map: dict[str, Fact] = {}
    for f in facts_data:
        fid = f.get("fact_id")
        if fid:
            facts_map[fid] = Fact(**f)

    plan_entities_set: set[str] = set()
    anchor_year = 2024
    if plan_data and isinstance(plan_data, dict):
        scope = plan_data.get("scope") or {}
        for ent in scope.get("entities", []):
            plan_entities_set.add(ent)
        periods = scope.get("periods", [])
        if periods:
            m = re.search(r"\b(20\d{2})\b", periods[-1])
            if m:
                anchor_year = int(m.group(1))

    # Also include any entity cited in facts
    for f in facts_data:
        ent = f.get("entity_id")
        if ent:
            plan_entities_set.add(ent)
        other_ent = f.get("other_entity_id")
        if other_ent:
            plan_entities_set.add(other_ent)

    catalog_entities_set = set(plan_entities_set)
    catalog_entities_set.update([
        "VCB", "CTG", "BID", "TCB", "MBB", "VPB", "HDB", "ACB",
        "STB", "TPB", "VIB", "LPB", "SHB", "MSB", "SSB", "OCB", "EIB",
    ])

    metric_terms: dict[str, tuple[str, ...]] = {}
    hi_words: dict[str, tuple[str, ...]] = {}
    lo_words: dict[str, tuple[str, ...]] = {}
    directions: dict[str, str] = {}
    flat_pp: dict[str, float] = {}

    for mid, pres in METRIC_PRESENTATIONS.items():
        terms = [pres.label, pres.short_label, mid.rsplit(".", 1)[-1]]
        if pres.synonyms:
            terms.extend(pres.synonyms)
        metric_terms[mid] = tuple(dict.fromkeys(t for t in terms if t))
        if pres.superlative_hi:
            hi_words[mid] = tuple(pres.superlative_hi)
        if pres.superlative_lo:
            lo_words[mid] = tuple(pres.superlative_lo)
        directions[mid] = pres.direction
        flat_pp[mid] = pres.flat_threshold_pp

    return VerificationContext(
        facts=facts_map,
        plan_entities=frozenset(plan_entities_set),
        catalog_entities=frozenset(catalog_entities_set),
        metric_terms=metric_terms,
        hi_words=hi_words,
        lo_words=lo_words,
        directions=directions,
        flat_pp=flat_pp,
        anchor_year=anchor_year,
    )


def score_single_run(
    run_data: dict[str, Any],
    expected_coverage_map: dict[str, Any],
    gold_observations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    run_id = run_data["run_id"]
    task_id = run_data["task_id"]
    arm = run_data["arm"]
    rep = run_data.get("rep", 0)
    order = run_data.get("order", 0)
    status = run_data.get("status", "unknown")
    plan_hash = run_data.get("plan_hash", "none")
    plan_hash_valid = run_data.get("plan_hash_valid", True)
    duration_ms = run_data.get("duration_ms", 0)
    model_calls = run_data.get("model_calls", 0)
    tokens = run_data.get("tokens", {})
    in_tokens = tokens.get("input_tokens", 0)
    out_tokens = tokens.get("output_tokens", 0)
    total_tokens = tokens.get("total_tokens", 0)

    exp_task = expected_coverage_map.get(task_id, {}).get("expected_coverage", {})
    is_rejection_expected = exp_task.get("is_rejection", False)
    expected_error_code = exp_task.get("expected_error_code")

    response = run_data.get("response") or {}
    resp_status = response.get("status", status)
    error_info = response.get("error") or {}
    err_code = error_info.get("code") or ""
    err_msg = error_info.get("message") or ""
    limitations = response.get("limitations") or []

    # 1. Completion & Protocol Success
    # "completed" = the run produced an answered report (clean or with stated limitations);
    # "clean_completion" = the runtime accepted it without any limitation.
    answered_statuses = ("completed", "accepted_with_limitations")
    completed = 1 if status in answered_statuses and resp_status in answered_statuses else 0
    clean_completion = 1 if status == "completed" and resp_status == "completed" else 0
    if is_rejection_expected:
        # Success means properly rejected with expected error code
        code_matched = (
            err_code == expected_error_code
            or any(expected_error_code in lim for lim in limitations)
            or expected_error_code in err_msg
        )
        protocol_success = 1 if code_matched else 0
        correct_rejection = 1 if code_matched else 0
    else:
        protocol_success = 1 if completed == 1 else 0
        correct_rejection = None

    # Facts & Observations
    facts = response.get("facts") or []

    # Traceability
    all_cited_obs_ids = set()
    for f in facts:
        for obs_id in f.get("input_observation_ids", []):
            all_cited_obs_ids.add(obs_id)

    obs_cited_count = len(all_cited_obs_ids)
    obs_resolved_count = 0
    if gold_observations:
        for obs_id in all_cited_obs_ids:
            if obs_id in gold_observations:
                gold_rec = gold_observations[obs_id]
                # Valid locator check
                if gold_rec.get("source_locator"):
                    obs_resolved_count += 1
                elif gold_rec.get("quality_status") == "missing":
                    obs_resolved_count += 1
    else:
        obs_resolved_count = sum(1 for oid in all_cited_obs_ids if ":" in oid or len(oid) > 5)

    traceability_score = (obs_resolved_count / obs_cited_count) if obs_cited_count > 0 else (1.0 if completed or is_rejection_expected else 0.0)

    # Facts accuracy against Gold v5
    facts_accuracy_ok = True
    if gold_observations:
        for f in facts:
            f_val = f.get("value")
            f_obs_ids = f.get("input_observation_ids", [])
            if f_val is not None and len(f_obs_ids) == 1:
                g_obs = gold_observations.get(f_obs_ids[0])
                if g_obs and g_obs.get("value") is not None:
                    g_val = g_obs["value"]
                    if not matches_number(float(f_val), [float(g_val)], tol=0.01):
                        facts_accuracy_ok = False
                        break

    # Sentence-level numbers verification using thesis_data.narrative_verification
    report_spec = response.get("report_spec")
    sentences = extract_sentences_from_report_spec(report_spec)
    numbers_checked = 0
    numbers_matched = 0

    plan_obj = run_data.get("plan")
    ctx = build_verification_context_for_run(facts, plan_obj)

    sents_accepted_count = 0
    sents_discarded_count = 0

    for s_idx, sent in enumerate(sentences, start=1):
        s_id = sent.get("sentence_id") or f"sent-{s_idx}"
        ns = NarrativeSentence(
            sentence_id=s_id,
            author=sent.get("author", "system"),
            text=sent.get("text", ""),
            fact_ids=tuple(sent.get("fact_ids", ())),
            source=sent.get("source", "report"),
        )
        verdict = verify_sentence(ns, ctx)
        if verdict.ok:
            sents_accepted_count += 1
        else:
            sents_discarded_count += 1

        numbers_checked += verdict.numbers_checked
        numbers_matched += verdict.numbers_matched

    if numbers_checked > 0:
        numeric_correctness = (numbers_matched / numbers_checked) if facts_accuracy_ok else 0.0
    else:
        numeric_correctness = 1.0 if (completed and facts_accuracy_ok) else (1.0 if is_rejection_expected else 0.0)

    # Coverage
    required_obs_ids = set(exp_task.get("required_observation_ids", []))
    required_obs_count = len(required_obs_ids)
    covered_obs_count = 0

    if required_obs_count > 0:
        for obs_id in required_obs_ids:
            if obs_id in all_cited_obs_ids:
                covered_obs_count += 1
            else:
                g_meta = gold_observations.get(obs_id) if gold_observations else None
                if g_meta:
                    ent = g_meta["ticker"]
                    p = g_meta["period"]
                    m = g_meta["metric"]
                    for f in facts:
                        if f.get("entity_id") == ent and f.get("period") == p and f.get("metric_id") == m:
                            covered_obs_count += 1
                            break
        coverage_score = covered_obs_count / required_obs_count
    else:
        coverage_score = 1.0 if (completed or is_rejection_expected) else 0.0

    # Missingness handling: driven by expected-coverage file (not hardcoded task IDs)
    missingness_handled = None
    missing_count = exp_task.get("missing_count", 0)
    missing_obs_ids = set(exp_task.get("missing_observation_ids", []))

    if missing_count > 0:
        fabricated = [
            f for f in facts
            if any(oid in missing_obs_ids for oid in f.get("input_observation_ids", []))
            and f.get("value") is not None
        ]
        has_limitation = (
            any("thiếu" in lim.lower() or "unavailable" in lim.lower() or "missing" in lim.lower() or "acb" in lim.lower() for lim in limitations)
            or any("thiếu" in s.get("text", "").lower() or "missing" in s.get("text", "").lower() for s in sentences)
            or completed
        )
        missingness_handled = 1 if (len(fabricated) == 0 and has_limitation) else 0
    else:
        # No missing cells: reported as not applicable (None / ""), not as 100%
        missingness_handled = None

    # Narrative quality
    narrative_audit = response.get("narrative_audit") or {}
    has_audit = bool(response.get("narrative_audit"))

    if "sentences_checked" in narrative_audit and narrative_audit["sentences_checked"] is not None:
        try:
            sentences_proposed = int(narrative_audit["sentences_checked"])
        except (ValueError, TypeError):
            sentences_proposed = len(sentences)
    else:
        sentences_proposed = len(sentences)

    if "sentences_accepted" in narrative_audit and narrative_audit["sentences_accepted"] is not None:
        try:
            sentences_accepted = int(narrative_audit["sentences_accepted"])
        except (ValueError, TypeError):
            sentences_accepted = sents_accepted_count
    else:
        sentences_accepted = sents_accepted_count

    raw_dropped = None
    if "sentences_dropped" in narrative_audit:
        raw_dropped = narrative_audit["sentences_dropped"]
    elif "dropped_sentences" in narrative_audit:
        raw_dropped = narrative_audit["dropped_sentences"]

    if raw_dropped is not None:
        if isinstance(raw_dropped, list):
            sentences_discarded = len(raw_dropped)
        else:
            try:
                sentences_discarded = int(raw_dropped)
            except (ValueError, TypeError):
                sentences_discarded = 0
    else:
        sentences_discarded = sents_discarded_count

    discard_rate = (sentences_discarded / sentences_proposed) if sentences_proposed > 0 else 0.0

    if has_audit:
        composition_fallback = 1 if narrative_audit.get("composition_source") == "deterministic_fallback" else 0
    else:
        composition_fallback = None

    # Cross-level findings
    cross_level_critique = response.get("cross_level_critique") or []
    cross_level_findings_count = len(cross_level_critique)
    for blk in (report_spec.get("blocks", []) if report_spec else []):
        if isinstance(blk, dict) and blk.get("type") == "callout":
            cross_level_findings_count += 1

    # Revision rounds as executed by the runtime (the trace has no separate "revise" kind)
    trace = run_data.get("trace") or []
    revision_rounds = int(((response.get("revision_summary") or {}).get("rounds_executed")) or 0)

    return {
        "run_id": run_id,
        "task_id": task_id,
        "arm": arm,
        "rep": rep,
        "order": order,
        "status": status,
        "plan_hash": plan_hash,
        "plan_hash_valid": 1 if plan_hash_valid else 0,
        "completed": completed,
        "clean_completion": clean_completion,
        "protocol_success": protocol_success,
        "numeric_correctness": round(numeric_correctness, 4),
        "numbers_checked": numbers_checked,
        "numbers_matched": numbers_matched,
        "traceability_score": round(traceability_score, 4),
        "obs_cited_count": obs_cited_count,
        "obs_resolved_count": obs_resolved_count,
        "coverage_score": round(coverage_score, 4),
        "required_obs_count": required_obs_count,
        "covered_obs_count": covered_obs_count,
        "missingness_handled": missingness_handled if missingness_handled is not None else "",
        "correct_rejection": correct_rejection if correct_rejection is not None else "",
        "sentences_proposed": sentences_proposed,
        "sentences_accepted": sentences_accepted,
        "sentences_discarded": sentences_discarded,
        "discard_rate": round(discard_rate, 4),
        "composition_fallback": composition_fallback if composition_fallback is not None else "",
        "cross_level_findings_count": cross_level_findings_count,
        "duration_ms": duration_ms,
        "model_calls": model_calls,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "total_tokens": total_tokens,
        "revision_rounds": revision_rounds,
    }


def score_evaluation(
    *,
    runs_dir: Path,
    expected_coverage_path: Path,
    gold_path: Path | None = None,
    dataset_path: Path | None = None,
    output_csv: Path | None = None,
) -> list[dict[str, Any]]:
    effective_dataset = dataset_path or gold_path
    dataset_obs: dict[str, dict[str, Any]] = {}

    if effective_dataset is not None and Path(effective_dataset).exists():
        dataset_obs = load_dataset_observations(Path(effective_dataset))
    else:
        try:
            verified_gold = find_gold_path_or_none(effective_dataset)
            if verified_gold:
                dataset_obs = load_dataset_observations(verified_gold)
            else:
                for cand in (
                    ROOT / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
                    ROOT.parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
                    Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
                ):
                    if cand.exists():
                        dataset_obs = load_dataset_observations(cand)
                        break
        except Exception as exc:
            logger.warning("Dataset not available (%s); running scoring without dataset reconciliation.", exc)

    coverage_payload = json.loads(expected_coverage_path.read_text(encoding="utf-8"))
    coverage_map = {t["task_id"]: t for t in coverage_payload.get("tasks", [])}

    # Group runs by (task_id, arm, rep) to deduplicate if multiple files exist
    run_files = sorted(runs_dir.glob("*.json"))
    runs_by_key: dict[tuple[str, str, int], tuple[Path, dict[str, Any]]] = {}
    for rf in run_files:
        if rf.name == "manifest.json":
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            tid = data.get("task_id")
            arm = data.get("arm")
            rep = data.get("rep", 0)
            if tid and arm:
                key = (tid, arm, rep)
                runs_by_key[key] = (rf, data)
        except Exception as exc:
            logger.error("Failed to read run file %s: %s", rf, exc)

    scored_records: list[dict[str, Any]] = []
    for (tid, arm, rep), (rf, data) in sorted(runs_by_key.items(), key=lambda x: (x[0][2], x[0][0], x[0][1])):
        try:
            row = score_single_run(data, coverage_map, dataset_obs)
            scored_records.append(row)
        except Exception as exc:
            logger.error("Failed to score run file %s: %s", rf, exc)

    if output_csv is not None and scored_records:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(scored_records[0].keys())
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(scored_records)
        print(f"Scored {len(scored_records)} runs. Output written to: {output_csv}")

    return scored_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic scoring for ER-8 / ER-9 evaluation runs")
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--coverage-path", type=Path, default=None)
    parser.add_argument("--gold-path", type=Path, default=None, help="Path to verified Gold SQLite snapshot (deprecated alias for --dataset-path)")
    parser.add_argument("--dataset-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--er9", action="store_true", help="Score ER-9 ten-bank run")

    args = parser.parse_args()

    is_er9 = args.er9 or (args.runs_dir and "er9" in str(args.runs_dir.as_posix()))

    coverage_path = args.coverage_path
    if coverage_path is None:
        if is_er9:
            coverage_path = ROOT / "data" / "evaluation" / "er9-expected-coverage-v1.json"
        else:
            coverage_path = ROOT / "data" / "evaluation" / "er8-expected-coverage-v2.json"

    runs_dir = args.runs_dir
    if runs_dir is None:
        exp_name = "er9" if is_er9 else "er8"
        if (ROOT / "experiments" / exp_name / "runs").exists() and any((ROOT / "experiments" / exp_name / "runs").glob("*.json")):
            runs_dir = ROOT / "experiments" / exp_name / "runs"
        else:
            runs_dir = ROOT / "experiments" / exp_name / "dry-run" / "runs"

    output_csv = args.output
    if output_csv is None:
        exp_name = "er9" if is_er9 else "er8"
        if "dry-run" in str(runs_dir.as_posix()):
            output_csv = ROOT / "experiments" / exp_name / "dry-run" / "scores" / "deterministic.csv"
        else:
            output_csv = ROOT / "experiments" / exp_name / "scores" / "deterministic.csv"

    dataset_path = args.dataset_path or args.gold_path
    if dataset_path is None and is_er9:
        for cand in (
            ROOT / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
            ROOT.parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
            Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
        ):
            if cand.exists():
                dataset_path = cand
                break

    score_evaluation(
        runs_dir=runs_dir,
        expected_coverage_path=coverage_path,
        gold_path=dataset_path,
        dataset_path=dataset_path,
        output_csv=output_csv,
    )


if __name__ == "__main__":
    main()
