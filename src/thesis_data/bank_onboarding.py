"""Provider-neutral validation for reviewed bank onboarding packets.

Packets are exchange records, not database schemas. They preserve raw facts,
source locations, review decisions, formula lineage, and explicit missingness
before a candidate is materialized through the generic canonical provider.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetSource,
    ObservationEvidenceRef,
    ObservationReview,
    canonical_observation_id,
)
from .evidence_contract import DatasetDocument
from .metrics import (
    calculate_llr,
    calculate_npl,
    calculate_npl_g35_balance,
    calculate_parent_attributable_equity,
    calculate_roa_ttm,
    calculate_roe_ttm,
)
from .onboarding_contract import (
    DatasetSnapshotStatus,
    OnboardingValidationReport,
    OnboardingValidationStatus,
    RawDatasetDescriptor,
    build_snapshot_metadata,
)
from .onboarding_validation import CanonicalDatasetCandidate
from .schema import QualityStatus


BANK_PACKET_SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
_PRIMARY_METRICS = {
    "bank.npl_g35",
    "bank.llr_coverage",
    "bank.roa",
    "bank.roe",
}
_METRIC_LABELS = {
    "bank.npl_g35": "Share of loans in groups 3–5",
    "bank.llr_coverage": "Provision coverage of group 3–5 NPL",
    "bank.roa": "Return on assets",
    "bank.roe": "Return on parent-attributable equity",
}


class BankPacketSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    kind: Literal["primary_filing", "uploaded_csv", "supplementary_document"]
    source_tier: Literal["primary", "user_supplied", "cross_check", "context", "fallback"]
    artifact_ref: str = Field(min_length=1)
    source_url: str | None = None
    content_sha256: str
    publisher: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    document_type: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "BankPacketSource":
        if not _SHA256_PATTERN.fullmatch(self.content_sha256):
            raise ValueError("source content_sha256 must be a 64-character SHA-256")
        if not self.artifact_ref.strip() or Path(self.artifact_ref).is_absolute():
            raise ValueError("artifact_ref must be a non-empty relative path")
        if self.source_tier == "user_supplied" and self.kind != "uploaded_csv":
            raise ValueError("user_supplied source tier is reserved for uploaded CSV")
        if self.kind == "primary_filing" and self.source_tier != "primary":
            raise ValueError("primary_filing source must have primary tier")
        try:
            retrieved_at = datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("source retrieved_at must be an ISO date-time") from exc
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("source retrieved_at must include a timezone")
        if self.kind == "primary_filing" and not self.source_url:
            raise ValueError("primary filing source requires an official URL")
        if self.source_url is not None and not urlparse(self.source_url).scheme:
            raise ValueError("source_url must be a URI")
        return self


class BankPacketEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)


class BankPacketReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
    decision: Literal["matched_reported_value", "reproduced_derived_value"]
    primary_evidence: tuple[BankPacketEvidence, ...] = Field(min_length=1)
    resolution_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_review(self) -> "BankPacketReview":
        refs = [(item.source_id, item.source_locator) for item in self.primary_evidence]
        if len(refs) != len(set(refs)):
            raise ValueError("review primary evidence references must be unique")
        try:
            reviewed_at = datetime.fromisoformat(self.reviewed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("reviewed_at must be an ISO date-time") from exc
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return self


class BankPacketFormula(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    formula_version: str = Field(min_length=1)
    input_observation_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_inputs(self) -> "BankPacketFormula":
        if len(self.input_observation_ids) != len(set(self.input_observation_ids)):
            raise ValueError("formula input observation IDs must be unique")
        return self


class BankPacketObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    value: float | None = Field(allow_inf_nan=False)
    unit: str | None
    period_basis: Literal["point_in_time", "quarter_only", "ytd", "annual", "ttm"] | None
    reporting_scope: Literal["consolidated", "separate", "system", "unknown"]
    quality_status: Literal["pending_validation", "valid", "missing", "conflicting", "invalid"]
    candidate_source_id: str | None = None
    candidate_locator: str | None = None
    review: BankPacketReview | None = None
    formula: BankPacketFormula | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "BankPacketObservation":
        if not re.fullmatch(r"(?:\d{4}_Q[1-4]|FY\d{4})", self.period_id):
            raise ValueError("period_id must use YYYY_Qn or FYyyyy")
        if self.quality_status == "valid":
            if self.value is None or not self.unit or self.period_basis is None:
                raise ValueError("valid observation requires a value, unit, and period basis")
            if self.reporting_scope == "unknown":
                raise ValueError("valid observation requires a known reporting scope")
            if self.review is None:
                raise ValueError("valid observation requires source reconciliation review")
            if not self.candidate_source_id or not self.candidate_locator:
                raise ValueError("valid observation requires candidate source and locator")
            if self.review.decision == "reproduced_derived_value" and self.formula is None:
                raise ValueError("reproduced derived observation requires formula lineage")
            if self.review.decision == "matched_reported_value" and self.formula is not None:
                raise ValueError("matched reported observation cannot carry a derived formula")
        elif self.quality_status == "missing":
            if self.value is not None or not self.reason:
                raise ValueError("missing observation requires null value and reason")
        elif self.value is None and not self.reason:
            raise ValueError("non-valid null observation requires a reason")
        if self.metric_id.startswith("company."):
            raise ValueError("bank packets must use bank.* metric IDs from the metric dictionary")
        if self.metric_id not in _PRIMARY_METRICS and not self.metric_id.startswith("bank.input."):
            raise ValueError("bank packet metric is outside the bank dictionary and support-input namespace")
        if self.quality_status == "valid":
            expected_unit = "percent" if self.metric_id in _PRIMARY_METRICS else "billion_vnd"
            if self.unit != expected_unit:
                raise ValueError(f"valid {self.metric_id} observation must use {expected_unit}")
            expected_basis = {
                "bank.npl_g35": "point_in_time",
                "bank.llr_coverage": "point_in_time",
                "bank.roa": "ttm",
                "bank.roe": "ttm",
            }.get(self.metric_id)
            if expected_basis is not None and self.period_basis != expected_basis:
                raise ValueError(f"{self.metric_id} observation has an incompatible period basis")
        return self


class BankOnboardingPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    packet_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    sources: tuple[BankPacketSource, ...] = Field(min_length=1)
    observations: tuple[BankPacketObservation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "BankOnboardingPacket":
        source_ids = [item.source_id for item in self.sources]
        observation_ids = [item.observation_id for item in self.observations]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("packet source IDs must be unique")
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("packet observation IDs must be unique")
        source_map = {item.source_id: item for item in self.sources}
        observation_map = {item.observation_id: item for item in self.observations}
        declared_primary_metrics = {
            (item.metric_id, item.period_id)
            for item in self.observations
            if item.metric_id in _PRIMARY_METRICS
        }
        target_periods = {
            period_id
            for metric_id, period_id in declared_primary_metrics
            if metric_id in _PRIMARY_METRICS
        }
        if len(target_periods) != 1 or {
            metric_id for metric_id, _period_id in declared_primary_metrics
        } != _PRIMARY_METRICS:
            raise ValueError("packet must represent each dictionary primary bank metric for one target period")
        for observation in self.observations:
            if observation.quality_status == "valid":
                for evidence in observation.review.primary_evidence:
                    source = source_map.get(evidence.source_id)
                    if source is None:
                        raise ValueError("review primary evidence source does not resolve")
                    if source.source_tier != "primary" or source.kind != "primary_filing":
                        raise ValueError("accepted review evidence must resolve to a primary filing")
                candidate_source = source_map.get(observation.candidate_source_id or "")
                if candidate_source is None:
                    raise ValueError("valid observation candidate source does not resolve")
                if observation.candidate_source_id not in {
                    item.source_id for item in observation.review.primary_evidence
                }:
                    raise ValueError("valid observation locator must refer to reviewed primary evidence")
                if observation.candidate_locator not in {
                    item.source_locator for item in observation.review.primary_evidence
                }:
                    raise ValueError("valid candidate locator must be present in review evidence")
                if observation.formula is not None:
                    for reference in observation.formula.input_observation_ids:
                        input_observation = observation_map.get(reference)
                        if input_observation is None:
                            raise ValueError("formula input observation does not resolve")
                        if input_observation.quality_status != "valid":
                            raise ValueError("formula input observation must be valid")
            elif observation.quality_status == "pending_validation" and observation.value is not None:
                # Pending numeric rows are retained as candidates, but cannot
                # feed any accepted derived row.
                pass
        _validate_packet_calculations(observation_map)
        return self


def _at(observations: dict[str, BankPacketObservation], metric_id: str, period_id: str) -> BankPacketObservation:
    matches = [
        item for item in observations.values()
        if item.metric_id == metric_id and item.period_id == period_id and item.quality_status == "valid"
    ]
    if len(matches) != 1:
        raise ValueError(f"formula requires one valid {metric_id} observation for {period_id}")
    return matches[0]


def _same_quarter_previous_year(period_id: str) -> str:
    try:
        year, quarter = period_id.split("_Q", 1)
        return f"{int(year) - 1}_Q{int(quarter)}"
    except (ValueError, TypeError) as exc:
        raise ValueError("TTM formula period must use YYYY_Qn") from exc


def _validate_packet_calculations(observations: dict[str, BankPacketObservation]) -> None:
    """Reproduce the four dictionary ratios before a packet can be loaded."""

    for observation in observations.values():
        if observation.quality_status != "valid" or observation.formula is None:
            continue
        inputs = [observations[item] for item in observation.formula.input_observation_ids]
        values = {item.metric_id: item.value for item in inputs}
        period = observation.period_id
        if observation.metric_id == "bank.npl_g35":
            expected_input_ids = {
                _at(observations, metric, period).observation_id
                for metric in (
                    "bank.input.npl_group_3_balance",
                    "bank.input.npl_group_4_balance",
                    "bank.input.npl_group_5_balance",
                    "bank.input.gross_customer_loans",
                )
            }
            _validate_formula_inputs(observation, expected_input_ids)
            result = calculate_npl(
                values.get("bank.input.npl_group_3_balance"),
                values.get("bank.input.npl_group_4_balance"),
                values.get("bank.input.npl_group_5_balance"),
                values.get("bank.input.gross_customer_loans"),
            )
        elif observation.metric_id == "bank.llr_coverage":
            expected_input_ids = {
                _at(observations, metric, period).observation_id
                for metric in (
                    "bank.input.loan_loss_provisions",
                    "bank.input.npl_g35_balance",
                )
            }
            _validate_formula_inputs(observation, expected_input_ids)
            result = calculate_llr(
                values.get("bank.input.loan_loss_provisions"),
                values.get("bank.input.npl_g35_balance"),
            )
        elif observation.metric_id in {"bank.roa", "bank.roe"}:
            prior_period = _same_quarter_previous_year(period)
            profit_metric = (
                "bank.input.profit_after_tax"
                if observation.metric_id == "bank.roa"
                else "bank.input.parent_attributable_profit"
            )
            denominator_metric = (
                "bank.input.total_assets"
                if observation.metric_id == "bank.roa"
                else "bank.input.parent_attributable_equity"
            )
            current_profit = _at(observations, profit_metric, period).value
            prior_profit_observation = _at(observations, profit_metric, prior_period)
            prior_profit = prior_profit_observation.value
            current_denominator_observation = _at(observations, denominator_metric, period)
            prior_denominator_observation = _at(observations, denominator_metric, prior_period)
            current_denominator = current_denominator_observation.value
            prior_denominator = prior_denominator_observation.value
            _validate_formula_inputs(
                observation,
                {
                    _at(observations, profit_metric, period).observation_id,
                    prior_profit_observation.observation_id,
                    current_denominator_observation.observation_id,
                    prior_denominator_observation.observation_id,
                },
            )
            average_denominator = (Decimal(str(current_denominator)) + Decimal(str(prior_denominator))) / Decimal("2")
            if observation.metric_id == "bank.roa":
                result = calculate_roa_ttm(
                    current_profit,
                    prior_profit,
                    prior_profit,
                    average_denominator,
                )
            else:
                result = calculate_roe_ttm(
                    current_profit,
                    prior_profit,
                    prior_profit,
                    average_denominator,
                )
        elif observation.metric_id == "bank.input.npl_g35_balance":
            expected_input_ids = {
                _at(observations, metric, period).observation_id
                for metric in (
                    "bank.input.npl_group_3_balance",
                    "bank.input.npl_group_4_balance",
                    "bank.input.npl_group_5_balance",
                )
            }
            _validate_formula_inputs(observation, expected_input_ids)
            result = calculate_npl_g35_balance(
                values.get("bank.input.npl_group_3_balance"),
                values.get("bank.input.npl_group_4_balance"),
                values.get("bank.input.npl_group_5_balance"),
            )
            if result.value is None or result.formula_version != observation.formula.formula_version:
                raise ValueError("NPL balance formula version or inputs are unsupported")
            if observation.value is None or abs(Decimal(str(observation.value)) - result.value) > Decimal("0.0000001"):
                raise ValueError("NPL balance does not reproduce from accepted group balances")
            continue
        elif observation.metric_id == "bank.input.parent_attributable_equity":
            expected_input_ids = {
                _at(observations, metric, period).observation_id
                for metric in (
                    "bank.input.total_equity",
                    "bank.input.non_controlling_interests",
                )
            }
            _validate_formula_inputs(observation, expected_input_ids)
            result = calculate_parent_attributable_equity(
                values.get("bank.input.total_equity"),
                values.get("bank.input.non_controlling_interests"),
            )
            if result.value is None or result.formula_version != observation.formula.formula_version:
                raise ValueError("parent-equity formula version or inputs are unsupported")
            if observation.value is None or abs(Decimal(str(observation.value)) - result.value) > Decimal("0.0000001"):
                raise ValueError("parent-attributable equity does not reproduce from accepted inputs")
            continue
        else:
            raise ValueError("packet formula version is unsupported for its metric")
        if result.value is None or observation.value is None:
            raise ValueError("valid derived observation did not reproduce to a numeric value")
        if result.formula_version != observation.formula.formula_version:
            raise ValueError("packet formula version does not match deterministic implementation")
        if abs(result.value - Decimal(str(observation.value))) > Decimal("0.00005"):
            raise ValueError("packet derived value does not reproduce from accepted inputs")


def _validate_formula_inputs(
    observation: BankPacketObservation,
    expected_input_ids: set[str],
) -> None:
    actual = set(observation.formula.input_observation_ids)
    if actual != expected_input_ids:
        raise ValueError("formula input lineage does not match the required metric inputs")


def parse_bank_onboarding_packet(content: bytes) -> BankOnboardingPacket:
    """Parse and validate packet structure and cross-record references."""

    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("bank onboarding packet must be UTF-8 JSON") from exc
    return BankOnboardingPacket.model_validate(payload)


def verify_packet_artifacts(
    packet: BankOnboardingPacket,
    *,
    packet_path: Path,
    source_manifest_path: Path,
) -> tuple[dict[str, Path], dict[str, dict[str, object]]]:
    """Verify each artifact against its byte/hash sidecar before reconciliation."""

    try:
        manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("source artifact manifest is unreadable") from exc
    if manifest.get("schema_version") != "1.0" or not isinstance(manifest.get("artifacts"), dict):
        raise ValueError("source artifact manifest schema is invalid")
    base = packet_path.resolve().parent
    root = Path(__file__).resolve().parents[2]
    paths: dict[str, Path] = {}
    details: dict[str, dict[str, object]] = {}
    for source in packet.sources:
        record = manifest["artifacts"].get(source.source_id)
        if not isinstance(record, dict):
            raise ValueError("packet source has no byte-count and hash manifest entry")
        if record.get("artifact_ref") != source.artifact_ref:
            raise ValueError("source artifact_ref does not match manifest")
        if record.get("content_sha256", "").lower() != source.content_sha256.lower():
            raise ValueError("source content hash does not match manifest")
        if record.get("source_url") != source.source_url:
            raise ValueError("source URL does not match manifest")
        if not isinstance(record.get("byte_length"), int) or record["byte_length"] < 0:
            raise ValueError("source byte length is invalid")
        artifact_path = (base / source.artifact_ref).resolve()
        if not artifact_path.is_relative_to(root):
            raise ValueError("source artifact_ref must resolve inside the repository")
        try:
            content = artifact_path.read_bytes()
        except OSError as exc:
            raise ValueError("source artifact is unavailable") from exc
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != record["byte_length"]:
            raise ValueError("source byte length does not match manifest")
        if digest.lower() != source.content_sha256.lower():
            raise ValueError("source artifact SHA-256 verification failed")
        paths[source.source_id] = artifact_path
        details[source.source_id] = record
    return paths, details


def build_bank_dataset_candidate(
    packet: BankOnboardingPacket,
    *,
    artifact_paths: dict[str, Path],
    artifact_details: dict[str, dict[str, object]],
    created_at: datetime | None = None,
) -> tuple[CanonicalDatasetCandidate, RawDatasetDescriptor, OnboardingValidationReport]:
    """Convert one verified packet to generic candidate/provider contracts."""

    source_records: list[DatasetSource] = []
    source_map: dict[str, DatasetSource] = {}
    raw_record: tuple[BankPacketSource, bytes] | None = None
    for source in packet.sources:
        artifact_path = artifact_paths[source.source_id]
        artifact_bytes = artifact_path.read_bytes()
        source_status = (
            QualityStatus.PENDING_VALIDATION
            if source.source_tier == "user_supplied"
            else QualityStatus.VALID
        )
        record = DatasetSource(
            source_ref=source.source_id,
            source_type="csv" if source.kind == "uploaded_csv" else "filing",
            source_tier=source.source_tier,
            source_url=source.source_url or f"urn:source:{source.source_id}",
            publisher=source.publisher,
            retrieved_at=source.retrieved_at,
            content_hash=source.content_sha256.lower(),
            validation_status=source_status,
            notes=source.document_type,
        )
        source_records.append(record)
        source_map[source.source_id] = record
        if source.kind == "primary_filing" and source_status is QualityStatus.VALID:
            if raw_record is None:
                raw_record = (source, artifact_bytes)
    if raw_record is None:
        raise ValueError("packet requires a verified primary filing artifact")
    raw_source, raw_bytes = raw_record
    raw_descriptor = RawDatasetDescriptor(
        raw_dataset_id=f"{packet.packet_id}-source",
        source_type="filing",
        original_name=Path(raw_source.artifact_ref).name,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        ingested_at=datetime.fromisoformat(raw_source.retrieved_at.replace("Z", "+00:00")),
    )
    metadata = build_snapshot_metadata(
        packet.dataset_id,
        raw_descriptor,
        mapping_version=f"bank-packet-{packet.schema_version}",
        validation_version="bank-onboarding-reconciliation-v1",
        status=DatasetSnapshotStatus.CANDIDATE,
        created_at=created_at,
    )
    packet_id_map: dict[str, str] = {}
    for observation in packet.observations:
        packet_id_map[observation.observation_id] = canonical_observation_id(
            metadata.dataset_snapshot_id,
            packet.entity_id,
            observation.period_id,
            observation.metric_id,
        )

    document_id = f"document:{packet.packet_id}"
    document = DatasetDocument(
        document_id=document_id,
        dataset_id=packet.dataset_id,
        dataset_snapshot_id=metadata.dataset_snapshot_id,
        source_ref=raw_source.source_id,
        document_type=raw_source.document_type or "audited_financial_filing",
        title=f"{packet.entity_id} audited filing source artifact",
        publisher=raw_source.publisher,
        content_hash=raw_source.content_sha256.lower(),
        metadata={
            "packet_id": packet.packet_id,
            "source_byte_length": artifact_details[raw_source.source_id]["byte_length"],
            "pdf_page_count": artifact_details[raw_source.source_id].get("pdf_page_count"),
            "text_layer_status": artifact_details[raw_source.source_id].get("text_layer_status"),
        },
    )
    observations: list[CanonicalObservation] = []
    evidence_rows: list[DatasetEvidence] = []
    for item in packet.observations:
        review = item.review
        review_record = None
        if review is not None:
            review_record = ObservationReview(
                reviewer_id=review.reviewer_id,
                reviewed_at=review.reviewed_at,
                decision=review.decision,
                primary_evidence=tuple(
                    ObservationEvidenceRef(
                        source_ref=reference.source_id,
                        locator=reference.source_locator,
                    )
                    for reference in review.primary_evidence
                ),
                resolution_note=review.resolution_note,
            )
        formula = item.formula
        first_evidence = review.primary_evidence[0] if review is not None else None
        if item.quality_status == "valid" and first_evidence is not None:
            source_ref = None if formula is not None else first_evidence.source_id
            source_locator = first_evidence.source_locator
        else:
            source_ref = item.candidate_source_id
            source_locator = item.candidate_locator
        observation = CanonicalObservation(
            observation_id=packet_id_map[item.observation_id],
            dataset_id=packet.dataset_id,
            dataset_snapshot_id=metadata.dataset_snapshot_id,
            entity_id=packet.entity_id,
            period_id=item.period_id,
            metric_id=item.metric_id,
            value=item.value,
            unit=item.unit,
            source_ref=source_ref,
            source_locator=source_locator,
            period_basis=item.period_basis,
            reporting_scope=None if item.reporting_scope == "unknown" else item.reporting_scope,
            review=review_record,
            validation_status=QualityStatus(item.quality_status),
            missing_reason=item.reason,
            derivation_method=formula.formula_version if formula is not None else None,
            input_observation_ids=(
                tuple(packet_id_map[reference] for reference in formula.input_observation_ids)
                if formula is not None
                else ()
            ),
            metadata={"packet_observation_id": item.observation_id},
        )
        if item.quality_status == "valid" and first_evidence is not None:
            evidence_rows.append(
                DatasetEvidence(
                    evidence_id=f"evidence:{packet.packet_id}:{item.observation_id}",
                    source_ref=first_evidence.source_id,
                    document_id=document_id,
                    entity_id=packet.entity_id,
                    period_id=item.period_id,
                    metric_id=item.metric_id,
                    locator=first_evidence.source_locator,
                    quote=review.resolution_note,
                )
            )
        observations.append(observation)

    period_ids = sorted({item.period_id for item in packet.observations})
    metric_ids = sorted({item.metric_id for item in packet.observations})
    metrics = tuple(
        DatasetMetric(
            metric_id=metric_id,
            display_name=_METRIC_LABELS.get(
                metric_id,
                metric_id.removeprefix("bank.input.").replace("_", " ").capitalize(),
            ),
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit=next(
                (item.unit for item in packet.observations if item.metric_id == metric_id and item.unit),
                None,
            ),
        )
        for metric_id in metric_ids
    )
    candidate = CanonicalDatasetCandidate(
        metadata=metadata,
        source=source_map[raw_source.source_id],
        entities=(
            DatasetEntity(
                entity_id=packet.entity_id,
                entity_type=DatasetEntityType.COMPANY,
                display_name=packet.entity_id,
                attributes={"sector": "bank"},
            ),
        ),
        periods=tuple(DatasetPeriod(period_id=item, label=item) for item in period_ids),
        metrics=metrics,
        observations=tuple(observations),
        additional_sources=tuple(
            item for item in source_records if item.source_ref != raw_source.source_id
        ),
        documents=(document,),
        evidence=tuple(evidence_rows),
    )
    report = OnboardingValidationReport(
        dataset_id=packet.dataset_id,
        candidate_snapshot_id=metadata.dataset_snapshot_id,
        status=OnboardingValidationStatus.VALID,
        row_count=len(packet.observations),
        candidate_observation_count=sum(
            1 for item in packet.observations if item.value is not None
        ),
        missing_observation_count=sum(
            1 for item in packet.observations if item.quality_status == "missing"
        ),
        rejected_row_count=0,
    )
    return candidate, raw_descriptor, report
