# Hierarchical Multi-Agent Financial Analysis Thesis

## Project goal

Build and evaluate a hierarchical multi-agent application for fundamental analysis of Vietnamese listed banks. Securities companies remain extension material.

The system should connect macro context, sector benchmarks, company metrics, and document evidence through a supervised critique loop.

The primary academic comparison is against a fair single-agent baseline using the same questions, data, and evidence rules.

## Current phase

The project is executing the six-day applied-thesis master plan in
`docs/THESIS-MASTERPLAN-2026-09-24.md`. A five-bank Gold v5 artifact and a scored
issuer-count pilot exist, but the final query-adaptive critique/revision loop,
new-bank onboarding demonstration, deployed end-to-end workflow, and approved
six-chapter report still require verification. Historical benchmark results
must retain their recorded limitations and cannot be relabeled as results of
the final loop.


## Canonical files

- `AGENTS.md` — project rules and ownership boundaries.
- `CONTRIBUTING.md` — GitHub Flow contribution rules and PR requirements.
- `docs/SDLC.md` — canonical branch, lifecycle, change-type gates, CI limits, and historical-branch policy.
- `docs/SPEC.md` — approved scope and acceptance criteria.
- `docs/ARCHITECTURE.md` — system layers and runtime flow.
- `docs/DATA-CONTRACT.md` — typed data and agent payload contracts.
- `docs/DECISIONS.md` — durable decisions and rejected alternatives.
- `docs/RESEARCH.md` — verified sources, findings, and open questions.
- `docs/CONSTRAINTS.md` — quality, security, reproducibility, and performance standards.
- `docs/ARCHITECTURAL-GUARDRAILS.md` — binding application-first constitution and transferability rules.
- `docs/THESIS-MASTERPLAN-2026-09-24.md` — six-day phase plan and advisor acceptance evidence.
- `docs/PHASE-0A-ONBOARDING-CONTRACTS.md` — Phase 0A contract slice and deferred boundaries.
- `docs/PRIORITIES-AND-TRADEOFFS.md` — ordered scope decisions and what is deferred.
- `docs/SCOPE-STRESS-TEST.md` — feasibility assumptions and 48/80/200-cell scope options.
- `docs/NEXT-PHASE-PRIORITIES.md` — assumption audit, decision tree, and next-sprint gates.
- `docs/BASELINE-AND-WRITING-PLAN.md` — gated experiment build and parallel thesis-writing plan.
- `docs/PHASE-TRANSITION-CHECKLIST-VI.md` — current guarded-build status, parallel tracks, and baseline entry/exit gates.
- `reports/data-foundation/database-quality-verdict.md` — measured staging-versus-gold database assessment.
- `experiments/` — versioned question set, scoring rubric, and run-contract preparation.
- `docs/ADVISOR-SCOPE-ONE-PAGER-VI.md` — concise Vietnamese scope decision for advisor review.
- `docs/THESIS-DRAFT-OUTLINE-VI.md` — chapter outline separating writable design from gated results.
- `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` — working prose draft for the stable parts of Chapters 1–4.

## Repository entry points

- `frontend/` — runnable React product frontend.
- `src/thesis_data/` — Python analysis/research core.
- `research/evaluation-ui/` — blind human evaluation tool.
- `legacy/frozen-report-viewer/` — historical read-only report viewer.
- `experiments/` — experiment definitions and plans.
- `scripts/` — active generic project scripts.
- `docs/` — thesis and design documentation.

## Source material

The original thesis document is stored under `docs/` with its PDF and extracted thesis images.

Those source artifacts are references for the implementation and evaluation design.

## Planned data layout

```text
data/raw/          immutable downloaded files and API captures
data/normalized/   cleaned source-aligned tables
data/processed/    derived metrics and peer benchmarks
data/documents/    PDFs and document metadata
data/manifests/    retrieval, coverage, and validation manifests
data/vector/       local vector index artifacts
experiments/       fixed question sets and run configurations
reports/           experiment outputs and thesis-ready tables
```

## Working rule

`main` is the only canonical integration branch. All new work starts from the
latest `main`, uses a dedicated short-lived branch, and reaches `main` through
a reviewed Pull Request. Never develop directly on `main` or force-push it.

No provider-backed comparative multi-agent experiment begins until the
data-foundation exit criteria in `docs/SPEC.md` are met. Guarded deterministic
scaffolding, fixtures, review tooling, and Chapters 1–4 drafts may proceed in
parallel as specified in `docs/DECISIONS.md`.

When implementation starts, every change must have a test or a documented reason why an executable test is not applicable.

The later Gold v5 issuer-count pilot planned 75 jobs, completed 61, recorded 14
failures, and received 244 blind human-review dimension scores. Its frozen
result is
`reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.md`.
These results are historical pilot evidence, not evaluation of the final
query-adaptive targeted-revision workflow.
