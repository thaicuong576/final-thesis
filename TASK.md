# Task manifest — prompt contract v1 register

## Identity

- Branch: `codex/thesis-prompt-contract-v1-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: tracked documentation and lessons log only; no application, data, deployment, evaluation-run, or contract-schema changes.

## Objective

Restore the tracked prompt-control artifact referenced by `docs/DATA-CONTRACT.md` and register the current three-arm experiment prompt contract without claiming that the final A/B/C protocol is frozen or that live provider readiness has passed.

## Binding references

- `docs/DATA-CONTRACT.md`
- `docs/ARCHITECTURE.md`
- `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`
- `experiments/README.md`
- `data/evaluation/p4-task-specs-v1.json`
- `docs/ARCHITECTURAL-GUARDRAILS.md`
- `.agent/memory/lessons-learned.md`

## Acceptance criteria

1. `docs/PROMPT-CONTRACT-VI.md` exists and is linked from the contract reference with an auditable `prompt-contract-v1` identity.
2. The document defines common prompt invariants and the intended A/B/C arm differences without inventing model names, credentials, live-provider results, or final scores.
3. The document lists the freeze inputs and states that missing rendered prompt hashes, accepted snapshot/readiness, or other protocol gates block scoring.
4. The missing-artifact discovery is recorded as a durable lesson.
5. Only documentation and the lessons log change; `src/`, `frontend/`, `data/`, `contracts/`, deployment settings, and experiment runs remain untouched.
6. Link checks, `git diff --check`, and a focused existing control test pass. Remote CI must pass before handoff.

## Required handoff

Report base SHA, branch, commit SHA, PR, changed files, tests, known blockers, and working-tree status. Do not merge the PR. A/B/C remains pre-freeze until the live provider, accepted snapshot, prompt-render hash, task eligibility, rubric, and run controls are independently verified.
