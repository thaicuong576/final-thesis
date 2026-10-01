"""Analysis writer protocol and OpenAI adapter for Vietnamese banking reports."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Protocol, Sequence

from thesis_data.report_spec import normalize_report_spec_dict


_INLINE_FACT_REF_RE = re.compile(
    r"\s*[\(\[]\s*(?:fact_ids?\s*[:=]\s*)?fact:[^\)\]]*[\)\]]"  # "(fact:...)", "[fact:..., fact:...]"
    r"|\s*fact:[A-Za-z0-9_.:\-]+",  # bare "fact:delta:VPB:..." tokens
)


def _strip_inline_fact_refs(value: Any) -> Any:
    """Remove fact identifiers the model sometimes inlines into prose.

    Citations belong in ``fact_ids``; an identifier inside ``text`` would be shown to
    the reader verbatim, so every ``text`` string in the decoded output is cleaned.
    """
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == "text" and isinstance(item, str):
                cleaned = _INLINE_FACT_REF_RE.sub("", item)
                out[key] = re.sub(r"\s+([.,;:])", r"", cleaned).strip()
            else:
                out[key] = _strip_inline_fact_refs(item)
        return out
    if isinstance(value, list):
        return [_strip_inline_fact_refs(item) for item in value]
    return value


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


class AnalysisWriterError(ValueError):
    """Raised when the configured writer fails its contract or output is invalid."""


QUESTION_TYPE_LABELS: dict[str, str] = {
    "lookup": "tra cứu",
    "company_profile": "hồ sơ doanh nghiệp",
    "ranking": "xếp hạng",
    "trend": "xu hướng",
    "head_to_head": "so sánh trực diện",
}

FINDINGS_PROMPT_TEMPLATE = (
    "Bạn là chuyên viên phân tích {role_label} trong một nhóm phân tích ngân hàng.\n"
    "Câu hỏi: {question} (dạng: {question_type_label}).\n"
    "Viết tối đa {max_sentences} câu nhận định tiếng Việt trả lời trực tiếp câu hỏi, chỉ dựa trên các fact được cung cấp. Ưu tiên insight quan trọng nhất trước.\n"
    "Quy tắc:\n"
    "1. Mỗi câu liệt kê fact_ids nó dựa vào, chỉ dùng fact_id có trong danh sách.\n"
    "2. Khi nêu số, chép đúng chuỗi \"hien_thi\". Không tự tính, không tự làm tròn, không thêm số khác.\n"
    "3. Chỉ nói tăng/giảm/liên tục/thu hẹp khi có fact thay đổi; chỉ nói cao hơn/thấp hơn/nhỉnh hơn khi có fact chênh lệch; chỉ nói \"nhất/hạng\" khi có fact hạng.\n"
    "3b. Nếu fact có \"huong\", mô tả chiều đúng bằng cụm đó (ví dụ \"đi ngang\", không viết \"giảm nhẹ\"; \"cao hơn trung vị nhóm\", không viết \"ngang trung vị\"). Khi so sánh hai ngân hàng, nêu rõ tên chỉ tiêu, không chỉ đếm số chỉ tiêu dẫn trước.\n"
    "4. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Được dùng \"hàm ý\" cho phép phân rã như ROE/ROA. Không khuyến nghị mua/bán.\n"
    "5. Câu tối đa 30 từ, giọng báo cáo phân tích, dùng tên chỉ tiêu tiếng Việt, không dùng mã như bank.roe.\n"
    "6. Nếu có \"ung_vien_mau_thuan\", được nêu dữ kiện liên quan nhưng không kết luận nguyên nhân.\n"
    "Trả về JSON: {{\"sentences\":[{{\"text\":\"…\",\"fact_ids\":[\"…\"]}}]}}"
)

COMPOSE_REPORT_PROMPT_TEMPLATE = (
    "Bạn là điều phối viên, dựng báo cáo phân tích kiểu equity research bằng tiếng Việt cho câu hỏi: {question} (dạng: {question_type_label}).\n"
    "Bạn có: các câu nhận định đã được kiểm chứng (sentence_id), danh sách dataset có thể vẽ (dataset_id, allowed_charts), tín hiệu, phát hiện liên tầng.\n"
    "Hãy chọn và sắp xếp các khối để trả lời câu hỏi rõ nhất, đưa kết luận lên đầu:\n"
    "- Câu hỏi tra cứu: dùng kind \"answer_card\" với khối \"answer\" và tối đa 1 hình.\n"
    "- Còn lại: kind \"note\", bắt đầu bằng \"headline\" (tối đa 16 từ, mở đầu bằng mã ngân hàng hoặc chủ đề và dấu hai chấm, là một nhận định).\n"
    "- Mỗi hình chọn chart trong allowed_charts của dataset, có title ngắn và 1 câu takeaway kèm fact_ids.\n"
    "- Chỉ đưa hình thật sự hỗ trợ một luận điểm; không đưa hình trùng ý.\n"
    "- Ưu tiên dùng lại sentence_id. Chỉ viết câu mới khi thật cần, và câu mới phải kèm fact_ids.\n"
    "- Câu mới tả chiều thay đổi/chênh lệch phải dùng đúng cụm trong \"huong\" của fact (đi ngang, cao hơn trung vị nhóm…).\n"
    "- Phát hiện liên tầng đã xác nhận nên được đưa vào callout.\n"
    "Quy tắc số, xu hướng, nguyên nhân, khuyến nghị: giống chuyên viên. Giới hạn: tối đa 4 hình, 5 luận điểm, 3 callout.\n"
    "Trả về JSON đúng schema ReportSpec, trong đó câu có thể là {{\"sentence_id\":\"…\"}} (dùng lại) hoặc {{\"text\":\"…\",\"fact_ids\":[…]}} (câu mới).\n"
    "Ví dụ cấu trúc cho note:\n"
    "{{\"kind\":\"note\",\"note_label\":null,\"blocks\":[{{\"type\":\"headline\",\"sentence\":{{\"sentence_id\":\"sent-company-1\"}}}},{{\"type\":\"section\",\"title\":\"Phân tích chi tiết\",\"sentences\":[{{\"sentence_id\":\"sent-company-2\"}}]}}]}}\n"
    "Ví dụ cấu trúc cho answer_card:\n"
    "{{\"kind\":\"answer_card\",\"note_label\":null,\"blocks\":[{{\"type\":\"answer\",\"value_fact_id\":\"fact:value:VCB:2024_Q4:bank.npl_g35\",\"sentences\":[{{\"text\":\"Tỷ lệ nợ xấu của VCB quý 4/2024 là 0,96%.\",\"fact_ids\":[\"fact:value:VCB:2024_Q4:bank.npl_g35\"]}}]}}]}}"
)

_COMPOSE_SENTENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sentence_id": {"type": ["string", "null"]},
        "text": {"type": ["string", "null"]},
        "fact_ids": {"type": ["array", "null"], "items": {"type": "string"}},
    },
    "required": ["sentence_id", "text", "fact_ids"],
    "additionalProperties": False,
}

_COMPOSE_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["answer_card", "note"]},
        "note_label": {"type": ["string", "null"]},
        "blocks": {
            "type": "array",
            "items": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["headline"]},
                            "sentence": _COMPOSE_SENTENCE_SCHEMA,
                        },
                        "required": ["type", "sentence"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["answer"]},
                            "value_fact_id": {"type": "string"},
                            "sentences": {
                                "type": "array",
                                "items": _COMPOSE_SENTENCE_SCHEMA,
                            },
                        },
                        "required": ["type", "value_fact_id", "sentences"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["key_points"]},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "sentences": {
                                            "type": "array",
                                            "items": _COMPOSE_SENTENCE_SCHEMA,
                                        },
                                    },
                                    "required": ["title", "sentences"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["type", "items"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["section"]},
                            "title": {"type": "string"},
                            "sentences": {
                                "type": "array",
                                "items": _COMPOSE_SENTENCE_SCHEMA,
                            },
                        },
                        "required": ["type", "title", "sentences"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["figure"]},
                            "figure_no": {"type": "integer"},
                            "chart": {
                                "type": "string",
                                "enum": [
                                    "kpi_strip",
                                    "ranked_bar",
                                    "line_trend",
                                    "small_multiples",
                                    "scatter",
                                    "rank_heatmap",
                                    "grouped_bar",
                                    "comparison_table",
                                ],
                            },
                            "dataset_id": {"type": "string"},
                            "title": {"type": "string"},
                            "takeaway": _COMPOSE_SENTENCE_SCHEMA,
                        },
                        "required": ["type", "figure_no", "chart", "dataset_id", "title", "takeaway"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["callout"]},
                            "tone": {"type": "string", "enum": ["notice", "warning"]},
                            "title": {"type": "string"},
                            "finding_id": {"type": ["string", "null"]},
                            "sentences": {
                                "type": "array",
                                "items": _COMPOSE_SENTENCE_SCHEMA,
                            },
                        },
                        "required": ["type", "tone", "title", "finding_id", "sentences"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["table"]},
                            "dataset_id": {"type": "string"},
                            "title": {"type": "string"},
                        },
                        "required": ["type", "dataset_id", "title"],
                        "additionalProperties": False,
                    },
                ]
            },
        },
    },
    "required": ["kind", "note_label", "blocks"],
    "additionalProperties": False,
}


REWRITE_SENTENCE_PROMPT_TEMPLATE = (
    "Bạn là chuyên viên phân tích {role_label} trong một nhóm phân tích ngân hàng.\n"
    "Câu hỏi: {question}.\n"
    "Câu nhận định gốc gặp vấn đề phản biện sau:\n"
    "Vấn đề: {issue_description}\n"
    "Yêu cầu xử lý: {required_action}\n"
    "Hãy viết lại 1 câu nhận định tiếng Việt để khắc phục vấn đề trên, chỉ dùng các fact được cung cấp.\n"
    "Quy tắc:\n"
    "1. Liệt kê fact_ids câu dựa vào, chỉ dùng fact_id trong danh sách.\n"
    "2. Khi nêu số, chép đúng chuỗi \"hien_thi\". Không tự tính, không tự làm tròn, không thêm số khác.\n"
    "3. Chỉ nói tăng/giảm khi có fact thay đổi; chỉ nói cao/thấp hơn khi có fact chênh lệch.\n"
    "3b. Nếu fact có \"huong\", mô tả chiều đúng bằng cụm đó (ví dụ \"đi ngang\", không viết \"giảm nhẹ\"; \"cao hơn trung vị nhóm\", không viết \"ngang trung vị\"). Khi so sánh hai ngân hàng, nêu rõ tên chỉ tiêu, không chỉ đếm số chỉ tiêu dẫn trước.\n"
    "4. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Tối đa 30 từ.\n"
    "Trả về JSON: {{\"text\":\"…\",\"fact_ids\":[\"…\"]}}"
)


def _normalize_facts(facts: Sequence[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for f in facts:
        if isinstance(f, dict):
            fid = f.get("fact_id", "")
            mota = f.get("mo_ta") or f.get("description") or ""
            hienthi = f.get("hien_thi") or f.get("display_value") or str(f.get("value", ""))
        else:
            fid = getattr(f, "fact_id", "")
            mota = getattr(f, "mo_ta", None) or getattr(f, "description", "")
            hienthi = getattr(f, "hien_thi", None) or getattr(f, "display_value", "") or str(getattr(f, "value", ""))
        item = {
            "fact_id": str(fid),
            "mo_ta": str(mota),
            "hien_thi": str(hienthi),
        }
        huong = f.get("huong") if isinstance(f, dict) else getattr(f, "huong", None)
        if huong:
            item["huong"] = str(huong)
        normalized.append(item)
    return normalized


class AnalysisWriter(Protocol):
    """Protocol for writer implementations providing specialist findings and report composition."""

    def write_findings(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]] | None = None,
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]: ...

    def compose_report(
        self,
        *,
        question: str,
        question_type: str,
        sentences: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        signals: Sequence[Mapping[str, Any]] | None = None,
        findings: Sequence[Mapping[str, Any]] | None = None,
        facts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    def rewrite_sentence(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]: ...


class OpenAIAnalysisWriter:
    """OpenAI Responses / chat adapter providing specialist findings, composition, and sentence revision."""

    def __init__(self, *, client: Any, model: str) -> None:
        if client is None or not isinstance(model, str) or not model.strip():
            raise AnalysisWriterError("analysis_writer_configuration_invalid")
        self.client = client
        self.model = model.strip()
        self._current_role: str = "orchestrator"

    def write_findings(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Any],
        datasets_summary: Sequence[Any],
        candidates: Sequence[Any] | None = None,
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]:
        self._current_role = role
        try:
            return self._write_findings_internal(
                role=role,
                question=question,
                question_type=question_type,
                facts=facts,
                datasets_summary=datasets_summary,
                candidates=candidates,
                max_sentences=max_sentences,
            )
        finally:
            self._current_role = "orchestrator"

    def _write_findings_internal(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Any],
        datasets_summary: Sequence[Any],
        candidates: Sequence[Any] | None = None,
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]:
        role_label = "doanh nghiệp" if role in ("company", "doanh nghiệp") else "so sánh nhóm ngành"
        q_label = QUESTION_TYPE_LABELS.get(question_type, question_type)
        instructions = FINDINGS_PROMPT_TEMPLATE.format(
            role_label=role_label,
            question=question,
            question_type_label=q_label,
            max_sentences=max_sentences,
        )
        norm_facts = _normalize_facts(facts)
        payload = {
            "question": question,
            "question_type": question_type,
            "role": role,
            "facts": norm_facts,
            "datasets_summary": list(datasets_summary),
            "ung_vien_mau_thuan": list(candidates or []),
            "max_sentences": max_sentences,
        }
        schema = {
            "type": "object",
            "properties": {
                "sentences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "fact_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["text", "fact_ids"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["sentences"],
            "additionalProperties": False,
        }
        decoded = self._request(
            name="specialist_findings",
            instructions=instructions,
            payload=payload,
            schema=schema,
        )
        sentences = decoded.get("sentences")
        if not isinstance(sentences, list):
            raise AnalysisWriterError("analysis_writer_findings_output_invalid")
        return [s for s in sentences if isinstance(s, dict)]

    def compose_report(
        self,
        *,
        question: str,
        question_type: str,
        sentences: Sequence[Any],
        datasets_summary: Sequence[Any],
        signals: Sequence[Any] | None = None,
        findings: Sequence[Any] | None = None,
        facts: Sequence[Any] | None = None,
    ) -> dict[str, Any]:
        q_label = QUESTION_TYPE_LABELS.get(question_type, question_type)
        instructions = COMPOSE_REPORT_PROMPT_TEMPLATE.format(
            question=question,
            question_type_label=q_label,
        )
        payload = {
            "question": question,
            "question_type": question_type,
            "sentences": list(sentences),
            "datasets_summary": list(datasets_summary),
            "signals": list(signals or []),
            "findings": list(findings or []),
            "facts": _normalize_facts(facts or []),
        }
        decoded = self._request(
            name="report_specification",
            instructions=instructions,
            payload=payload,
            schema=_COMPOSE_REPORT_SCHEMA,
        )
        if not isinstance(decoded, dict):
            raise AnalysisWriterError("analysis_writer_compose_output_invalid")
        return normalize_report_spec_dict(decoded, question_type)

    def rewrite_sentence(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Any],
    ) -> dict[str, Any]:
        self._current_role = role
        try:
            return self._rewrite_sentence_internal(
                role=role,
                question=question,
                sentence=sentence,
                issue=issue,
                facts=facts,
            )
        finally:
            self._current_role = "orchestrator"

    def _rewrite_sentence_internal(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Any],
    ) -> dict[str, Any]:
        role_label = "doanh nghiệp" if role in ("company", "doanh nghiệp") else "so sánh nhóm ngành"
        desc = issue.get("description", "")
        action = issue.get("required_action", "")
        instructions = REWRITE_SENTENCE_PROMPT_TEMPLATE.format(
            role_label=role_label,
            question=question,
            issue_description=desc,
            required_action=action,
        )
        norm_facts = _normalize_facts(facts)
        payload = {
            "question": question,
            "original_sentence": dict(sentence),
            "issue": dict(issue),
            "facts": norm_facts,
        }
        schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "fact_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["text", "fact_ids"],
            "additionalProperties": False,
        }
        decoded = self._request(
            name="rewritten_sentence",
            instructions=instructions,
            payload=payload,
            schema=schema,
        )
        text = decoded.get("text")
        fact_ids = decoded.get("fact_ids")
        if not isinstance(text, str) or not isinstance(fact_ids, list):
            raise AnalysisWriterError("analysis_writer_rewrite_output_invalid")
        return {"text": text, "fact_ids": [str(fid) for fid in fact_ids]}

    def _request(
        self,
        *,
        name: str,
        instructions: str,
        payload: Mapping[str, Any],
        schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                if hasattr(self.client, "responses"):
                    request_kwargs: dict[str, Any] = {
                        "model": self.model,
                        "instructions": instructions,
                        "input": json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "max_output_tokens": 2500,
                        "store": False,
                    }
                    if schema is not None:
                        request_kwargs["text"] = {
                            "format": {
                                "type": "json_schema",
                                "name": name,
                                "strict": True,
                                "schema": schema,
                            }
                        }
                    else:
                        request_kwargs["text"] = {
                            "format": {
                                "type": "json_object",
                            }
                        }
                    response = self.client.responses.create(**request_kwargs)
                    output_text = getattr(response, "output_text", None)
                else:
                    messages = [
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
                    ]
                    kwargs: dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 2500,
                    }
                    if schema is not None:
                        kwargs["response_format"] = {
                            "type": "json_schema",
                            "json_schema": {"name": name, "schema": schema, "strict": True},
                        }
                    else:
                        kwargs["response_format"] = {"type": "json_object"}
                    response = self.client.chat.completions.create(**kwargs)
                    output_text = response.choices[0].message.content
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2 and ("Connection error" in str(exc) or "timeout" in str(exc).lower()):
                    import time
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise AnalysisWriterError("analysis_writer_request_failed") from exc

        status = getattr(response, "status", None)
        if status not in (None, "completed"):
            raise AnalysisWriterError("analysis_writer_response_incomplete")
        if not isinstance(output_text, str) or not output_text.strip():
            raise AnalysisWriterError("analysis_writer_output_missing")
        clean_text = _clean_json_text(output_text)
        try:
            decoded = json.loads(clean_text)
        except (TypeError, ValueError) as exc:
            raise AnalysisWriterError("analysis_writer_json_invalid") from exc
        if not isinstance(decoded, dict):
            raise AnalysisWriterError("analysis_writer_output_invalid")
        return _strip_inline_fact_refs(decoded)
