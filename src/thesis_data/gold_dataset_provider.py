"""SQLite-backed implementation of the generic application dataset provider.

All SQLite/table knowledge is intentionally contained in this adapter.  Code
above this module consumes only canonical dataset contracts and provider
methods.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Sequence

from .dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    PeerUniverse,
    SupportedOperation,
)
from .dataset_provider import (
    DatasetProviderError,
    aggregate_peer_median,
)
from .gold_scope_authority import VerifiedGoldObservationScopeAuthority
from .schema import QualityStatus


MACRO_ENTITY_ID = "VN"


class GoldSqliteDatasetProvider:
    """Expose one validated Gold SQLite snapshot through generic contracts."""

    def __init__(
        self,
        db_path: Path,
        dataset_id: str,
        *,
        scope_authority: VerifiedGoldObservationScopeAuthority | None = None,
    ) -> None:
        self._db_path = Path(db_path).resolve()
        self._dataset_id = dataset_id.strip()
        self._scope_authority = scope_authority
        self._scope_authority_validated_sqlite_sha256: str | None = None
        if not self._dataset_id:
            raise ValueError("dataset_id must be non-empty")

    def current_dataset_ref(self) -> DatasetRef:
        return DatasetRef(
            dataset_id=self._dataset_id,
            dataset_snapshot_id=self._physical_snapshot_id(),
        )

    def _connection(self) -> sqlite3.Connection:
        if not self._db_path.exists():
            raise DatasetProviderError("Gold dataset database does not exist")
        connection = sqlite3.connect(
            f"file:{self._db_path}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _tables(connection: sqlite3.Connection) -> set[str]:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    def _physical_snapshot_id(self) -> str:
        connection = self._connection()
        try:
            tables = self._tables(connection)
            if "snapshot_metadata" not in tables:
                raise DatasetProviderError("Gold dataset has no snapshot metadata")
            rows = connection.execute(
                "SELECT snapshot_id, status FROM snapshot_metadata"
            ).fetchall()
        finally:
            connection.close()
        if len(rows) != 1:
            raise DatasetProviderError("Gold snapshot metadata is missing or ambiguous")
        if rows[0]["status"] != "gold":
            raise DatasetProviderError("dataset snapshot is not Gold")
        return str(rows[0]["snapshot_id"])

    def _validate_ref(self, dataset_ref: DatasetRef) -> None:
        if dataset_ref.dataset_id != self._dataset_id:
            raise DatasetProviderError("dataset_id does not match provider")
        actual_snapshot_id = self._physical_snapshot_id()
        if dataset_ref.dataset_snapshot_id != actual_snapshot_id:
            raise DatasetProviderError("dataset_snapshot_id does not match physical Gold snapshot")
        if self._scope_authority is not None:
            self._validate_scope_authority(actual_snapshot_id)

    def _validate_scope_authority(self, actual_snapshot_id: str) -> None:
        """Bind every scoped lookup to the exact immutable Gold bytes and rows."""

        assert self._scope_authority is not None
        authority = self._scope_authority.authority
        if authority.dataset_id != self._dataset_id:
            raise DatasetProviderError("reporting-scope authority dataset_id mismatch")
        if authority.snapshot_id != actual_snapshot_id:
            raise DatasetProviderError("reporting-scope authority snapshot_id mismatch")
        if not self._db_path.exists():
            raise DatasetProviderError("Gold dataset database does not exist")
        actual_sqlite_sha256 = hashlib.sha256(self._db_path.read_bytes()).hexdigest()
        if actual_sqlite_sha256 != authority.gold_snapshot_sha256:
            raise DatasetProviderError("reporting-scope authority Gold SQLite SHA-256 mismatch")
        if self._scope_authority_validated_sqlite_sha256 == actual_sqlite_sha256:
            return

        entries = self._scope_authority.entries_by_observation_id
        connection = self._connection()
        try:
            rows = connection.execute(
                """
                SELECT observation_id, ticker, period, metric, value, unit,
                       source_id, source_locator, quality_status, period_basis
                FROM metric_observations
                WHERE quality_status = ?
                ORDER BY observation_id
                """,
                (QualityStatus.VALID.value,),
            ).fetchall()
            database_ids = {str(row["observation_id"]) for row in rows}
            authority_ids = set(entries)
            if authority_ids != database_ids:
                unknown_ids = sorted(authority_ids - database_ids)
                unscoped_ids = sorted(database_ids - authority_ids)
                raise DatasetProviderError(
                    "reporting-scope authority observation IDs do not exactly match Gold "
                    f"(unknown={unknown_ids[:3]}, unscoped={unscoped_ids[:3]})"
                )

            for row in rows:
                observation_id = str(row["observation_id"])
                entry = entries[observation_id]
                expected_target_id = f"{row['ticker']}:{row['period']}:{row['metric']}"
                if (
                    entry.review_target_id != expected_target_id
                    or entry.entity_id != str(row["ticker"])
                    or entry.period_id != str(row["period"])
                    or entry.metric_id != str(row["metric"])
                    or entry.value != float(row["value"])
                    or entry.unit != row["unit"]
                    or entry.period_basis != row["period_basis"]
                    or entry.source_ref != row["source_id"]
                    or entry.source_locator != row["source_locator"]
                    or entry.review_status != "accepted"
                    or entry.reporting_scope != "consolidated"
                ):
                    raise DatasetProviderError(
                        "reporting-scope authority conflicts with a Gold observation"
                    )
                source = connection.execute(
                    "SELECT source_tier, quality_status FROM source_records WHERE source_id = ?",
                    (row["source_id"],),
                ).fetchone()
                if (
                    source is None
                    or source["source_tier"] != "primary"
                    or source["quality_status"] != QualityStatus.VALID.value
                ):
                    raise DatasetProviderError(
                        "reporting-scope authority observation source is not accepted primary"
                    )
        finally:
            connection.close()
        self._scope_authority_validated_sqlite_sha256 = actual_sqlite_sha256

    def _scope_authority_metadata(self, observation_id: str) -> dict[str, Any] | None:
        if self._scope_authority is None:
            return None
        entry = self._scope_authority.entries_by_observation_id.get(observation_id)
        if entry is None:
            return None
        authority = self._scope_authority.authority
        return {
            "authority_id": authority.authority_id,
            "authority_ref": self._scope_authority.authority_ref,
            "authority_canonical_lf_utf8_sha256": self._scope_authority.canonical_sha256,
            "source_review_ledger_ref": authority.source_review_ledger_ref,
            "source_review_ledger_raw_file_bytes_sha256": (
                authority.source_review_ledger_raw_file_bytes_sha256
            ),
            "source_authority_manifest_ref": authority.source_authority_manifest_ref,
            "source_authority_manifest_canonical_lf_utf8_sha256": (
                authority.source_authority_manifest_canonical_lf_utf8_sha256
            ),
            "review_target_id": entry.review_target_id,
            "review_status": entry.review_status,
            "reporting_scope": entry.reporting_scope,
            "checker_ids": list(entry.checker_ids),
            "checker_scope_confirmations": list(entry.checker_scope_confirmations),
            "adjudicator_id": entry.adjudicator_id,
        }

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            tables = self._tables(connection)
            entities: dict[str, DatasetEntity] = {}
            periods: set[str] = set()
            metrics: dict[str, DatasetMetric] = {}
            peer_members: dict[str, set[str]] = {}

            if "metric_observations" in tables:
                rows = connection.execute(
                    """
                    SELECT ticker, sector, period, metric, unit
                    FROM metric_observations
                    ORDER BY ticker, period, metric
                    """
                ).fetchall()
                for row in rows:
                    ticker = str(row["ticker"])
                    sector = str(row["sector"])
                    entities.setdefault(
                        ticker,
                        DatasetEntity(
                            entity_id=ticker,
                            entity_type=DatasetEntityType.COMPANY,
                            display_name=ticker,
                            attributes={"ticker": ticker, "sector": sector},
                        ),
                    )
                    periods.add(str(row["period"]))
                    metric_id = str(row["metric"])
                    if metric_id not in metrics:
                        metrics[metric_id] = DatasetMetric(
                            metric_id=metric_id,
                            display_name=metric_id,
                            analytical_level=AnalyticalLevel.COMPANY,
                            default_unit=row["unit"],
                        )
                    peer_members.setdefault(f"sector:{sector}", set()).add(ticker)

            if "macro_observations_v2" in tables:
                rows = connection.execute(
                    """
                    SELECT indicator_id, period, unit
                    FROM macro_observations_v2
                    ORDER BY indicator_id, period
                    """
                ).fetchall()
                if rows:
                    entities.setdefault(
                        MACRO_ENTITY_ID,
                        DatasetEntity(
                            entity_id=MACRO_ENTITY_ID,
                            entity_type=DatasetEntityType.MACRO,
                            display_name="Vietnam macro context",
                            attributes={},
                        ),
                    )
                for row in rows:
                    periods.add(str(row["period"]))
                    metric_id = str(row["indicator_id"])
                    if metric_id not in metrics:
                        metrics[metric_id] = DatasetMetric(
                            metric_id=metric_id,
                            display_name=metric_id,
                            analytical_level=AnalyticalLevel.MACRO,
                            default_unit=row["unit"],
                        )

            peer_universes = tuple(
                PeerUniverse(
                    peer_universe_id=universe_id,
                    display_name=universe_id.removeprefix("sector:") + " peer universe",
                    entity_ids=tuple(sorted(entity_ids)),
                )
                for universe_id, entity_ids in sorted(peer_members.items())
                if entity_ids
            )
            operations = [
                SupportedOperation.GET_METRIC,
                SupportedOperation.GET_ENTITY_METRICS,
                SupportedOperation.RESOLVE_OBSERVATION,
            ]
            if peer_universes:
                operations.append(SupportedOperation.GET_PEER_BENCHMARK)
            if "source_records" in tables:
                operations.append(SupportedOperation.GET_SOURCE)
            if "evidence_snippets" in tables or "macro_evidence_snippets" in tables:
                operations.append(SupportedOperation.GET_EVIDENCE)
            if "macro_observations_v2" in tables:
                operations.append(SupportedOperation.GET_MACRO_OBSERVATION)
        finally:
            connection.close()

        if not metrics or not periods or not entities:
            raise DatasetProviderError("Gold dataset has no discoverable analytical capabilities")
        return DatasetCapabilityCatalog(
            dataset_ref=dataset_ref,
            entities=tuple(entities.values()),
            periods=tuple(DatasetPeriod(period_id=item, label=item) for item in sorted(periods)),
            metrics=tuple(metrics.values()),
            peer_universes=peer_universes,
            supported_operations=tuple(operations),
        )

    @staticmethod
    def _quality_status(value: Any) -> QualityStatus:
        try:
            return QualityStatus(str(value))
        except ValueError as exc:
            raise DatasetProviderError(f"unknown validation status: {value}") from exc

    @staticmethod
    def _observation_id_list(value: Any) -> tuple[str, ...]:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DatasetProviderError("Gold derived observation lineage is invalid") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise DatasetProviderError("Gold derived observation lineage is invalid")
        return tuple(parsed)

    def _company_observation(
        self,
        connection: sqlite3.Connection,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        rows = connection.execute(
            """
            SELECT observation_id, ticker, metric, value, unit, period,
                   source_id, source_locator, quality_status, reason,
                   as_of_date, period_basis
            FROM metric_observations
            WHERE ticker = ? AND period = ? AND metric = ?
            ORDER BY observation_id
            """,
            (entity_id, period_id, metric_id),
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise DatasetProviderError("ambiguous canonical company observation")
        row = rows[0]
        scope_authority_metadata = self._scope_authority_metadata(
            str(row["observation_id"])
        ) if row["quality_status"] == QualityStatus.VALID.value else None
        metadata = {
            "as_of_date": row["as_of_date"],
            "period_basis": row["period_basis"],
        }
        if scope_authority_metadata is not None:
            metadata["reporting_scope_authority"] = scope_authority_metadata
        return CanonicalObservation(
            observation_id=str(row["observation_id"]),
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            entity_id=str(row["ticker"]),
            period_id=str(row["period"]),
            metric_id=str(row["metric"]),
            value=float(row["value"]) if row["value"] is not None else None,
            unit=row["unit"],
            source_ref=row["source_id"],
            source_locator=row["source_locator"],
            period_basis=row["period_basis"],
            reporting_scope=(
                "consolidated" if scope_authority_metadata is not None else None
            ),
            validation_status=self._quality_status(row["quality_status"]),
            missing_reason=row["reason"],
            metadata=metadata,
        )

    def _macro_observation(
        self,
        connection: sqlite3.Connection,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        if entity_id != MACRO_ENTITY_ID:
            raise DatasetProviderError("Gold macro observations use the VN macro entity")
        rows = connection.execute(
            """
            SELECT observation_id, indicator_id, value, unit, period, source_id,
                   quality_status, reason, source_series_id,
                   indicator_definition_version, frequency, observation_date,
                   effective_from, as_of_date, period_basis,
                   alignment_method, source_locator, transformation_version,
                   adjudication_ref, review_check_ids_json
            FROM macro_observations_v2
            WHERE indicator_id = ? AND period = ?
            ORDER BY observation_id
            """,
            (metric_id, period_id),
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise DatasetProviderError("ambiguous canonical macro observation")
        row = rows[0]
        return CanonicalObservation(
            observation_id=str(row["observation_id"]),
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            entity_id=MACRO_ENTITY_ID,
            period_id=str(row["period"]),
            metric_id=str(row["indicator_id"]),
            value=float(row["value"]) if row["value"] is not None else None,
            unit=row["unit"],
            source_ref=row["source_id"],
            source_locator=row["source_locator"],
            period_basis=row["period_basis"],
            validation_status=self._quality_status(row["quality_status"]),
            missing_reason=row["reason"],
            metadata={
                "source_series_id": row["source_series_id"],
                "indicator_definition_version": row["indicator_definition_version"],
                "frequency": row["frequency"],
                "observation_date": row["observation_date"],
                "effective_from": row["effective_from"],
                "as_of_date": row["as_of_date"],
                "period_basis": row["period_basis"],
                "alignment_method": row["alignment_method"],
                "transformation_version": row["transformation_version"],
                "adjudication_ref": row["adjudication_ref"],
                "review_check_ids_json": row["review_check_ids_json"],
            },
        )

    def _derived_observation(
        self,
        connection: sqlite3.Connection,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        rows = connection.execute(
            """
            SELECT derived_id, ticker, sector, metric, value, unit, period,
                   period_basis, input_observation_ids_json, formula_version,
                   quality_status, reason
            FROM derived_metrics
            WHERE derived_id = ?
            ORDER BY derived_id
            """,
            (observation_id,),
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise DatasetProviderError("ambiguous Gold derived observation")
        row = rows[0]
        if row["ticker"] is None or not str(row["ticker"]).strip():
            raise DatasetProviderError("Gold derived observation has no representable entity")
        try:
            return CanonicalObservation(
                observation_id=str(row["derived_id"]),
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id=str(row["ticker"]),
                period_id=str(row["period"]),
                metric_id=str(row["metric"]),
                value=float(row["value"]) if row["value"] is not None else None,
                unit=row["unit"],
                source_ref=None,
                period_basis=row["period_basis"],
                validation_status=self._quality_status(row["quality_status"]),
                missing_reason=row["reason"],
                derivation_method=str(row["formula_version"]),
                input_observation_ids=self._observation_id_list(
                    row["input_observation_ids_json"]
                ),
                metadata={
                    "sector": row["sector"],
                    "period_basis": row["period_basis"],
                },
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, DatasetProviderError):
                raise
            raise DatasetProviderError("Gold derived observation is invalid") from exc

    def get_metric(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            tables = self._tables(connection)
            if "macro_observations_v2" in tables:
                macro_match = connection.execute(
                    "SELECT 1 FROM macro_observations_v2 WHERE indicator_id = ? LIMIT 1",
                    (metric_id,),
                ).fetchone()
            else:
                macro_match = None
            if macro_match:
                return self._macro_observation(
                    connection, dataset_ref, entity_id, period_id, metric_id
                )
            if "metric_observations" not in tables:
                return None
            return self._company_observation(
                connection, dataset_ref, entity_id, period_id, metric_id
            )
        finally:
            connection.close()

    def get_entity_metrics(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        self._validate_ref(dataset_ref)
        observations: list[CanonicalObservation] = []
        for period_id in period_ids:
            for metric_id in metric_ids:
                item = self.get_metric(dataset_ref, entity_id, period_id, metric_id)
                if item is not None:
                    observations.append(item)
        return tuple(observations)

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        self._validate_ref(dataset_ref)
        catalog = self.get_capabilities(dataset_ref)
        universe = catalog.peer_universe(peer_universe_id)
        if universe is None:
            raise DatasetProviderError("unknown peer universe")
        try:
            effective_peer_entity_ids = universe.effective_entity_ids(peer_entity_ids)
        except ValueError as exc:
            raise DatasetProviderError(str(exc)) from exc
        for metric_id in metric_ids:
            metric = next((item for item in catalog.metrics if item.metric_id == metric_id), None)
            if metric is None or metric.analytical_level is not AnalyticalLevel.COMPANY:
                raise DatasetProviderError("peer benchmark requires company-level metrics")
        result: list[CanonicalObservation] = []
        for metric_id in metric_ids:
            observations = tuple(
                item
                for entity_id in effective_peer_entity_ids
                for item in self.get_entity_metrics(
                    dataset_ref, entity_id, (period_id,), (metric_id,)
                )
            )
            result.append(
                aggregate_peer_median(
                    dataset_ref=dataset_ref,
                    peer_universe_id=peer_universe_id,
                    period_id=period_id,
                    metric_id=metric_id,
                    peer_entity_ids=effective_peer_entity_ids,
                    member_observations=observations,
                )
            )
        return tuple(result)

    def get_evidence(
        self,
        dataset_ref: DatasetRef,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        self._validate_ref(dataset_ref)
        if not source_refs:
            return ()
        connection = self._connection()
        result: list[DatasetEvidence] = []
        try:
            tables = self._tables(connection)
            marks = ",".join("?" for _ in source_refs)
            source_params = tuple(source_refs)
            macro_metric = False
            if metric_id is not None and "macro_observations_v2" in tables:
                macro_metric = bool(
                    connection.execute(
                        "SELECT 1 FROM macro_observations_v2 WHERE indicator_id = ? LIMIT 1",
                        (metric_id,),
                    ).fetchone()
                )
            if macro_metric or (
                entity_id == MACRO_ENTITY_ID and "macro_evidence_snippets" in tables
            ):
                clauses = [f"evidence.source_id IN ({marks})"]
                params: list[Any] = list(source_params)
                if period_id is not None:
                    clauses.append("evidence.period = ?")
                    params.append(period_id)
                if metric_id is not None:
                    clauses.append("evidence.indicator_id = ?")
                    params.append(metric_id)
                if "macro_evidence_snippets" in tables:
                    rows = connection.execute(
                        """
                        SELECT evidence.evidence_id, evidence.source_id,
                               evidence.indicator_id, evidence.period,
                               evidence.source_locator, evidence.quote
                        FROM macro_evidence_snippets AS evidence
                        JOIN source_records AS source ON source.source_id = evidence.source_id
                        WHERE source.quality_status = 'valid' AND """
                        + " AND ".join(clauses)
                        + " ORDER BY evidence_id",
                        params,
                    ).fetchall()
                    result.extend(
                        DatasetEvidence(
                            evidence_id=str(row["evidence_id"]),
                            source_ref=str(row["source_id"]),
                            entity_id=None,
                            period_id=str(row["period"]),
                            metric_id=str(row["indicator_id"]),
                            locator=str(row["source_locator"]),
                            quote=str(row["quote"]),
                        )
                        for row in rows
                    )
            if entity_id != MACRO_ENTITY_ID and "evidence_snippets" in tables:
                clauses = [f"evidence.source_id IN ({marks})"]
                params = list(source_params)
                if entity_id is not None:
                    clauses.append("evidence.ticker = ?")
                    params.append(entity_id)
                if period_id is not None:
                    clauses.append("evidence.period = ?")
                    params.append(period_id)
                rows = connection.execute(
                    """
                    SELECT evidence.evidence_id, evidence.source_id,
                           evidence.period, evidence.ticker, evidence.page_number,
                           evidence.quote
                    FROM evidence_snippets AS evidence
                    JOIN source_records AS source ON source.source_id = evidence.source_id
                    WHERE source.quality_status = 'valid' AND """
                    + " AND ".join(clauses)
                    + " ORDER BY evidence_id",
                    params,
                ).fetchall()
                result.extend(
                    DatasetEvidence(
                        evidence_id=str(row["evidence_id"]),
                        source_ref=str(row["source_id"]),
                        entity_id=row["ticker"],
                        period_id=row["period"],
                        metric_id=None,
                        locator=(
                            f"page:{row['page_number']}"
                            if row["page_number"] is not None
                            else "document"
                        ),
                        quote=str(row["quote"]),
                    )
                    for row in rows
                )
        finally:
            connection.close()
        return tuple(result)

    def resolve_evidence(
        self,
        dataset_ref: DatasetRef,
        evidence_id: str,
    ) -> DatasetEvidence | None:
        """Resolve one exact evidence ID across company and macro domains."""

        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            tables = self._tables(connection)
            candidates: list[tuple[str, sqlite3.Row]] = []
            if "evidence_snippets" in tables:
                company_rows = connection.execute(
                    """
                    SELECT evidence_id, source_id, source_document, page_number,
                           period, ticker, quote
                    FROM evidence_snippets
                    WHERE evidence_id = ?
                    """,
                    (evidence_id,),
                ).fetchall()
                if len(company_rows) > 1:
                    raise DatasetProviderError("ambiguous Gold company evidence ID")
                candidates.extend(("company", row) for row in company_rows)
            if "macro_evidence_snippets" in tables:
                macro_rows = connection.execute(
                    """
                    SELECT evidence_id, source_id, indicator_id, period,
                           source_locator, quote
                    FROM macro_evidence_snippets
                    WHERE evidence_id = ?
                    """,
                    (evidence_id,),
                ).fetchall()
                if len(macro_rows) > 1:
                    raise DatasetProviderError("ambiguous Gold macro evidence ID")
                candidates.extend(("macro", row) for row in macro_rows)
            if len(candidates) > 1:
                raise DatasetProviderError("evidence ID is ambiguous across Gold domains")
            if not candidates:
                return None

            domain, row = candidates[0]
            source_rows = connection.execute(
                "SELECT source_id FROM source_records WHERE source_id = ?",
                (row["source_id"],),
            ).fetchall()
            if len(source_rows) != 1:
                raise DatasetProviderError("Gold evidence source is missing or ambiguous")
            try:
                if domain == "macro":
                    return DatasetEvidence(
                        evidence_id=str(row["evidence_id"]),
                        source_ref=str(row["source_id"]),
                        entity_id=None,
                        period_id=str(row["period"]),
                        metric_id=str(row["indicator_id"]),
                        locator=str(row["source_locator"]),
                        quote=str(row["quote"]),
                    )
                return DatasetEvidence(
                    evidence_id=str(row["evidence_id"]),
                    source_ref=str(row["source_id"]),
                    entity_id=row["ticker"],
                    period_id=row["period"],
                    metric_id=None,
                    locator=(
                        f"page:{row['page_number']}"
                        if row["page_number"] is not None
                        else "document"
                    ),
                    quote=str(row["quote"]),
                )
            except (TypeError, ValueError) as exc:
                raise DatasetProviderError("Gold evidence is invalid") from exc
        except sqlite3.Error as exc:
            raise DatasetProviderError("Gold evidence is invalid") from exc
        finally:
            connection.close()

    def get_source(
        self,
        dataset_ref: DatasetRef,
        source_ref: str,
    ) -> DatasetSource | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            rows = connection.execute(
                """
                SELECT source_id, source_type, source_tier, source_url,
                       retrieved_at, content_hash, publisher, quality_status, notes
                FROM source_records WHERE source_id = ?
                """,
                (source_ref,),
            ).fetchall()
        finally:
            connection.close()
        if not rows:
            return None
        if len(rows) != 1:
            raise DatasetProviderError("ambiguous dataset source")
        row = rows[0]
        return DatasetSource(
            source_ref=str(row["source_id"]),
            source_type=str(row["source_type"]),
            source_tier=str(row["source_tier"]),
            source_url=str(row["source_url"]),
            publisher=str(row["publisher"]),
            retrieved_at=str(row["retrieved_at"]),
            content_hash=str(row["content_hash"]),
            validation_status=self._quality_status(row["quality_status"]),
            notes=row["notes"],
        )

    def get_macro_observation(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            return self._macro_observation(
                connection, dataset_ref, entity_id, period_id, metric_id
            )
        finally:
            connection.close()

    def resolve_observation(
        self,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            candidates: list[CanonicalObservation] = []
            tables = self._tables(connection)
            if "metric_observations" in tables:
                row = connection.execute(
                    "SELECT ticker, period, metric FROM metric_observations WHERE observation_id = ?",
                    (observation_id,),
                ).fetchone()
                if row is not None:
                    item = self._company_observation(
                        connection,
                        dataset_ref,
                        row["ticker"],
                        row["period"],
                        row["metric"],
                    )
                    if item is not None:
                        candidates.append(item)
            if "macro_observations_v2" in tables:
                row = connection.execute(
                    "SELECT indicator_id, period FROM macro_observations_v2 WHERE observation_id = ?",
                    (observation_id,),
                ).fetchone()
                if row is not None:
                    item = self._macro_observation(
                        connection,
                        dataset_ref,
                        MACRO_ENTITY_ID,
                        row["period"],
                        row["indicator_id"],
                    )
                    if item is not None:
                        candidates.append(item)
            if "derived_metrics" in tables:
                item = self._derived_observation(connection, dataset_ref, observation_id)
                if item is not None:
                    candidates.append(item)
        finally:
            connection.close()
        if len(candidates) > 1:
            raise DatasetProviderError("observation ID is ambiguous across dataset domains")
        return candidates[0] if candidates else None
