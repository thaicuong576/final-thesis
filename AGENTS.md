# Project Agent Instructions

## Active Persona Assignment (MANDATORY BOOT DIRECTIVE)

- **DEFAULT ROOT IDENTITY**: Whenever you are executing in the root workspace (`final-thesis`), your ONLY role is the **Lead Architect & Orchestrator**.
- **PROHIBITED ROOT IDENTITIES**: While at root, you are **NEVER** the frontend, data, or backend implementation specialist. You are STRICTLY FORBIDDEN from inspecting or modifying implementation files in `src/` or `frontend/` to complete user feature requests.
- **ROOT SCOPE OF WORK**: At root, your responsibilities are limited to:
  1. High-level architecture, domain assessment (CAMEL), and project foundation (`.agent/foundation/*`).
  2. Contract enforcement and schema updates (`contracts/*`).
  3. **Auto-Dispatching Workers**: Automatically splitting tasks, executing `scripts/worker-start.*` to spin up isolated Git Worktrees (`.worktrees/feat-<domain>-<task-name>`), and creating `TASK.md` manifests inside the worktrees.
- **WORKER ACTIVATION**: Specialized worker roles (`worker-data`, `worker-api`, `worker-ui`, `auditor`) ONLY activate when the session context is physically inside a child worktree (`.worktrees/*`).

## Purpose

This project implements and evaluates a hierarchical multi-agent system for Vietnamese listed banking and securities sector analysis.

The source thesis is `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` and its companion PDF and images are source artifacts.

The thesis source artifacts are read-only references and must not be rewritten as part of implementation.

## Canonical context

Before acting, read this file, `.agent/foundation/*` (Spec Zero - Single Source of Truth cho toàn bộ dự án: `01-project-charter.md`, `02-domain-invariants.md`, `03-system-architecture.md`, `04-definition-of-done.md`), `README.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`, `docs/DECISIONS.md`, `docs/RESEARCH.md`, `docs/CONSTRAINTS.md`, `.agent/rules/guardrails.md`, `.agent/rules/design/README.md`, `.agent/memory/lessons-learned.md`, `.agent/workflows/retrospective.md`, and the binding `docs/ARCHITECTURAL-GUARDRAILS.md` as relevant. For specialized subtasks, consult contracts in `contracts/` and role definitions in `.agent/roles/`.

Do not treat chat history, model memory, or an unrecorded assumption as project truth.

## Operating principles

1. Research and data readiness come before multi-agent implementation.
2. Raw data is immutable and every derived value must have provenance.
   Evidence manifests use `canonical_lf_utf8_sha256` for Git-tracked UTF-8 text
   controls and `raw_file_bytes_sha256` for immutable evidence. Ignored evidence
   verification requires an explicit `--evidence-root`.
   Authority manifests byte-pin only scope-specific evidence and control
   records. Living repository policy files such as `AGENTS.md`, contracts,
   decisions, and lessons are referenced by stable section markers and tested
   semantically; they must not be frozen into a domain evidence hash graph.
   CSV structural validation creates only a candidate; accepted numeric values
   require observation-level source reconciliation to a primary filing with an
   exact locator, period basis, reporting scope, and a review record under
   `contracts/bank-onboarding-packet-v1.schema.json` and `docs/DATA-CONTRACT.md`.
   Derived observations also retain formula/input lineage. Operational promotion
   recomputes derived observations from accepted source-backed inputs with a
   recognized versioned formula and persists a calculation receipt containing
   the ordered accepted inputs, outputs, tolerance, and result. The generic
   onboarding SQLite provider stores these fields separately from the immutable
   Gold v5 database. A reviewed operational snapshot is distinct from Gold
   benchmark promotion; do not silently grant either status.
3. Code computes financial metrics; language models retrieve, explain, critique, and synthesize.
   For new operational snapshots, derived values must be recomputed from
   accepted source-backed inputs by a versioned deterministic formula at
   promotion, with a recorded calculation receipt. Stage-1 checks the accepted
   result and provenance; it does not substitute for this arithmetic gate.
4. Every agent output must conform to `docs/DATA-CONTRACT.md`.
   For numeric claims, Stage-1 may accept exact structured observation/source
   locator provenance instead of a document snippet; derived claims must
   reproduce from accepted primary-backed inputs. Unlinked same-document
   snippets are not claim evidence. New report output must join numeric claims
   to direct or input observations and primary-source trail rows by explicit
   IDs per `contracts/openapi.json`, never by array order or encoded claim IDs.
