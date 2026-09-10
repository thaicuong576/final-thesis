#!/usr/bin/env python3
"""Build immutable blind packets and mechanical scores for composite runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.blind_scoring import (  # noqa: E402
    build_composite_blind_packets,
    load_complexity_manifests,
    operational_summary_by_tier,
    score_composite_answer,
)


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing_to_overwrite:{path}")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("db", type=Path)
    parser.add_argument("question_set", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", default="complexity-blind-v1")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error(f"output_dir_not_empty:{args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifests = load_complexity_manifests(args.run_dir)
    packets, private_map = build_composite_blind_packets(
        args.run_dir, args.db, args.question_set, seed=args.seed
    )
    mechanical_rows = [
        row for packet in packets for row in score_composite_answer(packet)
    ]
    _write_new(
        args.output_dir / "blind-packets.jsonl",
        "".join(json.dumps(packet, ensure_ascii=False, sort_keys=True) + "\n" for packet in packets),
    )
    _write_new(
        args.output_dir / "private-identity-map.json",
        json.dumps(private_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _write_new(
        args.output_dir / "mechanical-score.jsonl",
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in mechanical_rows),
    )
    _write_new(
        args.output_dir / "operational-summary-by-tier.json",
        json.dumps(operational_summary_by_tier(manifests), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    summary = {
        "packet_count": len(packets),
        "mechanical_row_count": len(mechanical_rows),
        "arm_identity_stored_separately": True,
        "tier_identity_stored_separately": True,
        "seed": args.seed,
    }
    _write_new(
        args.output_dir / "build-summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
