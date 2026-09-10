"""Generate non-comparative manifests from the deterministic offline fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.offline_fixture import run_offline_fixture  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="new directory for fixture and manifests")
    args = parser.parse_args()
    try:
        result = run_offline_fixture(args.output_dir)
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.summary(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
