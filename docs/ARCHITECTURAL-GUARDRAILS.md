# Universal Project Constitution — Architectural Guardrails

**Status: LOCKED**
**Scope: the reusable analysis core, the reference application, and all future
implementation decisions**

This document is the canonical architectural guardrail for the thesis. It
turns the approved application-first constitution into repository-local rules.
When an implementation assumption conflicts with this document, stop and
report the conflict before changing code. Do not silently reinterpret the
architecture to fit implementation convenience.

This guardrail does not claim that every phase is already implemented. It
defines the boundary and the acceptance conditions that future work must obey.

## 1. Thesis framing

The thesis is primarily a reusable hierarchical multi-agent financial-analysis
architecture, demonstrated through a reference web application that can be
integrated with enterprise data infrastructure.

It is not primarily an LLM benchmark, a multi-agent demo, a chatbot, a
bank-specific script, a frontend-only application, or a Gold-dataset
experiment.

The business workflow is:

```text
Enterprise / research data
  → adapters and providers
  → canonical dataset and validated snapshot
  → analysis request
  → hierarchical multi-agent workflow
  → Macro / Sector / Company analysis
  → orchestrator cross-level review
  → bounded critique and targeted revision
  → acceptance and quality controls
  → evidence-backed report
```

The reference application is one deployment of this architecture. The
reusable core must remain usable if the frontend, storage technology,
organization, model provider, or domain-agent set changes.

## 2. Core/application boundary

The reusable analysis core contains:

- structured analysis and report contracts;
- domain-agent interfaces and tools;
- hierarchical orchestration;
- critique/revision workflow;
- deterministic acceptance and QA;
- evidence and provenance handling;
- audit/event contracts;
- report and synthesis logic.

The application/integration layer contains:

- SQL, warehouse, CSV, Excel, API, and document adapters;
- organization-specific schemas and metric mappings;
- storage and infrastructure;
- authentication and deployment concerns;
- the reference frontend client.

The core must not depend directly on the reference application's physical
database, local paths, UI, fixed issuer universe, fixed periods, or one model
provider.

## 3. Transferability guardrail

Before a major implementation step, ask:

> If the thesis frontend were removed and the current SQLite/Gold database were
> replaced by an enterprise warehouse, could the analysis core continue to
> operate by replacing adapters/providers and configuration?

The required answer is **yes**. This does not mean that a new organization
needs zero work. Adapter implementations, metric/domain configuration, source
tools, infrastructure, and deployment integration may change; orchestration,
critique/revision, acceptance, provenance, audit, and report logic should not
be rewritten for that reason.

Any new coupling that makes this answer **no** must be reported before work
continues.

## 4. Locked phase roadmap

### Phase 0 — Data foundation and integration boundary

Create the boundary from raw sources to a canonical, validated dataset:

```text
CSV / Excel / SQL / warehouse / API / documents
  → adapters/providers
  → canonical data contract
  → validated dataset snapshot
  → capability catalog
```

The minimum conceptual entities are Dataset, DatasetSnapshot, Source, Entity,
Period, MetricDefinition, Observation, Document, Evidence, and
DatasetCapability. The canonical observation is semantic and extensible; do
not create one core database column per financial metric.

Gold is a validated dataset instance and an adapter/provider fixture. Gold is
not the architecture. The thesis MVP needs one practical adapter and
documented extension points, not a complete ETL platform.

### Phase 1 — Structured analysis contracts

Represent material output through machine-checkable AtomicClaim,
StructuredAssertion, EvidenceRef, Scope, InferenceType, and Limitation
contracts. Preserve dataset/snapshot identity where applicable. Free prose may
not silently introduce material unsupported assertions.

### Phase 2 — Deterministic acceptance harness

The reusable acceptance harness must fail closed on numeric inaccuracy, invalid
references, missing critical evidence, scope violations, fabricated facts,
blocking contradictions, and empty claim output. Missing data remains missing.

Acceptance validates through provider interfaces and canonical observations;
it must not grow Gold-specific table access such as
`validate_against_gold_sqlite(...)`.

### Phase 3 — Semantic critique and bounded revision

