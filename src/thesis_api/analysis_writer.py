"""Analysis writer protocol and OpenAI adapter for Vietnamese banking reports."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

from thesis_data.report_spec import normalize_report_spec_dict

logger = logging.getLogger(__name__)


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


class ThrottledDeltaEmitter:
    """Coalesces streamed text deltas to at most ~8 events per second (~125 ms interval)."""

    def __init__(self, callback: Callable[[str], None], min_interval_sec: float = 0.125) -> None:
        self.callback = callback
        self.min_interval_sec = min_interval_sec
        self._buffer: list[str] = []
        self._last_emit_time = 0.0

    def feed(self, delta: str) -> None:
        if not delta:
            return
        self._buffer.append(delta)
        now = time.monotonic()
        if now - self._last_emit_time >= self.min_interval_sec:
            self.flush(now)

    def flush(self, now: float | None = None) -> None:
        if not self._buffer:
            return
        text = "".join(self._buffer)
        self._buffer.clear()
        self._last_emit_time = now if now is not None else time.monotonic()
        self.callback(text)


class StreamingJsonTextExtractor:
    """Incremental extractor that pulls human-readable prose (values of 'text', 'title', 'headline')

    from partial JSON chunks without emitting JSON syntax, braces, or technical keys.
    """

    def __init__(self, on_delta: Callable[[str], None], target_keys: set[str] | None = None) -> None:
        self.on_delta = on_delta
        self.target_keys = target_keys or {"text", "title", "headline"}
        self._in_string = False
        self._escape = False
        self._in_unicode_escape = False
        self._unicode_hex: list[str] = []
        self._current_string: list[str] = []
        self._candidate_key: str | None = None
        self._last_key: str | None = None
        self._in_target_value = False
        self._had_previous_sentence = False

    def feed(self, chunk: str) -> None:
        delta_buffer: list[str] = []
        for char in chunk:
            if not self._in_string:
                if char == '"':
                    self._in_string = True
                    self._escape = False
                    self._in_unicode_escape = False
                    self._unicode_hex = []
                    self._current_string = []
                    # Check if this string is the value for a target key
                    if self._last_key in self.target_keys:
                        self._in_target_value = True
                        if self._had_previous_sentence:
                            delta_buffer.append(" ")
                    else:
                        self._in_target_value = False
                elif char == ':':
                    self._last_key = self._candidate_key
                    self._candidate_key = None
                elif char in ('{', '}', '[', ']', ','):
                    if char in ('{', '[', '}', ']'):
                        self._last_key = None
                        self._candidate_key = None
            else:
                if self._in_unicode_escape:
                    self._unicode_hex.append(char)
                    if len(self._unicode_hex) == 4:
                        try:
                            unescaped_char = chr(int("".join(self._unicode_hex), 16))
                        except ValueError:
                            unescaped_char = ""
                        self._in_unicode_escape = False
                        self._unicode_hex = []
                        self._escape = False
                        self._current_string.append(unescaped_char)
                        if self._in_target_value:
                            delta_buffer.append(unescaped_char)
                elif self._escape:
                    if char == 'u':
                        self._in_unicode_escape = True
                        self._unicode_hex = []
                    else:
                        unescaped_char = {
                            '"': '"',
                            '\\': '\\',
                            '/': '/',
                            'b': '\b',
                            'f': '\f',
                            'n': '\n',
                            'r': '\r',
                            't': '\t',
                        }.get(char, char)
                        self._escape = False
                        self._current_string.append(unescaped_char)
                        if self._in_target_value:
                            delta_buffer.append(unescaped_char)
                elif char == '\\':
                    self._escape = True
                elif char == '"':
                    self._in_string = False
                    if self._in_target_value:
                        self._in_target_value = False
                        self._last_key = None
                        self._had_previous_sentence = True
                    else:
                        self._candidate_key = "".join(self._current_string)
                else:
                    self._current_string.append(char)
                    if self._in_target_value:
                        delta_buffer.append(char)

        if delta_buffer:
            self.on_delta("".join(delta_buffer))


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
    "1. Chép chính xác chuỗi fact_id từ danh sách; tuyệt đối không tự tạo hoặc sửa fact_id.\n"
    "2. fact_ids phải chứa fact của MỌI số liệu, mọi thứ hạng và mọi kỳ xuất hiện trong câu; chỉ được nêu tên quý nếu fact được trích dẫn có kỳ (period) hoặc kỳ gốc (from_period) là quý đó.\n"
    "3. Viết kỳ đầy đủ theo định dạng: \"quý N/YYYY\".\n"
    "4. Khi nêu số, chép đúng chuỗi \"hien_thi\". Không tự tính, không tự làm tròn, không thêm số khác.\n"
    "5. Mỗi số liệu và thứ hạng phải đứng liền sau tên ngân hàng và chỉ tiêu tương ứng, ví dụ \"HDB đạt 25,4% (hạng 1/10)\"; không viết \"<NGÂN HÀNG> hạng X/Y (Z%)\" và không đặt thứ hạng sau mệnh đề thiếu tên chỉ tiêu.\n"
    "6. Một câu chỉ mô tả một chỉ tiêu và dùng một từ định hướng (tăng / giảm / đi ngang / cao hơn / thấp hơn). Hai chỉ tiêu biến động khác nhau phải tách thành hai câu riêng. Chỉ nói tăng/giảm/liên tục/thu hẹp khi có fact thay đổi; chỉ nói cao hơn/thấp hơn/nhỉnh hơn khi có fact chênh lệch; chỉ nói \"nhất/hạng\" khi có fact hạng.\n"
    "6b. Nếu fact có \"huong\", mô tả chiều đúng bằng cụm đó (ví dụ \"đi ngang\", không viết \"giảm nhẹ\"; \"cao hơn trung vị nhóm\", không viết \"ngang trung vị\"). Khi so sánh hai ngân hàng, nêu rõ tên chỉ tiêu, không chỉ đếm số chỉ tiêu dẫn trước.\n"
    "7. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Được dùng \"hàm ý\" cho phép phân rã như ROE/ROA. Không khuyến nghị mua/bán.\n"
    "8. Câu tối đa 30 từ, giọng báo cáo phân tích, dùng tên chỉ tiêu tiếng Việt, không dùng mã như bank.roe.\n"
    "9. Nếu có \"ung_vien_mau_thuan\", được nêu dữ kiện liên quan nhưng không kết luận nguyên nhân.\n"
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
    "Quy tắc cho câu mới và takeaway:\n"
    "1. Chép chính xác chuỗi fact_id từ danh sách; tuyệt đối không tự tạo hoặc sửa fact_id.\n"
    "2. fact_ids phải chứa fact của MỌI số liệu, mọi thứ hạng và mọi kỳ xuất hiện trong câu; chỉ được nêu tên quý nếu fact trích dẫn có kỳ hoặc kỳ gốc là quý đó.\n"
    "3. Viết kỳ đầy đủ theo định dạng: \"quý N/YYYY\".\n"
    "4. Khi nêu số, chép đúng chuỗi \"hien_thi\". Không tự tính, không tự làm tròn, không thêm số khác.\n"
    "5. Mỗi số liệu và thứ hạng phải đứng liền sau tên ngân hàng và chỉ tiêu tương ứng, ví dụ \"HDB đạt 25,4% (hạng 1/10)\"; không viết \"<NGÂN HÀNG> hạng X/Y (Z%)\" và không đặt thứ hạng sau mệnh đề thiếu tên chỉ tiêu.\n"
    "6. Một câu chỉ mô tả một chỉ tiêu và dùng một từ định hướng (tăng / giảm / đi ngang / cao hơn / thấp hơn). Hai chỉ tiêu biến động khác nhau phải tách thành hai câu riêng.\n"
    "7. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Giới hạn: tối đa 4 hình, 5 luận điểm, 3 callout.\n"
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
    "1. Chép chính xác chuỗi fact_id từ danh sách; tuyệt đối không tự tạo hoặc sửa fact_id.\n"
    "2. fact_ids phải chứa fact của MỌI số liệu, mọi thứ hạng và mọi kỳ xuất hiện trong câu; chỉ được nêu tên quý nếu fact trích dẫn có kỳ hoặc kỳ gốc là quý đó.\n"
    "3. Viết kỳ đầy đủ theo định dạng: \"quý N/YYYY\".\n"
    "4. Khi nêu số, chép đúng chuỗi \"hien_thi\". Không tự tính, không tự làm tròn, không thêm số khác.\n"
    "5. Mỗi số liệu và thứ hạng phải đứng liền sau tên ngân hàng và chỉ tiêu tương ứng, ví dụ \"HDB đạt 25,4% (hạng 1/10)\"; không viết \"<NGÂN HÀNG> hạng X/Y (Z%)\" và không đặt thứ hạng sau mệnh đề thiếu tên chỉ tiêu.\n"
    "6. Một câu chỉ mô tả một chỉ tiêu và dùng một từ định hướng (tăng / giảm / đi ngang / cao hơn / thấp hơn). Hai chỉ tiêu biến động khác nhau phải tách thành hai câu riêng. Chỉ nói tăng/giảm khi có fact thay đổi; chỉ nói cao/thấp hơn khi có fact chênh lệch.\n"
    "6b. Nếu fact có \"huong\", mô tả chiều đúng bằng cụm đó (ví dụ \"đi ngang\", không viết \"giảm nhẹ\"; \"cao hơn trung vị nhóm\", không viết \"ngang trung vị\"). Khi so sánh hai ngân hàng, nêu rõ tên chỉ tiêu, không chỉ đếm số chỉ tiêu dẫn trước.\n"
    "7. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Tối đa 30 từ.\n"
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
    ) -> dict[str, Any]: ...

    def rewrite_sentence(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Mapping[str, Any]],
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
    ) -> dict[str, Any]: ...


class OpenAIAnalysisWriter:
    """OpenAI Responses / chat adapter providing specialist findings, composition, and sentence revision."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        max_output_tokens: int | None = None,
    ) -> None:
        if client is None or not isinstance(model, str) or not model.strip():
            raise AnalysisWriterError("analysis_writer_configuration_invalid")
        self.client = client
        self.model = model.strip()
        self._current_role: str = "orchestrator"
        self.retry_count: int = 0
        self.retries: list[dict[str, Any]] = []
        if max_output_tokens is None:
            from thesis_api.settings import get_settings

            self.max_output_tokens = get_settings().analysis_writer_max_output_tokens
        else:
            self.max_output_tokens = int(max_output_tokens)

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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
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
                on_delta=on_delta,
                on_discard=on_discard,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
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
            on_delta=on_delta,
            on_discard=on_discard,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
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
            on_delta=on_delta,
            on_discard=on_discard,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        self._current_role = role
        try:
            return self._rewrite_sentence_internal(
                role=role,
                question=question,
                sentence=sentence,
                issue=issue,
                facts=facts,
                on_delta=on_delta,
                on_discard=on_discard,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
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
            on_delta=on_delta,
            on_discard=on_discard,
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
        on_delta: Callable[[str], None] | None = None,
        on_discard: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        deltas_emitted = False

        def _track_delta(delta: str) -> None:
            nonlocal deltas_emitted
            if delta:
                deltas_emitted = True
                if on_delta is not None:
                    on_delta(delta)

        if on_delta is not None:
            try:
                if hasattr(self.client, "responses"):
                    request_kwargs: dict[str, Any] = {
                        "model": self.model,
                        "instructions": instructions,
                        "input": json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "max_output_tokens": self.max_output_tokens,
                        "store": False,
                        "stream": True,
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
                    stream_resp = self.client.responses.create(**request_kwargs)
                    emitter = ThrottledDeltaEmitter(_track_delta)
                    extractor = StreamingJsonTextExtractor(emitter.feed)
                    accumulated_chunks: list[str] = []
                    completed_response = None
                    for event in stream_resp:
                        event_type = getattr(event, "type", None)
                        if event_type == "response.output_text.delta":
                            chunk_text = getattr(event, "delta", "") or ""
                            if chunk_text:
                                accumulated_chunks.append(chunk_text)
                                extractor.feed(chunk_text)
                        elif event_type == "response.completed":
                            completed_response = getattr(event, "response", None)
                    emitter.flush()

                    status = getattr(completed_response, "status", None)
                    if status not in (None, "completed"):
                        raise AnalysisWriterError("analysis_writer_response_incomplete")

                    output_text = getattr(completed_response, "output_text", None) if completed_response is not None else None
                    if not output_text:
                        output_text = "".join(accumulated_chunks)

                    if not isinstance(output_text, str) or not output_text.strip():
                        raise AnalysisWriterError("analysis_writer_output_missing")

                    clean_text = _clean_json_text(output_text)
                    decoded = json.loads(clean_text)
                    if isinstance(decoded, dict):
                        return _strip_inline_fact_refs(decoded)
                    raise AnalysisWriterError("analysis_writer_output_invalid")
                else:
                    messages = [
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
                    ]
                    kwargs: dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_output_tokens,
                        "stream": True,
                    }
                    if schema is not None:
                        kwargs["response_format"] = {
                            "type": "json_schema",
                            "json_schema": {"name": name, "schema": schema, "strict": True},
                        }
                    else:
                        kwargs["response_format"] = {"type": "json_object"}
                    stream_resp = self.client.chat.completions.create(**kwargs)
                    emitter = ThrottledDeltaEmitter(_track_delta)
                    extractor = StreamingJsonTextExtractor(emitter.feed)
                    accumulated_chunks: list[str] = []
                    for chunk in stream_resp:
                        chunk_text = ""
                        if hasattr(chunk, "choices") and chunk.choices:
                            delta_obj = getattr(chunk.choices[0], "delta", None)
                            if delta_obj:
                                chunk_text = getattr(delta_obj, "content", "") or ""
                        elif isinstance(chunk, dict):
                            choices = chunk.get("choices", [])
                            if choices:
                                chunk_text = choices[0].get("delta", {}).get("content", "") or ""
                        if chunk_text:
                            accumulated_chunks.append(chunk_text)
                            extractor.feed(chunk_text)
                    emitter.flush()
                    output_text = "".join(accumulated_chunks)
                    if output_text.strip():
                        clean_text = _clean_json_text(output_text)
                        decoded = json.loads(clean_text)
                        if isinstance(decoded, dict):
                            return _strip_inline_fact_refs(decoded)
                        raise AnalysisWriterError("analysis_writer_output_invalid")
            except Exception as stream_exc:
                logger.warning("Writer streaming attempt failed; falling back to non-streamed call: %s", stream_exc)
                self.retry_count += 1
                self.retries.append({"name": name, "error": str(stream_exc)})
                if hasattr(self.client, "_tracker"):
                    getattr(self.client, "_tracker").discard_last_call(reason=f"stream_failed: {stream_exc}")
                if deltas_emitted and on_discard is not None:
                    try:
                        on_discard()
                    except Exception as discard_exc:
                        logger.warning("on_discard failed: %s", discard_exc)

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                if hasattr(self.client, "responses"):
                    request_kwargs: dict[str, Any] = {
                        "model": self.model,
                        "instructions": instructions,
                        "input": json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "max_output_tokens": self.max_output_tokens,
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
                        "max_tokens": self.max_output_tokens,
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
