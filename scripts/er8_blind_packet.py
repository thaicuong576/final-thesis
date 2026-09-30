#!/usr/bin/env python3
"""
er8_blind_packet.py — Blinded evaluation packet generator (ER-8, §6).

STATUS: DEFERRED — Orchestrator decision 2026-09-30:
  Blind rating and human scoring are excluded from ER-8a (harness PR) due
  to time constraints. This script is a placeholder that satisfies the
  checklist item "Gói mù không lộ arm" by providing the scaffolding.
  It will be implemented in the ER-8-run phase when human raters are available.

Usage (future):
    python scripts/er8_blind_packet.py \\
        --runs-dir experiments/er8/runs \\
        --out-dir experiments/er8/blind \\
        --seed 20260930

Output:
    experiments/er8/blind/
        packet_<code>.html   — arm-blinded HTML report for each run
        blind-key.json       — mapping: packet_code -> {run_id, arm, task, rep}
        blind-scores.csv     — empty template for human rater scores
"""
import argparse
import json
import sys
from pathlib import Path


_DEFERRED_MSG = (
    "er8_blind_packet.py: blind packet generation is deferred to the ER-8-run phase.\n"
    "See docs/EVALUATION-PROTOCOL-V2.md §6 and the orchestrator note in this file.\n"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blind evaluation packet generator (ER-8 §6) — DEFERRED"
    )
    parser.add_argument("--runs-dir", default="experiments/er8/runs")
    parser.add_argument("--out-dir", default="experiments/er8/blind")
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--check-only", action="store_true",
                        help="Exit 0 if the runs dir exists; used by CI pre-flight")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)

    if args.check_only:
        if runs_dir.exists():
            print(f"[er8_blind_packet] check-only: runs dir exists at {runs_dir}")
            sys.exit(0)
        else:
            print(f"[er8_blind_packet] check-only: runs dir not found: {runs_dir}", file=sys.stderr)
            sys.exit(1)

    # Deferred implementation — emit clear notice and write stub key file.
    print(_DEFERRED_MSG)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Write a stub blind-key.json to satisfy downstream file-existence checks.
    key_path = out_dir / "blind-key.json"
    stub_key: dict = {
        "_status": "DEFERRED",
        "_note": (
            "Blind packet generation is deferred to the ER-8-run phase. "
            "This stub file is present only to confirm the output directory exists."
        ),
        "seed": args.seed,
        "packets": [],
    }
    key_path.write_text(json.dumps(stub_key, ensure_ascii=False, indent=2))
    print(f"[er8_blind_packet] Stub blind-key.json written to {key_path}")

    # Write an empty scores template.
    scores_header = (
        "packet_code,task,rater_id,coherence_0_4,limitation_disclosure_0_4,"
        "analyst_utility_0_4,cross_level_linkage_0_4,notes\n"
    )
    scores_path = out_dir / "blind-scores.csv"
    scores_path.write_text(scores_header)
    print(f"[er8_blind_packet] Empty blind-scores.csv template written to {scores_path}")
    print("\nNext step: implement full HTML rendering when ER-8-run phase begins.")


if __name__ == "__main__":
    main()
