# Repository Hygiene / Dead-Asset Audit — 2026-09-16

Status: audit-only evidence for review. No implementation, data, thesis artifact,
branch history, or runtime behavior was changed by this audit.

## Scope and baseline

The prerequisite merge was verified before this branch was created:

- PR #4, `chore/historical-branch-cleanup`, is `MERGED` into `main`.
- `origin/main` and this audit branch both resolve to
  `2b77b938f2c314020aabf448535a890bc173f088`.
- Default branch is `main`.
- Audit branch: `chore/repository-hygiene-audit`.
- Audit worktree: `D:/eddie-projects/personal-projects/final-thesis-repository-hygiene-audit`.

The repository contains 494 tracked files at this baseline: 72 Python modules
under `src/thesis_data/`, 91 scripts, 91 tests, 61 tracked frontend files, 27
tracked data artifacts, and 66 tracked Markdown documents under `docs/`.
Disposition counts below are counts of auditable disposition rows/groups, not a
claim that those categories sum to all 494 files.

Evidence methods used:

- `git ls-files`, `git log`, `git status`, and `git ls-remote` for repository
  state and tracked-file inventory;
- AST/static import inspection for Python and TypeScript import/route scans;
- `rg` across source, tests, scripts, manifests, and documentation;
- SHA-256 grouping for exact file duplicates;
- JSON/JSONL parsing and manifest-local-path existence checks;
- read-only test, architecture-guard, compile, lint, frontend-test, and build
  commands.

## Executive summary

| Disposition | Count of audit rows/groups | Meaning |
|---|---:|---|
| Active / retain active | 10 | Current application, contract, adapter, research, or CI surfaces with observed callers or an explicit current role. |
| Retain historical / reproducibility | 11 | Experiments, thesis material, frozen viewer, human-review tooling, raw evidence, manifests, and phase records that must remain traceable. |
| Archive / consolidate candidate | 6 | Exact duplicates or stale historical/doc surfaces that may be handled in separate, reference-aware PRs. |
| Removal candidate | 2 | `frontend/src/features/create-analysis/index.ts` and `src/thesis_data/experiment_compat.py` are candidates only; neither is approved for deletion by this audit. |
| Architectural debt | 8 | Transitional Gold/SQLite runners, fixture-specific surfaces, missing dependency/state publication, and documentation/provenance drift. |
| Uncertain / investigate further | 5 | Items where absence of a current caller is not enough to establish safe removal. |

Overall status: **PHASE4_READY_WITH_NONBLOCKING_HYGIENE_DEBT**.

The active architecture is identifiable: the React application routes through
`frontend/src/main.tsx`, `frontend/src/App.tsx`, and
`frontend/src/app/router.tsx`; the provider-neutral core is represented by
`src/thesis_data/analysis_plan.py`, `dataset_provider.py`,
`dataset_contract.py`, `acceptance_resolver.py`, and the locked semantic/revision
modules. The main hygiene risks are not ambiguity about the canonical Phase 4
layer; they are missing ignored research artifacts, stale documentation links,
and transitional research runners that must not be mistaken for the new
application architecture.

## Safe-now candidates

“Safe-now” means suitable for a later, narrowly scoped PR after its own review.
It does not authorize deletion in this audit PR.

| Path | Classification | Evidence | Risk | Recommendation |
|---|---|---|---|---|
| `frontend/src/features/create-analysis/index.ts` | `POSSIBLY_UNUSED` barrel | The file exports `CreateAnalysisPage` and `analysisRequestSchema`, but the current page, router, and tests import their concrete paths. The TypeScript reverse-import scan found no importer for this barrel. | LOW–MEDIUM | `REMOVE_IN_SCOPED_PR` after a clean frontend lint/test/build and one final case-sensitive import scan. |
| `src/thesis_data/experiment_compat.py` | `POSSIBLY_UNUSED` compatibility layer | AST scan found no Python importer and repository search found only its own definitions plus documentation references, including Phase 2.5 compatibility notes. | MEDIUM–HIGH | `INVESTIGATE_FURTHER`; remove only after confirming old experiment manifests and external/user commands do not rely on it. |
| `CONTRIBUTING.md:4` | stale governance wording | It says historical branch `thesis/phase-1-7` is retained, while the cleanup record and remote state say historical branches were removed from the active branch set. | MEDIUM | `CONSOLIDATE` in a docs-only PR; preserve the historical fact in `docs/BRANCH-CLEANUP-2026-09-16.md`. |
| `docs/ADVISOR-ARTIFACT-INDEX-VI.md` and `docs/IMPLEMENTATION-ROADMAP-V1.md` | broken current-reference links | They link to ignored/untracked `data/processed/`, `reports/`, and frozen-viewer payloads absent from a clean checkout. | HIGH | `MIGRATE` only after deciding whether those artifacts are published, archived, or regenerated; do not delete the index. |
| `data/manifests/macro-official-2024-q4-v1.jsonl` | stale manifest path set | Nine `local_path` values point to `data/raw/macro-official-2024-q4-v1/`, which does not exist in this checkout; the same acquired artifacts exist under `data/raw/pre-phase4-acquisition-v1/` and are referenced by the newer manifest. | HIGH | `MIGRATE` through a data/provenance PR with owner review and hash re-verification. Do not patch or delete it in a hygiene PR. |

