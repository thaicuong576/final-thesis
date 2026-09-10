"""Deterministic scoring contracts for the gated thesis evaluation.

This module scores reviewer-supplied claim labels only. It does not parse model
prose, create gold labels, or decide whether a trigger is a contradiction.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .experiment_contract import ExperimentArm


class EvaluationDimension(StrEnum):
    FACTUAL_CORRECTNESS = "factual_correctness"
    CALCULATION_CORRECTNESS = "calculation_correctness"
    EVIDENCE_COMPLETENESS = "evidence_completeness"
    CITATION_CORRECTNESS = "citation_correctness"
    COVERAGE_DISCIPLINE = "coverage_discipline"
    CROSS_LEVEL_CONSISTENCY = "cross_level_consistency"
    ANOMALY_CLASSIFICATION = "anomaly_classification"


class ReviewStatus(StrEnum):
    SCORED = "scored"
    UNSCORABLE = "unscorable"


class ClaimReview(BaseModel):
    """One blind review decision for one claim and one dimension."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    arm: ExperimentArm
    dimension: EvaluationDimension
    review_status: ReviewStatus
    score: int | None = Field(default=None, ge=0, le=1)
    reviewer_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_score_status(self) -> "ClaimReview":
        if self.review_status is ReviewStatus.SCORED and self.score is None:
            raise ValueError("scored review requires score")
        if self.review_status is ReviewStatus.UNSCORABLE and self.score is not None:
            raise ValueError("unscorable review must not contain score")
        if (
            self.review_status is ReviewStatus.UNSCORABLE
            and self.reason_code not in {"contract_failure", "review_failure"}
        ):
            raise ValueError(
                "unscorable review reason_code must be contract_failure or review_failure"
            )
        return self


class ScoreSummary(BaseModel):
    """A per-arm, per-dimension, per-reviewer aggregate."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    question_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    arm: ExperimentArm
    dimension: EvaluationDimension
    reviewer_id: str = Field(min_length=1)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    unscorable_count: int = Field(ge=0)
    score_rate: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_counts(self) -> "ScoreSummary":
        if self.numerator > self.denominator:
            raise ValueError("numerator cannot exceed denominator")
        if self.score_rate is None and self.denominator:
            raise ValueError("score_rate is required when denominator is non-zero")
        return self


def summarize_claim_reviews(
    reviews: Sequence[ClaimReview],
) -> tuple[ScoreSummary, ...]:
    """Aggregate scores without hiding unscorable claims or reviewer identity."""

    if not reviews:
        return ()

    binding_fields = (
        "snapshot_id",
        "question_set_sha256",
        "rubric_version",
        "prompt_version",
        "model_id",
    )
    for field in binding_fields:
        if len({getattr(review, field) for review in reviews}) != 1:
            raise ValueError(f"mixed_{field}")

    seen: set[tuple[str, str, str, ExperimentArm, EvaluationDimension, str]] = set()
    groups: dict[
        tuple[ExperimentArm, EvaluationDimension, str],
        list[ClaimReview],
    ] = {}
    for review in reviews:
        key = (
            review.claim_id,
            review.question_id,
            review.run_id,
            review.arm,
            review.dimension,
            review.reviewer_id,
        )
        if key in seen:
            raise ValueError("duplicate_claim_review")
        seen.add(key)
        groups.setdefault(
            (review.arm, review.dimension, review.reviewer_id), []
        ).append(review)

    summaries: list[ScoreSummary] = []
    reference = reviews[0]
    for (arm, dimension, reviewer_id), rows in groups.items():
        scored = [row for row in rows if row.review_status is ReviewStatus.SCORED]
        numerator = sum(row.score or 0 for row in scored)
        denominator = len(scored)
        summaries.append(
            ScoreSummary(
                snapshot_id=reference.snapshot_id,
                question_set_sha256=reference.question_set_sha256,
                rubric_version=reference.rubric_version,
                prompt_version=reference.prompt_version,
                model_id=reference.model_id,
                arm=arm,
                dimension=dimension,
                reviewer_id=reviewer_id,
                numerator=numerator,
                denominator=denominator,
                unscorable_count=len(rows) - denominator,
                score_rate=(numerator / denominator if denominator else None),
            )
        )

    return tuple(
        sorted(
            summaries,
            key=lambda item: (item.arm.value, item.dimension.value, item.reviewer_id),
        )
    )
