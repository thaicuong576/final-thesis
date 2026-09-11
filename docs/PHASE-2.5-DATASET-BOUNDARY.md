# Phase 2.5 — Application Dataset Boundary

## Architectural decision

```text
Gold SQLite ≠ application architecture

Gold SQLite
  = GoldSqliteDatasetProvider
  = provider implementation #1
  = reproducible thesis/evaluation dataset
```

The application boundary is defined by the versioned contracts in
`src/thesis_data/dataset_contract.py`, the provider protocol in
`src/thesis_data/dataset_provider.py`, and the request/runtime modules. The
application does not use `ticker` as its identity, does not require the Gold
quarter regex, and does not know physical table names or database paths.

## Application path

```text
Dataset
  → Dataset Provider
  → Dataset Capability Catalog
  → AnalysisRequest
  → DatasetToolRuntime
  → future Macro / Sector / Company / Orchestrator agents
```

`AnalysisRequest` binds `dataset_id` and `dataset_snapshot_id` to every run.
`validate_analysis_request()` checks the request only against the discovered
capability catalog: entities, periods, metrics, macro metrics, peer universes,
and explicit peer members. It does not open a database.

`ApplicationRuntimeContext` binds the request, dataset reference, catalog, and
`FinancialDatasetProvider`. `DatasetToolRuntime` exposes generic read
operations (`get_metric`, `get_entity_metrics`, `get_peer_benchmark`,
`get_evidence`, `get_source`, `get_macro_observation`, and
`resolve_observation`) and rejects entity, period, metric, peer-universe, or
undiscovered-source requests outside the analysis scope.

The first non-SQLite implementation is
`InMemoryFinancialDatasetProvider`. It exists for application tests and local
development, and proves that the runtime boundary can operate without a
SQLite path.

## Gold provider path

```text
Frozen Gold SQLite
  → GoldSqliteDatasetProvider
  → canonical dataset contracts
  → capability catalog / AnalysisRequest binding
  → DatasetToolRuntime
```

Only `src/thesis_data/gold_dataset_provider.py` contains the Gold adapter's
SQLite/table knowledge. It discovers company entities from stored observations,
macro entities from `macro_observations_v2`, periods and metrics from rows, and
sector peer universes from actual stored sector membership. No fixed ACB/TCB/
VPB/MBB/VCB list is embedded in application runtime logic.

The adapter verifies exactly one physical snapshot metadata row, requires
`status=gold`, and requires the requested `DatasetRef` to match both the
configured dataset ID and the physical snapshot ID. Macro V2 effective/as-of
metadata is retained in canonical observation metadata. Missing rows remain
missing with their reason; they are never converted to zero.

Sources omit `local_path` from the application contract. Evidence can be
ticker-less, so macro evidence maps naturally to `DatasetEvidence` with a
null `entity_id` and explicit period/metric/locator.

## Thesis evaluation compatibility path

```text
Frozen Gold SQLite
  → GoldSqliteDatasetProvider
  → compatibility binding (`experiment_compat.py`)
  → existing QuestionSet / CompositeWorkloadSpec / experiment runner
```

`QuestionSet` remains an experiment fixture and is not the application
contract. `experiment_compat.py` provides a thin binding from an unchanged
question or question set to `AnalysisRequest`; existing experiment IDs,
question files, Gold snapshots, and Phase 1–2 execution paths remain intact.
The existing `GoldToolRuntime` is intentionally retained as a legacy
experiment/data-foundation compatibility path; new application runtime code
uses `DatasetToolRuntime`.

## Runtime observability

`runtime_events.py` defines the versioned public event envelope and all planned
event types. `InMemoryRuntimeEventRecorder` enforces contiguous sequence
numbers. The application runtime emits lifecycle/tool events only when the
corresponding operation occurs. Events carry logical artifact references and
public summaries, never private chain-of-thought, hidden reasoning, secrets,
or physical local paths. WebSocket/SSE infrastructure is out of scope.

## Scope and deferred work

This phase does not create an ETL platform, ingestion pipeline, vector DB/RAG,
schema-mapping UI, additional issuers, experiment arms, Stage-2 scoring,
critic/revision logic, or a full orchestrator.

Phase 3A remains provisional. Its current Gold-specific missingness vocabulary
and ref-type-only missingness check are intentionally not changed in this
phase. After this Dataset Boundary is reviewed, Phase 3A will be rebound to
canonical provider-resolved validation status and dataset identity. Phase 3B
is not started.
