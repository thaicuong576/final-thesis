# Phase 0B — CSV Structured Onboarding Vertical Slice

## Scope

Phase 0B proves one application-first path for an arbitrary structured CSV:

```text
CSV bytes
  → deterministic staging
  → explicit FieldMappingSpec
  → period/entity/value normalization
  → OnboardingValidationReport
  → candidate metadata
  → validated promotion
  → generic canonical SQLite snapshot
  → CanonicalSqliteDatasetProvider
  → DatasetCapabilityCatalog
  → AnalysisRequest / DatasetToolRuntime
```

This is one bounded reference adapter. It is not a generic ETL platform and it
does not add Excel, SQL/warehouse/API ingestion, documents, RAG, UI, or agent
runtime work.

## Components

- `src/thesis_data/csv_onboarding.py` parses strict UTF-8 CSV bytes, preserves
  headers/raw rows, computes the byte hash, and creates preview-only
  `StagedField` values.
- `src/thesis_data/onboarding_validation.py` consumes an explicit
  `FieldMappingSpec` and `MetricRegistry`, normalizes exact quarter formats,
  trims arbitrary entity IDs, parses only unambiguous decimal values, creates
  long-form `CanonicalObservation` objects, and returns a locked
  `OnboardingValidationReport` plus a candidate dataset.
- `src/thesis_data/canonical_snapshot.py` promotes only a candidate with a
  matching `VALID` report and atomically materializes generic tables:
  `dataset_metadata`, `sources`, `entities`, `periods`, `metrics`,
  `observations`, `peer_universes`, and `peer_universe_members`.
- `src/thesis_data/canonical_sqlite_provider.py` reads only those generic
  tables through `FinancialDatasetProvider`; it does not subclass or call the
  Gold adapter.

## Important invariants

- CSV content identity is the SHA-256 hash of the supplied bytes. Local paths
  are not application metadata.
- Headers and metric meaning are separate. A header such as `ROA (%)` becomes
  `company.roa` only through an explicit mapping.
- Blank mapped cells become `MISSING` observations with `value = NULL` and
  `missing_reason = DATA_UNAVAILABLE`; invalid numeric text is an `ERROR`.
- `YYYY_Qn`, `YYYYQn`, and `Qn-YYYY` normalize to `YYYY_Qn`; fuzzy periods are
  rejected.
- Canonical identity is `(entity_id, period_id, metric_id)` within a snapshot.
  Duplicates are reported and cannot be materialized.
- A candidate is materialized only through
  `build_snapshot_metadata(...) → CANDIDATE`, a matching `VALID` report, and
  `promote_snapshot_metadata(...)`. SQLite writes use one transaction and are
  rolled back on failure.
- Capabilities are discovered from persisted entities, periods, metrics, and
  peer metadata. The demo registry is not used as a capability list.
- CSV snapshots contain structured observations and source metadata, not
  document evidence; `get_evidence` is therefore not advertised.

## Verification

The focused coverage is in
`tests/test_phase0b_csv_onboarding.py`. It includes the primary
`BANK-X/BANK-Y` end-to-end path through `ApplicationRuntimeContext` and
`DatasetToolRuntime`, plus malformed CSV, mapping, normalization, duplicate,
missing-value, identity, capability, provenance, and transaction-failure
regressions.
