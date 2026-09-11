# Phase 0A — Canonical Onboarding Contracts

## Status

Phase 0A is implemented as the contract and deterministic-validation slice.
It does not create a canonical snapshot, parse CSV, or add a provider. Those
belong to Phase 0B.

The implementation is in
[`src/thesis_data/onboarding_contract.py`](../src/thesis_data/onboarding_contract.py).
It reuses the locked Phase 2.5 contracts instead of replacing them:

```text
RawDatasetDescriptor
  → explicit FieldMappingSpec
  → deterministic validation contracts
  → DatasetSnapshotMetadata
  → future canonical snapshot/provider
```

## Contracts

- `RawDatasetDescriptor` identifies immutable source content with a content
  hash and source type. `original_name` is a display name, not a physical
  path identity.
- `DatasetSnapshotMetadata` binds dataset/snapshot identity to source content,
  accepted mapping version, validation version, status, and creation time.
- `StagedField` records preview-only type/sample/null information. It does not
  infer financial meaning.
- `FieldMappingSpec` requires explicit entity, period, metric, unit, and
  analytical-level mappings. It cannot map identity/source fields as metrics.
- `MetricDefinition` and `MetricRegistry` describe admissible metric meaning;
  they do not claim that every dataset contains every registered metric.
- `OnboardingValidationIssue` provides deterministic issue IDs and a small
  ERROR/WARNING severity contract. `OnboardingValidationReport` is a stable,
  fail-closed status contract.

## Deterministic rules

`validate_field_mapping()` checks only explicit metadata and available raw
headers. It reports missing required fields, unsupported metrics, unit
conflicts, analytical-level conflicts, and missing source fields without
reading storage or asking an LLM to approve semantics.

Identity fields (`entity_field`, `period_field`, and optional
`source_ref_field`) must be distinct and cannot be reused as metric fields.
Deterministic validation issues derive their IDs from code, row, field, and
metric context; issue messages do not define identity. A VALID report may carry
WARNING issues but cannot carry ERROR issues or rejected rows. An INVALID report
requires at least one ERROR issue.

`compute_field_mapping_version()` hashes the canonical explicit mapping.
`compute_dataset_snapshot_id()` hashes the dataset ID, source content hash,
mapping version, and validation version. Therefore a changed source or changed
accepted mapping version produces a new snapshot identity. The same tuple is
reproducible.

`validate_snapshot_metadata()` fails closed when metadata does not match the
raw source hash or the recomputed identity.

`build_snapshot_metadata()` creates CANDIDATE metadata and rejects a direct
ACCEPTED status. `promote_snapshot_metadata()` is the deterministic acceptance
boundary: it validates source/identity metadata and requires a matching VALID
`OnboardingValidationReport` before returning ACCEPTED metadata.

## Seed registry boundary

`demo_metric_registry()` contains only a small demonstration taxonomy:
company ROA/ROE/NPL, sector credit growth, and macro policy rate. Registry
membership is not dataset capability. Actual availability must be derived from
the accepted snapshot's `DatasetCapabilityCatalog` in a later phase.

## Deliberate non-goals

Phase 0A does not implement CSV/Excel/SQL ingestion, normalization of raw rows,
SQLite materialization, provider methods, documents, PDF parsing, OCR, RAG,
LLM mapping approval, UI, agents, critic/revision, or experiment changes.

## Verification

The focused contract suite is
[`tests/test_phase0a_onboarding_contracts.py`](../tests/test_phase0a_onboarding_contracts.py).
It covers explicit mapping, registry/capability distinction, path-free source
identity, snapshot reproducibility/change detection, fail-closed reports, and
forged metadata.