Semantic evaluation occurs after deterministic integrity checks. Use the
existing `CritiqueIssue` concept and bounded actions such as re-query,
evidence retrieval, claim revision/removal, limitation addition, and
cross-level reconciliation. The default maximum is two revision rounds, and
only affected agents should be rerun where possible.

`ACCEPT_WITH_LIMITATIONS` is permitted only when integrity gates pass and the
remaining deficiency is explicitly caused by unavailable or insufficient data
or evidence. It must never hide numeric mismatch, invalid evidence,
unsupported inference, unresolved blocking contradiction, poor synthesis, or
provider/system failure.

### Phase 4 — Domain-agent layer

The locked initial specialist set is:

- Macro Agent;
- Sector Agent;
- Company Agent.

Agents consume provider-neutral tools. They must not depend on hard-coded
database paths, Gold tables, fixed tickers, one five-bank universe, fixed
periods, or fixed metrics. The intended dependency direction is:

```text
Agent → domain tool → provider/evidence provider → storage/API/warehouse
```

The design must allow later Risk, Valuation, ESG, or other agents without
redesigning the orchestrator.

### Phase 5 — Hierarchical orchestrated runtime

The orchestrator owns scope, planning, delegation, collection, cross-level
review, divergence detection, targeted revision, synthesis, and acceptance
submission. The locked worker structure is Macro/Sector/Company.

An analysis context must carry dataset identity, objective, targets, periods,
metrics, and peer-universe scope. The orchestrator must not contain
storage-specific business logic. Cross-level disagreement is not automatically
a contradiction, and every critique/revision round must remain auditable.

### Phase 6 — Application and enterprise integration

The reference application flow is:

```text
Dataset → Create Analysis → Live Agent Workflow → Final Report → Report Library
```

Enterprise deployments may use an existing UI and call an Analysis API. The
frontend is a reference client, not a prerequisite for the core. Dataset,
analysis, report, and event/SSE APIs are valid integration boundaries.

Runtime events may expose task, action, tool activity, artifact, output,
review, revision, and status. They must never expose chain-of-thought, hidden
scratchpads, system prompts, or raw private reasoning.

The current observable event vocabulary includes `DATASET_SELECTED`,
`SCOPE_VALIDATED`, `TASK_ASSIGNED`, `AGENT_STARTED`, `TOOL_STARTED`,
`TOOL_COMPLETED`, `AGENT_OUTPUT_CREATED`, `REVIEW_ISSUE_CREATED`,
`REVISION_REQUESTED`, `REVISION_COMPLETED`, `SYNTHESIS_COMPLETED`,
`REPORT_ACCEPTED`, `RUN_BLOCKED`, and `RUN_FAILED`.

### Phase 7 — Evaluation and transferability validation

Research retains the three-arm comparison:

- A — single-agent baseline;
- B — hierarchical without critique;
- C — final hierarchical with bounded critique/revision.

The final product uses the final architecture only; it must not expose an
architecture selector. Research benchmarking, ablation, human evaluation, and
architecture selection belong in research/evaluation code.

The thesis should include a lightweight transferability demonstration in which
two source adapters (for example Gold SQLite and a CSV fixture) feed the same
canonical contract, orchestrator, agents, acceptance harness, and report
pipeline. This demonstrates replaceability; it is not a data-engineering
benchmark.

## 5. Data and provenance rules

Use semantic, extensible contracts with a MetricDefinition/catalog layer. A
canonical observation conceptually carries:

```text
dataset_id, snapshot_id, domain, entity_id, period_id, metric_id,
value, unit, source_ref, validation_status
```

Raw data is immutable. Derived values retain input observation IDs and formula
versions. Missing values are explicit nulls with reasons. Published claims
retain source identity, period, unit, locator, and quality status.

Structured numeric data and unstructured evidence are separate source
families:

```text
Structured: raw source → normalization → observations → validation → snapshot
Documents: document → metadata/chunks → EvidenceRef
```

Do not force every document into numeric observation columns. Numeric claims may
trace to observations; narrative or policy claims may trace to document
evidence.

