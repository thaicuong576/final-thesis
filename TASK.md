# Task manifest — pinned accepted snapshot startup validation

## Identity

- Branch: `codex/p4-snapshot-startup-validation-20260926`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main`)
- Role: `worker-api`
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- PR: #67 — `feat(api): validate pinned SQLite snapshot at startup`

## Objective

Make the reference API advertise readiness only when an explicitly configured,
stable, hash-pinned accepted SQLite snapshot, provider identity, separate run
store, and required specialist/reviewer configuration are all available.

## Scope

- API settings, startup lifecycle, readiness/capabilities, snapshot/provider
  binding, separate analysis-run storage, and focused API/startup tests.
- Documentation and lessons that record the new startup boundary.

Out of scope: frontend changes, Gold/data artifact mutation, schema migration,
deployment settings/secrets, live analysis requests, and final A/B/C scoring.

## Acceptance criteria

1. Missing path, snapshot ID/hash, invalid hash, unavailable file, WAL/sidecar,
   integrity failure, byte mutation, hash mismatch, or provider identity
   mismatch fails closed with a stable limitation code.
2. The accepted snapshot is opened read-only and cannot alias the writable
   `ANALYSIS_RUNS_DB_PATH`; readiness inspection does not create run history.
3. Startup may initialize the separate run store, but must not silently infer a
   local Gold artifact or snapshot identity.
4. API/OpenAPI and architecture checks plus focused and full CI tests pass.
5. The PR documents that offline tests do not establish live deployment
   readiness; no merge occurs without explicit user authorization.

## Verification handoff

- Focused independent audit: 75 tests passed with `PYTHONPATH=src;tests`.
- `python scripts/check_architecture_guardrails.py`: PASS.
- `python scripts/check_openapi_contract.py`: PASS.
- Known external blocker: deployment still needs explicit snapshot provisioning
  and environment configuration; no settings or secrets were changed here.
