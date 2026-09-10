"""Copy a run manifest while binding it to an equivalent versioned snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    old_snapshot = data.get("snapshot_id")
    if not old_snapshot:
        raise ValueError("manifest has no snapshot_id")
    data["snapshot_id"] = args.snapshot_id
    data.setdefault("provenance_notes", []).append(
        {
            "type": "snapshot_retarget",
            "from_snapshot_id": old_snapshot,
            "to_snapshot_id": args.snapshot_id,
            "reason": "same frozen scope and accepted observations; evidence-complete Gold snapshot",
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "from_snapshot_id": old_snapshot, "to_snapshot_id": args.snapshot_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
