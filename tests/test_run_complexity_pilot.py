import tempfile
import unittest
from pathlib import Path

from scripts.run_complexity_pilot import ensure_output_dir


class ComplexityPilotRunnerTests(unittest.TestCase):
    def test_output_directory_is_created_and_non_empty_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            ensure_output_dir(output)
            self.assertTrue(output.exists())
            (output / "existing.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                ensure_output_dir(output)


if __name__ == "__main__":
    unittest.main()
