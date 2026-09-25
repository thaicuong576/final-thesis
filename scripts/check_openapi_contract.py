"""Validate OpenAPI and local references, including accidentally erased $ref keys."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openapi_spec_validator import validate


def check_contract(path: Path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))

    def walk(value: object, location: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "":
                    raise ValueError(f"empty contract key at {location}")
                if key == "$ref":
                    if not isinstance(child, str) or not child.startswith("#/"):
                        raise ValueError(f"expected local schema reference at {location}")
                    resolved = document
                    for segment in child[2:].split("/"):
                        segment = segment.replace("~1", "/").replace("~0", "~")
                        if not isinstance(resolved, dict) or segment not in resolved:
                            raise ValueError(f"unresolved reference {child} at {location}")
                        resolved = resolved[segment]
                walk(child, f"{location}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{location}/{index}")

    walk(document, "#")
    validate(document)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=Path("contracts/openapi.json"))
    args = parser.parse_args()
    check_contract(args.path)
    print("OPENAPI_CONTRACT: PASS")
