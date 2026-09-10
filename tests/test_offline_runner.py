import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class OfflineRunnerTests(unittest.TestCase):
    def test_offline_fixture_adapter_uses_structured_provider_boundary(self):
        from thesis_data.offline_fixture import OfflineFixtureAdapter
        from thesis_data.provider_adapter import StructuredProviderAdapter

        self.assertIsInstance(OfflineFixtureAdapter(), StructuredProviderAdapter)

    def test_cli_generates_three_noncomparative_manifests(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_offline_fixture.py"
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "offline-run"
            result = subprocess.run(
                [sys.executable, str(script), str(output_dir)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(
            set(summary["arms"]),
            {
                "single_agent",
                "hierarchical_no_critique",
                "hierarchical_bounded_critique",
            },
        )
        self.assertEqual(summary["call_counts"], [1, 4, 6])
        self.assertTrue(summary["all_noncomparative"])

    def test_library_writes_shared_context_and_valid_offline_manifests(self):
        from thesis_data.offline_fixture import run_offline_fixture

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "offline-run"
            result = run_offline_fixture(output_dir)
            manifests = result.manifests

            self.assertEqual([manifest.call_count for manifest in manifests], [1, 4, 6])
            self.assertEqual(
                {manifest.job_id for manifest in manifests},
                {
                    "q1:single_agent",
                    "q1:hierarchical_no_critique",
                    "q1:hierarchical_bounded_critique",
                },
            )
            self.assertEqual(
                {manifest.environment for manifest in manifests}, {"offline_fixture"}
            )
            self.assertTrue(all(not manifest.comparative_result for manifest in manifests))
            self.assertEqual(
                {manifest.input_context_sha256 for manifest in manifests},
                {manifests[0].input_context_sha256},
            )
            self.assertEqual(manifests[0].input_evidence_ids, ["offline-fixture-evidence"])
            self.assertTrue((output_dir / "fixture.sqlite").exists())
            self.assertTrue((output_dir / "question-set.json").exists())
            self.assertTrue((output_dir / "plan.json").exists())
            self.assertEqual(len(list((output_dir / "manifests").glob("*.json"))), 3)

    def test_library_refuses_to_write_into_nonempty_output_directory(self):
        from thesis_data.offline_fixture import run_offline_fixture

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "offline-run"
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("do not overwrite", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                run_offline_fixture(output_dir)


if __name__ == "__main__":
    unittest.main()
