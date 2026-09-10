"""Deterministic prompt rendering for the guarded agent runtime.

The renderer is deliberately provider-neutral. It serializes the request and
prepared context only; it never calls a model, reads a secret, or accesses the
network. Provider-specific message envelopes belong to a later transport.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .agent_runtime import AgentCallRequest
from .workload_contract import AnalysisTask, CompositeWorkloadSpec


ROLE_INSTRUCTIONS: dict[str, str] = {
    "single_agent": "Retrieve only the requested Gold facts with the available tools, then synthesize the final response.",
    "macro": "Use only the declared macro indicators: retrieve them and separate observed macro facts from interpretation.",
    "sector": "Retrieve only requested bank metrics and peer scope; do not calculate from unaccepted facts.",
    "company": "Retrieve only requested issuer metrics and period scope; cite every numeric claim.",
    "orchestrator": "Synthesize validated worker payloads without inventing facts or changing their scope.",
    "verification": "Check only the focused verification request against Gold tools and evidence, and report uncertainty.",
}


class PromptRenderError(ValueError):
    """A runtime request cannot be rendered into a reproducible prompt."""

    def __init__(self, blockers: tuple[str, ...] | list[str]):
        self.blockers = tuple(blockers)
        super().__init__("prompt rendering rejected: " + ", ".join(self.blockers))


COMPOSITE_ROLE_INSTRUCTIONS: dict[str, str] = {
    "single_agent": "Own the complete composite workload, retrieve each declared slice, then synthesize one bounded report.",
    "company": "Retrieve only issuer-period slices assigned to the company role and return typed subreports; do not perform peer synthesis.",
    "sector": "Retrieve only the declared peer comparison slices and preserve issuer, period, and metric boundaries.",
    "macro": "Retrieve only declared macro indicators and report them separately from issuer metrics.",
    "orchestrator": "Merge validated subreports by issuer-period-task, preserve provenance, and never repair missing facts by inference.",
    "verification": "Re-check only flagged issuer-period-task slices against Gold and record pass, missing, or conflict explicitly.",
}

COMPOSITE_ROLE_TASKS: dict[str, tuple[str, ...]] = {
    "single_agent": tuple(task.value for task in AnalysisTask),
    "company": ("snapshot", "trend", "missing_conflict", "anomaly_review", "evidence_summary"),
    "sector": ("peer_comparison", "anomaly_review"),
    "orchestrator": tuple(task.value for task in AnalysisTask),
    "verification": tuple(task.value for task in AnalysisTask),
}


def render_composite_prompt(
    spec: CompositeWorkloadSpec,
    role: str,
    prompt_version: str,
    question_prompt: str = "Execute the declared composite workload.",
    prepared_context: Mapping[str, Any] | None = None,
    max_context_chars: int | None = None,
) -> str:
    """Render a scope-first SOP for a multi-issuer composite workload.

    Composite prompts deliberately contain the workload contract, not prepared
    financial facts. Facts must be retrieved through the role-isolated Gold
    tools so increasing database size does not silently become prompt stuffing.
    """

    if role not in COMPOSITE_ROLE_INSTRUCTIONS:
        raise PromptRenderError(("prompt_role_unknown",))
    if not isinstance(prompt_version, str) or not prompt_version.strip():
        raise PromptRenderError(("prompt_version_missing",))
    if not question_prompt.strip():
        raise PromptRenderError(("prompt_question_missing",))

    scope = {
        "question_id": spec.question_id,
        "tier": spec.tier.value,
        "issuers": list(spec.issuers),
        "periods": list(spec.periods),
        "metric_ids": list(spec.metric_ids),
        "analysis_tasks": [task.value for task in spec.analysis_tasks],
        "peer_tickers": list(spec.peer_tickers),
        "macro_indicator_ids": list(spec.macro_indicator_ids),
        "complexity_vector": spec.complexity_vector.model_dump(mode="json"),
    }
    scope_json = json.dumps(
        scope,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    context_json = None
    if prepared_context is not None:
        try:
            context_json = json.dumps(
                prepared_context,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise PromptRenderError(("composite_context_not_json_safe",)) from exc
        if max_context_chars is not None and len(context_json) > max_context_chars:
            raise PromptRenderError(
                (
                    "composite_context_budget_exceeded",
                    f"context_chars={len(context_json)}",
                    f"context_budget_chars={max_context_chars}",
                )
            )
    role_tasks = tuple(task for task in COMPOSITE_ROLE_TASKS[role] if task in {item.value for item in spec.analysis_tasks})
    context_line = (
        f"Prepared worker context JSON: {context_json}"
        if context_json is not None
        else "Prepared worker context JSON: (none; retrieve through role-scoped tools.)"
    )
    return "\n".join(
        (
            f"Prompt version: {prompt_version}",
            f"Role: {role}",
            f"Role instruction: {COMPOSITE_ROLE_INSTRUCTIONS[role]}",
            f"Role task scope: {', '.join(role_tasks)}",
            f"Composite workload tier: {spec.tier.value}",
            f"Issuers: {', '.join(spec.issuers)}",
            f"Periods: {', '.join(spec.periods)}",
            f"Metric IDs: {', '.join(spec.metric_ids)}",
            "Sector benchmark tool scope: use sector='bank' exactly.",
            f"Analysis tasks: {', '.join(task.value for task in spec.analysis_tasks)}",
            f"Question: {question_prompt.strip()}",
            "Stage 1: decompose the request into the declared issuer-period-task cells before retrieving anything.",
            "Stage 2: retrieve each cell only through the role-isolated, read-only Gold tools; use the bounded batch tools first for declared ticker-period or period sets, then use single-cell tools only for focused follow-up checks.",
            "Stage 3: validate ticker, period, metric, unit, observation IDs, source IDs, and evidence IDs before using a fact.",
            "Stage 4: assemble subreports by exact (issuer, period, task) key; never silently overwrite duplicate or conflicting cells.",
            "Stage 5: synthesize only after all available cells are classified as valid, missing, unaccepted, or conflict.",
            "Coverage requirement: single_agent and orchestrator emit exactly issuer_count × period_count × analysis_task_count subreports. Company and sector workers emit only their role task scope; verification emits only the flagged in-scope subreport(s). For each issuer-period, the same validated tool payload may be referenced by multiple task subreports, but no duplicate key is allowed.",
            "Provenance requirement: every data_slice containing any non-null metric or benchmark must copy at least one exact non-empty observation_ids or source_ids list from the corresponding tool result. A payload_ref does not create provenance by itself. Never emit an unsupported numeric claim. If no validated numeric payload exists, use null values with an explicit missing reason.",
            "Final provenance checklist: before returning JSON, inspect every non-null metric and benchmark in every data_slice and inline payload. Copy the exact observation_ids/source_ids returned by the tool call that supplied that number. If the tool result did not return a provenance ID, set that number to null and add a quality flag; do not return an unsupported number.",
            "Normalization requirement: emit each unique issuer-period AgentPayload once in data_slices. Task subreports should set payload=null and payload_ref='<issuer>|<period>' instead of duplicating the same metrics six times. Use payload inline only for a genuinely task-specific payload.",
            "Subreport encoding requirement: for single_agent, company, sector, and orchestrator, subreports is a compact array with exactly one object for each required '<issuer>|<period>|<task>' key from the frozen scope. In compact v3 mode, you may return subreports=[] after returning one canonical data_slice per issuer-period; the runtime deterministically expands task references from those slices. Each explicit object must carry issuer, period, task, status, payload or payload_ref, missing_reasons, and provenance IDs; do not omit a key or add a duplicate.",
            "Do not stop after snapshot cells: trend, peer_comparison, missing_conflict, anomaly_review, and evidence_summary are separate required task keys.",
            "For company or sector worker roles, emit only the task keys in the declared role task scope; the orchestrator is responsible for full composite coverage.",
            "Claim requirement: emit a top-level claims array for the user-facing analysis contract. Each claim must have a unique claim_id, claim_type, priority, title, checkable claim text, interpretation, limitation, support level, and at least one exact data_ref encoded as '<ticker>|<period>|<metric_id>'. Use only in-scope data refs. Copy evidence_ids and source_ids exactly from retrieved tool results and also publish their union in the top-level evidence_ids/source_ids fields. Mark support='evidence_backed' only when the cited evidence actually supports the referenced metric; otherwise use source_locator_only or partially_supported. Never write a causal conclusion without causal evidence.",
            "Retrieval policy: closed world. Do not use web search, arbitrary files, arbitrary SQL, unstated facts, or facts from another workload.",
            "Missing-data policy: never guess, interpolate, or fill a missing/conflicting cell. Preserve an explicit reason and provenance.",
            "Output policy: return one CompositeAnalysisPayload-compatible JSON object with typed subreports, quality counts, findings, and provenance.",
            f"Frozen composite scope JSON: {scope_json}",
            context_line,
        )
    )


def render_agent_prompt(request: AgentCallRequest) -> str:
    """Render one request with stable ordering and an explicit frozen scope."""

    if request.role not in ROLE_INSTRUCTIONS:
        raise PromptRenderError(("prompt_role_unknown",))
    if not request.question_prompt.strip():
        raise PromptRenderError(("prompt_question_missing",))

    scope = {
        "macro_indicator_ids": list(request.macro_indicator_ids),
        "metric_ids": list(request.metric_ids),
        "period": request.period,
        "periods": list(request.periods or (request.period,)),
        "question_id": request.question_id,
        "question_type": request.question_type,
        "ticker": request.ticker,
        "peer_tickers": list(request.peer_tickers),
    }
    try:
        context_json = json.dumps(
            request.context,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        scope_json = json.dumps(
            scope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise PromptRenderError(("prompt_context_not_json_safe",)) from exc

    return "\n".join(
        (
            f"Prompt version: {request.prompt_version}",
            f"Role: {request.role}",
            f"Role instruction: {ROLE_INSTRUCTIONS[request.role]}",
            f"Ticker: {request.ticker}",
            f"Periods: {', '.join(request.periods or (request.period,))}",
            f"Metric IDs: {', '.join(request.metric_ids) or '(none)' }",
            f"Macro indicator IDs: {', '.join(request.macro_indicator_ids) or '(none)' }",
            f"Question: {request.question_prompt.strip()}",
            "Retrieval policy: This is a closed-world task. Use only the role-scoped read-only Gold tools; do not use web search, files, arbitrary SQL, or unstated facts.",
            "Missing-data policy: Never guess or fill a missing/conflicting cell. Return null with an explicit reason and preserve provenance.",
            f"Output policy: Return only an AgentPayload-compatible JSON object after retrieval. Set agent_id exactly to {request.role}; set ticker exactly to {request.ticker} unless the role is macro; set period exactly to {request.period}; use only requested periods in metric_periods. Every numeric claim needs its unit, period, and observation/source/evidence provenance. For evidence, copy the complete evidence object verbatim from get_evidence results; never paraphrase its quote, page, period, ticker, or IDs.",
            "If no macro indicator IDs are declared for the macro role, return a partial macro payload with no metric claims; do not answer bank metrics as a macro worker.",
            f"Frozen scope JSON: {scope_json}",
            f"Prepared context JSON: {context_json}",
        )
    )
