"""Replaceable, prefetched-only narrative writer used by the adaptive runtime."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


class AnalysisWriterError(ValueError):
    """Raised when the configured writer fails its narrow output contract."""


class OpenAIAnalysisWriter:
    """OpenAI Responses adapter that can write prose but cannot retrieve facts."""

    def __init__(self, *, client: Any, model: str) -> None:
        if client is None or not isinstance(model, str) or not model.strip():
            raise AnalysisWriterError("analysis_writer_configuration_invalid")
        self.client = client
        self.model = model.strip()

    def write_specialist(
        self,
        *,
        plan: Mapping[str, Any],
        role: str,
        claims: Sequence[Mapping[str, Any]],
        issues: Sequence[Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        claim_ids = [str(item["claim_id"]) for item in claims]
        result = self._request(
            name="specialist_presentation",
            instructions=(
                "You are a specialist presentation writer. Use only the supplied frozen plan, accepted claims, "
                "and observations. Write concise grounded prose for each exact claim_id. Do not change facts, "
                "scope, uncertainty, limitations, or provenance. Do not add causal conclusions, external facts, "
                "source IDs, period labels, or numerical values that are absent from the supplied claim. Address the selected "
                "critique descriptions and required actions when present. Return every requested claim exactly once."
            ),
            payload={"plan": plan, "role": role, "claims": list(claims), "selected_issues": list(issues)},
            schema={
                "type": "object",
                "properties": {
                    "claim_texts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim_id": {"type": "string", "enum": claim_ids},
                                "prose": {"type": "string"},
                                "supporting_claim_ids": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": claim_ids},
                                },
                            },
                            "required": ["claim_id", "prose", "supporting_claim_ids"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["claim_texts"],
                "additionalProperties": False,
            },
        )
        values = result.get("claim_texts")
        if not isinstance(values, list):
            raise AnalysisWriterError("analysis_writer_specialist_output_invalid")
        output: dict[str, dict[str, Any]] = {}
        for item in values:
            if not isinstance(item, dict) or set(item) != {"claim_id", "prose", "supporting_claim_ids"}:
                raise AnalysisWriterError("analysis_writer_specialist_output_invalid")
            claim_id, prose, support_ids = item["claim_id"], item["prose"], item["supporting_claim_ids"]
            if claim_id in output or not isinstance(prose, str) or not isinstance(support_ids, list):
                raise AnalysisWriterError("analysis_writer_specialist_output_invalid")
            if support_ids != [claim_id]:
                raise AnalysisWriterError("analysis_writer_specialist_support_scope_invalid")
            output[claim_id] = {"prose": prose, "supporting_claim_ids": support_ids}
        if set(output) != set(claim_ids):
            raise AnalysisWriterError("analysis_writer_specialist_claim_set_invalid")
        return output

    def synthesize(
        self,
        *,
        plan: Mapping[str, Any],
        specialist_outputs: Mapping[str, Sequence[Mapping[str, str]]],
        issues: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        claim_ids = list(dict.fromkeys(
            str(item["claim_id"])
            for values in specialist_outputs.values()
            for item in values
        ))
        result = self._request(
            name="analysis_synthesis",
            instructions=(
                "You are the constrained orchestrator synthesizer. Summarize only the supplied specialist prose "
                "and frozen plan. Keep every claim ID join implicit in prose; do not add facts, numbers, sources, "
                "period labels, causal claims, or conclusions beyond the inputs. Address selected critique descriptions and "
                "required actions. For a Company plan with multiple ordered periods, the specialist outputs may include "
                "accepted_observation rows. You may describe only the direction supported by those exact metric-period "
                "values; do not add numeric values, deltas, causes, or unstated periods. Return a concise caveat-aware summary."
            ),
            payload={"plan": plan, "specialist_outputs": specialist_outputs, "selected_issues": list(issues)},
            schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "supporting_claim_ids": {
                        "type": "array",
                        "items": {"type": "string", "enum": claim_ids},
                    },
                },
                "required": ["summary", "supporting_claim_ids"],
                "additionalProperties": False,
            },
        )
        summary = result.get("summary")
        support_ids = result.get("supporting_claim_ids")
        if not isinstance(summary, str) or not summary.strip() or not isinstance(support_ids, list):
            raise AnalysisWriterError("analysis_writer_synthesis_output_invalid")
        if support_ids != claim_ids:
            raise AnalysisWriterError("analysis_writer_synthesis_support_scope_invalid")
        return {"summary": summary, "supporting_claim_ids": support_ids}

    def _request(self, *, name: str, instructions: str, payload: Mapping[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
                max_output_tokens=2500,
                store=False,
            )
        except Exception as exc:
            raise AnalysisWriterError("analysis_writer_request_failed") from exc
        status = getattr(response, "status", None)
        if status not in (None, "completed"):
            raise AnalysisWriterError("analysis_writer_response_incomplete")
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise AnalysisWriterError("analysis_writer_output_missing")
        try:
            decoded = json.loads(output_text)
        except (TypeError, ValueError) as exc:
            raise AnalysisWriterError("analysis_writer_json_invalid") from exc
        if not isinstance(decoded, dict):
            raise AnalysisWriterError("analysis_writer_output_invalid")
        return decoded