No candidate above is a “delete now” recommendation. The only low-risk
candidate is the unused frontend barrel, and even that should be removed in its
own PR because an import-path mistake can be build-breaking.

## Do-not-touch list

The following may look old or unreferenced but are retained intentionally:

- All raw artifacts under `data/raw/`, both manifests, reconciliation files,
  candidate registries, and source hashes. They are evidence/provenance, not
  dead files.
- `src/thesis_data/schema.py`, `dataset_contract.py`, `dataset_provider.py`,
  `acceptance.py`, `acceptance_resolver.py`, `semantic_evaluation.py`,
  `semantic_critic.py`, and `revision_controller.py`. These are central
  contracts or locked acceptance/revision behavior.
- Gold and SQLite adapters such as `gold_dataset_provider.py`,
  `canonical_sqlite_provider.py`, `macro_gold.py`, and the historical
  `agent_tools.py`/`query.py` path. They are transitional or adapter surfaces,
  not evidence that Gold is the reusable core.
- `experiments/runs/offline-fixture-v1` through `v9`. The runs README records
  v9 as current and v1–v8 as historical plumbing snapshots; exact byte
  equality is not enough to erase experiment lineage.
- `legacy/frozen-report-viewer/`, `research/evaluation-ui/`, thesis drafts,
  visual assets, and phase/decision documents. Their product-runtime absence
  does not make them disposable thesis evidence.
- Ignored `data/processed/`, `reports/`, `.agents/`, and local SQLite/report
  artifacts. Their absence from this clean checkout is a reproducibility issue,
  not permission to manufacture, promote, or remove them.
- Diverged worktrees and branches outside `main`. This audit did not compare,
  merge, delete, or rewrite them.

## Python module audit

### Classification method

The table uses the required classification vocabulary. “Internal callers” are
other `src/thesis_data` modules found by AST import inspection. “External refs”
are script/test references found by repository search; a zero count is a
candidate signal only, not proof of safe removal. High-risk modules and the
transitional paths are discussed after the table.

