# Task manifest — private Supabase snapshot bootstrap

## Identity

- Branch: `feat/THES-76-supabase-snapshot-bootstrap`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main`)
- Role: `worker-api` / infrastructure boundary
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Binding contracts: `docs/DATA-CONTRACT.md`, `docs/ARCHITECTURAL-GUARDRAILS.md`, `docs/DEPLOYMENT-STAGING.md`, `contracts/schema.sql`, `contracts/run-store-schema.sql`.

## Objective

Allow the free Render deployment to hydrate an explicitly configured accepted SQLite snapshot from a private Supabase Storage object at application startup, verify its bytes and SQLite integrity before the API serves readiness, and keep analytical data read-only and separate from mutable analysis-run history.

## Scope

- Add a small infrastructure-side bootstrap adapter using the standard library; do not add Supabase SDK coupling to the reusable analysis core.
- Support explicit `SQLITE_DB_PATH`, expected snapshot ID, expected file SHA-256, Supabase project URL, private bucket, object path, and service-role secret through environment configuration.
- Download only when the configured local path is absent or does not match the expected immutable artifact; write through a temporary file and atomically replace it after hash/integrity validation.
- Fail closed on missing/invalid bootstrap configuration or mismatched bytes; never make the bucket public and never log secrets.
- Document the exact Render/Supabase setup and the free-plan restart behavior.
- Add focused tests with an offline HTTP fixture; no live Supabase or Render calls.

## Out of scope

- Uploading to Supabase, setting Render secrets, deploying, merging, live analysis, or changing the SQLite schema.
- Migrating the canonical analytical snapshot to Supabase PostgreSQL.
- Persisting mutable run history in Supabase Storage; `ANALYSIS_RUNS_DB_PATH` remains separate.

## Acceptance criteria

1. A valid private-object response hydrates the requested path and passes exact SHA-256 plus SQLite integrity checks.
2. Existing matching files are reused without a network request; mismatched files are never served.
3. Missing secrets, invalid URLs, HTTP failures, hash mismatches, and corrupt SQLite fail closed with actionable non-secret errors.
4. The FastAPI startup path runs bootstrap before readiness and does not break offline/test app factories when bootstrap is not configured.
5. `SQLITE_DB_PATH` remains explicit; the accepted snapshot is opened read-only by the analysis provider and remains distinct from `ANALYSIS_RUNS_DB_PATH`.
6. Focused tests, full checkout-available tests, OpenAPI, architecture guardrails, compileall, and `git diff --check` pass.

## Required handoff

Report base SHA, branch, commit SHA, PR, changed files, tests, known failures, user-set Render variables, and working-tree status. Do not include or request secret values in the PR or chat.
