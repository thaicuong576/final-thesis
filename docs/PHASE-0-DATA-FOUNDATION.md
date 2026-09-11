# Phase 0 — Data Foundation and Integration Boundary

## Purpose

Phase 0 establishes the smallest application-facing data boundary for the
thesis. It separates analytical code from the physical shape of a dataset and
makes data identity, provenance, validation status, and missingness explicit.

The boundary is intentionally useful before the full agent workflow exists:
an application request can discover a dataset, read canonical observations,
retrieve source metadata, and consume pre-extracted evidence through the same
provider-neutral contracts.

## Frozen application architecture

```text
User Query
    ↓
AnalysisRequest + DatasetRef
    ↓
ApplicationRuntimeContext
    ↓
DatasetToolRuntime
    ↓
FinancialDatasetProvider
    ├── validated dataset adapter
    ├── canonical CSV adapter
    └── future dataset adapters
    ↓
CanonicalObservation / DatasetSource / DatasetEvidence
```

The application core owns request scope, capability checks, tool arguments,
event safety, and provider-neutral contracts. A provider owns the translation
from its physical storage into those contracts.

## Current vertical slices

### Structured data

The CSV slice stages immutable bytes, validates an explicit field mapping,
normalizes supported quarter identifiers, represents blank values as explicit
`MISSING` observations, and materializes a canonical SQLite snapshot. The
canonical snapshot contains the reference tables needed by the provider:

- dataset metadata and identity;
- sources;
- entities, periods, and metrics;
- observations;
- optional peer universes and memberships;
- optional documents and evidence.

The CSV adapter is one ingestion implementation, not part of the application
contract. The canonical SQLite provider exposes only the generic provider
interface to the application.

The provenance topology is deliberately split while remaining inside one
immutable snapshot:

```text
Structured source
    → CanonicalObservation

Document source
    → DatasetDocument
        → DatasetEvidence
```

The structured source and document source can therefore have independent
source references and content hashes. A document/evidence source is not forced
to reuse the CSV source.

### Unstructured evidence

Phase 0C defines a minimal `DatasetDocument` and reuses `DatasetEvidence` with
an optional `document_id`. It accepts only pre-extracted evidence rows. Each
persisted evidence row must resolve to a document, a source, and the same
dataset/snapshot identity. Evidence may intentionally have
`metric_id = null` when the physical evidence does not establish a canonical
metric binding.

The provider advertises `get_evidence` only when the canonical snapshot has
one or more evidence rows. A structured CSV snapshot with no evidence remains
valid and simply does not advertise that operation.

The accepted canonical SQLite schema is explicitly versioned as
`canonical-snapshot-v2`. Its `content_manifest_hash` binds the complete
accepted content universe: canonical source identities and hashes, document
content/source references, evidence identities/locators/quotes, and the
structured mapping/validation versions. Consequently, changing document
content or changing an evidence quote/locator creates a different accepted
snapshot identity even when the CSV bytes are unchanged.

This phase does not implement PDF parsing, OCR, chunking, embeddings, RAG,
semantic search, document ranking, or model-based extraction. Those are future
providers or ingestion stages and must not be implied by this boundary.

## Storage and portability rule

The validated Gold dataset remains an existing provider fixture and is not
rewritten by Phase 0. The canonical SQLite snapshot is reference storage for
the generic CSV boundary; it is not a requirement imposed on every provider.

Portability is demonstrated by sending both the Gold provider and the
canonical CSV provider through the same
`FinancialDatasetProvider → DatasetRef → AnalysisRequest →
ApplicationRuntimeContext → DatasetToolRuntime` path. The application helper
contains no Gold vocabulary, SQLite access, CSV parsing, physical table names,
or issuer-specific identifiers.

Replacing the physical dataset therefore primarily requires a provider and
its adapter-level tests. The request, capability, tool, event, and future
agent layers remain reusable while the provider satisfies the same contract.
This is a transferability claim about the integration boundary, not a claim
that all datasets have identical schemas or semantics.

## Integrity rules

- Dataset and snapshot identities are part of every canonical observation.
- Accepted documents and persisted evidence carry the final snapshot identity;
  provisional candidate IDs are not retained in the materialized snapshot.
- Source, document, and evidence IDs are unique within a snapshot, and every
  document/evidence source relationship is resolved and matched before
  publication.
- A provider rejects persisted rows whose identity differs from the requested
  `DatasetRef`; it never normalizes a physical mismatch into the request.
- The canonical provider accepts exactly the supported onboarding and snapshot
  schema contract versions.
- Raw dataset identifiers are opaque application identifiers and cannot contain
  filesystem path separators.
- Public source labels and document metadata cannot contain local filesystem
  paths.
- A valid numeric observation carries source provenance or explicit derivation
  provenance. Peer medians carry their input observation IDs and do not invent
  a source reference.
- Evidence provenance is separate from metric binding. A quote can be
  retrievable without being falsely attributed to a requested metric.
- Missing values remain explicit missing states; they are never zero-filled.

## Boundary status

Implemented in Phase 0:

- provider-neutral dataset contracts;
- fail-closed request and capability validation;
- immutable CSV staging and explicit mapping validation;
- canonical CSV SQLite materialization;
- optional pre-extracted document/evidence persistence and retrieval;
- provider capability gating for evidence;
- transferability proof across two provider implementations.

Not implemented in Phase 0:

- automatic source discovery;
- full PDF/document ingestion;
- RAG or vector stores;
- semantic evidence entailment;
- critic/revision control;
- Phase 3 semantic evaluation;
- the final multi-agent application loop.
