#!/usr/bin/env python3
"""Render one arm-blind scaling packet for independent human review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _find_packet(path: Path, blind_id: str) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        packet = json.loads(line)
        if packet.get("blind_id") == blind_id:
            return packet
    raise LookupError(f"blind_id_not_found:{blind_id}")


def render_markdown(packet: dict[str, Any]) -> str:
    question = packet.get("question", {})
    answer = packet.get("answer", {})
    gold = packet.get("gold_reference", {})
    lines = [
        f"# Blind review packet: `{packet.get('blind_id', '')}`",
        "",
        "This rendering contains only the arm-blind question, answer, and Gold reference.",
        "Do not use it to infer arm, run, or model identity.",
        "",
        "## Question",
        "",
        f"- ID: `{question.get('id', '')}`",
        f"- Type: `{question.get('type', '')}`",
        "",
        str(question.get("prompt", "")),
        "",
        "## Answer",
        "",
        "```json",
        json.dumps(answer, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Gold reference",
        "",
        "```json",
        json.dumps(gold, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("score_dir", type=Path)
    parser.add_argument("blind_id")
    parser.add_argument("--output", type=Path, help="optional Markdown output path")
    args = parser.parse_args()
    packet = _find_packet(args.score_dir / "blind-packets.jsonl", args.blind_id)
    rendered = render_markdown(packet)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"blind_id": args.blind_id, "output": str(args.output)}, ensure_ascii=False))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
