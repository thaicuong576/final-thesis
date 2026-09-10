"""Role-isolated, read-only tools over the promoted Gold snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .agent_runtime import AgentToolCall
from .query import EvidenceQuery, get_company_metrics, get_evidence, get_macro_context, get_sector_benchmarks
from .workload_contract import CompositeWorkloadSpec


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompanyMetricArguments(ToolArguments):
    ticker: str = Field(min_length=1, max_length=12)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    metric_ids: list[str] = Field(min_length=1, max_length=16)


class CompanyMetricBatchArguments(ToolArguments):
    tickers: list[str] = Field(min_length=1, max_length=12)
    periods: list[str] = Field(min_length=1, max_length=8)
    metric_ids: list[str] = Field(min_length=1, max_length=16)


class SectorBenchmarkArguments(ToolArguments):
    sector: str = Field(min_length=1, max_length=32)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    metric_ids: list[str] = Field(min_length=1, max_length=16)
    tickers: list[str] = Field(min_length=1, max_length=32)


class SectorBenchmarkBatchArguments(ToolArguments):
    sector: Literal["bank"]
    periods: list[str] = Field(min_length=1, max_length=8)
    metric_ids: list[str] = Field(min_length=1, max_length=16)
    tickers: list[str] = Field(min_length=1, max_length=32)


class MacroArguments(ToolArguments):
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    indicator_ids: list[str] = Field(min_length=1, max_length=16)


class EvidenceArguments(ToolArguments):
    source_ids: list[str] = Field(min_length=1, max_length=32)
    ticker: str = Field(min_length=1, max_length=12)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")


class EvidenceBatchArguments(ToolArguments):
    source_ids: list[str] = Field(min_length=1, max_length=32)
    tickers: list[str] = Field(min_length=1, max_length=12)
    periods: list[str] = Field(min_length=1, max_length=8)


class SourceMetadataArguments(ToolArguments):
    source_ids: list[str] = Field(min_length=1, max_length=32)


class MissingConflictArguments(ToolArguments):
    ticker: str = Field(min_length=1, max_length=12)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    metric_id: str = Field(min_length=1, max_length=64)


class MissingConflictBatchArguments(ToolArguments):
    tickers: list[str] = Field(min_length=1, max_length=12)
    periods: list[str] = Field(min_length=1, max_length=8)
    metric_ids: list[str] = Field(min_length=1, max_length=16)


ARGUMENT_MODELS: dict[str, type[ToolArguments]] = {
    "get_company_metrics": CompanyMetricArguments,
    "get_company_metrics_batch": CompanyMetricBatchArguments,
    "get_sector_benchmarks": SectorBenchmarkArguments,
    "get_sector_benchmarks_batch": SectorBenchmarkBatchArguments,
    "get_macro_context": MacroArguments,
    "get_evidence": EvidenceArguments,
    "get_evidence_batch": EvidenceBatchArguments,
    "get_source_metadata": SourceMetadataArguments,
    "check_missing_or_conflict": MissingConflictArguments,
    "check_missing_or_conflict_batch": MissingConflictBatchArguments,
}

ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "single_agent": (
        "get_company_metrics",
        "get_sector_benchmarks",
        "get_macro_context",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
    "company": (
        "get_company_metrics",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
    "sector": (
        "get_sector_benchmarks",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
    "macro": (
        "get_macro_context",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
    "orchestrator": (
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
    "verification": (
        "get_company_metrics",
        "get_sector_benchmarks",
        "get_macro_context",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
    ),
}

COMPOSITE_ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "single_agent": (
        "get_company_metrics",
        "get_sector_benchmarks",
        "get_macro_context",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
        "get_company_metrics_batch",
        "get_sector_benchmarks_batch",
        "get_evidence_batch",
        "check_missing_or_conflict_batch",
    ),
    "company": (
        "get_company_metrics",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
        "get_company_metrics_batch",
        "get_evidence_batch",
        "check_missing_or_conflict_batch",
    ),
    "sector": (
        "get_sector_benchmarks",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
        "get_sector_benchmarks_batch",
        "get_evidence_batch",
        "check_missing_or_conflict_batch",
    ),
    "orchestrator": (
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
        "get_evidence_batch",
        "check_missing_or_conflict_batch",
    ),
    "verification": (
        "get_company_metrics",
        "get_sector_benchmarks",
        "get_macro_context",
        "get_evidence",
        "get_source_metadata",
        "check_missing_or_conflict",
        "get_company_metrics_batch",
        "get_sector_benchmarks_batch",
        "get_evidence_batch",
        "check_missing_or_conflict_batch",
    ),
}

TOOL_DESCRIPTIONS = {
    "get_company_metrics": "Read accepted issuer metrics for a declared ticker and period from the Gold snapshot.",
    "get_company_metrics_batch": "Read accepted issuer metrics for all declared ticker-period combinations in one bounded batch.",
    "get_sector_benchmarks": "Read deterministic accepted peer medians for the declared sector, period, and peer set.",
    "get_sector_benchmarks_batch": "Read deterministic accepted peer medians for all declared periods in one bounded batch.",
    "get_macro_context": "Read accepted macro observations for declared indicators and period.",
    "get_evidence": "Read page-aware evidence snippets for accepted source IDs and the declared issuer-period.",
    "get_evidence_batch": "Read page-aware evidence snippets for all declared issuer-period combinations in one bounded batch.",
    "get_source_metadata": "Read safe metadata for accepted source IDs without exposing local paths.",
    "check_missing_or_conflict": "Check one Gold cell and return valid, missing, unaccepted, or conflict state without guessing.",
    "check_missing_or_conflict_batch": "Check all declared Gold cells and return valid, missing, unaccepted, or conflict states without guessing.",
}


class ToolExecutionError(ValueError):
    """A model tool request cannot cross the local read-only boundary."""


def validate_composite_tool_scope(
    arguments: ToolArguments,
    spec: CompositeWorkloadSpec,
    role: str,
    *,
    allowed_source_ids: Sequence[str] | None = None,
) -> None:
    """Validate a tool request against a frozen composite workload.

    Source IDs are not part of the analytical workload itself, so callers may
    pass the source IDs discovered from the same scoped Gold results. When that
    set is provided, evidence and metadata calls must stay inside it.
    """

    if role not in ROLE_TOOLS:
        raise ToolExecutionError("unknown role")
    if isinstance(arguments, CompanyMetricArguments):
        if arguments.ticker not in spec.issuers or arguments.period not in spec.periods:
            raise ToolExecutionError("company query outside composite scope")
        if not set(arguments.metric_ids).issubset(spec.metric_ids):
            raise ToolExecutionError("company metric outside composite scope")
        return
    if isinstance(arguments, CompanyMetricBatchArguments):
        if not set(arguments.tickers).issubset(spec.issuers) or not set(arguments.periods).issubset(spec.periods):
            raise ToolExecutionError("company batch outside composite scope")
        if not set(arguments.metric_ids).issubset(spec.metric_ids):
            raise ToolExecutionError("company metric outside composite scope")
        return
    if isinstance(arguments, SectorBenchmarkArguments):
        if arguments.sector != "bank" or arguments.period not in spec.periods:
            raise ToolExecutionError("sector query outside composite scope")
        if not set(arguments.metric_ids).issubset(spec.metric_ids):
            raise ToolExecutionError("sector metric outside composite scope")
        if not set(arguments.tickers).issubset(spec.peer_tickers):
            raise ToolExecutionError("peer ticker outside composite scope")
        return
    if isinstance(arguments, SectorBenchmarkBatchArguments):
        if arguments.sector != "bank" or not set(arguments.periods).issubset(spec.periods):
            raise ToolExecutionError("sector batch outside composite scope")
        if not set(arguments.metric_ids).issubset(spec.metric_ids):
            raise ToolExecutionError("sector metric outside composite scope")
        if not set(arguments.tickers).issubset(spec.peer_tickers):
            raise ToolExecutionError("peer ticker outside composite scope")
        return
    if isinstance(arguments, MacroArguments):
        if arguments.period not in spec.periods:
            raise ToolExecutionError("macro period outside composite scope")
        if not set(arguments.indicator_ids).issubset(spec.macro_indicator_ids):
            raise ToolExecutionError("macro indicator outside composite scope")
        return
    if isinstance(arguments, EvidenceArguments):
        if arguments.ticker not in spec.issuers or arguments.period not in spec.periods:
            raise ToolExecutionError("evidence query outside composite scope")
        if allowed_source_ids is not None and not set(arguments.source_ids).issubset(allowed_source_ids):
            raise ToolExecutionError("evidence source outside composite scope")
        return
    if isinstance(arguments, EvidenceBatchArguments):
        if not set(arguments.tickers).issubset(spec.issuers) or not set(arguments.periods).issubset(spec.periods):
            raise ToolExecutionError("evidence batch outside composite scope")
        if allowed_source_ids is not None and not set(arguments.source_ids).issubset(allowed_source_ids):
            raise ToolExecutionError("evidence source outside composite scope")
        return
    if isinstance(arguments, MissingConflictArguments):
        if arguments.ticker not in spec.issuers or arguments.period not in spec.periods:
            raise ToolExecutionError("missing query outside composite scope")
        if arguments.metric_id not in spec.metric_ids:
            raise ToolExecutionError("missing metric outside composite scope")
        return
    if isinstance(arguments, MissingConflictBatchArguments):
        if not set(arguments.tickers).issubset(spec.issuers) or not set(arguments.periods).issubset(spec.periods):
            raise ToolExecutionError("missing batch outside composite scope")
        if not set(arguments.metric_ids).issubset(spec.metric_ids):
            raise ToolExecutionError("missing metric outside composite scope")
        return
    if isinstance(arguments, SourceMetadataArguments):
        if allowed_source_ids is not None and not set(arguments.source_ids).issubset(allowed_source_ids):
            raise ToolExecutionError("metadata source outside composite scope")
        return
    raise ToolExecutionError("unsupported composite tool arguments")


def _source_tiers(source_policy_id: str) -> tuple[str, ...]:
    if source_policy_id in {"primary-only-v1", "fixture-primary-only-v1", "offline-fixture-primary-only-v1"}:
        return ("primary",)
    raise ToolExecutionError("unknown source policy")


def _connection(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _quality_counts(value: Any) -> tuple[int, int, int]:
    valid = missing = conflict = 0
    if isinstance(value, dict):
        status = value.get("status")
        if status == "conflict":
            conflict += 1
        elif status in {"missing", "unaccepted"}:
            missing += 1
        for field in ("metrics", "sector_benchmarks"):
            values = value.get(field)
            if isinstance(values, dict):
                for item in values.values():
                    if item is None:
                        missing += 1
                    else:
                        valid += 1
        if isinstance(value.get("observation_ids"), list):
            valid += len(value["observation_ids"])
    elif isinstance(value, list):
        valid += len(value)
    return valid, missing, conflict


@dataclass(frozen=True)
class ToolExecution:
    output: dict[str, Any] | list[dict[str, Any]]
    trace: AgentToolCall


class GoldToolRuntime:
    """Execute only bounded, parameterized, read-only Gold queries."""

    def __init__(
        self,
        db_path: Path,
        *,
        ticker: str | None = None,
        tickers: Sequence[str] | None = None,
        periods: Sequence[str],
        metric_ids: Sequence[str],
        macro_indicator_ids: Sequence[str],
        peer_tickers: Sequence[str],
        source_policy_id: str,
        composite_tools: bool = False,
    ) -> None:
        self.db_path = db_path.resolve()
        declared_tickers = tuple(tickers or ((ticker,) if ticker else ()))
        if not declared_tickers or any(not item for item in declared_tickers):
            raise ValueError("at least one declared ticker is required")
        if len(set(declared_tickers)) != len(declared_tickers):
            raise ValueError("declared tickers must be unique")
        self.tickers = frozenset(declared_tickers)
        self.allowed_tickers = self.tickers
        self.ticker = ticker or declared_tickers[0]
        self.periods = frozenset(periods)
        self.metric_ids = frozenset(metric_ids)
        self.macro_indicator_ids = frozenset(macro_indicator_ids)
        self.peer_tickers = frozenset(peer_tickers)
        self.source_tiers = _source_tiers(source_policy_id)
        self.composite_tools = composite_tools

    def _ticker_in_scope(self, ticker: str) -> bool:
        return ticker in self.tickers

    def definitions(self, role: str) -> list[dict[str, Any]]:
        registry = COMPOSITE_ROLE_TOOLS if self.composite_tools else ROLE_TOOLS
        names = registry.get(role)
        if names is None:
            raise ToolExecutionError("unknown role")
        if not self.macro_indicator_ids:
            names = tuple(name for name in names if name != "get_macro_context")
        definitions: list[dict[str, Any]] = []
        for name in names:
            schema = ARGUMENT_MODELS[name].model_json_schema()
            schema.pop("title", None)
            definitions.append(
                {
                    "type": "function",
                    "name": name,
                    "description": TOOL_DESCRIPTIONS[name],
                    "parameters": schema,
                    "strict": True,
                }
            )
        return definitions

    def _validate_scope(self, name: str, arguments: ToolArguments) -> None:
        if isinstance(arguments, CompanyMetricArguments):
            if not self._ticker_in_scope(arguments.ticker) or arguments.period not in self.periods:
                raise ToolExecutionError("company query outside request scope")
            if not set(arguments.metric_ids).issubset(self.metric_ids):
                raise ToolExecutionError("company metric outside request scope")
        elif isinstance(arguments, CompanyMetricBatchArguments):
            if not set(arguments.tickers).issubset(self.tickers) or not set(arguments.periods).issubset(self.periods):
                raise ToolExecutionError("company batch outside request scope")
            if not set(arguments.metric_ids).issubset(self.metric_ids):
                raise ToolExecutionError("company metric outside request scope")
        elif isinstance(arguments, SectorBenchmarkArguments):
            if arguments.sector != "bank":
                raise ToolExecutionError("sector name outside request scope")
            if arguments.period not in self.periods:
                raise ToolExecutionError("sector period outside request scope")
            if not set(arguments.metric_ids).issubset(self.metric_ids):
                raise ToolExecutionError("sector metric outside request scope")
            if not set(arguments.tickers).issubset(self.peer_tickers):
                raise ToolExecutionError("peer ticker outside request scope")
        elif isinstance(arguments, SectorBenchmarkBatchArguments):
            if arguments.sector != "bank":
                raise ToolExecutionError("sector name outside request scope")
            if not set(arguments.periods).issubset(self.periods):
                raise ToolExecutionError("sector batch outside request scope")
            if not set(arguments.metric_ids).issubset(self.metric_ids):
                raise ToolExecutionError("sector metric outside request scope")
            if not set(arguments.tickers).issubset(self.peer_tickers):
                raise ToolExecutionError("peer ticker outside request scope")
        elif isinstance(arguments, MacroArguments):
            if arguments.period not in self.periods:
                raise ToolExecutionError("macro period outside request scope")
            if not set(arguments.indicator_ids).issubset(self.macro_indicator_ids):
                raise ToolExecutionError("macro indicator outside request scope")
        elif isinstance(arguments, EvidenceArguments):
            if not self._ticker_in_scope(arguments.ticker) or arguments.period not in self.periods:
                raise ToolExecutionError("evidence query outside request scope")
        elif isinstance(arguments, EvidenceBatchArguments):
            if not set(arguments.tickers).issubset(self.tickers) or not set(arguments.periods).issubset(self.periods):
                raise ToolExecutionError("evidence batch outside request scope")
        elif isinstance(arguments, MissingConflictArguments):
            if not self._ticker_in_scope(arguments.ticker) or arguments.period not in self.periods:
                raise ToolExecutionError("missing query outside request scope")
            if arguments.metric_id not in self.metric_ids:
                raise ToolExecutionError("missing metric outside request scope")
        elif isinstance(arguments, MissingConflictBatchArguments):
            if not set(arguments.tickers).issubset(self.tickers) or not set(arguments.periods).issubset(self.periods):
                raise ToolExecutionError("missing batch outside request scope")
            if not set(arguments.metric_ids).issubset(self.metric_ids):
                raise ToolExecutionError("missing metric outside request scope")

    def execute(self, role: str, name: str, raw_arguments: dict[str, Any]) -> ToolExecution:
        registry = COMPOSITE_ROLE_TOOLS if self.composite_tools else ROLE_TOOLS
        allowed = registry.get(role)
        if allowed is None or name not in allowed:
            raise ToolExecutionError("tool not allowed for role")
        model = ARGUMENT_MODELS[name]
        try:
            arguments = model.model_validate(raw_arguments)
        except ValueError as exc:
            raise ToolExecutionError("tool arguments invalid") from exc
        self._validate_scope(name, arguments)
        data = self._run(name, arguments)
        encoded = _json(data)
        valid, missing, conflict = _quality_counts(data)
        trace = AgentToolCall(
            name=name,
            arguments=arguments.model_dump(mode="json"),
            result_sha256=sha256(encoded.encode("utf-8")).hexdigest(),
            valid_count=valid,
            missing_count=missing,
            conflict_count=conflict,
        )
        return ToolExecution(data, trace)

    def _run(self, name: str, arguments: ToolArguments) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(arguments, CompanyMetricArguments):
            return get_company_metrics(
                self.db_path, arguments.ticker, arguments.period, arguments.metric_ids,
                source_tiers=self.source_tiers,
            ).model_dump(mode="json")
        if isinstance(arguments, CompanyMetricBatchArguments):
            return [
                get_company_metrics(
                    self.db_path,
                    ticker,
                    period,
                    arguments.metric_ids,
                    source_tiers=self.source_tiers,
                ).model_dump(mode="json")
                for ticker in arguments.tickers
                for period in arguments.periods
            ]
        if isinstance(arguments, SectorBenchmarkArguments):
            return get_sector_benchmarks(
                self.db_path, arguments.sector, arguments.period, arguments.metric_ids,
                tickers=arguments.tickers, source_tiers=self.source_tiers,
            ).model_dump(mode="json")
        if isinstance(arguments, SectorBenchmarkBatchArguments):
            return [
                get_sector_benchmarks(
                    self.db_path,
                    arguments.sector,
                    period,
                    arguments.metric_ids,
                    tickers=arguments.tickers,
                    source_tiers=self.source_tiers,
                ).model_dump(mode="json")
                for period in arguments.periods
            ]
        if isinstance(arguments, MacroArguments):
            return get_macro_context(
                self.db_path, arguments.period, arguments.indicator_ids,
                source_tiers=self.source_tiers,
            ).model_dump(mode="json")
        if isinstance(arguments, EvidenceArguments):
            return [
                item.model_dump(mode="json")
                for item in get_evidence(
                    self.db_path,
                    arguments.source_ids,
                    EvidenceQuery(ticker=arguments.ticker, period=arguments.period),
                    source_tiers=self.source_tiers,
                )
            ]
        if isinstance(arguments, EvidenceBatchArguments):
            grouped: list[dict[str, Any]] = []
            for ticker in arguments.tickers:
                for period in arguments.periods:
                    grouped.append(
                        {
                            "ticker": ticker,
                            "period": period,
                            "evidence": [
                                item.model_dump(mode="json")
                                for item in get_evidence(
                                    self.db_path,
                                    arguments.source_ids,
                                    EvidenceQuery(ticker=ticker, period=period),
                                    source_tiers=self.source_tiers,
                                )
                            ],
                        }
                    )
            return grouped
        if isinstance(arguments, SourceMetadataArguments):
            return self._source_metadata(arguments.source_ids)
        if isinstance(arguments, MissingConflictArguments):
            return self._missing_or_conflict(arguments)
        if isinstance(arguments, MissingConflictBatchArguments):
            return [
                self._missing_or_conflict(
                    MissingConflictArguments(
                        ticker=ticker,
                        period=period,
                        metric_id=metric_id,
                    )
                )
                for ticker in arguments.tickers
                for period in arguments.periods
                for metric_id in arguments.metric_ids
            ]
        raise ToolExecutionError("unsupported tool")

    def _source_metadata(self, source_ids: Sequence[str]) -> list[dict[str, Any]]:
        marks = ",".join("?" for _ in source_ids)
        connection = _connection(self.db_path)
        try:
            rows = connection.execute(
                f"""SELECT source_id, source_type, source_tier, source_url,
                    retrieved_at, content_hash, publisher, quality_status, notes
                    FROM source_records
                    WHERE source_id IN ({marks}) AND quality_status = 'valid'
                      AND source_tier IN ({','.join('?' for _ in self.source_tiers)})
                    ORDER BY source_id""",
                (*source_ids, *self.source_tiers),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "source_id": row[0], "source_type": row[1], "source_tier": row[2],
                "source_url": row[3], "retrieved_at": row[4], "content_hash": row[5],
                "publisher": row[6], "quality_status": row[7], "notes": row[8],
            }
            for row in rows
        ]

    def _missing_or_conflict(self, arguments: MissingConflictArguments) -> dict[str, Any]:
        connection = _connection(self.db_path)
        try:
            rows = connection.execute(
                """SELECT metric.observation_id, metric.value, metric.unit,
                    metric.source_id, metric.quality_status, metric.reason,
                    source.quality_status, source.source_tier
                    FROM metric_observations AS metric
                    LEFT JOIN source_records AS source ON source.source_id = metric.source_id
                    WHERE metric.ticker = ? AND metric.period = ? AND metric.metric = ?
                    ORDER BY metric.observation_id""",
                (arguments.ticker, arguments.period, arguments.metric_id),
            ).fetchall()
        finally:
            connection.close()
        accepted = [
            row for row in rows
            if row[4] == "valid" and row[1] is not None
            and row[6] == "valid" and row[7] in self.source_tiers
        ]
        observation_ids = [row[0] for row in accepted]
        source_ids = sorted({row[3] for row in accepted if row[3]})
        if len({row[1] for row in accepted}) > 1:
            status = "conflict"
            reason = "multiple accepted observations have different values"
        elif accepted:
            status = "valid"
            reason = None
        elif any(row[4] == "missing" for row in rows):
            status = "missing"
            reason = next((row[5] for row in rows if row[4] == "missing" and row[5]), "missing observation")
        else:
            status = "unaccepted"
            reason = "no accepted observation under the source policy"
        result: dict[str, Any] = {
            "ticker": arguments.ticker,
            "period": arguments.period,
            "metric_id": arguments.metric_id,
            "status": status,
            "reason": reason,
            "observation_ids": observation_ids,
            "source_ids": source_ids,
        }
        if accepted:
            result.update({"value": accepted[0][1], "unit": accepted[0][2], "metric_period": arguments.period})
        return result
