# Architecture

> Binding architectural rules: [`ARCHITECTURAL-GUARDRAILS.md`](ARCHITECTURAL-GUARDRAILS.md).
> This document describes the current implementation; the guardrail defines
> the non-negotiable boundary for future work.

Status: Working architecture with a query-adaptive final target. The current
runtime remains a transitional benchmark/scaffold and does not yet implement
the final adaptive critique/revision path.

## Design principle

The system separates deterministic financial computation from qualitative retrieval and language-model reasoning. It runs locally from a frozen gold snapshot so that baseline and hierarchical systems receive identical facts and evidence.

## Logical flow

```text
Immutable raw inputs
  → source registry and coverage manifest
  → normalized observations
  → deterministic metrics and peer benchmarks
  → validated evidence records
  → versioned gold snapshot
  → analysis request and capability validation
  → frozen AnalysisPlan
  → active specialist capabilities only
  → synthesis and canonical claims
  → Stage-1 deterministic acceptance
  → semantic critique and targeted revision
  → final synthesis and acceptance
  → report, quality report, and reproducible run record
```

The active specialist set is derived from the request and dataset capabilities.
Macro, Sector/Peer, and Company are not mandatory sequential stages. The
existing benchmark runners below are retained as transitional infrastructure;
their verification calls must not be described as the Phase 3B semantic
critic/revision loop.

## Data plane

### Raw and staging plane

Downloaded files and API responses are immutable and hash-recorded. The existing staging SQLite databases remain available for research and reconciliation but are not valid inputs for published benchmark conclusions while their quality status is pending validation.

### Normalized and gold plane

Normalized observations use canonical ticker, sector, metric, period, unit, source ID, locator, and quality status fields. Derived values retain input observation IDs and formula versions. A new versioned gold snapshot is created after readiness gates pass; it never overwrites a staging database.
Gold promotion also materializes per-ticker/per-metric coverage summaries so the
90% coverage gate is auditable rather than inferred from total row counts.
The comparative experiment entrypoint must pass `src/thesis_data/baseline_gate.py`:
it rejects staging/candidate snapshots, non-valid sources, incomplete target cells,
duplicate targets, target cells without a `value_check` label, and invalid metric
provenance before any agent arm is called. Gold promotion applies the same
cell-level review invariant before materializing a versioned snapshot.
The run-level contract in `src/thesis_data/experiment_contract.py` additionally
checks arm-specific critique budgets, snapshot identity, question-set identity,
typed question-set schema, and question validity before dispatch.
The adapter-based dispatch scaffold in `src/thesis_data/agent_runtime.py` then
prepares the same accepted company/sector/macro context plus page-aware
evidence snippets for each arm and records calls. Evidence is filtered through
the read-only boundary by valid source, target ticker, and period; its IDs are
carried into the run manifest. It is offline-testable and does not embed a
model provider or network fallback.
The provider-neutral `StructuredProviderAdapter` boundary in
`src/thesis_data/provider_adapter.py` is also testable: it accepts only an
explicitly injected transport, parses typed/JSON responses into `AgentPayload`,
and preserves or explicitly marks `AgentCallTelemetry`. Malformed responses,
missing required telemetry, and transport failures fail closed. The boundary
still does not create a provider client, resolve secrets, or make network
calls; provider execution remains a separate post-Gold gate.
The transport receives the deterministic prompt from
`src/thesis_data/prompting.py`, so provider-specific code cannot silently
rebuild the prompt with a different scope or version.
`src/thesis_data/run_manifest.py` stores a SHA-256 fingerprint of that rendered
prompt per call (while accepting legacy manifests without the additive field),
so prompt drift is detectable without persisting the full context-bearing
prompt text.
Company and sector metric queries also join `source_records` and require the
source itself to be `valid`; a valid-looking metric row cannot bypass source
quality status.
Sector benchmarks are filtered to the explicit peer set from the selected
question when present, or the frozen Gold ticker scope otherwise; unrelated
sector rows cannot silently change a peer median.

