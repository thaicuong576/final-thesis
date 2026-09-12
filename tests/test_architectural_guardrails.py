import ast
import runpy
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ArchitecturalGuardrailTests(unittest.TestCase):
    def test_application_first_guardrail_preflight_passes(self):
        result = subprocess.run(
            [sys.executable, "scripts/check_architecture_guardrails.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ARCHITECTURE_GUARDRAILS: PASS", result.stdout)

    def test_reusable_core_import_guard_rejects_forbidden_framework_roots(self):
        guard = runpy.run_path(str(ROOT / "scripts" / "check_architecture_guardrails.py"))
        import_roots = guard["_import_roots"]
        for source, expected_root in (
            ("import langgraph.graph", "langgraph"),
            ("from langchain.runnables import Runnable", "langchain"),
            ("from openai import OpenAI", "openai"),
        ):
            with self.subTest(expected_root=expected_root):
                self.assertIn(expected_root, import_roots(ast.parse(source)))

    def test_guard_fails_for_forbidden_import_in_a_core_file(self):
        guard = runpy.run_path(str(ROOT / "scripts" / "check_architecture_guardrails.py"))
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            fake_core = Path(temp_dir) / "fake_core.py"
            fake_core.write_text("import langgraph.graph\n", encoding="utf-8")
            guard["_check"].__globals__["APPLICATION_CORE_FILES"] = (fake_core,)
            failures = guard["_check"]()
        self.assertTrue(
            any("forbidden framework/provider import" in failure for failure in failures),
            failures,
        )

    def test_framework_import_guard_is_scoped_to_reusable_core(self):
        guard = runpy.run_path(str(ROOT / "scripts" / "check_architecture_guardrails.py"))
        non_core = ROOT / "src" / "thesis_data" / "openai_transport.py"
        self.assertNotIn(non_core, guard["APPLICATION_CORE_FILES"])


if __name__ == "__main__":
    unittest.main()
