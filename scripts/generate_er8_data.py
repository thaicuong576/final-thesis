#!/usr/bin/env python3
"""Generate ER-8 candidate questions, task specs, and expected coverage from Gold v5.

All values and observation IDs are extracted directly from the hash-bound Gold v5 SQLite
in read-only mode (mode=ro), ensuring zero hardcoded numbers.
Hashes are computed using canonical LF UTF-8 SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

GOLD_RELATIVE_CANDIDATES = [
    ROOT / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    ROOT.parents[1] / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    ROOT.parent / "data" / "processed" / "gold-bank-2025-expanded-v5-evidence.sqlite",
    Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/gold-bank-2025-expanded-v5-evidence.sqlite"),
]

GOLD_RAW_BYTES_SHA256 = "1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73"
AUTHORITY_SIDECAR_REL = "data/evaluation/gold-v5-reporting-scope-authority-v1.json"
AUTHORITY_SIDECAR_SHA256 = "fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f"


def find_gold_path() -> Path:
    for candidate in GOLD_RELATIVE_CANDIDATES:
        if candidate.exists():
            # Verify SHA-256
            raw_hash = hashlib.sha256(candidate.read_bytes()).hexdigest().lower()
            if raw_hash == GOLD_RAW_BYTES_SHA256:
                return candidate
    raise FileNotFoundError("Could not find verified Gold v5 SQLite database matching expected hash.")


def canonical_lf_utf8_sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    text = content.decode("utf-8", errors="strict")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


QUESTIONS = [
    {
        "task_id": "T01",
        "question_text": "Sức khỏe tài chính của MBB trong quý 4/2024 so với các ngân hàng cùng nhóm.",
        "task_type": "company_profile",
        "entities": ["MBB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T02",
        "question_text": "Đánh giá chất lượng tài sản và khả năng sinh lời của VCB trong quý 4/2024.",
        "task_type": "company_profile",
        "entities": ["VCB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T03",
        "question_text": "Tỷ lệ nợ xấu của ACB trong quý 1/2024 là bao nhiêu?",
        "task_type": "lookup",
        "entities": ["ACB"],
        "periods": ["2024_Q1"],
        "metrics": ["bank.npl_g35"],
        "peer_universe": [],
        "is_rejection": False,
        "is_missing": True,
    },
    {
        "task_id": "T04",
        "question_text": "Xu hướng nợ xấu và tỷ lệ bao phủ nợ xấu của TCB diễn biến thế nào trong năm 2024?",
        "task_type": "trend",
        "entities": ["TCB"],
        "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
        "metrics": ["bank.npl_g35", "bank.llr_coverage"],
        "peer_universe": [],
        "is_rejection": False,
    },
    {
        "task_id": "T05",
        "question_text": "ROA và ROE của MBB thay đổi thế nào qua các quý năm 2024?",
        "task_type": "trend",
        "entities": ["MBB"],
        "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
        "metrics": ["bank.roa", "bank.roe"],
        "peer_universe": [],
        "is_rejection": False,
    },
    {
        "task_id": "T06",
        "question_text": "Ngân hàng nào có tỷ lệ nợ xấu thấp nhất trong quý 4/2024?",
        "task_type": "ranking",
        "entities": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.npl_g35"],
        "peer_universe": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T07",
        "question_text": "Xếp hạng ROE các ngân hàng trong quý 4/2024.",
        "task_type": "ranking",
        "entities": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.roe"],
        "peer_universe": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T08",
        "question_text": "ACB đánh đổi chất lượng tài sản và khả năng sinh lời thế nào trong năm 2024 so với các ngân hàng cùng nhóm?",
        "task_type": "trend",
        "entities": ["ACB"],
        "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": ["ACB", "MBB", "TCB", "VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
        "is_missing": True,  # ACB Q1 missing cells
    },
    {
        "task_id": "T09",
        "question_text": "So sánh ACB và TCB trong quý 4/2024.",
        "task_type": "head_to_head",
        "entities": ["ACB", "TCB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": ["ACB", "TCB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T10",
        "question_text": "VCB hay VPB tốt hơn về chất lượng tài sản trong quý 4/2024?",
        "task_type": "head_to_head",
        "entities": ["VCB", "VPB"],
        "periods": ["2024_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35"],
        "peer_universe": ["VCB", "VPB"],
        "peer_period": "2024_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "R1",
        "question_text": "Tỷ lệ nợ xấu của VCB trong quý 1/2025 là bao nhiêu?",
        "task_type": "rejection",
        "entities": ["VCB"],
        "periods": ["2025_Q1"],
        "metrics": ["bank.npl_g35"],
        "peer_universe": [],
        "is_rejection": True,
        "expected_error_code": "unsupported_period",
    },
    {
        "task_id": "R2",
        "question_text": "Phân tích tình hình tài chính của CTG trong quý 4/2024.",
        "task_type": "rejection",
        "entities": ["CTG"],
        "periods": ["2024_Q4"],
        "metrics": [],
        "peer_universe": [],
        "is_rejection": True,
        "expected_error_code": "unsupported_entity",
    },
]


def load_gold_observations(gold_path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    conn = sqlite3.connect(f"file:{gold_path.as_posix()}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute(
        "SELECT observation_id, ticker, period, metric, value, unit, quality_status, reason, source_id, source_locator "
        "FROM metric_observations"
    )
    rows = c.fetchall()
    conn.close()

    result = {}
    for r in rows:
        key = (r[1], r[2], r[3])  # (ticker, period, metric)
        result[key] = {
            "observation_id": r[0],
            "entity_id": r[1],
            "period_id": r[2],
            "metric_id": r[3],
            "value": r[4],
            "unit": r[5],
            "quality_status": r[6],
            "reason": r[7],
            "source_id": r[8],
            "source_locator": r[9],
        }
    return result


def main() -> None:
    gold_path = find_gold_path()
    print(f"Found Gold v5 at: {gold_path}")
    gold_obs = load_gold_observations(gold_path)
    print(f"Loaded {len(gold_obs)} observations from Gold v5.")

    eval_dir = ROOT / "data" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate er8-questions-v2.jsonl
    questions_file = eval_dir / "er8-questions-v2.jsonl"
    lines = []
    for q in QUESTIONS:
        lines.append(json.dumps({"task_id": q["task_id"], "question_text": q["question_text"]}, ensure_ascii=False))
    questions_content = "\n".join(lines) + "\n"
    questions_file.write_text(questions_content, encoding="utf-8", newline="\n")
    questions_hash = canonical_lf_utf8_sha256(questions_content)
    print(f"Written: {questions_file} (hash: {questions_hash})")

    # 2. Compute expected coverage from Gold observations
    coverage_tasks = []
    task_specs = []

    for q in QUESTIONS:
        tid = q["task_id"]
        q_text = q["question_text"]
        q_hash = hashlib.sha256(q_text.encode("utf-8")).hexdigest()

        if q["is_rejection"]:
            task_specs.append({
                "task_id": tid,
                "task_type": q["task_type"],
                "question_sha256_utf8": q_hash,
                "target_entity_ids": q["entities"],
                "period_ids": q["periods"],
                "metric_ids": q["metrics"],
                "required_capabilities": ["Company"],
                "arms": ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique"],
                "prompt_version": "er8-natural-v2",
                "eligibility_status": "rejection_control",
                "expected_error_code": q["expected_error_code"],
            })
            coverage_tasks.append({
                "task_id": tid,
                "question_sha256_utf8": q_hash,
                "expected_coverage": {
                    "is_rejection": True,
                    "expected_error_code": q["expected_error_code"],
                    "valid_count": 0,
                    "missing_count": 0,
                    "required_observation_count": 0,
                    "required_observation_ids": [],
                    "missing_observation_ids": [],
                    "expected_observations": {},
                },
            })
            continue

        # Extract observations
        required_obs_ids = []
        missing_obs_ids = []
        expected_obs_data = {}

        for ent in q["entities"]:
            for p in q["periods"]:
                for m in q["metrics"]:
                    key = (ent, p, m)
                    obs = gold_obs.get(key)
                    if obs:
                        obs_id = obs["observation_id"]
                        required_obs_ids.append(obs_id)
                        expected_obs_data[obs_id] = {
                            "entity_id": ent,
                            "period_id": p,
                            "metric_id": m,
                            "value": obs["value"],
                            "unit": obs["unit"],
                            "quality_status": obs["quality_status"],
                            "source_locator": obs["source_locator"],
                        }
                        if obs["quality_status"] == "missing":
                            missing_obs_ids.append(obs_id)

        # Peer denominators
        peer_denominators = {}
        if q["peer_universe"]:
            p_period = q.get("peer_period", q["periods"][-1])
            for m in (q["metrics"] if q["metrics"] else ["bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"]):
                count = 0
                for p_ent in q["peer_universe"]:
                    p_obs = gold_obs.get((p_ent, p_period, m))
                    if p_obs and p_obs["quality_status"] == "valid":
                        count += 1
                peer_denominators[m] = count

        task_specs.append({
            "task_id": tid,
            "task_type": q["task_type"],
            "question_sha256_utf8": q_hash,
            "target_entity_ids": q["entities"],
            "period_ids": q["periods"],
            "metric_ids": q["metrics"],
            "required_capabilities": ["Company"] if not q["peer_universe"] else ["Company", "Peer"],
            "arms": ["single_agent", "hierarchical_no_critique", "hierarchical_with_critique"],
            "prompt_version": "er8-natural-v2",
            "eligibility_status": "eligible_for_evaluation",
        })

        coverage_tasks.append({
            "task_id": tid,
            "question_sha256_utf8": q_hash,
            "expected_coverage": {
                "is_rejection": False,
                "task_type": q["task_type"],
                "target_entity_ids": q["entities"],
                "period_ids": q["periods"],
                "metric_ids": q["metrics"],
                "valid_count": len(required_obs_ids) - len(missing_obs_ids),
                "missing_count": len(missing_obs_ids),
                "required_observation_count": len(required_obs_ids),
                "required_observation_ids": sorted(required_obs_ids),
                "missing_observation_ids": sorted(missing_obs_ids),
                "peer_denominators": peer_denominators,
                "expected_observations": expected_obs_data,
            },
        })

    # 3. Write er8-task-specs-v2.json
    specs_file = eval_dir / "er8-task-specs-v2.json"
    specs_payload = {
        "manifest_id": "er8-gold-evaluation-task-specs-v2",
        "status": "frozen_protocol_v2_task_specs",
        "protocol_ref": "docs/EVALUATION-PROTOCOL-V2.md",
        "dataset": {
            "dataset_id": "gold-bank-2025-expanded-v5-evidence",
            "snapshot_id": "gold-bank-2025-expanded-v5-evidence",
            "sqlite_sha256_raw_file_bytes": GOLD_RAW_BYTES_SHA256,
            "authority_sidecar_ref": AUTHORITY_SIDECAR_REL,
            "authority_sidecar_sha256_canonical_lf_utf8": AUTHORITY_SIDECAR_SHA256,
        },
        "question_set": {
            "path": "data/evaluation/er8-questions-v2.jsonl",
            "encoding": "UTF-8",
            "newline": "LF",
            "hash_mode": "canonical_lf_utf8_sha256",
            "canonical_lf_utf8_sha256": questions_hash,
        },
        "tasks": task_specs,
    }
    specs_content = json.dumps(specs_payload, indent=2, ensure_ascii=False) + "\n"
    specs_file.write_text(specs_content, encoding="utf-8", newline="\n")
    specs_hash = canonical_lf_utf8_sha256(specs_content)
    print(f"Written: {specs_file} (hash: {specs_hash})")

    # 4. Write er8-expected-coverage-v2.json
    coverage_file = eval_dir / "er8-expected-coverage-v2.json"
    coverage_payload = {
        "manifest_id": "er8-expected-coverage-v2",
        "status": "frozen_protocol_v2_expected_coverage",
        "dataset_id": "gold-bank-2025-expanded-v5-evidence",
        "snapshot_id": "gold-bank-2025-expanded-v5-evidence",
        "snapshot_sha256_raw_file_bytes": GOLD_RAW_BYTES_SHA256,
        "question_set_hash_mode": "canonical_lf_utf8_sha256",
        "question_set_canonical_lf_utf8_sha256": questions_hash,
        "task_specs_canonical_lf_utf8_sha256": specs_hash,
        "peer_scope_label": "bounded five-bank case study; do not generalize to the whole sector",
        "coverage_source": "read-only Gold v5 SQLite observations (mode=ro)",
        "tasks": coverage_tasks,
    }
    coverage_content = json.dumps(coverage_payload, indent=2, ensure_ascii=False) + "\n"
    coverage_file.write_text(coverage_content, encoding="utf-8", newline="\n")
    coverage_hash = canonical_lf_utf8_sha256(coverage_content)
    print(f"Written: {coverage_file} (hash: {coverage_hash})")

    print("\nGeneration complete!")
    print(f"Questions hash: {questions_hash}")
    print(f"Task specs hash: {specs_hash}")
    print(f"Expected coverage hash: {coverage_hash}")


if __name__ == "__main__":
    main()
