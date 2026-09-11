# Product and Research Specification

Status: Working scope accepted for data-foundation implementation; advisor confirmation remains a governance checkpoint.

## Objective

Design, implement, and evaluate an applied-fintech prototype that produces
traceable financial analysis by composing only the analytical capabilities
required by each request. The prototype combines deterministic financial data
processing with a query-adaptive hierarchical workflow, explicit cross-level
links, and bounded semantic critique/revision.

## Research question

In research comparison, on the same frozen dataset, evidence policy, question
set, model version, and output contract, does a query-adaptive hierarchical
workflow with bounded critique/revision improve factual correctness, evidence
traceability, cross-level consistency, and analytical usefulness over a fair
single-agent baseline, and what additional latency, model calls, and cost does
it require?

## Empirical scope policy

The first reproducible baseline uses the smallest source-reconciled scope that
can satisfy the readiness gate. The default first-baseline scope is the
48-cell feasibility pilot: ACB, TCB, and VPB across `2024_Q1`--`2024_Q4` and
four core metrics. The original five-bank/eight-quarter design remains a
provisional upper bound and may be promoted to an 80-cell or 200-cell
expansion only after the pilot's source coverage, conflict rate, and review
throughput pass the decision tree. Unchecked expansion rows are not a
readiness requirement for the first baseline.

## Provisional upper-bound scope

### Issuers and periods

- Five Vietnamese listed banks, provisionally VCB, ACB, MBB, TCB, and VPB, subject to primary-source coverage checks before freeze.
- Eight fixed fiscal quarters: `2024_Q1` through `2025_Q4`.
- A recorded benchmark cutoff and publication-availability rule.
- The other staged issuers remain preserved as out-of-benchmark data.
- Securities companies and TCBS are extension material, not primary benchmark members.

### Metrics

- Primary bank metrics: NPL group 3–5, loan-loss-reserve coverage, CIR, and ROA/ROE using an explicitly selected profit convention.
- Conditional metric: NIM after earning-asset mapping and source reconciliation.
- Extension metrics: CASA, simple LDR, disclosed CAR, and additional market indicators only after coverage and definition validation.
- Sector outputs: median, percentile, and period-over-period change from accepted observations only.
- Macro context: policy-rate movement and credit-growth context, plus other indicators only when period-aligned authoritative sources are available.

## First-baseline pilot scope

- Issuers: `ACB`, `TCB`, and `VPB`.
- Periods: `2024_Q1`, `2024_Q2`, `2024_Q3`, and `2024_Q4`.
- Core metrics: NPL group 3--5, loan-loss-reserve coverage, ROA, and ROE.
- CIR and NIM remain conditional until their definitions and signs reconcile
  across the included issuers.
- The pilot contains 48 target cells and is the default scope for the first
  provider-backed baseline after Gold promotion.

The full draft question set contains one macro-to-bank question. Because the
current official macro route has not yet produced a period-aligned 2024_Q4 Gold
observation, the primary evaluation may use the separate
`experiments/question-set-core-v1.json` (13 bank-focused questions, 39 jobs
across the three arms). The macro question remains a pre-registered extension
and is not included in the primary aggregate until its macro observations pass
the same Gold policy. This narrows the evaluation track, not the system
architecture: Macro, Sector/Peer, and Company remain available capabilities,
while the active set is selected from the request-derived AnalysisPlan.

Metric definitions, units, period rules, source tiers, and formula tests are maintained in `docs/METRIC-DICTIONARY.md`.

## Source and data policy

Official issuer filings or investor-relations documents, SBV publications, and GSO publications are primary evidence. Structured vendor APIs are ingestion accelerators or cross-checks until reconciled. Research reports are contextual material and cannot replace primary numeric evidence.

Raw inputs are immutable. A missing value is represented as null with a reason. Every accepted observation and published claim has source identity, period, unit, locator, and quality status. The staging snapshot is never overwritten by a gold snapshot.

## System outputs

1. A structured company and sector analysis report.
2. A peer comparison table based on accepted observations.
3. A source-linked evidence trail.
4. A critique/revision history with resolved, explained, or unresolved outcomes.
5. A data-quality report with coverage and limitations.
6. A reproducible run record containing snapshot identity, configuration, model calls, timing, and cost.

## Required phases

### Research and data foundation

Create a source inventory, retrieval manifest, normalized dataset, metric dictionary, quality report, evidence records, and manually checked gold sample. The phase is complete only when the readiness checklist produces `READY_FOR_BASELINE`.

### Baseline

Implement a single-agent workflow using the same prepared data, deterministic tools, evidence policy, fixed questions, and output contract as the hierarchical systems.

### Query-adaptive hierarchical system

Implement Macro, Sector, and Company capabilities coordinated by a Master
Orchestrator. The Orchestrator validates dataset capabilities, freezes an
AnalysisPlan, selects only required specialists and applicable links, performs
synthesis, runs Stage-1 deterministic acceptance on canonical claims, and then
uses a semantic critic with at most two targeted revision rounds. Inactive
specialists are `NOT_APPLICABLE`, not failures. Every re-synthesis must pass
Stage-1 again before semantic scoring or acceptance.

### Evaluation

Run the single-agent baseline, hierarchical-without-critique, and
hierarchical-with-critique arms against the same request-derived scopes and
fixed question set. The primary aggregate may use the bank-core question set;
report the macro extension separately if its Gold gate passes. Compare factual
correctness, calculation correctness, evidence completeness, citation
correctness, critique/revision quality, cross-level consistency, analytical
usefulness, latency, model calls, and cost. These arms remain research
artifacts and are not exposed as a product architecture selector.

## Data-foundation exit criteria

- A versioned selected-scope configuration is frozen for the first baseline;
  by default this is the 3-issuer/4-period pilot above. An 80- or 200-cell
  expansion must pass the same gates independently before it is included.
- Coverage is reported for every selected ticker, primary metric, and period.
- Every metric has a documented formula, unit, source, and period rule.
- Raw files and API responses are preserved unchanged.
- Date, duplicate, missing, unit, period, and cross-source checks are implemented.
- Primary metric validated coverage is at least 90%, or each gap has an explicit exclusion reason.
- A manually verified gold sample contains at least 40 metric/evidence items and covers every selected bank and primary metric.
- Every derived value retains its input observation IDs and formula version.
- Every published claim has complete provenance.
- Critical and major conflicts are resolved or excluded.

The current staging database does not meet these criteria. See `docs/DATA-READINESS-CHECKLIST.md`.

## Non-goals for the thesis MVP

- Real-time trading or investment execution.
- A production-grade financial advisory product.
- Unbounded autonomous research or a general-purpose crawler.
- Broad coverage of every listed company or every financial sector.
- Treating research reports or fallback macro data as substitutes for primary evidence.
- Claiming universal superiority of hierarchical agents.

## Definition of done

The thesis MVP is complete when a versioned gold snapshot passes the readiness
gate, deterministic calculations and contracts pass their tests, the final
query-adaptive application workflow runs end to end on a supported request,
the research arms run on their fixed evaluation scope, reports contain valid
citations and quality flags, and the results document both benefits and
costs—including null or negative findings.
