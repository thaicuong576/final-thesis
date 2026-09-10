"""Assemble an immutable composite run from explicit retries.

By default, failed retries are rejected. ``--allow-unrecovered`` is an
explicit analysis mode that preserves those failed manifests in the composed
run so reliability and missing-output rates can be scored without treating a
failed provider job as a valid answer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thesis_data.run_manifest import ExperimentRunManifest  # noqa: E402


def _manifests(directory: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in directory.glob("*.json"):
        if path.name in {"failures.json", "recovery-map.json"}:
            continue
        manifest = ExperimentRunManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if manifest.job_id is None:
            continue
        if manifest.job_id in result:
            raise ValueError(f"duplicate job in recovery source: {manifest.job_id}")
        result[manifest.job_id] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_run", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--retry-run", type=Path, action="append", default=[])
    parser.add_argument(
        "--allow-unrecovered",
        action="store_true",
        help="include explicit failed retry manifests for failure-rate analysis",
    )
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError(f"refusing_to_overwrite:{args.output_dir}")
    base = _manifests(args.base_run)
    retries: dict[str, Path] = {}
    for directory in args.retry_run:
        for job_id, path in _manifests(directory).items():
            if job_id in retries:
                raise ValueError(f"duplicate retry job: {job_id}")
            retries[job_id] = path
    selected: dict[str, Path] = {}
    recovery_map: dict[str, dict[str, str]] = {}
    for job_id, path in sorted(base.items()):
        manifest = ExperimentRunManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if manifest.failure_status is not None:
            replacement = retries.get(job_id)
            if replacement is None:
                raise ValueError(f"missing retry for failed job: {job_id}")
            replacement_manifest = ExperimentRunManifest.model_validate(json.loads(replacement.read_text(encoding="utf-8")))
            if replacement_manifest.failure_status is not None and not args.allow_unrecovered:
                raise ValueError(f"retry still failed: {job_id}")
            selected[job_id] = replacement
            recovery_map[job_id] = {"selected": "retry", "source": str(replacement)}
        else:
            selected[job_id] = path
            recovery_map[job_id] = {"selected": "base", "source": str(path)}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for job_id, path in sorted(selected.items()):
        target = args.output_dir / path.name
        shutil.copyfile(path, target)
    failures = []
    for job_id, path in sorted(selected.items()):
        manifest = ExperimentRunManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if manifest.failure_status is not None:
            failures.append(
                {
                    "job_id": job_id,
                    "failure_status": manifest.failure_status,
                    "blockers": list(manifest.failure_blockers),
                }
            )
    (args.output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "recovery-map.json").write_text(
        json.dumps(recovery_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"manifest_count": len(selected), "failure_count": len(failures), "output_dir": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"recovery assembly rejected: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
