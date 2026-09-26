# TASK — P4A multi-period Company trend runtime

## Dispatch

- Primary roles: `worker-api` owns API routing/DTOs; `worker-data` owns the
  storage-neutral Stage-1 completeness gate in `src/thesis_data/`.
- Base: `origin/main@35fec43f7f8189614f585511c050ad2a9627d01f`.
- Branch: `codex/p4-company-trend-runtime-20260926`.
- Tracking: Linear intentionally omitted because the user explicitly waived it
  for this workstream.
- Binding sources: `.agent/foundation/*`, `docs/ARCHITECTURAL-GUARDRAILS.md`,
  `docs/DATA-CONTRACT.md`, `contracts/openapi.json`, D-038/D-039/D-073 and the
  new P4A decision, `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`, and tracked T04/T05
  candidate inputs.

## Objective

Add one contract-first, provider-backed multi-period **Company trend** vertical
slice that makes candidate tasks T04 and T05 executable through the same frozen
plan, grounded writer, synthesis, Stage-1, semantic critique and bounded targeted
revision path as single-period analysis. This PR does not implement T08 or run
the scored A/B/C experiment.

## Frozen scope

1. Preserve the existing single-period API behavior.
2. Accept an explicit ordered period list of two to four unique canonical
   periods. A legacy `period` may coexist only as the final/anchor period.
3. Multi-period scope in this PR is Company-only: one target entity, no peer or
   macro capability. Any multi-period peer/macro request fails before provider
   retrieval; it must never degrade to one period.
4. Treat one trend as one logical task with period-keyed read-only context, not
   four independent analysis requests.
5. Prove T04 (TCB NPL + LLR coverage, 2024_Q1..Q4) and T05 (MBB ROA + ROE,
   2024_Q1..Q4) without hard-coding those issuers or metrics in reusable logic.
6. Keep T08, cross-level link normalization, macro, arbitrary range parsing,
   new delta formulas, UI work, live scoring and protocol freeze outside scope.

## Required contract behavior

- `AnalysisRequest.periods` carries the exact oldest-to-newest scope. Missing,
  duplicate, descending, over-budget or query-mismatched scopes fail before
  specialist/provider dispatch. `period` alone normalizes to a one-item list.
- `AnalysisPlan.periods` freezes that ordered list; `period` is the final anchor.
- Company output uses typed metric-period records. No map keyed only by metric
  may overwrite repeated metrics from different periods.
- Every `(entity, metric, period)` cell produces either an accepted observation
  with unit/basis/scope/provenance or explicit missingness with a reason.
- Numeric `AtomicClaim` objects remain one period each and preserve observation,
  source and locator lineage. Trend synthesis may describe direction but may not
  introduce unsupported numbers or causes.
- All expected cells in the frozen plan are checked by Stage-1. Partial silent
  coverage is a hard failure. The gate must derive expected cells from the
  frozen plan or receive an explicit typed expected-cell set; API-only checks
  are insufficient.
- The candidate hash binds the ordered period scope even when claim payloads
  are byte-identical under reordered plans.
- Targeted revision consumes issue/action content, changes only affected prose,
  preserves numeric/provenance fields, re-synthesizes and reruns Stage-1.
- Sync, SSE and persisted run history serialize the same ordered period scope.

## Acceptance cases

- Existing single-period company and peer tests remain green.
- T04 and T05 offline E2E each retrieve eight exact metric-period cells from one
  accepted snapshot, call Company only, expose no overwritten metric, and retain
  exact claim/evidence joins.
- Core Stage-1 accepts a complete valid matrix and a matrix with an explicit
  accepted missing cell; it rejects a dropped cell, duplicate/extra cell,
  range-level trend assertion used in place of facts, and invalid missing row.
- Reversing plan period order changes candidate identity and fails chronological
  request validation before dispatch.
- One multi-period semantic issue causes a material targeted Company revision;
  an unrepaired critical issue fails within the bounded round limit.
- A missing period, duplicate/descending list, list/query mismatch, unsupported
  period, fifth period, conflicting `period` versus final `periods` item, and any
  multi-period peer request all fail before data or model calls.
- Run history/SSE round-trip the same periods, claims and terminal state.
- Candidate P4 files remain pre-freeze and no A/B/C scores are generated.

## Ownership and boundaries

- Lead owns `contracts/`, `.agent/foundation/`, `AGENTS.md`, architectural
  decisions and this manifest.
- `worker-api` may edit `src/thesis_api/`, `src/thesis_agents/` and directly
  relevant API tests. It must not edit `contracts/`, `frontend/` or data files.
- `worker-data` may edit reusable `src/thesis_data/` and directly relevant core
  tests for the plan-aware coverage gate and candidate hashing. It must not edit
  API, frontend, contracts, or root-owned architecture records.
- Auditor is read-only and reviews exact final head.
- Raw/accepted data is immutable; history remains in the separate run store.

## Verification and handoff

Run focused core/API tests, full Python discovery, OpenAPI validation, architecture
guardrails, compileall, `git diff --check`, P4/VPB verifiers against the explicit
root evidence directory, and verify the root Gold DB hash is unchanged. Open a
PR titled `feat(api): add grounded company trend runtime`, wait for every remote
check and independent audit, and do not merge without explicit user approval.

The handoff reports base SHA, branch, commit SHA, PR, changed files, tests,
known failures/limitations and working-tree status.
