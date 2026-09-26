# Task manifest — mark legacy seven-chapter draft as superseded

## Identity

- Branch: `codex/thesis-six-chapter-canonicalization-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` and this manifest only.

## Objective

Prevent the legacy seven-chapter working draft from being mistaken for the
approved six-chapter thesis structure. Preserve its historical content while
pointing authors to the canonical six-chapter outline and evidence-bounded
working drafts; do not rewrite source thesis artifacts or fabricate results.

## Acceptance criteria

1. A prominent banner states that the seven-chapter document is superseded and
   not the final submission structure.
2. The banner points to the approved six-chapter working path without creating
   broken relative links on `main`.
3. No chapter content, source thesis artifact, application code, data, contract,
   experiment, deployment setting, secret or score changes.
4. Markdown links, `git diff --check` and scope checks pass; remote CI must be
   green before handoff.
5. Leave the PR open and do not merge without explicit user authorization.
