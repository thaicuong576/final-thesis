"""Generic canonical-snapshot SQLite adapter for the data foundation.

This provider knows only the portable canonical tables created by
``canonical_snapshot.py``.  It does not subclass, import, or query the Gold
SQLite adapter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence
import sqlite3

from .canonical_snapshot import (
    CANONICAL_CALCULATION_RECEIPT_METADATA_KEY,
    CANONICAL_SNAPSHOT_SCHEMA_VERSION,
)
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
    DerivedCalculationReceipt,
    ObservationReview,
    PeerUniverse,
    SupportedOperation,
)
from .dataset_provider import DatasetProviderError, aggregate_peer_median
from .evidence_contract import DOCUMENT_CONTRACT_VERSION
from .onboarding_contract import ONBOARDING_CONTRACT_VERSION
from .schema import QualityStatus


class CanonicalSqliteDatasetProvider:
    """Read one accepted generic canonical snapshot through a provider API."""

    def __init__(self, db_path: Path, dataset_id: str | None = None) -> None:
        self._db_path = Path(db_path).resolve()
        self._dataset_id = dataset_id.strip() if dataset_id is not None else None
        if self._dataset_id == "":
            raise ValueError("dataset_id must be non-empty")

    def _connection(self) -> sqlite3.Connection:
        if not self._db_path.exists():
            raise DatasetProviderError("canonical dataset database does not exist")
        connection = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _tables(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    @staticmethod
    def _metadata(connection: sqlite3.Connection) -> sqlite3.Row:
        try:
            rows = connection.execute(
                "SELECT * FROM dataset_metadata"
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatasetProviderError("canonical dataset metadata is unavailable") from exc
        if len(rows) != 1:
            raise DatasetProviderError("canonical dataset metadata is missing or ambiguous")
        row = rows[0]
        if row["status"] != "accepted":
            raise DatasetProviderError("canonical dataset snapshot is not accepted")
        if row["contract_version"] != ONBOARDING_CONTRACT_VERSION:
            raise DatasetProviderError("canonical dataset contract version is unsupported")
        if row["schema_version"] != CANONICAL_SNAPSHOT_SCHEMA_VERSION:
            raise DatasetProviderError("canonical dataset schema version is unsupported")
        if not str(row["content_manifest_hash"]).strip():
            raise DatasetProviderError("canonical dataset content manifest is invalid")
        return row

    def _physical_dataset_ref(self) -> DatasetRef:
        connection = self._connection()
        try:
            row = self._metadata(connection)
            return DatasetRef(
                dataset_id=str(row["dataset_id"]),
                dataset_snapshot_id=str(row["dataset_snapshot_id"]),
            )
        finally:
            connection.close()

    def current_dataset_ref(self) -> DatasetRef:
        return self._physical_dataset_ref()

    def _validate_ref(self, dataset_ref: DatasetRef) -> None:
        actual = self._physical_dataset_ref()
        if self._dataset_id is not None and dataset_ref.dataset_id != self._dataset_id:
            raise DatasetProviderError("dataset_id does not match provider")
        if dataset_ref != actual:
            raise DatasetProviderError("dataset reference does not match canonical snapshot")

    @staticmethod
    def _json_object(value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DatasetProviderError("canonical metadata JSON is invalid") from exc
        if not isinstance(parsed, dict):
            raise DatasetProviderError("canonical metadata JSON must be an object")
        return parsed

    @staticmethod
    def _json_list(value: str) -> tuple[str, ...]:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DatasetProviderError("canonical observation lineage JSON is invalid") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise DatasetProviderError("canonical observation lineage JSON is invalid")
        return tuple(parsed)

    @staticmethod
    def _status(value: Any) -> QualityStatus:
        try:
            return QualityStatus(str(value))
        except ValueError as exc:
            raise DatasetProviderError("canonical observation status is invalid") from exc

    def get_capabilities(self, dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            entities = tuple(
                DatasetEntity(
                    entity_id=str(row["entity_id"]),
                    entity_type=DatasetEntityType(str(row["entity_type"])),
                    display_name=str(row["display_name"]),
                    attributes=self._json_object(row["attributes_json"]),
                )
                for row in connection.execute(
                    "SELECT entity_id, entity_type, display_name, attributes_json FROM entities ORDER BY entity_id"
                ).fetchall()
            )
            periods = tuple(
                DatasetPeriod(period_id=str(row["period_id"]), label=str(row["label"]))
                for row in connection.execute(
                    "SELECT period_id, label FROM periods ORDER BY period_id"
                ).fetchall()
            )
            metrics = tuple(
                DatasetMetric(
                    metric_id=str(row["metric_id"]),
                    display_name=str(row["display_name"]),
                    analytical_level=AnalyticalLevel(str(row["analytical_level"])),
                    default_unit=row["default_unit"],
                )
                for row in connection.execute(
                    "SELECT metric_id, display_name, analytical_level, default_unit FROM metrics ORDER BY metric_id"
                ).fetchall()
            )
            peer_universes: list[PeerUniverse] = []
            for universe_row in connection.execute(
                "SELECT peer_universe_id, display_name FROM peer_universes ORDER BY peer_universe_id"
            ).fetchall():
                members = tuple(
                    str(row["entity_id"])
                    for row in connection.execute(
                        "SELECT entity_id FROM peer_universe_members WHERE peer_universe_id = ? ORDER BY entity_id",
                        (universe_row["peer_universe_id"],),
                    ).fetchall()
                )
                if members:
                    peer_universes.append(
                        PeerUniverse(
                            peer_universe_id=str(universe_row["peer_universe_id"]),
                            display_name=str(universe_row["display_name"]),
                            entity_ids=members,
                        )
                    )
            source_refs = tuple(
                str(row["source_ref"])
                for row in connection.execute(
                    "SELECT source_ref FROM sources ORDER BY source_ref"
                ).fetchall()
            )
            evidence_count = 0
            if "evidence" in self._tables(connection):
                evidence_count = int(
                    connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
                )
        except (sqlite3.Error, ValueError) as exc:
            if isinstance(exc, DatasetProviderError):
                raise
            raise DatasetProviderError("canonical dataset capabilities are invalid") from exc
        finally:
            connection.close()

        if not entities or not periods or not metrics:
            raise DatasetProviderError("canonical dataset has no discoverable capabilities")
        operations = [
            SupportedOperation.GET_METRIC,
            SupportedOperation.GET_ENTITY_METRICS,
            SupportedOperation.RESOLVE_OBSERVATION,
            SupportedOperation.GET_SOURCE,
        ]
        if peer_universes:
            operations.append(SupportedOperation.GET_PEER_BENCHMARK)
        if any(item.analytical_level is AnalyticalLevel.MACRO for item in metrics):
            operations.append(SupportedOperation.GET_MACRO_OBSERVATION)
        if evidence_count > 0:
            operations.append(SupportedOperation.GET_EVIDENCE)
        return DatasetCapabilityCatalog(
            dataset_ref=dataset_ref,
            entities=entities,
            periods=periods,
            metrics=metrics,
            peer_universes=tuple(peer_universes),
            source_refs=source_refs,
            supported_operations=tuple(operations),
        )

    def _observation_from_row(
        self,
        row: sqlite3.Row,
        dataset_ref: DatasetRef,
    ) -> CanonicalObservation:
        persisted_dataset_id = str(row["dataset_id"])
        persisted_snapshot_id = str(row["dataset_snapshot_id"])
        if persisted_dataset_id != dataset_ref.dataset_id:
            raise DatasetProviderError("persisted observation dataset_id does not match requested dataset")
        if persisted_snapshot_id != dataset_ref.dataset_snapshot_id:
            raise DatasetProviderError(
                "persisted observation dataset_snapshot_id does not match requested snapshot"
            )
        review_payload = self._json_object(row["review_json"])
        try:
            review = ObservationReview.model_validate(review_payload) if review_payload else None
        except (TypeError, ValueError) as exc:
            raise DatasetProviderError("canonical observation review is invalid") from exc
        metadata = self._json_object(row["metadata_json"])
        receipt_payload = metadata.pop(CANONICAL_CALCULATION_RECEIPT_METADATA_KEY, None)
        try:
            calculation_receipt = (
                DerivedCalculationReceipt.model_validate(receipt_payload)
                if receipt_payload is not None
                else None
            )
        except (TypeError, ValueError) as exc:
            raise DatasetProviderError("canonical observation calculation receipt is invalid") from exc
        return CanonicalObservation(
            observation_id=str(row["observation_id"]),
            dataset_id=persisted_dataset_id,
            dataset_snapshot_id=persisted_snapshot_id,
            entity_id=str(row["entity_id"]),
            period_id=str(row["period_id"]),
            metric_id=str(row["metric_id"]),
            value=float(row["value"]) if row["value"] is not None else None,
            unit=row["unit"],
            source_ref=row["source_ref"],
            source_locator=row["source_locator"],
            period_basis=row["period_basis"],
            reporting_scope=row["reporting_scope"],
            review=review,
            validation_status=self._status(row["validation_status"]),
            missing_reason=row["missing_reason"],
            derivation_method=row["derivation_method"],
            input_observation_ids=self._json_list(row["input_observation_ids_json"]),
            calculation_receipt=calculation_receipt,
            metadata=metadata,
        )

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
            rows = connection.execute(
                "SELECT * FROM observations WHERE entity_id = ? AND period_id = ? AND metric_id = ? ORDER BY observation_id",
                (entity_id, period_id, metric_id),
            ).fetchall()
            if len(rows) > 1:
                raise DatasetProviderError("ambiguous canonical observation")
            return self._observation_from_row(rows[0], dataset_ref) if rows else None
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
        if not period_ids or not metric_ids:
            return ()
        period_placeholders = ",".join("?" for _ in period_ids)
        metric_placeholders = ",".join("?" for _ in metric_ids)
        connection = self._connection()
        try:
            rows = connection.execute(
                f"SELECT * FROM observations WHERE entity_id = ? AND period_id IN ({period_placeholders}) AND metric_id IN ({metric_placeholders}) ORDER BY period_id, metric_id",
                (entity_id, *period_ids, *metric_ids),
            ).fetchall()
            return tuple(self._observation_from_row(row, dataset_ref) for row in rows)
        finally:
            connection.close()

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
            effective_ids = universe.effective_entity_ids(peer_entity_ids)
        except ValueError as exc:
            raise DatasetProviderError(str(exc)) from exc
        result: list[CanonicalObservation] = []
        for metric_id in metric_ids:
            metric = next((item for item in catalog.metrics if item.metric_id == metric_id), None)
            if metric is None or metric.analytical_level is not AnalyticalLevel.COMPANY:
                raise DatasetProviderError("peer benchmark requires company-level metrics")
            observations = tuple(
                item
                for entity_id in effective_ids
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
                    peer_entity_ids=effective_ids,
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
        try:
            if "evidence" not in self._tables(connection):
                raise DatasetProviderError("canonical snapshot has no document evidence")
            source_placeholders = ",".join("?" for _ in source_refs)
            clauses = [f"e.source_ref IN ({source_placeholders})"]
            params: list[Any] = list(source_refs)
            for column, value in (
                ("e.entity_id", entity_id),
                ("e.period_id", period_id),
                ("e.metric_id", metric_id),
            ):
                if value is not None:
                    clauses.append(f"{column} = ?")
                    params.append(value)
            rows = connection.execute(
                "SELECT e.* FROM evidence AS e WHERE "
                + " AND ".join(clauses)
                + " ORDER BY e.evidence_id",
                params,
            ).fetchall()
            return tuple(
                self._evidence_from_row(connection, row, dataset_ref)
                for row in rows
            )
        except sqlite3.Error as exc:
            raise DatasetProviderError("canonical document evidence is invalid") from exc
        finally:
            connection.close()

    def resolve_evidence(
        self,
        dataset_ref: DatasetRef,
        evidence_id: str,
    ) -> DatasetEvidence | None:
        """Resolve one exact evidence row from the canonical snapshot."""

        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            if "evidence" not in self._tables(connection):
                return None
            rows = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchall()
            if len(rows) > 1:
                raise DatasetProviderError("ambiguous canonical evidence ID")
            return self._evidence_from_row(connection, rows[0], dataset_ref) if rows else None
        except sqlite3.Error as exc:
            raise DatasetProviderError("canonical evidence is invalid") from exc
        finally:
            connection.close()

    def _evidence_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        dataset_ref: DatasetRef,
    ) -> DatasetEvidence:
        if (
            str(row["dataset_id"]) != dataset_ref.dataset_id
            or str(row["dataset_snapshot_id"]) != dataset_ref.dataset_snapshot_id
        ):
            raise DatasetProviderError("persisted evidence identity does not match requested dataset")
        source = connection.execute(
            "SELECT source_ref FROM sources WHERE source_ref = ?",
            (row["source_ref"],),
        ).fetchone()
        if source is None:
            raise DatasetProviderError("evidence source does not resolve")
        documents = connection.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (row["document_id"],),
        ).fetchall()
        if len(documents) != 1:
            raise DatasetProviderError("evidence document is missing or ambiguous")
        document = documents[0]
        if (
            str(document["dataset_id"]) != dataset_ref.dataset_id
            or str(document["dataset_snapshot_id"]) != dataset_ref.dataset_snapshot_id
            or str(document["source_ref"]) != str(row["source_ref"])
            or str(document["contract_version"]) != DOCUMENT_CONTRACT_VERSION
        ):
            raise DatasetProviderError("evidence document identity is invalid")
        return DatasetEvidence(
            evidence_id=str(row["evidence_id"]),
            source_ref=str(row["source_ref"]),
            document_id=str(row["document_id"]),
            entity_id=row["entity_id"],
            period_id=row["period_id"],
            metric_id=row["metric_id"],
            locator=str(row["locator"]),
            quote=str(row["quote"]),
        )

    def get_source(self, dataset_ref: DatasetRef, source_ref: str) -> DatasetSource | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            row = connection.execute(
                "SELECT * FROM sources WHERE source_ref = ?",
                (source_ref,),
            ).fetchone()
            if row is None:
                return None
            return DatasetSource(
                source_ref=str(row["source_ref"]),
                source_type=str(row["source_type"]),
                source_tier=str(row["source_tier"]),
                source_url=str(row["source_url"]),
                publisher=str(row["publisher"]),
                retrieved_at=str(row["retrieved_at"]),
                content_hash=str(row["content_hash"]),
                validation_status=self._status(row["validation_status"]),
                notes=row["notes"],
            )
        finally:
            connection.close()

    def get_macro_observation(
        self,
        dataset_ref: DatasetRef,
        entity_id: str,
        period_id: str,
        metric_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        catalog = self.get_capabilities(dataset_ref)
        metric = next((item for item in catalog.metrics if item.metric_id == metric_id), None)
        entity = next((item for item in catalog.entities if item.entity_id == entity_id), None)
        if metric is None or metric.analytical_level is not AnalyticalLevel.MACRO:
            raise DatasetProviderError("metric is not a declared macro metric")
        if entity is None or entity.entity_type is not DatasetEntityType.MACRO:
            raise DatasetProviderError("entity is not a declared macro entity")
        return self.get_metric(dataset_ref, entity_id, period_id, metric_id)

    def resolve_observation(
        self,
        dataset_ref: DatasetRef,
        observation_id: str,
    ) -> CanonicalObservation | None:
        self._validate_ref(dataset_ref)
        connection = self._connection()
        try:
            rows = connection.execute(
                "SELECT * FROM observations WHERE observation_id = ?",
                (observation_id,),
            ).fetchall()
            if len(rows) > 1:
                raise DatasetProviderError("ambiguous canonical observation ID")
            return self._observation_from_row(rows[0], dataset_ref) if rows else None
        finally:
            connection.close()
