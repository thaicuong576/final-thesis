# Task manifest — evaluation freeze readiness record

## Identity

- Branch: `codex/evaluation-freeze-readiness-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: evaluation-control documentation only; no application, data, contract-schema, deployment, secret, or experiment-run changes.

## Objective

Record a dated, evidence-backed A/B/C freeze decision that binds the current question set, Gold snapshot, prompt-version control, task eligibility, and missing runtime gates. This record must make it impossible to mistake candidate task metadata or offline probes for scored results.

## Acceptance criteria

1. The readiness record names the exact question-set and Gold snapshot identities and their hash modes.
2. It reports task eligibility and freeze/scoring flags from the tracked evaluation artifacts, without changing them.
3. It separates verified offline implementation evidence from live provider/readiness and final scoring evidence.
4. It records the precise gates required before fair A/B/C execution and the run-manifest fields required for reproducibility.
5. Only documentation and this task manifest change; no scoring run, deployment setting, secret, or accepted dataset is created or modified.
6. Link checks and `git diff --check` pass; the PR remains unmerged until explicitly authorized.