| Module | Classification | Static evidence | Newer architecture / removal risk |
|---|---|---|---|
| `__init__.py` | `ACTIVE_CORE` | Package boundary; no reverse importer is expected. | Required package marker; do not remove. |
| `acceptance.py` | `ACTIVE_CORE` | Internal: `gold_acceptance_compat`, `revision_controller`; external refs: acceptance tests. | Core Stage-1 behavior plus compatibility entrypoints; HIGH. |
| `acceptance_resolver.py` | `ACTIVE_CORE` | Internal: acceptance, semantic, revision, LangGraph; boundary tests. | Provider-neutral resolution; HIGH. |
| `agent_runtime.py` | `ACTIVE_RESEARCH` | Internal: agent tools, baseline/composite runners, transports; 8 test/script refs. | Transitional benchmark scaffold, explicitly retained for research reproducibility; HIGH. |
| `agent_tools.py` | `ACTIVE_RESEARCH` | Internal: composite/openai transports; agent/composite/macro tests. | Gold-oriented transitional tools; superseded for new app work but required by old runs; HIGH. |
| `analysis_plan.py` | `ACTIVE_CORE` | Internal: semantic/revision/LangGraph/OpenAI; Phase 3A–D tests. | Current query-adaptive planner contract; HIGH. |
| `analysis_report.py` | `ACTIVE_CORE` | Report render/validation scripts and report tests. | Current report contract; HIGH. |
| `analysis_report_validation.py` | `ACTIVE_CORE` | Report render/validation scripts and tests. | Current output validation; HIGH. |
| `analysis_request.py` | `ACTIVE_CORE` | Internal: plan/application/transferability/compat; Phase 0/2.5/3A tests. | Dataset-bound request contract; HIGH. |
| `anomaly.py` | `ACTIVE_RESEARCH` | Internal: old agent/composite runtime; anomaly test. | Transitional research verification; retain until old benchmarks are retired. |
| `application_runtime.py` | `ACTIVE_APP` | Internal: dataset tool runtime/transferability; application-boundary tests. | Current app boundary; HIGH. |
| `baseline_batch_runner.py` | `ACTIVE_RESEARCH` | Internal: offline fixture; planning/run scripts and tests. | Baseline experiment entrypoint; HIGH reproducibility risk. |
| `baseline_gate.py` | `ACTIVE_RESEARCH` | Internal: experiment contract; baseline scripts/tests. | Research gate, not application runtime. |
| `baseline_plan.py` | `ACTIVE_RESEARCH` | Internal: batch/runner/offline fixture; 13 script/test refs. | Current experiment planning surface; HIGH. |
| `baseline_runner.py` | `ACTIVE_RESEARCH` | Internal: batch runner; OpenAI baseline script/tests. | Research baseline runner; retain. |
| `blind_aggregate.py` | `ACTIVE_RESEARCH` | Blind-score aggregation scripts/tests. | Human/AI evaluation reproducibility; HIGH. |
| `blind_ai_review.py` | `ACTIVE_RESEARCH` | Blind review script/tests. | Evaluation tool; not product dead code. |
| `blind_scoring.py` | `ACTIVE_RESEARCH` | Multiple blind-score scripts/tests. | Evaluation scoring; HIGH. |
| `canonical_snapshot.py` | `ACTIVE_CORE` | Internal: SQLite provider; Phase 0/acceptance tests. | Snapshot identity/promotion boundary; HIGH. |
| `canonical_sqlite_provider.py` | `ACTIVE_ADAPTER` | Phase 0B/0C and resolver tests. | Storage adapter; physical coupling is intentionally at adapter boundary. |
| `comparative_gate.py` | `ACTIVE_RESEARCH` | Complexity pilot script and tests. | Research comparison gate; not current app runtime. |
| `composite_runner.py` | `ACTIVE_RESEARCH` | Internal: run manifest; complexity script/tests. | Older composite benchmark; transitional, HIGH. |
| `composite_schema.py` | `ACTIVE_RESEARCH` | Internal: acceptance/runner/transport/provider adapter; composite tests. | Legacy composite payload compatibility; do not remove before experiment migration. |
| `composite_transport.py` | `ACTIVE_RESEARCH` | Internal: composite runner/OpenAI/provider adapter; complexity/transport tests. | Old provider transport; transitional. |
| `context_budget.py` | `ACTIVE_CORE` | Internal: composite runner; context-budget test. | Bounded-context utility still supports research; low removal confidence. |
| `csv_onboarding.py` | `ACTIVE_ADAPTER` | Internal onboarding validation; Phase 0B/0C tests. | Current structured-ingestion adapter; HIGH. |
| `dataset_contract.py` | `ACTIVE_CORE` | 17 internal callers and 11 external refs. | Canonical dataset boundary; HIGH. |
| `dataset_provider.py` | `ACTIVE_CORE` | Provider, resolver, runtime, and application callers. | Provider-neutral contract; HIGH. |
| `dataset_tool_runtime.py` | `ACTIVE_APP` | Application/transferability callers; Phase 0B/2.5 tests. | Current tool boundary; HIGH. |
| `documents.py` | `ACTIVE_RESEARCH` | Document audit script/tests and legacy query callers. | Evidence/research utility; retain. |
| `evidence_contract.py` | `ACTIVE_CORE` | Snapshot/provider/onboarding callers; boundary tests. | Provenance contract; HIGH. |
| `evaluation.py` | `ACTIVE_RESEARCH` | Blind-review scripts/tests. | Evaluation pipeline; HIGH. |
| `expansion_review.py` | `ACTIVE_RESEARCH` | Candidate audit/build scripts/tests. | Gold expansion review; HIGH. |
| `experiment_compat.py` | `POSSIBLY_UNUSED` | No AST Python importer; docs references remain. | Possible migration shim; removal requires compatibility/history review. |
| `experiment_contract.py` | `ACTIVE_RESEARCH` | 15 script/test refs and runner callers. | Experiment contract; HIGH. |
| `gold_acceptance_compat.py` | `COMPATIBILITY_LAYER` | Gold provider/acceptance tests only. | Explicit Gold bridge; not reusable core, but needed by historical tests. |
| `gold_dataset_provider.py` | `ACTIVE_ADAPTER` | Resolver/runtime boundary tests and Gold compatibility. | Gold fixture adapter; retained behind provider boundary. |
| `in_memory_provider.py` | `ACTIVE_ADAPTER` | Provider-boundary and Phase 2.5 tests. | Test/application provider implementation; active. |
| `kpi.py` | `ACTIVE_RESEARCH` | KPI extraction/import scripts and tests. | Research data preparation; retain. |
| `kpi_storage.py` | `ACTIVE_RESEARCH` | KPI import script/tests. | Research storage helper; no deletion evidence. |
| `langgraph_revision_runtime.py` | `ACTIVE_ADAPTER` | Phase 3B-C tests; revision controller caller. | Locked orchestration adapter; not dead because direct runtime imports are intentionally narrow. |
| `macro_gold.py` | `ACTIVE_ADAPTER` | Macro snapshot script and Macro Gold tests. | Gold-specific materializer; adapter/fixture, not Phase 4 core. |
| `metrics.py` | `ACTIVE_RESEARCH` | Legacy `query.py` caller and metric test. | Transitional query metrics; retain until old benchmark migration. |
| `normalize.py` | `ACTIVE_ADAPTER` | Normalization script plus onboarding/resolver tests. | Ingestion adapter; HIGH. |
| `offline_fixture.py` | `ACTIVE_RESEARCH` | Offline runner script, baseline callers, tests. | Reproducible experiment fixture; HIGH. |
| `onboarding_contract.py` | `ACTIVE_CORE` | Snapshot/provider/CSV/validation callers; Phase 0 tests. | Dataset onboarding contract; HIGH. |
| `onboarding_validation.py` | `ACTIVE_CORE` | Canonical snapshot/CSV/onboarding callers; Phase 0 tests. | Deterministic validation boundary; HIGH. |
| `openai_semantic_critic.py` | `ACTIVE_ADAPTER` | Phase 3B-D tests. | Model provider adapter by design; narrow direct callers are expected. |
| `openai_transport.py` | `ACTIVE_ADAPTER` | Baseline/complexity scripts and transport tests. | Provider transport; research adapter. |
| `periods.py` | `ACTIVE_CORE` | KPI/normalize/snapshot callers; period tests. | Canonical period handling; HIGH. |
| `pilot_assembly.py` | `ACTIVE_RESEARCH` | Official-pilot script/tests. | Gold/research assembly; retain. |
| `prompting.py` | `ACTIVE_CORE` | Provider adapter/run manifest callers; prompt/provider tests. | Provider-neutral prompt contract; active. |
| `provider_adapter.py` | `ACTIVE_ADAPTER` | Offline/OpenAI transport and complexity scripts/tests. | Provider boundary; active. |
| `provider_config.py` | `ACTIVE_ADAPTER` | Baseline, transport, OpenAI critic, provider callers. | Configuration adapter; secret-safe boundary. |
| `query.py` | `ACTIVE_RESEARCH` | Internal: old agent/tools/blind/documents; query and Macro tests; `scripts/query_snapshot.py`. | SQLite/Gold-oriented historical query path; transitional, HIGH. |
| `question_set.py` | `ACTIVE_RESEARCH` | Baseline/offline/experiment callers and validation scripts. | Experiment fixture; retain. |
| `report_view.py` | `ACTIVE_CORE` | Report render scripts via `analysis_report`; report tests. | Output shaping; active. |
| `review_import.py` | `ACTIVE_RESEARCH` | Review promotion script/tests. | Human review ledger; HIGH. |
| `review_navigation.py` | `ACTIVE_RESEARCH` | Blind source-navigation script/tests. | Review reproducibility; retain. |
| `review_progress.py` | `ACTIVE_RESEARCH` | Review progress script/tests. | Review reproducibility; retain. |
| `review_promotion.py` | `ACTIVE_RESEARCH` | Promotion script/tests. | Gold/review governance; HIGH. |
| `revision_controller.py` | `ACTIVE_CORE` | LangGraph adapter and Phase 3B-D tests. | Locked bounded revision kernel; HIGH. |
| `run_manifest.py` | `ACTIVE_RESEARCH` | Baseline/complexity/offline scripts/tests. | Experiment lineage; HIGH. |
| `runtime_events.py` | `ACTIVE_CORE` | Application/dataset tool runtime; Phase 2.5 tests. | Public event contract; active. |
| `schema.py` | `ACTIVE_CORE` | 69 internal callers and 34 script/test refs. | Central models; do not touch for hygiene. |
| `semantic_critic.py` | `ACTIVE_CORE` | OpenAI/revision callers; Phase 3B-A/B/D tests. | Provider-neutral semantic boundary; LOCKED. |
| `semantic_evaluation.py` | `ACTIVE_CORE` | LangGraph/OpenAI/revision/critic callers; Phase 3A/B tests. | Locked Stage-2 evaluation boundary; HIGH. |
| `snapshot.py` | `ACTIVE_RESEARCH` | Snapshot audit script/tests. | Historical/research snapshot tooling; retain. |
| `storage.py` | `ACTIVE_ADAPTER` | 30 script/test refs and research adapters. | Existing storage adapter; do not infer deadness from lack of app imports. |
| `transferability.py` | `ACTIVE_ADAPTER` | Application boundary plus transferability test. | Explicit transferability smoke helper; active despite narrow callers. |
| `transport_errors.py` | `ACTIVE_CORE` | Composite/OpenAI transport callers. | Shared error contract; active. |
| `workload_contract.py` | `ACTIVE_CORE` | Agent/composite/prompting/question/run-manifest callers; 9 external refs. | Shared workload contract; active. |

