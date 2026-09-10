"""Combine the MBB profitability and credit candidate packets append-safely."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            rows.append(row)
    if not rows:
        raise ValueError(f"candidate packet is empty: {path}")
    return rows


def build(profitability: Path, credit: Path, output: Path) -> list[dict]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    rows = _load(profitability) + _load(credit)
    observation_ids = [str(row.get("observation_id", "")).strip() for row in rows]
    if any(not value for value in observation_ids) or len(set(observation_ids)) != len(observation_ids):
        raise ValueError("combined candidate packet must have unique non-empty observation IDs")
    if any(row.get("ticker") != "MBB" for row in rows):
        raise ValueError("combined candidate packet must contain only MBB rows")
    if any(row.get("quality_status") != "pending_validation" for row in rows):
        raise ValueError("combined candidate packet must contain pending_validation rows only")
    rows.sort(key=lambda row: row["observation_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profitability", type=Path, required=True)
    parser.add_argument("--credit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build(args.profitability, args.credit, args.output)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
