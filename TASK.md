# Task manifest — correct staging readiness guide

## Identity

- Branch: `codex/deployment-guide-readiness-correction-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `docs/DEPLOYMENT-STAGING.md`, `.agent/memory/lessons-learned.md`, and this manifest only.

## Objective

Reconcile the staging guide's historical Supabase/`DATABASE_URL` smoke-test language with the current SQLite accepted-snapshot readiness contract and the current live `503` evidence. Preserve historical records but prevent operators from treating them as current thesis acceptance.

## Acceptance criteria

1. The guide states that current readiness requires explicit `SQLITE_DB_PATH`, expected snapshot ID/hash, immutable SQLite validation, separate run history, and model/writer/critic configuration.
2. `DATABASE_URL` is clearly labeled as legacy connectivity infrastructure, not accepted analytical evidence for the current runtime.
3. Historical Sprint 0 smoke-test results remain traceable but are labeled historical; the 2026-09-27 read-only recheck is recorded as blocked.
4. No secrets, deployment settings, data artifacts, application code, frontend code, or contracts change.
5. Markdown links, `git diff --check`, and scope checks pass; remote CI must be green before handoff.