Outside-Gold bank onboarding follows the same provider boundary through a
separate immutable source packet. Parsing and mapping create a candidate;
structural success leaves uploaded numeric values pending. A reviewer must
match each accepted value to a valid primary source and exact locator, declare
period basis and reporting scope, and preserve formula/input lineage for
derived values. The generic canonical SQLite v3 provider stores and returns
these fields without changing the frozen Gold v5 artifact. Bank-specific IDs
come from the metric dictionary; packet conversion and provider access do not
branch on an issuer ID or the current five-bank sample.

Scanned PDF evidence is manually reconciled against rendered statement pages.
OCR or parser output can assist search but cannot promote a candidate; page
numbering, reporting scope, and source hash remain attached to the reviewed
observation.
The run's explicit source policy resolves to an allowlist of source tiers; the
current `*-primary-only-v1` policies allow only `primary`, and unknown policy
IDs fail before adapter dispatch. Company, sector, macro, and evidence queries
apply the same tier allowlist.

At dispatch time, each adapter call receives an isolated deep copy of its
context. Provenance validation and the recorded call trace use a separate
pre-call copy, so an adapter cannot mutate shared facts, expand the allowed
observation/source/evidence IDs, or alter the context that later workers see.
The returned payload must also preserve call identity: `agent_id` must equal the
request role, the period must equal the request period, and non-macro roles must
return the requested concrete ticker. Macro payloads may omit ticker because
their context is indicator-scoped. Metric maps are also bound to the request:
macro may publish only declared macro indicators, other roles may publish only
requested bank metrics/benchmarks, and each published metric must carry a unit
and an in-scope period. Any non-null numeric value must also carry observation,
source, or evidence provenance before it can be published.
All numeric boundary models reject non-finite values such as `NaN` and
Infinity before they can affect calculations or manifests.
The runtime tests also compare the prepared facts across all three arms to
ensure that the single-agent baseline is not given a weaker input.
Before preparation, the runtime binds the requested ticker, period, and metric
IDs to the selected typed question; mismatched requests are rejected before an
adapter call.
For a `company_trend` question, the caller must provide the complete ordered
question period list. The runtime prepares one read-only company, sector,
macro, and evidence context per period, and rejects an incomplete trend request
before dispatch. The resulting `AgentCallRequest` carries both the anchor
period and the ordered `periods` tuple, along with the selected question ID,
type, and prompt, so provider adapters do not have to infer the benchmark
question or its temporal scope from hidden process state.

Multi-period anomaly scanning applies the same deterministic rules separately
to each period and prefixes generated verification requests with that period.
The run manifest preserves the ordered period list for both the run and each
call trace; a trend result therefore cannot be mistaken for a single-period
run during later review.

`src/thesis_data/baseline_runner.py` is the execution boundary for one planned
baseline job. It verifies the plan job against the run configuration,
question-set hash, typed question metadata, issuer, periods, metrics, and macro
indicators before delegating to `run_agent_arm`. It accepts an injected adapter
only; it does not provide a network fallback or bypass the Gold gate.
The returned runtime result carries the validated `job_id`, which the manifest
builder persists so every planned result can be joined back to its exact plan
row.
The read-only `scripts/validate_baseline_plan.py` preflight audits the complete
plan against the current typed question set, including the exact hash, one job
per question/arm, and all job-level period/metric bindings, before any job is
eligible for dispatch.

The deterministic boundary also has a local smoke-test entrypoint at
`scripts/query_snapshot.py`. Its `company`, `sector`, `macro`, and `evidence`
subcommands return the same typed payloads as JSON, preserve observation/source/
evidence IDs, and open SQLite in read-only mode. This CLI is for development and
later agent adapters; it does not promote staging or candidate rows to Gold and
does not make network calls.

### Quantitative plane

Python code validates periods and units, derives quarter-only values from compatible YTD inputs, calculates ratios, computes peer statistics, and evaluates anomaly triggers. The language model is never the arithmetic authority.