### High-risk transitional modules

`agent_runtime.py`, `agent_tools.py`, `composite_runner.py`,
`composite_schema.py`, `composite_transport.py`, `query.py`, and related
baseline modules form a real, tested research path. They do encode older Gold,
SQLite, fixed-workload, or composite assumptions, but `docs/ARCHITECTURE.md`
explicitly describes the benchmark/scaffold as transitional and retained. The
new Phase 4 application must not import this path accidentally; deleting it now
would instead break historical baseline reproducibility.

`experiment_compat.py` is the only Python module with no discovered Python
caller. That is a removal candidate, not a deletion decision, because the file
is referenced by compatibility documentation and may serve external commands or
historical manifests not visible to static import analysis.

No module was classified `LEGACY_RUNTIME`, `TEST_SUPPORT`,
`HISTORICAL_BUT_REQUIRED`, or `UNKNOWN` as its primary disposition: modules
that are old but still executable were classified `ACTIVE_RESEARCH` or
`COMPATIBILITY_LAYER`, and modules that are package markers or locked contracts
were classified `ACTIVE_CORE`.

## Frontend audit

### Current route and entrypoint map

| Surface | Evidence | Disposition |
|---|---|---|
| `frontend/src/main.tsx` → `frontend/src/App.tsx` → `frontend/src/app/router.tsx` | Application bootstrap and router imports. | `RETAIN_ACTIVE`. |
| `/` | Redirects to `/analysis`. | `RETAIN_ACTIVE`. |
| `/analysis` | `CreateAnalysisPage`; tested in `frontend/tests/CreateAnalysisPage.test.tsx`. | `RETAIN_ACTIVE`. |
| `/data` | `DataPage`; tested in `frontend/tests/DataPage.test.tsx`. | `RETAIN_ACTIVE`. |
| `/analysis/new` | Redirects to `/analysis`. | Intentional compatibility route. |
| `/reports` | `ReportsPlaceholderPage`; route is reachable but intentionally placeholder. | `RETAIN_ACTIVE`, product incompleteness debt. |
| `/analysis/:runId`, `/reports/:reportId`, `/research` | Not registered in the current router. | Do not call dead without a separate product decision; no current source route evidence. |

