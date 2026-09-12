"""Fail-closed checks for the current application/core architecture boundary.

This is intentionally a narrow pre-flight guard. It protects the implemented
Dataset Boundary without pretending that the future agent loop or frontend is
already complete.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
GUARDRAIL_DOC = ROOT / "docs" / "ARCHITECTURAL-GUARDRAILS.md"
APPLICATION_CORE_FILES = (
    ROOT / "src" / "thesis_data" / "dataset_contract.py",
    ROOT / "src" / "thesis_data" / "dataset_provider.py",
    ROOT / "src" / "thesis_data" / "analysis_request.py",
    ROOT / "src" / "thesis_data" / "application_runtime.py",
    ROOT / "src" / "thesis_data" / "dataset_tool_runtime.py",
    ROOT / "src" / "thesis_data" / "runtime_events.py",
    ROOT / "src" / "thesis_data" / "acceptance.py",
    ROOT / "src" / "thesis_data" / "acceptance_resolver.py",
    ROOT / "src" / "thesis_data" / "semantic_evaluation.py",
    ROOT / "src" / "thesis_data" / "semantic_critic.py",
    ROOT / "src" / "thesis_data" / "revision_controller.py",
)
FORBIDDEN_CORE_TEXT = (
    "sqlite3",
    "GoldConfig",
    "GoldToolRuntime",
    "create_gold_snapshot_schema",
    "metric_observations",
    "source_records",
    "evidence_snippets",
    "macro_observations_v2",
    "derived_metrics",
    "snapshot_metadata",
    "peer-median-gold-v1",
)
FIXED_ISSUER_LITERAL = re.compile(r"\b(?:ACB|TCB|VPB|MBB|VCB)\b")
FORBIDDEN_CORE_IMPORT_ROOTS = frozenset({"langgraph", "langchain", "openai"})


def _import_roots(tree: ast.AST) -> frozenset[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
    return frozenset(roots)


def _check() -> list[str]:
    failures: list[str] = []
    if not GUARDRAIL_DOC.is_file():
        failures.append("missing docs/ARCHITECTURAL-GUARDRAILS.md")
    else:
        guardrail_text = GUARDRAIL_DOC.read_text(encoding="utf-8")
        for marker in (
            "**Status: LOCKED**",
            "## 2. Core/application boundary",
            "## 3. Transferability guardrail",
            "## 10. Mandatory pre-flight questions",
        ):
            if marker not in guardrail_text:
                failures.append(f"guardrail document missing marker: {marker}")

    for path in APPLICATION_CORE_FILES:
        if not path.is_file():
            failures.append(f"missing application core module: {path.relative_to(ROOT)}")
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            failures.append(f"application core does not parse: {path.relative_to(ROOT)}: {exc}")
            continue
        forbidden_imports = sorted(_import_roots(tree) & FORBIDDEN_CORE_IMPORT_ROOTS)
        for module_root in forbidden_imports:
            failures.append(
                f"forbidden framework/provider import in application core: "
                f"{module_root} ({path.relative_to(ROOT)})"
            )
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        if "sqlite3" in imported_modules:
            failures.append(f"SQLite import in application core: {path.relative_to(ROOT)}")
        for forbidden in FORBIDDEN_CORE_TEXT[1:]:
            if forbidden in source:
                failures.append(
                    f"Gold-specific dependency {forbidden} in application core: "
                    f"{path.relative_to(ROOT)}"
                )
        if FIXED_ISSUER_LITERAL.search(source):
            failures.append(
                f"fixed thesis issuer literal in application core: {path.relative_to(ROOT)}"
            )

    return failures


def main() -> int:
    failures = _check()
    if failures:
        print("ARCHITECTURE_GUARDRAILS: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ARCHITECTURE_GUARDRAILS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
