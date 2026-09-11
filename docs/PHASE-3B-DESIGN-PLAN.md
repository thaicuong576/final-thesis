# Phase 3B Design Plan — Query-Adaptive Semantic Critique and Revision

Status: pre-implementation contract for review. No Phase 3B runtime is
implemented by this document.

## Purpose

Phase 3B adds semantic quality evaluation and bounded targeted revision to the
query-adaptive analysis architecture. It does not create a generic autonomous
agent loop, replace the application planner, add RAG, or change historical
experiment artifacts.

## Frozen execution contract

The product first creates an `AnalysisPlan` from the `AnalysisRequest` and the
selected dataset capability catalog. Only specialists required by that plan
are active. Macro, Sector/Peer, and Company remain available capabilities;
none is mandatory for every request.

The initial output path is:

```text
active specialist outputs
  → synthesis
  → canonical AtomicClaim[]
  → Stage-1 deterministic acceptance
  → semantic critic
  → decision
```

The revision path is:

```text
CritiqueIssue[]
  → plan validation
  → affected active specialists only
  → merge revised specialist artifacts
  → re-synthesis of applicable outputs/links
  → canonical AtomicClaim[]
  → Stage-1 again
  → semantic critic again
  → accept / limited accept / revise / fail
```

The final candidate after every synthesis must pass Stage-1 before semantic
quality can produce an accepted result. Semantic scoring cannot override a
failed deterministic gate.

## Semantic applicability

The current six dimensions are:

- groundedness;
- cross-level integration;
- answer coverage;
- logical soundness;
- uncertainty/limitations;
- analytical usefulness.

A dimension is explicitly `NOT_APPLICABLE` when the frozen plan has no target
for it. `NOT_APPLICABLE` is not a failure and not a perfect score. Its policy
weight is excluded from the denominator, and the remaining weights are
renormalized. In the initial rule, cross-level integration is applicable iff
the plan declares at least one applicable link; the other five dimensions are
applicable by default.

Phase 3B-0 must make this state representable in the result and acceptance
contracts. An LLM/provider adapter must not decide applicability or use a
neutral `0.0`/`1.0` score hack.

## CritiqueIssue routing

Before routing, the critic result must be validated against the frozen plan:

- the affected specialist is active;
- affected claim IDs are known;
- cross-level reconciliation refers to a declared applicable link;
- every declared applicable link has exactly one result;
- unknown, duplicate, or omitted link results are rejected.

The existing `CritiqueIssue` concept remains the issue carrier. Cross-level
divergence is not automatically a contradiction.

## Limited acceptance

`ACCEPT_WITH_LIMITATIONS` is allowed only after Stage-1 passes and the remaining
unresolved issue is genuinely caused by unavailable or insufficient data or
evidence. The contract must keep data-availability and evidence-availability
families auditable. It must reject limited acceptance for unsupported
reasoning, ignored available evidence, incomplete synthesis, numeric/reference
integrity failure, unresolved contradiction, or provider/system failure.

## Research/product boundary

The product executes the final query-adaptive architecture and does not expose
Arm A/B/C. Research keeps:

- A — single-agent baseline;
- B — hierarchical without critique/revision;
- C — hierarchical with bounded critique/revision.

For B and C, initial planning and active-specialist selection must be
equivalent. C's additional mechanism is the bounded semantic critic and
targeted revision loop.

## Staged implementation roadmap

### Phase 3B-0 — Applicability and acceptance contract

Represent `NOT_APPLICABLE`, renormalized quality totals, plan-valid issue
routing, and explicit limited-acceptance issue families. No model or runtime
changes.

### Phase 3B-A — Fixture critic

Define a provider-neutral `SemanticCritic` protocol, deterministic result
validation, and fixture outputs using `StructuredCriticResult`. No OpenAI
integration and no changes to `run_agent_arm()`.

### Phase 3B-B — Bounded revision controller

Implement injected revision and synthesis adapters. Enforce maximum two
revision rounds, rerun affected active specialists only, rerun Stage-1 after
each re-synthesis, and persist auditable round state.

### Phase 3B-C — Runtime and claim adapters

Bridge application worker outputs into canonical `AtomicClaim[]` and connect
the controller to the query-adaptive application boundary. Keep Gold/SQLite
knowledge inside adapters/providers.

### Phase 3B-D — Replaceable model provider

Add a structured critic provider adapter behind the provider boundary. The
provider returns typed critic output; it does not own applicability, scoring
policy, acceptance, or routing decisions.

## Explicit non-goals

- no generic autonomous loop;
- no mandatory Macro → Sector → Company execution;
- no frontend architecture selector;
- no RAG or unrestricted data discovery;
- no modification of historical benchmark artifacts;
- no direct `db_path`, SQLite, or Gold-table dependency in the Phase 3B core.