The TypeScript graph found 93 internal import edges. All reachable UI
components, hooks, services, models, and primitives have importers except
`frontend/src/features/create-analysis/index.ts`, which has no importer in
`frontend/src` or `frontend/tests`. The feature code itself is active through
concrete imports; only this barrel is a candidate.

`frontend/src/entities/analysis/api/analysisService.ts` is an active client
scaffold, not a backend integration: it returns client-validation state. The
mock capability/dataset providers are also active application adapters, clearly
described as simulated data. They should be replaced behind the same service
boundary in a later Phase 4/5 task, not deleted as dead code.

`frontend/package.json` has scripts for `dev`, `build`, `lint`, `test`, and
`preview`. Static usage inspection found no dependency that can be proven
unused; React Query, React Hook Form, Zod, Radix primitives, Lucide, Vite,
TypeScript, ESLint, and Vitest all have source/config/test evidence.

`.github/workflows/frontend.yml` is the only active CI workflow. It runs Node
24 with `npm ci`, lint, test, and build on frontend changes. There is no root
Python dependency manifest or Python CI workflow in the tracked tree.

## Research and legacy audit

| Surface | Evidence | Classification | Action |
|---|---|---|---|
| `legacy/frozen-report-viewer/` | `index.html` fetches `data/analysis-report.json` and `data/analysis-series.json`; README documents generation through report scripts. Those payloads are absent from a clean checkout. | `RETAIN_REPRODUCIBILITY` | Keep. Later either publish a deterministic fixture package or explicitly document that the viewer requires ignored generated inputs. |
| `research/evaluation-ui/` | `review.html` and README implement a standalone human evaluation/review surface. | `RETAIN_RESEARCH` | Keep; not part of the React product route. |
| `app/` | Directory is absent from current `main`. | `ARCHIVE_REFERENCE_ONLY` | Do not recreate or delete based on old thesis links. Historical docs referring to `app/index.html` need later wording cleanup. |
| `experiments/runs/offline-fixture-v1` … `v8` | `experiments/runs/README.md` identifies v9 as current and v1–v8 as earlier plumbing snapshots. | `RETAIN_REPRODUCIBILITY` | Keep until experiment lineage is tagged/exported and a separate cleanup PR proves consolidation safe. |
| `experiments/runs/offline-fixture-v9` | Current planned/offline fixture with manifests, plan, and question set. | `RETAIN_ACTIVE` | Keep; it is not evidence of a completed provider-backed run. |
| `scripts/run_*`, `scripts/validate_*`, review/import scripts | Referenced by tests and experiment docs. | `RETAIN_RESEARCH` | Keep; audit did not find a safe deletion set. |

## Data audit

### Inventory and integrity

The clean canonical tree contains 27 tracked data artifacts:

- two manifests under `data/manifests/`;
- 16 raw pre-Phase-4 documents/structured artifacts under
  `data/raw/pre-phase4-acquisition-v1/`;
- three macro-official reconciliation JSON artifacts;
- three pre-Gold decision artifacts;
- two pre-Phase-4 acquisition reconciliation artifacts.

All 27 tracked data files have unique SHA-256 hashes; no exact byte-identical
data-file duplicate was found. No SQLite or DB file is tracked or present in
the clean checkout because `.gitignore` excludes `*.sqlite` and `*.db`.

The available provenance chain is:

```text
raw pre-phase4 artifacts
  → data/manifests/pre-phase4-acquisition-v1.jsonl
  → data/reconciliation/pre-phase4-acquisition-v1/
  → data/reconciliation/pre-gold-decision-2024-q4-v1/
  → candidate/reconciliation decisions
```

It is intentionally not a promoted canonical SQLite snapshot in this checkout.
The acquisition package records candidates as `review_required` or explicit
`missing`; `sector.system_npl_ratio` remains `missing / DATA_UNAVAILABLE` and
peer substitution is not used.

### Provenance issue requiring a separate data PR

`data/manifests/macro-official-2024-q4-v1.jsonl` contains nine local paths under
`data/raw/macro-official-2024-q4-v1/`, but that directory is absent. The
referenced artifact names include:

```text
sbv-policy-rates-overview.html
sbv-policy-rates-history-api.json
sbv-policy-rates-regulated.html
sbv-policy-rate-record-3451452.json
sbv-policy-rate-record-3451452-rendered.html
sbv-credit-growth-2024-09-17.html
sbv-credit-statistics-route.html
sbv-credit-statistics-api-2024.json
sbv-credit-growth-lead-2025-03-18.html
```

The newer `data/manifests/pre-phase4-acquisition-v1.jsonl` references existing
paths under `data/raw/pre-phase4-acquisition-v1/`. This looks like a manifest
version/path migration issue, not dead data. It must be repaired by a scoped
provenance PR that rechecks hashes and candidate references; this audit does not
rewrite it.

### Data disposition

