import subprocess
from pathlib import Path
import sys
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


if __name__ == "__main__":
    unittest.main()
