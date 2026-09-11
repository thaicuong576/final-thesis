"""Thin binding from frozen experiment fixtures to the application request."""

from __future__ import annotations

from .analysis_request import AnalysisRequest
from .dataset_contract import DatasetRef
from .question_set import EvaluationQuestion, QuestionScope, QuestionSet, QuestionType


def analysis_request_from_question(
    question: EvaluationQuestion,
    scope: QuestionScope,
    dataset_ref: DatasetRef,
    *,
    request_id: str | None = None,
    peer_universe_id: str | None = None,
) -> AnalysisRequest:
    """Bind one experiment question without making it the app contract."""

    if question.type is QuestionType.COMPOSITE_WORKLOAD:
        workload = question.workload
        if workload is None:  # guarded by the QuestionSet contract
            raise ValueError("composite question workload is missing")
        metric_ids = tuple(dict.fromkeys((*workload.metric_ids, *workload.macro_indicator_ids)))
        return AnalysisRequest(
            request_id=request_id or question.id,
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            target_entity_ids=workload.issuers,
            period_ids=workload.periods,
            metric_ids=metric_ids,
            macro_metric_ids=workload.macro_indicator_ids,
            peer_universe_id=peer_universe_id,
            peer_entity_ids=workload.peer_tickers if peer_universe_id else (),
            objective=question.prompt,
        )

    target_entity_ids = (question.issuer,) if question.issuer else ()
    period_ids = question.periods or ((question.period,) if question.period else ())
    bank_metric_ids = question.bank_metric_ids or scope.core_metrics
    if question.target_cell is not None:
        bank_metric_ids = tuple(dict.fromkeys((*bank_metric_ids, question.target_cell.metric)))
    metric_ids = tuple(dict.fromkeys((*bank_metric_ids, *question.macro_indicator_ids)))
    if question.peer_set and peer_universe_id is None:
        raise ValueError("peer question requires peer_universe_id for application binding")
    return AnalysisRequest(
        request_id=request_id or question.id,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        target_entity_ids=target_entity_ids,
        period_ids=period_ids,
        metric_ids=metric_ids,
        macro_metric_ids=question.macro_indicator_ids,
        peer_universe_id=peer_universe_id,
        peer_entity_ids=question.peer_set,
        objective=question.prompt,
        causal_claim_policy=question.causal_claim_policy,
    )


def analysis_request_from_question_set(
    question_set: QuestionSet,
    question_id: str,
    dataset_ref: DatasetRef,
    *,
    peer_universe_id: str | None = None,
) -> AnalysisRequest:
    """Resolve and bind a question from the unchanged experiment fixture."""

    question = next(
        (item for item in question_set.questions if item.id == question_id),
        None,
    )
    if question is None:
        raise ValueError(f"unknown question: {question_id}")
    return analysis_request_from_question(
        question,
        question_set.scope,
        dataset_ref,
        peer_universe_id=peer_universe_id,
    )
