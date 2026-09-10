import unittest
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from thesis_data.experiment_contract import ExperimentArm


_REVIEW_BINDING = {
    "run_id": "run-single-q1",
    "snapshot_id": "gold-v1",
    "question_set_sha256": "a" * 64,
    "rubric_version": "rubric-v1",
    "prompt_version": "prompt-v1",
    "model_id": "model-v1",
}


def _evaluation_api():
    try:
        from thesis_data.evaluation import (
            ClaimReview,
            EvaluationDimension,
            ReviewStatus,
            summarize_claim_reviews,
        )
    except ModuleNotFoundError as exc:
        raise AssertionError("evaluation scoring scaffold is missing") from exc
    return ClaimReview, EvaluationDimension, ReviewStatus, summarize_claim_reviews


class EvaluationScaffoldTests(unittest.TestCase):
    def test_summary_keeps_unscorable_reviews_out_of_rate_but_visible(self):
        ClaimReview, Dimension, Status, summarize = _evaluation_api()
        reviews = [
            ClaimReview(
                claim_id="claim-1",
                question_id="question-1",
                **_REVIEW_BINDING,
                arm=ExperimentArm.SINGLE_AGENT,
                dimension=Dimension.FACTUAL_CORRECTNESS,
                review_status=Status.SCORED,
                score=1,
                reviewer_id="checker-A",
                reason_code="matches_gold",
            ),
            ClaimReview(
                claim_id="claim-2",
                question_id="question-1",
                **_REVIEW_BINDING,
                arm=ExperimentArm.SINGLE_AGENT,
                dimension=Dimension.FACTUAL_CORRECTNESS,
                review_status=Status.UNSCORABLE,
                score=None,
                reviewer_id="checker-A",
                reason_code="contract_failure",
            ),
        ]

        summary = summarize(reviews)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0].numerator, 1)
        self.assertEqual(summary[0].denominator, 1)
        self.assertEqual(summary[0].unscorable_count, 1)
        self.assertEqual(summary[0].score_rate, 1.0)

    def test_claim_review_rejects_score_status_mismatch(self):
        ClaimReview, Dimension, Status, _ = _evaluation_api()

        with self.assertRaises(ValueError):
            ClaimReview(
                claim_id="claim-1",
                question_id="question-1",
                **_REVIEW_BINDING,
                arm=ExperimentArm.SINGLE_AGENT,
                dimension=Dimension.EVIDENCE_COMPLETENESS,
                review_status=Status.UNSCORABLE,
                score=0,
                reviewer_id="checker-A",
                reason_code="review_failure",
            )

    def test_summary_rejects_duplicate_reviewer_claim_dimension(self):
        ClaimReview, Dimension, Status, summarize = _evaluation_api()
        row = dict(
            claim_id="claim-1",
            question_id="question-1",
            run_id="run-1",
            snapshot_id="gold-v1",
            question_set_sha256="a" * 64,
            rubric_version="rubric-v1",
            prompt_version="prompt-v1",
            model_id="model-v1",
            arm=ExperimentArm.SINGLE_AGENT,
            dimension=Dimension.CITATION_CORRECTNESS,
            review_status=Status.SCORED,
            score=1,
            reviewer_id="checker-A",
            reason_code="supported",
        )

        with self.assertRaisesRegex(ValueError, "duplicate_claim_review"):
            summarize([ClaimReview(**row), ClaimReview(**row)])

    def test_summary_rejects_mixed_evaluation_binding(self):
        ClaimReview, Dimension, Status, summarize = _evaluation_api()
        common = dict(
            question_id="question-1",
            snapshot_id="gold-v1",
            question_set_sha256="a" * 64,
            rubric_version="rubric-v1",
            prompt_version="prompt-v1",
            model_id="model-v1",
            arm=ExperimentArm.SINGLE_AGENT,
            dimension=Dimension.FACTUAL_CORRECTNESS,
            review_status=Status.SCORED,
            score=1,
            reviewer_id="checker-A",
            reason_code="matches_gold",
        )
        first = ClaimReview(claim_id="claim-1", run_id="run-1", **common)
        second = ClaimReview(
            claim_id="claim-2",
            run_id="run-2",
            **{**common, "snapshot_id": "gold-v2"},
        )

        with self.assertRaisesRegex(ValueError, "mixed_snapshot_id"):
            summarize([first, second])

    def test_summary_cli_emits_reproducible_json_without_mutating_input(self):
        ClaimReview, Dimension, Status, _ = _evaluation_api()
        reviews = [
            ClaimReview(
                claim_id="claim-1",
                question_id="question-1",
                **_REVIEW_BINDING,
                arm=ExperimentArm.SINGLE_AGENT,
                dimension=Dimension.FACTUAL_CORRECTNESS,
                review_status=Status.SCORED,
                score=1,
                reviewer_id="checker-A",
                reason_code="matches_gold",
            ),
            ClaimReview(
                claim_id="claim-2",
                question_id="question-1",
                **_REVIEW_BINDING,
                arm=ExperimentArm.SINGLE_AGENT,
                dimension=Dimension.FACTUAL_CORRECTNESS,
                review_status=Status.UNSCORABLE,
                score=None,
                reviewer_id="checker-A",
                reason_code="review_failure",
            ),
        ]
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "summarize_claim_reviews.py"
        )

        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "reviews.jsonl"
            original = "".join(
                json.dumps(review.model_dump(mode="json"), sort_keys=True) + "\n"
                for review in reviews
            )
            input_path.write_text(original, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(input_path)],
                cwd=Path(__file__).resolve().parents[1],
                env={**__import__("os").environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(len(output), 1)
            self.assertEqual(output[0]["denominator"], 1)
            self.assertEqual(output[0]["unscorable_count"], 1)
            self.assertEqual(input_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