| Data class | Paths | Disposition |
|---|---|---|
| `RAW_SOURCE_OF_RECORD` | `data/raw/pre-phase4-acquisition-v1/**` | Keep; HIGH risk. |
| `MANIFEST` | `data/manifests/*.jsonl` | Keep; repair only through provenance review. |
| `RECONCILIATION_ARTIFACT` | `data/reconciliation/**` | Keep; captures non-promotion and missingness decisions. |
| `CANONICAL_DATASET_INPUT` | No tracked SQLite snapshot in clean checkout | Do not infer absence means deadness; restore/publish only by explicit dataset decision. |
| `GENERATED_REBUILDABLE` | Ignored `data/processed/`, reports, local DBs | Not tracked here; source-of-truth policy is unresolved. |
| `DUPLICATE` | None among tracked data hashes | No removal candidate. |
| `ORPHAN` | Nine stale manifest local paths, not raw files | Investigate/repair; do not delete. |

## Documentation audit

| Path/group | Classification | Evidence / risk | Recommendation |
|---|---|---|---|
| `AGENTS.md`, `README.md`, `PRODUCT.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`, `docs/CONSTRAINTS.md`, `docs/ARCHITECTURAL-GUARDRAILS.md` | `CURRENT_CANONICAL` | Define current boundaries; guardrails say capability pool is selected by `AnalysisPlan`, not a mandatory Macro→Sector→Company chain. | Keep; use as Phase 4 authority. |
| `AGENTS.md:15`, `README.md:20-22`, `docs/PHASE-TRANSITION-CHECKLIST-VI.md:126` | `STALE` / `CONTRADICTORY` state references | They require `.agents/project-state/current.json` and `events.jsonl`, but those files/directories are absent from clean `main`. | Fix in a governance/state PR; do not create state files during this audit. |
| `CONTRIBUTING.md:4` | `STALE` | Refers to deleted/retained historical branch state using ambiguous wording. | Update separately. |
| `docs/BRANCH-INVENTORY-2026-09-16.md`, `docs/BRANCH-CLEANUP-2026-09-16.md` | `HISTORICAL_PHASE_RECORD` | They intentionally record old branch names and cleanup decisions. | Keep; do not “correct” history away. |
| `docs/PRE-PHASE4-DATA-ACQUISITION-REPORT.md:8` | `HISTORICAL_PHASE_RECORD` with stale branch label | It records `prep/pre-phase4-data-acquisition`, which is historical. | Keep; optional later annotation, not deletion. |
| `docs/ADVISOR-ARTIFACT-INDEX-VI.md`, `docs/IMPLEMENTATION-ROADMAP-V1.md`, `docs/THESIS-VISUAL-PLAN-VI.md` | `CURRENT_REFERENCE` with broken ignored-artifact links | They link to absent `reports/`, `data/processed/`, and frozen-viewer data. | Migrate after artifact publication policy is decided. |
| `docs/THESIS-DRAFT-*`, `docs/THESIS-VISUAL-PLAN-VI.md`, source thesis Markdown/PDF/images | `HISTORICAL_BUT_REQUIRED` | Thesis traceability and advisor-facing material; several documents intentionally preserve old architecture context. | Keep; do not delete or rewrite in hygiene PR. |
| `docs/superpowers/**` | `HISTORICAL_PHASE_RECORD` | Historical plans mention old Gold/SQLite and absent `.agents` state, but are execution history. | Keep; archive/label only in a later docs PR if desired. |
| `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` and `docs/THESIS-DRAFT-ESSAY-VI.md` | `DUPLICATE` exact SHA-256 | Byte-identical, but thesis artifact identity and references are not yet reconciled. | `CONSOLIDATE` only after advisor/user decision and link audit. |

The current canonical specs do not force the obsolete three-agent pipeline. The
historical thesis drafts and old composite experiment documents do contain that
language; it should be treated as historical context unless it is copied into a
current spec. No automatic document rewrite is justified here.

## Build, configuration, and CI audit

- `.github/workflows/frontend.yml` is active and complete for the React surface:
  Node 24, `npm ci`, lint, tests, build.
- `.github/pull_request_template.md` is governance metadata and is active.
- `frontend/package.json`, `frontend/package-lock.json`, Vite, TypeScript,
  ESLint, and Vitest configs are referenced by the workflow and package scripts.
- There is no tracked root `pyproject.toml`, `requirements.txt`, or Python CI
  workflow. Python tests require `PYTHONPATH=src` in this clean checkout. This
  is a reproducibility/package-management gap, not permission to invent a
  package manager in this audit.
- `.gitignore` covers `.env`, `.agents/`, `data/`, `reports/`, `tmp/`, Python
  caches, frontend `node_modules`/`dist`, and local SQLite/DB files. That policy
  explains why several advisor links do not resolve in a clean clone.

## Generated and transient artifact audit

Before running checks, the audit worktree had no `__pycache__/`,
`.pytest_cache/`, `frontend/node_modules/`, `frontend/dist/`, `reports/`,
`tmp/`, or `.agents/` directory. The audit then generated ignored Python cache
files and frontend `node_modules/`/`dist/` only to execute verification. They
are not tracked and do not appear in `git status --porcelain`.

No tracked coverage output, temporary SQLite database, copied log, editor file,
or OS file was found. Tracked PNGs are thesis/visual assets under `docs/` and
must not be treated as transient screenshots. Tracked JSON/JSONL under
`data/` and `experiments/` is source/evidence/experiment input, not disposable
build output.