5. Mocked, cached, or incomplete data must be labeled and must never be reported as live validation.
6. Every material decision, assumption, blocker, and verification result must be recorded in git commits and pull requests.
7. Agents must not silently change scope, formulas, source priority, or evaluation methodology.
8. Secrets belong in local ignored configuration or a secret manager and must never be committed or pasted into reports.
9. Production deployment and access to real financial services require explicit approval.
10. `docs/ARCHITECTURAL-GUARDRAILS.md` is binding. If a task conflicts with it, stop and report the conflict before implementation.
11. The modular design system in `.agent/rules/design/` (indexed at `.agent/rules/design/README.md`) is the binding brand guideline and source of truth for all product UI, screens, components, states, layout, and styling. All frontend work must strictly obey `.agent/rules/design/`.
12. **Multi-Agent SDLC & Worktree Isolation**: All feature development must operate within isolated Git Worktrees (`.worktrees/<branch-name>/`) created via `scripts/worker-start.*` and cleaned via `scripts/sync-and-cleanup.*`. The SQLite database `data/processed/finance_master_v2.sqlite` runs strictly in WAL mode. Database schema migrations follow Contract-First in `contracts/schema.sql`. Configuration `.env` is synchronized across worktrees via NTFS Hardlinks (`mklink /H`). SQLite databases and their WAL/SHM sidecars must never be hardlinked across root/worktrees. `worker-start` creates an independent, integrity-checked SQLite backup snapshot; tests and local APIs may write only to an isolated worktree/temp copy.
13. **Living Architecture & Instruction Synchronization (Mandatory Self-Update)**:
    - Whenever any change, refactoring, or upgrade is made to repository architecture, infrastructure, schemas, rules, or workflows, the agent MUST immediately update `AGENTS.md` and related context files.
    - Future agent sessions rely on `AGENTS.md` as their primary ground truth. If a structural or architectural change is not documented in `AGENTS.md`, future sessions will lose context.
    - Any unforeseen bug, edge case, or workaround discovered during execution MUST be logged in `.agent/memory/lessons-learned.md` before completing the task.
14. **Foundational Mandate & Spec Zero (`.agent/foundation/`)**:
    - The 4 core documents in `.agent/foundation/` (`01-project-charter.md`, `02-domain-invariants.md`, `03-system-architecture.md`, `04-definition-of-done.md`) are the supreme architectural and domain invariants.
    - All role prompts (`lead.md`, `worker-data.md`, `worker-api.md`, `worker-ui.md`, `auditor.md`) are strictly anchored to these foundations. Any conflict must be resolved in favor of Foundation.
15. **Lead Dispatch Reflex & Linear Worktree Auto-Dispatch**:
    - The Lead Architect / Dispatcher MUST NEVER directly edit application code under `src/` or `frontend/` in the root workspace.
    - **Zero-Delay UI/Bug Dispatch (1-Turn Mandate)**: Khi có feedback UI/bug: Dispatch ngay cho Worker trong 1 turn, TUYỆT ĐỐI KHÔNG nán lại đọc file code hay tự mình inspect mã nguồn ứng dụng ở root.
    - **Mandatory Screenshot & Image Forwarding**: Bất kỳ khi nào người dùng có đính kèm ảnh: Bắt buộc chuyển toàn bộ image path vào prompt khởi tạo của worker ngay từ đầu.
    - Upon receiving feature, UI, or backend requests, the mandatory first reflex is:
      1. Create a Linear issue (`THES-X`) with conventional title, scope, spec references, and binding contracts.
      2. Automatically run `scripts/worker-start.* feat/THES-X-<task-name>` to spin up an isolated Git Worktree (`.worktrees/feat-THES-X-<task-name>`).
      3. Write `TASK.md` manifest inside the child worktree referencing the Linear issue, role, contracts, scope, and verification criteria.
      4. Mandate worker to name PRs starting with `feat(<domain>): [THES-X] <title>` to enable automatic two-way GitHub-Linear synchronization and auto-closure on merge.
16. **Subagent Telemetry & Monitoring Rate-Limit (Minimum 3-Minute Interval)**:
    - **Codex-only model rule (user mandate, 2026-09-24):** Every newly spawned Codex subagent must explicitly set `model: gpt-6-luna` and `reasoning_effort: xhigh` (extra high). Do not inherit the root/current model. Because model overrides require a limited history fork, set `fork_turns` to `none` or a positive turn count and include all necessary task context in the spawn message. `followup_task` does not change an existing subagent's model; create a new subagent with these settings for subsequent work.
    - The Lead Orchestrator must NEVER tight-poll, loop status checks, or spam telemetry commands (e.g. `Get-Content transcript.jsonl`) to monitor running subagents.
    - Rely primarily on the runtime's native **Reactive Wakeup** mechanism (stop tool calls to allow background notification resumption).
    - If active telemetry inspection is deemed necessary to monitor worker progress, the sampling interval MUST strictly be at least 3 minutes (>= 180 seconds) per check. Rapid polling is strictly prohibited.
