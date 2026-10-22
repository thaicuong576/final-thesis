#!/usr/bin/env python3
"""Generate ER-9 questions, task specs, and expected coverage from ten-bank quarterly operational snapshot.

All values and observation IDs are extracted directly from the hash-bound operational SQLite
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

ER9_RELATIVE_CANDIDATES = [
    ROOT / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
    ROOT.parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
    ROOT.parent / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
]

ER9_RAW_BYTES_SHA256 = "2a18845feb8dddd83ace39a4ea56fc5d5fbe4a3cb0fcccdfce374a48627f560a"
ER9_SNAPSHOT_ID = "snapshot-42a105f6d7978ef00e972dae40d3f4050dba6102e7b33611a60c521b6f2ce54e"
TEN_BANKS = ["ACB", "BID", "CTG", "HDB", "MBB", "SHB", "STB", "TCB", "VCB", "VPB"]


def find_er9_dataset_path(explicit_path: Path | None = None) -> Path:
    if explicit_path and explicit_path.exists():
        raw_hash = hashlib.sha256(explicit_path.read_bytes()).hexdigest().lower()
        if raw_hash == ER9_RAW_BYTES_SHA256:
            return explicit_path
        raise ValueError(f"Supplied ER-9 database SHA-256 mismatch: {raw_hash} != {ER9_RAW_BYTES_SHA256}")

    for candidate in ER9_RELATIVE_CANDIDATES:
        if candidate.exists():
            raw_hash = hashlib.sha256(candidate.read_bytes()).hexdigest().lower()
            if raw_hash == ER9_RAW_BYTES_SHA256:
                return candidate
    raise FileNotFoundError("Could not find verified ER-9 operational SQLite database matching expected hash.")


def canonical_lf_utf8_sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    text = content.decode("utf-8", errors="strict")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


QUESTIONS = [
    {
        "task_id": "T01",
        "question_text": "Sức khỏe tài chính của BID trong quý 2/2026 so với các ngân hàng cùng nhóm.",
        "task_type": "company_profile",
        "entities": ["BID"],
        "periods": ["2026_Q2"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": TEN_BANKS,
        "peer_period": "2026_Q2",
        "is_rejection": False,
    },
    {
        "task_id": "T02",
        "question_text": "Đánh giá chất lượng tài sản và khả năng sinh lời của STB trong quý 4/2025.",
        "task_type": "company_profile",
        "entities": ["STB"],
        "periods": ["2025_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": TEN_BANKS,
        "peer_period": "2025_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T03",
        "question_text": "Tỷ lệ bao phủ nợ xấu của HDB trong quý 1/2026 là bao nhiêu?",
        "task_type": "lookup",
        "entities": ["HDB"],
        "periods": ["2026_Q1"],
        "metrics": ["bank.llr_coverage"],
        "peer_universe": [],
        "is_rejection": False,
    },
    {
        "task_id": "T04",
        "question_text": "Xu hướng nợ xấu và tỷ lệ bao phủ nợ xấu của CTG diễn biến thế nào trong năm 2025?",
        "task_type": "trend",
        "entities": ["CTG"],
        "periods": ["2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4"],
        "metrics": ["bank.npl_g35", "bank.llr_coverage"],
        "peer_universe": [],
        "is_rejection": False,
    },
    {
        "task_id": "T05",
        "question_text": "ROA và ROE của SHB thay đổi thế nào qua các quý năm 2025?",
        "task_type": "trend",
        "entities": ["SHB"],
        "periods": ["2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4"],
        "metrics": ["bank.roa", "bank.roe"],
        "peer_universe": [],
        "is_rejection": False,
    },
    {
        "task_id": "T06",
        "question_text": "Ngân hàng nào có tỷ lệ nợ xấu thấp nhất trong quý 2/2026?",
        "task_type": "ranking",
        "entities": TEN_BANKS,
        "periods": ["2026_Q2"],
        "metrics": ["bank.npl_g35"],
        "peer_universe": TEN_BANKS,
        "peer_period": "2026_Q2",
        "is_rejection": False,
    },
    {
        "task_id": "T07",
        "question_text": "Xếp hạng ROE các ngân hàng trong quý 4/2025.",
        "task_type": "ranking",
        "entities": TEN_BANKS,
        "periods": ["2025_Q4"],
        "metrics": ["bank.roe"],
        "peer_universe": TEN_BANKS,
        "peer_period": "2025_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T08",
        "question_text": "VPB đánh đổi chất lượng tài sản và khả năng sinh lời thế nào trong năm 2025 so với các ngân hàng cùng nhóm?",
        "task_type": "trend",
        "entities": ["VPB"],
        "periods": ["2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": TEN_BANKS,
        "peer_period": "2025_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "T09",
        "question_text": "So sánh MBB và TCB trong quý 2/2026.",
        "task_type": "head_to_head",
        "entities": ["MBB", "TCB"],
        "periods": ["2026_Q2"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"],
        "peer_universe": ["MBB", "TCB"],
        "peer_period": "2026_Q2",
        "is_rejection": False,
    },
    {
        "task_id": "T10",
        "question_text": "VCB hay CTG tốt hơn về chất lượng tài sản trong quý 4/2025?",
        "task_type": "head_to_head",
        "entities": ["VCB", "CTG"],
        "periods": ["2025_Q4"],
        "metrics": ["bank.llr_coverage", "bank.npl_g35"],
        "peer_universe": ["VCB", "CTG"],
        "peer_period": "2025_Q4",
        "is_rejection": False,
    },
    {
        "task_id": "R1",
        "question_text": "Tỷ lệ nợ xấu của VCB trong quý 3/2026 là bao nhiêu?",
        "task_type": "rejection",
        "entities": ["VCB"],
        "periods": ["2026_Q3"],
        "metrics": ["bank.npl_g35"],
        "peer_universe": [],
        "is_rejection": True,
        "expected_error_code": "unsupported_period",
    },
    {
        "task_id": "R2",
        "question_text": "Phân tích tình hình tài chính của OCB trong quý 4/2025.",
        "task_type": "rejection",
        "entities": ["OCB"],
        "periods": ["2025_Q4"],
        "metrics": [],
        "peer_universe": [],
        "is_rejection": True,
        "expected_error_code": "unsupported_entity",
    },
]


def load_dataset_observations(db_path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute(
        "SELECT observation_id, entity_id, period_id, metric_id, value, unit, validation_status, source_ref, source_locator "
        "FROM observations"
    )
    rows = c.fetchall()
    conn.close()

    result = {}
    for r in rows:
        key = (r[1], r[2], r[3])  # (entity_id, period_id, metric_id)
        result[key] = {
            "observation_id": r[0],
            "entity_id": r[1],
            "period_id": r[2],
            "metric_id": r[3],
            "value": r[4],
            "unit": r[5],
            "quality_status": r[6],
            "source_id": r[7],
            "source_locator": r[8],
        }
    return result


def main() -> None:
    dataset_path = find_er9_dataset_path()
    print(f"Found ER-9 operational snapshot at: {dataset_path}")
    obs_map = load_dataset_observations(dataset_path)
    print(f"Loaded {len(obs_map)} observations from operational snapshot.")

    eval_dir = ROOT / "data" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate er9-questions-v1.jsonl
    questions_file = eval_dir / "er9-questions-v1.jsonl"
    lines = []
    for q in QUESTIONS:
        lines.append(json.dumps({"task_id": q["task_id"], "question_text": q["question_text"]}, ensure_ascii=False))
    questions_content = "\n".join(lines) + "\n"
    questions_file.write_text(questions_content, encoding="utf-8", newline="\n")
    questions_hash = canonical_lf_utf8_sha256(questions_content)
    print(f"Written: {questions_file} (hash: {questions_hash})")

    # 2. Compute expected coverage from operational observations
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
                "prompt_version": "er9-natural-v1",
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
                    obs = obs_map.get(key)
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
                    p_obs = obs_map.get((p_ent, p_period, m))
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
            "prompt_version": "er9-natural-v1",
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

    # 3. Write er9-task-specs-v1.json
    specs_file = eval_dir / "er9-task-specs-v1.json"
    specs_payload = {
        "manifest_id": "er9-ten-bank-evaluation-task-specs-v1",
        "status": "frozen_protocol_v2_task_specs",
        "protocol_ref": "docs/EVALUATION-PROTOCOL-V2.md",
        "dataset": {
            "dataset_id": "bank-quarterly-top10-operational-v1",
            "snapshot_id": ER9_SNAPSHOT_ID,
            "sqlite_sha256_raw_file_bytes": ER9_RAW_BYTES_SHA256,
            "authority_sidecar_ref": None,
            "authority_sidecar_sha256_canonical_lf_utf8": None,
        },
        "question_set": {
            "path": "data/evaluation/er9-questions-v1.jsonl",
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

    # 4. Write er9-expected-coverage-v1.json
    coverage_file = eval_dir / "er9-expected-coverage-v1.json"
    coverage_payload = {
        "manifest_id": "er9-expected-coverage-v1",
        "status": "frozen_protocol_v2_expected_coverage",
        "dataset_id": "bank-quarterly-top10-operational-v1",
        "snapshot_id": ER9_SNAPSHOT_ID,
        "snapshot_sha256_raw_file_bytes": ER9_RAW_BYTES_SHA256,
        "question_set_hash_mode": "canonical_lf_utf8_sha256",
        "question_set_canonical_lf_utf8_sha256": questions_hash,
        "task_specs_canonical_lf_utf8_sha256": specs_hash,
        "peer_scope_label": "ten listed banks, operational snapshot, not the whole sector",
        "coverage_source": "read-only canonical operational SQLite observations (mode=ro)",
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