The current trigger implementation is intentionally conservative: missing or
unaccepted company/sector values always create a verification request;
company-versus-sector deviation triggers are opt-in per metric and require a
positive pre-registered threshold plus an identical known unit. A trigger is a
request to check evidence, not a contradiction label.

### Evidence plane

PDFs and policy documents are parsed into page- and section-aware evidence records with source ID, ticker, period, document type, page, source URL, retrieval time, file hash, and parser status. Retrieval may use metadata filtering first. A vector index is optional and never replaces the original document or page reference. Each PDF also records text-layer coverage, extraction errors, table-parser warnings, and hash status. A scanned or mixed-text PDF is not treated as searchable merely because the file exists; it requires OCR or manual labeling before values become accepted evidence.

## Agent responsibilities

### Single-agent baseline

Uses the same deterministic query and evidence tools as the hierarchical arms and produces the same output contract. It is the primary fair baseline.

### Macro capability

Retrieves accepted policy-rate, credit-growth, and retained macro evidence for the target period. It preserves source status and does not infer causality from a single macro movement.

### Sector / Peer capability

Retrieves accepted peer medians, percentiles, and period changes for the frozen peer set. It does not recompute ratios from prose.

### Company capability

Retrieves accepted company metrics and filing evidence, explains company-specific drivers, and preserves missing or conflicting values.

### Master Orchestrator

Creates the request-derived `AnalysisPlan`, selects only required capabilities,
dispatches active specialists, validates payloads, reviews declared applicable
links, performs synthesis, and submits canonical claims to acceptance. Semantic
critique and bounded revision follow the Phase 3B contract below. Unresolved
limitations are shown in the final quality section.

## Current transitional verification scaffold

The current `run_agent_arm()` and `run_composite_arm()` implementations can
dispatch bounded `verification` calls after orchestration. They record calls
and payloads, but they do not create `StructuredCriticResult` or
`CritiqueIssue`, rerun affected specialists, re-synthesize, or re-evaluate the
final candidate. Existing benchmark artifacts must retain this limitation.

## Query-adaptive critique and revision target

The target Phase 3B order is:

```text
active specialist outputs
  → synthesis/re-synthesis
  → canonical AtomicClaim[]
  → Stage-1 deterministic acceptance
  → semantic critic
  → decision / targeted revision
```

For revision, validate every issue against the frozen `AnalysisPlan`, rerun
only affected active specialists, merge their revised artifacts, re-synthesize
the applicable outputs and links, and run Stage-1 again before semantic
evaluation. The controller is bounded to two revision rounds. A semantic critic
cannot override a failed deterministic gate. A dimension with no plan-derived
evaluation target is `NOT_APPLICABLE`; its configured weight is excluded and
the remaining quality weights are renormalized.

Cross-level reconciliation is allowed only for a declared applicable link.
Cross-level divergence is not automatically a contradiction.

The existing deterministic anomaly rules remain useful trigger inputs, but are
not presumed logical contradictions and do not replace semantic critique.

## Storage boundaries

- Raw source files are immutable.
- Normalized and processed tables are reproducible derivatives.
- Evidence metadata is stored alongside document and chunk identifiers.
- Gold snapshots, experiment configurations, and outputs are versioned.
- Secrets never enter the repository.

## Evaluation boundary

Research executes three arms: single-agent, hierarchical without
critique/revision, and hierarchical with bounded critique/revision. All use the
same request-derived scope, snapshot, source policy, model version, and output
contract. The product does not expose this architecture selector. Calls,
latency, tokens/cost, validation failures, evidence completeness, citation
correctness, factual correctness, semantic quality, and revision outcomes are
recorded.

## Deployment direction

The MVP runs locally and offline from cached fixtures and a validated snapshot. Preview deployment is optional after the experiment runner and data contracts are stable. Production deployment and real financial actions are outside the thesis MVP.