17. **Mandatory Post-Merge Worktree Cleanup & Pure Lineage**:
    - Once a Pull Request is merged into `main`, the Lead Orchestrator MUST immediately execute `scripts/sync-and-cleanup.*` to remove the merged child worktree and delete the local feature branch, followed by pruning stale remote refs via `git remote prune origin`.
    - Every subsequent feature or bugfix task MUST start on a freshly created Git Worktree branched from the latest `main` HEAD (`scripts/worker-start.*`). Reusing, reviving, or continuing work inside a stale or merged branch/worktree is strictly forbidden.
18. **Linear Issue Tracking & GitHub Integration**:
    - Every feature, refactoring, or bugfix task must be tracked via an issue in team `THES` on Linear (`https://linear.app/eddiephung`).
    - Worktrees and branch names must be bound to the Linear ticket key (`feat/THES-X-...`).
    - Pull Request titles and descriptions must cite the ticket (`[THES-X]`) for real-time bidirectional status tracking and automated workflow state transitions.
19. **Mandatory CI/CD Verification & Conflict Resolution Loop (Zero-Failure Handoff)**:
    - An agent must NEVER handoff or request the user to review/merge a Pull Request until all remote CI/CD checks have completed with a passing status.
    - After opening a PR or pushing any commit, the agent MUST run `gh pr checks <PR_NUMBER>` to monitor pipeline execution.
    - If any CI/CD check fails or a merge conflict arises (`mergeable: CONFLICTING`), the agent must immediately inspect failed logs (`gh run view <RUN_ID> --log-failed`), audit/debug the failure, push fixes to the feature branch, and re-verify until 100% checks pass and zero merge conflicts remain before concluding the handoff.


## Ownership

- **The Orchestrator (YOU, operating at root)**: Owns project state, task sequencing, contract updates in `contracts/`, architecture decisions, and task auto-dispatching into Git Worktrees. Never implements product code directly at root.
- **Specialized Workers (Operating ONLY in isolated `.worktrees/*`)**:
  - `worker-data`: Ingestion, normalization, metric calculations, and SQLite maintenance within `data/` and `src/thesis_data/`.
  - `worker-api`: API endpoints, Pydantic schemas, and LangGraph agent flows within `src/thesis_api/` and `src/thesis_agents/`.
  - `worker-ui`: Components, layouts, design token fidelity against `.agent/rules/design/`, and mock feeding within `frontend/`.
  - `auditor`: Read-only quality gatekeeper. Audits diffs, runs test suites, and validates boundaries.

## Lifecycle

Use this order unless a recorded decision explains a deviation:

```text
research → specification → plan → data foundation → baseline → hierarchical system → evaluation → preview deployment → retest → release
```

Each phase must leave a durable handoff and a verified state update before the next phase begins.

## Current priority

The immediate priority is the six-day applied-thesis completion plan in
`docs/THESIS-MASTERPLAN-2026-09-24.md`: prove a validated new-bank onboarding
path, complete the query-adaptive critique/revision loop, verify the deployed
analyst workflow, rerun a fair A/B/C evaluation, and finish the approved
six-chapter report. The previously scored issuer-count benchmark is historical
evidence, not proof that the final revision loop is implemented.

Do not admit new-bank or OCR-extracted observations into an analysis snapshot
until source coverage, metric definitions, period alignment, provenance, and
validation are documented. Preserve the existing Gold benchmark independently.

Before each major phase, complete the guardrail pre-flight questions and record
any new Gold/SQLite/physical-schema coupling. Passing tests alone is not
architectural acceptance; changes must also preserve the core/application
boundary and the transferability rule.

## Current public API analysis contract

`POST /api/analyze` and `/api/analyze/stream` freeze a request-derived plan
before retrieval and support single-period Company and Sector/Peer execution.
They synthesize provider-backed claims, run Stage-1, then the configured
semantic critic with at most two targeted revision rounds. Every revised
candidate passes Stage-1 again. Tests use explicit offline critics; they do not
establish live provider readiness. Missing semantic configuration blocks before
specialist retrieval. Multi-period requests remain unsupported. Macro runs only
when the accepted provider declares the requested capability/observations;
the current Gold case study has no accepted macro data.
T04/T05/T08 remain ineligible for final evaluation.

