#!/usr/bin/env python3
"""Run two arm-blinded AI-assisted rubric reviews over blind packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import monotonic
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.blind_ai_review import (  # noqa: E402
    build_reviewer_prompt,
    parse_review_decisions,
    review_response_schema,
    successful_blind_ids,
)
from thesis_data.blind_scoring import load_complexity_manifests, load_provider_manifests  # noqa: E402
from thesis_data.evaluation import ClaimReview, EvaluationDimension, ReviewStatus  # noqa: E402
from thesis_data.experiment_contract import ExperimentArm  # noqa: E402


DEFAULT_DOTENV = Path(r"D:\eddie-projects\personal-projects\mis-talent\.env")
REVIEWERS = {
    "ai_checker_a": "strict claim-by-claim evaluator",
    "ai_checker_b": "adversarial missing-and-conflict evaluator",
}


def _load_key(dotenv_path: Path, env_name: str) -> str:
    lines = dotenv_path.read_text(encoding="utf-8").splitlines()
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
    raise RuntimeError("review API key not found in external dotenv file")


def _json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("review_output_json_invalid")
        parsed = json.loads(candidate[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("review_output_not_object")
    return parsed


def _usage_value(usage: Any, key: str) -> int:
    if isinstance(usage, dict):
        return int(usage.get(key, 0) or 0)
    return int(getattr(usage, key, 0) or 0)


def _call_reviewer(client: Any, packet: dict[str, Any], reviewer_id: str, model_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prompt = build_reviewer_prompt(packet, reviewer_id)
    started = monotonic()
    response = client.responses.create(
        model=model_id,
        input=[{"role": "user", "content": prompt}],
        text={
            "format": {
                "type": "json_schema",
                "name": "blind_review",
                "strict": True,
                "schema": review_response_schema(),
            }
        },
        max_output_tokens=2048,
    )
    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("review_output_text_missing")
    decisions = parse_review_decisions(_json_object(output_text))
    usage = getattr(response, "usage", None)
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    telemetry = {
        "status": "provided",
        "latency_ms": round((monotonic() - started) * 1000, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_estimate": round(input_tokens * 0.20 / 1_000_000 + output_tokens * 1.20 / 1_000_000, 8),
    }
    return decisions, telemetry


def _claim_reviews(
    packet: dict[str, Any],
    decisions: list[dict[str, Any]],
    reviewer_id: str,
    manifest: dict[str, Any],
) -> list[ClaimReview]:
    rows: list[ClaimReview] = []
    for decision in decisions:
        if decision["review_status"] == "unscorable" and decision["reason_code"] == "not_applicable":
            continue
        rows.append(
            ClaimReview(
                claim_id=f"{packet['blind_id']}:{decision['dimension']}",
                question_id=manifest["question_id"],
                run_id=manifest["run_id"],
                snapshot_id=manifest["snapshot_id"],
                question_set_sha256=manifest["question_set_sha256"],
                rubric_version=manifest["rubric_version"],
                prompt_version=manifest["prompt_version"],
                model_id=manifest["model_id"],
                arm=ExperimentArm(manifest["arm"]),
                dimension=EvaluationDimension(decision["dimension"]),
                review_status=ReviewStatus(decision["review_status"]),
                score=decision["score"],
                reviewer_id=reviewer_id,
                reason_code=decision["reason_code"],
            )
        )
    return rows


def run_suite(
    packets_path: Path,
    run_dir: Path,
    output_dir: Path,
    *,
    dotenv_path: Path,
    model_id: str,
) -> dict[str, Any]:
    packets = [
        json.loads(line)
        for line in packets_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    identity_map = json.loads((output_dir / "private-identity-map.json").read_text(encoding="utf-8"))
    manifests = (
        load_complexity_manifests(run_dir)
        if len(packets) != 39
        else load_provider_manifests(run_dir)
    )
    by_job = {manifest["job_id"]: manifest for manifest in manifests}
    by_blind_id = {
        blind_id: by_job[identity["job_id"]]
        for blind_id, identity in identity_map.items()
    }
    api_key = _load_key(dotenv_path, "OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is not installed") from exc
    client = OpenAI(api_key=api_key, max_retries=0)

    aggregate_reviews: dict[str, list[dict[str, Any]]] = {}
    total_calls = 0
    for reviewer_id in REVIEWERS:
        raw_path = output_dir / f"{reviewer_id}.jsonl"
        claim_path = output_dir / f"{reviewer_id}-claim-reviews.jsonl"
        telemetry_path = output_dir / f"{reviewer_id}-telemetry.jsonl"
        processed: set[str] = set()
        if raw_path.exists():
            records = [
                json.loads(line)
                for line in raw_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            processed = successful_blind_ids(records)
        raw_handle = raw_path.open("a", encoding="utf-8")
        claim_handle = claim_path.open("a", encoding="utf-8")
        telemetry_handle = telemetry_path.open("a", encoding="utf-8")
        try:
            for packet in packets:
                if packet["blind_id"] in processed:
                    continue
                try:
                    decisions, telemetry = _call_reviewer(client, packet, reviewer_id, model_id)
                    record = {
                        "blind_id": packet["blind_id"],
                        "reviewer_id": reviewer_id,
                        "decisions": decisions,
                    }
                    claims = _claim_reviews(packet, decisions, reviewer_id, by_blind_id[packet["blind_id"]])
                    telemetry_record = {
                        "blind_id": packet["blind_id"],
                        "reviewer_id": reviewer_id,
                        "model_id": model_id,
                        **telemetry,
                    }
                except Exception as exc:
                    record = {
                        "blind_id": packet["blind_id"],
                        "reviewer_id": reviewer_id,
                        "decisions": [],
                        "error": f"{exc.__class__.__name__}",
                    }
                    claims = []
                    telemetry_record = {
                        "blind_id": packet["blind_id"],
                        "reviewer_id": reviewer_id,
                        "model_id": model_id,
                        "status": "failed",
                        "error": f"{exc.__class__.__name__}",
                    }
                raw_handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                raw_handle.flush()
                for claim in claims:
                    claim_handle.write(claim.model_dump_json() + "\n")
                claim_handle.flush()
                telemetry_handle.write(json.dumps(telemetry_record, ensure_ascii=False, sort_keys=True) + "\n")
                telemetry_handle.flush()
                aggregate_reviews.setdefault(reviewer_id, []).append(record)
                total_calls += 1
        finally:
            raw_handle.close()
            claim_handle.close()
            telemetry_handle.close()

    summary = {
        "packet_count": len(packets),
        "reviewer_count": len(REVIEWERS),
        "reviewer_ids": list(REVIEWERS),
        "attempted_calls": total_calls,
        "model_id": model_id,
        "secret_value_written": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "ai-review-build-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packets_dir", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--dotenv", type=Path, default=DEFAULT_DOTENV)
    parser.add_argument("--model-id", default="gpt-5.6-luna")
    args = parser.parse_args()
    summary = run_suite(
        args.packets_dir / "blind-packets.jsonl",
        args.run_dir,
        args.packets_dir,
        dotenv_path=args.dotenv,
        model_id=args.model_id,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