## Duplicate and overlapping implementation audit

Exact SHA-256 grouping across all 494 tracked files found 10 duplicate groups:

1. `experiments/runs/offline-fixture-v7/hierarchical_no_critique.json` and v8.
2. `experiments/runs/offline-fixture-v2/single_agent.json` and v3.
3. `experiments/runs/offline-fixture-v7/single_agent.json` and v8.
4. `experiments/runs/offline-fixture-v2/hierarchical_no_critique.json` and v3.
5. `experiments/runs/offline-fixture-v2/hierarchical_bounded_critique.json` and v3.
6. `experiments/runs/offline-fixture-v7/hierarchical_bounded_critique.json` and v8.
7. `experiments/runs/offline-fixture-v1/question-set.json` through v6.
8. `experiments/runs/offline-fixture-v7/question-set.json`, v8, and v9.
9. `experiments/runs/analysis-report-v2-scaling-5issuer-plan.json` and
   `experiments/runs/complexity-plan-scaling-5issuer-v2.json`.
10. `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` and
   `docs/THESIS-DRAFT-ESSAY-VI.md`.

The v2/v3 and v7/v8 groups are separate exact-hash groups where the same
responsibility appears at different run versions; they are not evidence that a
whole run directory can be deleted.

The experiment README explicitly gives the historical versions meaning, so
these are consolidation/archive candidates, not safe deletion targets. No
near-identical source pair was promoted to a duplicate claim. The old composite
runner and new revision kernel are also not called duplicates: one is a
historical benchmark scaffold and the other is the locked provider-neutral
bounded revision implementation.

## Entry point and reachability map

### Product/application

- `frontend/src/main.tsx` → `frontend/src/App.tsx` →
  `frontend/src/app/router.tsx` → the four registered route behaviors.
- `frontend/src/entities/analysis/api/analysisService.ts` is the current
  client submission scaffold; it does not yet call a live backend.
- Python application boundary: `src/thesis_data/application_runtime.py` and
  `dataset_tool_runtime.py`, backed by provider-neutral contracts and adapters.

### Research and evaluation

- `python scripts/run_offline_fixture.py` → `offline_fixture.py` and
  workload/question contracts.
- `python scripts/run_openai_baseline.py` and
  `python scripts/run_complexity_pilot.py` → baseline/composite/provider
  research paths.
- `python scripts/run_blind_ai_review.py`, aggregation scripts, and review
  scripts → blind evaluation/review artifacts.
- `research/evaluation-ui/review.html` → standalone human review UI.

### Data and snapshot pipeline

- `scripts/normalize_vendor_snapshot.py` → normalization/period/storage
  adapters.
- `scripts/build_macro_gold_snapshot.py` → bounded Macro Gold adapter and
  materialization tests.
- `scripts/build_*_candidate_db.py`, review-import/promotion scripts →
  historical candidate/review pipeline.
- `scripts/query_snapshot.py` → read-only legacy snapshot query surface.

### Report generation

- `scripts/render_analysis_report.py`, `render_analysis_report_v2.py`, and
  batch variants → `report_view.py`, `analysis_report.py`, and validation.
- `legacy/frozen-report-viewer/index.html` reads generated payloads; it is not
  on the current React route graph.

Files outside the current application reachability graph are therefore not
automatically dead: many are in the research, review, data, or historical
reproducibility graphs above.

## Architectural debt

| ID | Debt | Evidence | Risk | Phase 4 handling |
|---|---|---|---|---|
| AD-01 | Gold/SQLite coupling in transitional research runtime | `agent_runtime.py`, `agent_tools.py`, `query.py`, `composite_*`, and Gold adapters are still executable and tested. | HIGH | Keep behind adapters; Phase 4 must use `AnalysisPlan` + provider boundary. |
| AD-02 | Legacy runner bypasses the current application path | `run_agent_arm`/`run_composite_arm` are documented as transitional scaffold in `docs/ARCHITECTURE.md`. | HIGH | Do not delete before baseline migration; do not use as Phase 4 product runtime. |
| AD-03 | Fixed five-bank/metric fixture remains in mock and experiment surfaces | Frontend mock providers and experiment question sets are intentionally narrow. | MEDIUM | Keep as fixture/config; do not mistake it for capability schema. |
| AD-04 | Historical composite path implies fixed Macro/Sector/Company flow | Old composite/research docs contain the sequence; current `AnalysisPlan` docs say capability selection is adaptive. | MEDIUM | Current guardrails win; label old docs as historical. |
| AD-05 | Legacy prose/composite output alongside structured claims | `composite_schema.py`/compatibility functions coexist with canonical structured contracts. | HIGH | Preserve until experiments migrate; new Phase 4 output must use current contract. |
| AD-06 | Python dependency and CI reproducibility is incomplete | No root package/dependency manifest and no Python workflow; clean tests need `PYTHONPATH=src` and some ignored inputs. | HIGH | Separate packaging/CI PR; do not invent it in cleanup audit. |
| AD-07 | Project-state contract is documented but absent from clean tree | `AGENTS.md`, README, and phase checklist reference `.agents/project-state/*`; path is ignored and absent. | HIGH | Decide whether state is generated/local or must be published before Phase 4 execution. |
| AD-08 | Manifest/report artifact paths are not clean-checkout complete | Nine old macro manifest paths and advisor/report links do not resolve. | HIGH | Separate provenance/artifact publication PR; no data promotion or deletion here. |

