"""Replaceable, prefetched-only narrative writer used by the adaptive runtime."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove leading ```json or ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        # Remove trailing ```
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


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
                "source IDs, or numerical values that are absent from the supplied claim. Address the selected "
                "critique descriptions and required actions when present. Return every requested claim exactly once.\n\n"
                "CRITICAL CONSTRAINTS FOR PROSE:\n"
                "- NEVER mention any year (such as 2024), quarter (such as Q4, quý 4, fourth quarter), or period words in the 'prose' field. The period is bound at the report level; any period mention will cause an immediate validation failure.\n"
                "- Write narrative focus solely on the entity, metric concept, and asserted value without period words.\n\n"
                "CRITICAL OUTPUT FORMAT: You must output ONLY a valid JSON object with the root key 'claim_texts'. "
                "Schema: {\"claim_texts\": [{\"claim_id\": \"exact_claim_id\", \"prose\": \"grounded narrative with NO period words\", \"supporting_claim_ids\": [\"exact_claim_id\"]}]}"
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
                "You are an executive synthesis writer. Summarize only the supplied claims into concise qualitative overview prose. "
                "Do not introduce external facts, causal conclusions, or claims absent from the supplied list. "
                "Cite every supporting claim ID exactly as provided.\n\n"
                "CRITICAL NEGATIVE CONSTRAINTS FOR SUMMARY:\n"
                "- You must write a strictly QUALITATIVE executive summary.\n"
                "- NEVER include digits, numbers, or spelled-out number words (do NOT write digits like 1.5, or words like one, two, half, percent, percentage, etc.).\n"
                "- NEVER write any years, quarters, dates, or period labels.\n"
                "- Describe the business insights qualitatively (e.g. credit quality health, provisioning discipline, profitability dynamics) without any quantitative words or numbers.\n\n"
                "CRITICAL OUTPUT FORMAT: You must output ONLY a valid JSON object with keys 'summary' and 'supporting_claim_ids'. "
                "Schema: {\"summary\": \"qualitative executive overview without numbers or period labels\", \"supporting_claim_ids\": [\"claim_id_1\", ...]}"
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
        clean_text = _clean_json_text(output_text)
        try:
            decoded = json.loads(clean_text)
        except (TypeError, ValueError) as exc:
            raise AnalysisWriterError("analysis_writer_json_invalid") from exc
        if not isinstance(decoded, dict):
            raise AnalysisWriterError("analysis_writer_output_invalid")
        return decoded
