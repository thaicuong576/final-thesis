# Task manifest — reconcile A/B/C scoring rubric

## Identity

- Branch: `codex/evaluation-rubric-contract-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `experiments/scoring-rubric-v1.md` and this manifest only.

## Objective

Reconcile the draft scoring rubric with the recorded applied-thesis evaluation
protocol: one author-rater, blinded/randomized answer review, a predeclared
delayed rescore subset, and explicit single-rater limitations. Preserve
deterministic claim/provenance dimensions, run-level operational measures and
binding identity fields without creating scores or freezing the experiment.

## Acceptance criteria

1. The rubric no longer requires two independent checkers or adjudication when
   the approved protocol uses one author-rater.
2. Blind ordering, arm masking, delayed subset rescore, preserved raw answers,
   reason codes and within-rater limitation remain explicit.
3. Deterministic measures and operational metrics remain compatible with
   `docs/EVALUATION-PROTOCOL-V1-DRAFT.md` and `docs/DATA-CONTRACT.md`.
4. The document remains draft/pre-freeze; no run, score, question, prompt,
   model, snapshot, contract, application code, deployment setting, secret or
   data artifact changes.
5. Markdown links, `git diff --check` and scope checks pass; remote CI must be
   green before handoff.

## Required handoff

Report base SHA, branch, commit SHA, PR, changed files, tests, known failures,
and working-tree status. Leave the PR open and do not merge without explicit
user authorization.
