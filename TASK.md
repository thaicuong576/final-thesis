# Task manifest — correct historical complexity-plan status

## Identity

- Branch: `codex/masterplan-historical-hash-correction-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation correction
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `docs/THESIS-MASTERPLAN-2026-09-24.md` and this manifest only.

## Objective

Correct the masterplan's stale P2 complexity-plan sentence so it distinguishes the pre-PR-#59 hash mismatch from the current canonical-hash audit, while preserving independent A/B/C freeze and runtime blockers. This is a documentation correction; it does not edit plan artifacts, score runs, or merge PR #62.

## Acceptance criteria

1. The historical mismatch remains traceable as a pre-PR-#59 finding.
2. The current five-plan read-only audit result is stated accurately, including the narrow D-073 legacy warning.
3. The text explicitly says plan-integrity resolution does not make A/B/C scoring eligible.
4. Only the masterplan and task manifest change; source thesis artifacts, application code, data, contracts, deployment settings, and experiment runs remain untouched.
5. `PYTHONPATH=src python -m unittest tests.test_complexity_plan -v`, link checks, and `git diff --check` pass. Open a PR and leave PR #62 unmerged.
