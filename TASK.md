# Task manifest — point README to the six-chapter path

## Identity

- Branch: `codex/docs/point-readme-to-six-chapter-path-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `README.md` and this manifest only.

## Objective

Correct repository navigation so the README does not present the superseded
seven-chapter working draft as the canonical thesis entry point. Point readers
to the approved six-chapter working path tracked in PR #70 while preserving the
fact that the final report remains pending live evidence and scoring.

## Acceptance criteria

1. README labels the seven-chapter draft as legacy/superseded.
2. README points to the six-chapter outline/working report through a valid
   external PR reference, without linking to files absent from `main`.
3. No application code, data, contracts, source thesis artifact, experiment,
   deployment setting, secret, or score changes.
4. Markdown link, `git diff --check`, and scope checks pass; remote CI must be
   green before handoff.
5. Leave the PR open and do not merge without explicit user authorization.
