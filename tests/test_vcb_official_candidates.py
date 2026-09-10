import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_vcb_official_candidates import build


class VcbOfficialCandidateTests(unittest.TestCase):
    def test_builds_twenty_pending_observations_across_four_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "vcb-candidates.jsonl"
            rows = build(output)
            persisted = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), 20)
        self.assertEqual(len(persisted), 20)
        self.assertEqual({row["ticker"] for row in rows}, {"VCB"})
        self.assertEqual({row["quality_status"] for row in rows}, {"pending_validation"})
        self.assertEqual(
            {row["metric"] for row in rows},
            {"bank.roa", "bank.roe", "bank.npl_g35", "bank.llr_coverage"},
        )
        self.assertEqual(
            [row["value"] for row in rows if row["metric"] == "bank.npl_g35"],
            [1.2207, 1.2008, 1.2228, 0.9636],
        )
        self.assertEqual(
            [row["value"] for row in rows if row["metric"] == "bank.llr_coverage"],
            [199.8177, 212.1089, 204.6495, 223.311],
        )
        self.assertEqual(
            len(
                {
                    row["observation_id"]
                    for row in rows
                }
            ),
            20,
        )

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "vcb-candidates.jsonl"
            output.write_text("existing\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                build(output)


if __name__ == "__main__":
    unittest.main()