Capabilities must describe what a dataset actually supports. Generic logic
must not hard-code the current five-bank scope. The current five-bank sample
(ACB, TCB, VPB, MBB, VCB; 2024 Q1–Q4; NPL, Coverage, ROA, ROE) is a narrow
validated demonstration and must not be described as the full banking sector.
The application must communicate capability limitations accurately.

## 6. Product principles

The product is a financial-analyst workspace, not a chatbot or terminal. The
live workflow should make the following observable:

```text
Orchestrator assigns work
  → Macro / Sector / Company activity
  → tool activity and agent outputs
  → orchestrator review
  → targeted revisions
  → final synthesis
```

User-facing copy should be business-oriented. Internal IDs may appear in
technical/audit detail but should not dominate the normal experience.

## 7. Replaceable infrastructure

The storage layer must remain replaceable: SQLite, PostgreSQL, SQL Server,
Snowflake, BigQuery, warehouse/lakehouse, and internal APIs are possible
future providers. Do not prematurely implement all connectors.

The model layer must remain replaceable: OpenAI, Claude, Gemini, or internal
models may sit behind provider-specific adapters. Structured contracts,
orchestration, acceptance, audit, and report logic must not depend on one LLM
provider.

## 8. Business value and non-goals

The system should help analysts load validated information, analyze macro,
sector/peer, and company layers, reduce repetitive synthesis, reconcile
cross-level insights, trace claims to evidence, revise weak output, produce a
structured report, and integrate with enterprise workflows.

Do not expand the thesis into a complete ETL product, every sector/metric or
issuer, every warehouse connector, unrestricted autonomous discovery,
investment execution, real-time trading, public production deployment, a
terminal-like UI, chain-of-thought exposure, or benchmark optimization before
the application architecture is sound. Prefer a narrow complete vertical
slice.

## 9. Engineering and review policy

Preserve working code. Prefer additive abstractions, interface extraction,
adapters, and configuration over broad rewrites. Before refactoring, identify
the actual coupling, the isolating interface, test compatibility, and whether
Gold evaluation remains unchanged.

Multiple sessions may work concurrently. Before major work, inspect the latest
base; do not revert unrelated work; isolate the assigned scope; report
conflicts; and allow frontend/core work to proceed independently through stable
contracts.

Implementation agents do not self-merge. The required review flow is:

```text
implement → isolated commit/PR → independent review → fix RED/YELLOW issues
→ re-review → GREEN → merge
```

Passing tests alone is not architectural acceptance.

## 10. Mandatory pre-flight questions

Before each major phase, record the answers to:

1. Does this increase coupling to the current Gold dataset?
2. Does this increase coupling to SQLite or a physical schema?
3. Does this hard-code the current five-bank universe?
4. Would it still work if the frontend were replaced?
5. Would it still work if the database were replaced through an adapter?
6. Is it reusable core logic or reference-application logic?
7. Does it preserve evidence/provenance?
8. Does it preserve dataset/snapshot traceability?
9. Does it help the financial-analyst workflow?
10. Is it thesis scope that is not necessary?

If questions 1–3 are unnecessarily **yes**, reconsider the design. If 4–5
are **no**, report the coupling before proceeding.

## 11. Conflict rule and current implementation boundary

When requirements are ambiguous, choose the option that preserves modularity,
application value, auditability, replaceable infrastructure, and a
demonstrable narrow vertical slice. Do not infer a new thesis objective from
implementation convenience.

The Phase 2.5 Dataset Boundary is the current application integration
foundation. Its Gold adapter is allowed to know SQLite; application contracts,
provider protocols, request validation, tool runtime, and event contracts are
not. Phase 3A remains provisional until reviewed after the dataset boundary;
the Phase 3A compatibility correction must consume the provider abstraction.
Do not start Phase 3B or semantic implementation work without an explicit
phase-start decision. The final three-specialist architecture is not complete
for final evaluation until the bounded Macro Gold layer is available.

The north-star description is:

> A reusable hierarchical multi-agent financial-analysis architecture with
> evidence-grounded outputs, bounded critique/revision, deterministic quality
> controls, and replaceable enterprise data interfaces, demonstrated through
> an end-to-end web application for financial analysts.

Any materially conflicting task must stop with a report of the conflicting
requirement, affected components, minimum correction, and whether existing
work can be preserved.
