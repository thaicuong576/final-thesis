# API readiness and revision audit — 2026-09-27

## Scope and result

This audit covers the API accepted-snapshot readiness boundary and the bounded
semantic critique/revision wiring. No deployment configuration, secret,
frontend source, schema contract, or data artifact was changed; frontend
validation was run only as an independent application DoD check. No real
external analysis was run.

The API previously resolved the default `data/processed/finance_master_v2.sqlite`
path even when `SQLITE_DB_PATH` had not been supplied. If an ignored local file
happened to exist, API routes could attempt to treat it as the accepted dataset.
The API now requires a non-empty explicitly supplied setting before readiness,
synchronous analysis, or streamed analysis can use that path. It then continues
to require a provider-validated accepted snapshot with runnable company claims,
required writer/critic configuration, and a distinct writable history store.
An unconfigured path reports unavailable and blocks before provider access.

The bounded revision path was reviewed against the runtime contract: selected
issues are checked against the frozen plan and active specialist/claim ownership;
the provider re-query must preserve frozen fact and provenance fields; selected
issue content is sent to the affected writer; a targeted content change is
required; synthesis is regenerated; and the candidate returns through Stage-1
under a maximum of two rounds. Existing offline tests exercise these boundaries.

## Readiness boundary

`/api/ready` reports local runnable configuration, not live model connectivity or
live analytical quality. Configuration strings and an accepted local snapshot
do not prove that a remote model endpoint is reachable or that its output is
acceptable. This audit did not inspect Render settings or verify a deployed
snapshot/provider. The deployed workflow and live-provider gates remain open.

## Verification

The following local checks passed:

- API readiness: `test_thesis_api.py` (13 tests).
- Adaptive API and targeted revision: `test_api_analyze.py` (27 tests).
- SSE runtime: `test_api_stream.py` (5 tests).
- Bounded revision controller: `test_phase3bb_revision_controller.py` (53 tests).
- OpenAPI contract: `python scripts/check_openapi_contract.py`.
- Architecture boundaries: `python scripts/check_architecture_guardrails.py`.
- Python compile: `python -m compileall -q src scripts tests`.
- Frontend tests: `npm test -- --run` — 9 files and 53 tests passed.
- Frontend build: `npm run build` — TypeScript and Vite production build
  passed. This validates the checked-out frontend, not the deployed URL.
- Independent full-suite rerun: 671 tests passed, 4 skipped. The expected
  persistence-failure and database-connectivity diagnostics remained
  non-failing fixture probes.
- `git diff --check`.

The readiness suite logged its existing timeout diagnostic for the placeholder
`DATABASE_URL` connection-probe test; the suite passed. No external analysis was
run. Offline fixtures are implementation evidence only; they are not live
provider validation, deployment readiness, or A/B/C scoring evidence.
