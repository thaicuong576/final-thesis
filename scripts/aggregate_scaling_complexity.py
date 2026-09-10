#!/usr/bin/env python3
"""Aggregate recovered composite runs by issuer-count, arm, and replicate."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def _manifest_paths(run_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in run_dir.glob("*.json")
        if path.name not in {"failures.json", "recovery-map.json"}
    )


def _metric(manifest: dict[str, Any], key: str) -> float:
    value = manifest.get(key)
    return float(value or 0.0)


def _summarize(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for manifest in manifests:
        vector = manifest.get("complexity_vector") or {}
        issuer_count = int(vector.get("issuer_count") or 0)
        groups[(issuer_count, str(manifest.get("arm")))].append(manifest)

    result: dict[str, Any] = {}
    for (issuer_count, arm), rows in sorted(groups.items()):
        completed = sum(1 for row in rows if not row.get("failure_status"))
        total_wall = sum(_metric(row, "wall_clock_latency_ms") for row in rows)
        total_cost = sum(_metric(row, "total_cost_estimate") for row in rows)
        total_input = sum(int(row.get("total_input_tokens") or 0) for row in rows)
        total_output = sum(int(row.get("total_output_tokens") or 0) for row in rows)
        result.setdefault(str(issuer_count), {})[arm] = {
            "jobs": len(rows),
            "completed_jobs": completed,
            "failed_jobs": len(rows) - completed,
            "cost_estimate_usd_total": round(total_cost, 8),
            "cost_per_completed_job_usd": round(total_cost / completed, 8) if completed else None,
            "wall_clock_latency_ms_total": round(total_wall, 3),
            "mean_wall_clock_latency_ms": round(total_wall / len(rows), 3) if rows else None,
            "throughput_completed_jobs_per_minute": round(completed / (total_wall / 60000), 6) if total_wall and completed else 0.0,
            "input_tokens_total": total_input,
            "output_tokens_total": total_output,
            "failure_statuses": sorted({str(row.get("failure_status")) for row in rows if row.get("failure_status")}),
            "question_ids": sorted({str(row.get("question_id")) for row in rows}),
        }
    return result


def _mechanical_by_issuer_count(
    score_dir: Path,
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    identity_map = json.loads((score_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    question_to_issuer_count = {
        str(row.get("question_id")): int((row.get("complexity_vector") or {}).get("issuer_count") or 0)
        for row in manifests
    }
    groups: dict[tuple[int, str, str], list[int]] = defaultdict(list)
    for line in (score_dir / "mechanical-score.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        identity = identity_map.get(str(row.get("blind_id")))
        if identity is None:
            continue
        issuer_count = question_to_issuer_count.get(str(identity["question_id"]))
        if not issuer_count:
            continue
        groups[(issuer_count, str(identity["arm"]), str(row["dimension"]))].append(int(row["score"]))

    result: dict[str, Any] = {}
    for (issuer_count, arm, dimension), values in sorted(groups.items()):
        result.setdefault(str(issuer_count), {}).setdefault(arm, {})[dimension] = {
            "count": len(values),
            "score_rate": round(sum(values) / len(values), 6),
        }
    return result


def aggregate(
    run_dir: Path,
    *,
    first_pass_dir: Path | None = None,
    score_dir: Path | None = None,
) -> dict[str, Any]:
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in _manifest_paths(run_dir)]
    first_pass_failures: list[dict[str, Any]] = []
    if first_pass_dir is not None:
        failure_path = first_pass_dir / "failures.json"
        if failure_path.exists():
            first_pass_failures = json.loads(failure_path.read_text(encoding="utf-8"))
    report = {
        "run_dir": str(run_dir),
        "manifest_count": len(manifests),
        "recovered_failure_count": sum(1 for row in manifests if row.get("failure_status")),
        "first_pass_failure_count": len(first_pass_failures),
        "first_pass_failures": first_pass_failures,
        "by_issuer_count_and_arm": _summarize(manifests),
        "interpretation": {
            "status": "descriptive_scaling_signal",
            "not_asymptotic_proof": True,
            "recovered_run_is_composed": True,
        },
        "protocol_versions": {
            "prompt_versions": {
                version: sum(1 for row in manifests if row.get("prompt_version") == version)
                for version in sorted({str(row.get("prompt_version")) for row in manifests})
            },
            "failure_by_prompt_version": {
                version: sum(
                    1
                    for row in manifests
                    if row.get("prompt_version") == version and row.get("failure_status")
                )
                for version in sorted({str(row.get("prompt_version")) for row in manifests})
            },
            "note": "The composed run preserves historical v2 successes and v3 compact-protocol recoveries; compare v3 stress results separately from v2 historical baselines.",
        },
    }
    if score_dir is not None:
        report["mechanical_by_issuer_count_and_arm"] = _mechanical_by_issuer_count(score_dir, manifests)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--first-pass-dir", type=Path, default=None)
    parser.add_argument("--score-dir", type=Path, default=None)
    args = parser.parse_args()
    report = aggregate(args.run_dir, first_pass_dir=args.first_pass_dir, score_dir=args.score_dir)
    if args.output.exists():
        raise FileExistsError(f"refusing_to_overwrite:{args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_count": report["manifest_count"], "issuer_counts": sorted(report["by_issuer_count_and_arm"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