The audit found no evidence that the current provider-neutral core violates the
locked transferability rule. The risk is accidental use of the transitional
research path or stale documentation, not ambiguity about which core is
authoritative.

## Proposed cleanup PR sequence

Do not create one giant cleanup PR. A safe sequence is:

1. `docs/clarify-current-branch-and-project-state` — correct
   `CONTRIBUTING.md` and decide how `.agents/project-state` is represented;
   preserve branch cleanup history.
2. `data/repair-macro-manifest-paths` — reconcile the nine old local paths to
   the acquired artifacts, recheck hashes and candidate references, and obtain
   explicit data-owner review. This is a provenance PR, not a cleanup shortcut.
3. `docs/repair-advisor-artifact-publication-policy` — either publish or
   explicitly regenerate the ignored `reports/`, `data/processed/`, and frozen
   viewer inputs; repair links without changing thesis claims.
4. `ui/remove-unused-create-analysis-barrel` — remove only the unimported
   frontend barrel after lint, test, build, and case-sensitive scan.
5. `research/resolve-experiment-compatibility-layer` — prove whether
   `experiment_compat.py` is externally needed; remove only if compatibility
   and reproducibility checks pass.
6. `chore/consolidate-exact-duplicate-experiment-artifacts` — only after run
   lineage, README references, and historical tags are explicit. Do not delete
   v1–v8 merely because v9 is current.
7. `docs/consolidate-duplicate-thesis-drafts` — only after user/advisor choice
   of canonical draft and link/reference migration.
8. `build/add-python-reproducibility-contract` — define dependencies and
   Python CI separately from repository hygiene; this is important but not a
   reason to change the current architecture in this PR.

## Verification record

Commands were run from the audit worktree after the read-only inspection:

| Check | Result |
|---|---|
| `PYTHONPATH=src python -m unittest discover -s tests -q` | **608 tests; 5 failures, 5 errors**. Failures/errors are existing clean-checkout reproducibility issues: absent ignored Gold/review artifacts (`test_blind_scoring`, three comparability-matrix tests, `test_review_ledger`, `test_gold_evidence_snapshot`, `test_review_progress`) and baseline plan hash/CLI mismatches (`test_baseline_plan`, 3 failures). No audit code was added before this result. |
| `python scripts/check_architecture_guardrails.py` | **PASS** — `ARCHITECTURE_GUARDRAILS: PASS`. |
| `python -m compileall -q src scripts tests` | **PASS**. |
| `npm ci --ignore-scripts --no-audit --no-fund` in `frontend/` | **PASS**, 582 packages installed into ignored local `node_modules`. |
| `npm run lint` | **PASS**. |
| `npm test -- --run` | **PASS** — 2 test files, 15 tests. |
| `npm run build` | **PASS** — 1,738 modules transformed; Vite emitted a non-blocking >500 kB chunk warning. |
| `git diff --check` | To be rerun after adding this report. |

The Python failures are themselves part of the hygiene finding: a clean clone
does not contain all artifacts assumed by the historical test suite. They must
not be “fixed” by weakening tests or adding fabricated data in this audit PR.

## Final handoff

Base SHA: `2b77b938f2c314020aabf448535a890bc173f088`

Branch: `chore/repository-hygiene-audit`

Commit SHA: to be recorded after the audit-only commit

PR: to be opened from `chore/repository-hygiene-audit` into `main`; do not merge
automatically.

Changed files: only `docs/REPOSITORY-HYGIENE-AUDIT-2026-09-16.md`.

Checks: architecture guard PASS; compileall PASS; frontend lint PASS; frontend
15/15 tests PASS; frontend build PASS with chunk-size warning; Python suite
608 with 5 failures and 5 errors caused by pre-existing missing/ignored
artifacts and plan-hash drift.

Known failures: listed in the verification table and should be tracked as
reproducibility/data-publication debt, not silently suppressed.

Working-tree status: must be clean except for the committed report after
commit/push; ignored audit dependencies/build output are not tracked.

Summary:

1. Cleanup candidates: 2 direct removal candidates, 6 archive/consolidation or
   migration groups, plus 8 architectural-debt records; none is approved for
   deletion by this audit.
2. Safe-now candidates: the unimported frontend barrel, after scoped checks;
   docs/path repairs are safe only in their own governance/provenance PRs.
3. Explicitly retained: raw evidence, manifests, reconciliation, Gold/provider
   adapters, contracts, experiment history, thesis artifacts, frozen viewer,
   and human evaluation tooling.
4. Architectural debt: transitional Gold/SQLite research path, old runner
   bypass, fixture-specific mocks, legacy composite/prose contracts, absent
   Python packaging/CI, missing project-state publication, and broken artifact
   links.
5. Phase 4 blocked?: **No.** The result is
   `PHASE4_READY_WITH_NONBLOCKING_HYGIENE_DEBT`; Phase 4 must start from the
   provider-neutral current architecture and record the debt.
6. Recommended PR sequence: governance/state → manifest provenance → artifact
   publication/docs → frontend barrel → compatibility-layer decision → exact
   experiment consolidation → thesis draft consolidation → Python packaging/CI.