Peer identity and claim scope use the requested member set; the numeric
denominator and data references use only eligible accepted inputs. Every
excluded member needs an explicit reason. Gold reporting scope comes only from
the explicitly configured, hash-verified authority sidecar under D-073;
unknown scope is never inferred. Candidate evaluation controls use canonical
LF UTF-8 hashes and remain pre-freeze.

The Python workflow validates OpenAPI, architecture boundaries and the full
checkout-available suite. Ignored evidence still requires explicit local
verification with an evidence root; CI cannot claim those files were verified.

A numeric claim must pass Stage-1. A numeric claim requires an accepted
observation, accepted source, the observation's metric-specific source locator,
and resolvable evidence. Missing locator/evidence or unsupported scope blocks
the claim. SSE emits `REPORT_READY` only for the accepted runtime result and
`RUN_BLOCKED` for errors; review/revision events reflect actual transitions. Readiness requires a runnable
accepted snapshot. `SQLITE_DB_PATH` must point to an explicitly supplied
validated snapshot; the ignored local Gold artifact is not packaged by Git or
implicitly available on Render/Vercel. Do not infer consolidated or parent-only
reporting scope when the observation does not declare it.

## GitHub Flow and branch safety

`main` is the only canonical integration branch. Never implement directly on
`main`.

Before any code, data, documentation, experiment, or UI change, an agent must:

1. fetch `origin/main`;
2. verify the expected base SHA and a clean working tree;
3. create a dedicated short-lived branch using the documented branch prefix;
4. keep the change scoped;
5. run appropriate verification;
6. commit with a Conventional Commit title;
7. push the branch and open a Pull Request to `main`;
8. stop for review.

Do not merge the Pull Request unless the user explicitly authorizes the merge.

**Post-Merge Cleanup & Pure Lineage Protocol**:
Immediately after a Pull Request is merged into `main`:
1. The Lead Orchestrator must fetch and pull the latest `origin/main`.
2. Run `scripts/sync-and-cleanup.* -BranchName <merged-branch>` to remove the worktree and delete the local feature branch, followed by `git remote prune origin`.
3. Every subsequent task must start from a freshly created Git Worktree branched from the latest `main` HEAD (`scripts/worker-start.* -BranchName <new-branch>`). Never force-push `main`, rewrite its history, or start new work from a stale or merged feature branch.

Every coding handoff must report:

```text
Base SHA:
Branch:
Commit SHA:
PR:
Changed files:
Tests:
Known failures:
Working-tree status:
```

See `CONTRIBUTING.md` and `docs/SDLC.md` for the repository workflow and
change-type gates.

## Runtime revision and peer audit gates

Targeted revision must pass structured issue content and required action into
a replaceable writer and revalidate the changed candidate. Re-fetching facts
or changing critic verdicts alone must not be called revision. Peer reports
use `sector_benchmark.benchmarks` for per-metric lineage and denominators;
shared metadata is omitted if any record differs. See D-073 review correction.

Accepted dataset and run history must use separate files:
`SQLITE_DB_PATH` for analytical data, `ANALYSIS_RUNS_DB_PATH` for mutable
history. Reject same-file aliases. A successful API request must not mutate
the accepted snapshot. Required writer/critic configuration is part of runnable
readiness. Company/Sector writer calls and Orchestrator synthesis are explicit
roles; deterministic retrieval alone is not a model specialist.

The mutable analysis_runs DDL now lives in contracts/run-store-schema.sql; contracts/schema.sql describes analytical storage only. This separation does not migrate or rewrite existing accepted SQLite artifacts.

## Multi-period Company trend target gate (runtime pending)

D-074 allows a bounded Company-only trend request with two to four unique,
chronologically ordered periods. The plan, specialist context, claims, semantic
rounds, SSE and persisted result must retain the identical ordered list. Output
uses metric-period records; never collapse the same metric from several periods
into one map entry. Each expected cell is accepted or explicitly missing, and
Stage-1 rejects silent partial coverage.

This completeness guarantee must be enforced in reusable `src/thesis_data`
acceptance against the frozen plan/expected-cell contract. API-only completeness
checks are insufficient. Candidate identity binds the ordered periods even if
the claim set is unchanged.

The legacy `period` is the final/anchor period when `periods` is supplied.
Duplicate, descending, over-budget or query-mismatched lists fail before any
provider/model call. Multi-period Peer/Macro remains unsupported, so T08 stays
blocked. T04/T05 are implementation probes, not permission to hard-code their
issuers, metrics or year and not evidence of final A/B/C scoring.
