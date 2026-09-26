import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_plan import load_complexity_question_set
from thesis_data.question_set import (
    CANONICAL_LF_UTF8_HASH_MODE,
    question_set_sha256,
)
from thesis_data.workload_contract import WorkloadTier


class ComplexityQuestionSetTests(unittest.TestCase):
    def payload(self):
        return {
            "schema_version": 1,
            "question_set_id": "complexity-v1",
            "status": "frozen",
            "scope": {
                "issuers": ["ACB", "TCB", "VPB"],
                "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                "core_metrics": ["bank.roa", "bank.roe"],
            },
            "questions": [
                {
                    "id": "ACB-composite",
                    "type": "composite_workload",
                    "prompt": "Analyze ACB.",
                    "workload": {
                        "question_id": "ACB-composite",
                        "tier": "tier_2",
                        "issuers": ["ACB"],
                        "periods": ["2024_Q1", "2024_Q2"],
                        "metric_ids": ["bank.roa", "bank.roe"],
                        "analysis_tasks": ["snapshot", "trend"],
                        "peer_tickers": ["ACB", "TCB", "VPB"],
                        "complexity_vector": {
                            "issuer_count": 1,
                            "period_count": 2,
                            "metric_count": 2,
                            "analysis_task_count": 2,
                            "cross_issuer_comparisons": 0,
                            "missing_conflict_checks": 0,
                            "evidence_groups": 0,
                        },
                    },
                }
            ],
        }

    def test_loader_accepts_composite_question_set_and_preserves_tier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(json.dumps(self.payload()), encoding="utf-8")
            question_set = load_complexity_question_set(path)

        self.assertEqual(question_set.question_set_id, "complexity-v1")
        self.assertEqual(question_set.questions[0].workload.tier, WorkloadTier.TIER_2)

    def test_loader_rejects_atomic_question_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            payload = self.payload()
            payload["questions"][0] = {
                "id": "atomic",
                "issuer": "ACB",
                "type": "company_snapshot",
                "period": "2024_Q1",
                "prompt": "atomic",
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_complexity_question_set(path)

    def test_frozen_project_set_has_three_tier2_and_one_tier3_workloads(self):
        path = Path(__file__).parents[1] / "experiments" / "question-set-complexity-v1.json"
        question_set = load_complexity_question_set(path)

        self.assertEqual(question_set.question_set_id, "pilot-2024-bank-complexity-v1")
        self.assertEqual(len(question_set.questions), 4)
        self.assertEqual(
            [question.workload.tier for question in question_set.questions],
            [WorkloadTier.TIER_2, WorkloadTier.TIER_2, WorkloadTier.TIER_2, WorkloadTier.TIER_3],
        )
        for question in question_set.questions:
            workload = question.workload
            self.assertEqual(len(workload.periods), 4)
            self.assertEqual(len(workload.metric_ids), 4)
            self.assertEqual(len(workload.analysis_tasks), 6)
            self.assertEqual(workload.peer_tickers, ("ACB", "TCB", "VPB"))

    def test_canonical_hash_normalizes_only_lf_line_endings(self):
        canonical = "\ufeff{\"label\":\"café \tvalue\"}\n".encode("utf-8")
        variants = (
            canonical,
            canonical.replace(b"\n", b"\r\n"),
            canonical.replace(b"\n", b"\r"),
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, content in enumerate(variants):
                path = Path(directory) / f"questions-{index}.json"
                path.write_bytes(content)
                paths.append(path)

            hashes = [
                question_set_sha256(
                    path,
                    hash_mode=CANONICAL_LF_UTF8_HASH_MODE,
                )
                for path in paths
            ]
            raw_hashes = [question_set_sha256(path) for path in paths]

        self.assertEqual(hashes, [hashes[0]] * len(variants))
        self.assertNotEqual(raw_hashes[0], raw_hashes[1])

    def test_canonical_hash_preserves_bom_codepoints_whitespace_and_final_newline(self):
        original = "\ufeff{\"label\":\"café value\"}\n".encode("utf-8")
        changed_content = (
            original.replace(b"value", b"other"),
            original.removeprefix(b"\xef\xbb\xbf"),
            "{\"label\":\"cafe\u0301 value\"}\n".encode("utf-8"),
            original.replace(b"caf\xc3\xa9 value", b"caf\xc3\xa9  value"),
            original.removesuffix(b"\n"),
        )

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            source.write_bytes(original)
            source_hash = question_set_sha256(
                source,
                hash_mode=CANONICAL_LF_UTF8_HASH_MODE,
            )
            for index, content in enumerate(changed_content):
                with self.subTest(change=index):
                    candidate = Path(directory) / f"changed-{index}.json"
                    candidate.write_bytes(content)
                    self.assertNotEqual(
                        source_hash,
                        question_set_sha256(
                            candidate,
                            hash_mode=CANONICAL_LF_UTF8_HASH_MODE,
                        ),
                    )

    def test_canonical_hash_requires_strict_utf8_and_raw_mode_remains_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                question_set_sha256(
                    path,
                    hash_mode=CANONICAL_LF_UTF8_HASH_MODE,
                )

            path.write_bytes(b"question\r\n")
            self.assertEqual(
                question_set_sha256(path),
                hashlib.sha256(b"question\r\n").hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
