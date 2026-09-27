# Handoff — 2026-09-27 — Render/Supabase staging

## Start here

Read this file and `AGENTS.md` before doing anything else. The canonical
integration branch is `main`; the latest merged commit at handoff time is:

```text
a38d5a9c26f107e2e84ebf53a85285ef10674106
docs(ops): record Render/Supabase handoff state (#77)
```

The implementation baseline for the private SQLite snapshot bootstrap is
`e6d2a453fb2f3567e23666250944e92fcb0b11dc` (PR #76).

The current coding task is not to redesign the infrastructure. First make the
existing Render staging service boot successfully with the already-uploaded
private Supabase Storage snapshot, then perform only the explicitly approved
read-only readiness checks. Do not run live analysis/A-B/C evaluation until the
user confirms model, repetition count, and budget.

## What was completed

- PR #76 was reviewed and squash-merged by explicit user authorization.
- All PR checks passed: Python contracts/tests, Vercel preview comments, and
  both Vercel contexts.
- The feature branch and child worktree were removed after merge; stale remote
  ref was pruned.
- The merged implementation downloads a private Supabase Storage object at API
  startup, writes it atomically to `SQLITE_DB_PATH`, and fails closed unless
  the raw SHA-256, SQLite integrity, and `snapshot_metadata.snapshot_id` all
  match the configured expectations.
- Local verification before merge: focused snapshot tests `6/6` passed; full
  backend suite `672 passed, 4 skipped, 163 subtests passed`; OpenAPI and
  architecture guardrails passed; compileall and `git diff --check` passed.
- No live model analysis, A/B/C run, AWS migration, or Llama Cloud setup was
  performed.

## Snapshot facts

The validated local Gold snapshot is:

```text
snapshot_id: gold-bank-2025-expanded-v5-evidence
file_size: 487424 bytes
raw_file_bytes_sha256: 1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73
local source used for verification:
C:\Users\ASUS\OneDrive\Desktop\final-thesis-backup\data\processed\gold-bank-2025-expanded-v5-evidence.sqlite
```

The file passed `PRAGMA integrity_check` (`ok`) and the Gold audit found no
findings for the expected ACB/MBB/TCB/VCB/VPB and 2024_Q1..Q4 coverage. The
user uploaded the same snapshot to Supabase Storage:

```text
Supabase project URL: https://klaukirnadifltzhqidg.supabase.co
project_ref: klaukirnadifltzhqidg
bucket: thesis-snapshots
object: gold-bank-2025-expanded-v5-evidence.sqlite
```

Never copy the Supabase service-role key into this file, chat, git, or the
browser. It is intended only for the Render backend secret.

## Current Render blocker

The user supplied a Render deploy log for the merged revision. Build and
upload succeeded, but application startup failed and Render exited with status
3. The relevant error was:

```text
Supabase snapshot bootstrap requires URL, bucket, object, service key, snapshot ID, and SHA-256.
```

This means at least one required value is absent/empty in the Render backend
service. It is a configuration validation failure before the Supabase object
download; it is not yet evidence of a bad SQLite file or a Supabase HTTP
permission failure.

The required Render environment names are:

```text
SUPABASE_URL=https://klaukirnadifltzhqidg.supabase.co
SUPABASE_STORAGE_BUCKET=thesis-snapshots
SUPABASE_STORAGE_OBJECT=gold-bank-2025-expanded-v5-evidence.sqlite
SUPABASE_SERVICE_ROLE_KEY=<Render secret; do not expose>
EXPECTED_DATASET_SNAPSHOT_ID=gold-bank-2025-expanded-v5-evidence
EXPECTED_SQLITE_SHA256=1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73
```

Also preserve the existing runtime paths from `render.yaml`:

```text
SQLITE_DB_PATH=/tmp/accepted.sqlite
ANALYSIS_RUNS_DB_PATH=/tmp/analysis_runs.sqlite
GOLD_SCOPE_AUTHORITY_PATH=data/evaluation/gold-v5-reporting-scope-authority-v1.json
```

The `render.yaml` declares the non-secret values, but the existing Render
service may not have synchronized them. Verify the names in the backend
service, not the frontend service. Do not print secret values. After correcting
configuration, deploy the latest `main` commit (`e6d2a453`) and wait for a
successful deployment.

## Required post-deploy verification

Use only GET/read-only checks first:

```text
GET https://final-thesis-zgwt.onrender.com/api/version
GET https://final-thesis-zgwt.onrender.com/api/ready
GET https://final-thesis-zgwt.onrender.com/api/capabilities
```

Expected success evidence:

- `/api/version.revision` is `e6d2a453fb2f3567e23666250944e92fcb0b11dc` (or
  a later intentional main revision).
- `/api/ready` returns HTTP 200 with `database: connected` and the Gold
  snapshot ID.
- `/api/capabilities` reports a non-null snapshot, entities/periods/metrics,
  and `analysis_available: true`.

Do not POST `/api/analyze` or `/api/analyze/stream` as a readiness probe.

## MCP setup for the next session

The user wants Codex to operate Render and inspect Supabase directly. In Codex
Desktop, open **Settings → MCP servers → Add server**, choose Streamable HTTP,
and authenticate through OAuth:

```text
Render
name: render
url: https://mcp.render.com/mcp

Supabase
name: supabase
url: https://mcp.supabase.com/mcp?project_ref=klaukirnadifltzhqidg&read_only=true&features=docs,database,debugging
```

Restart Codex and use `/mcp` to confirm both are connected. Render MCP can
inspect services/deploys/logs and can modify service environment variables or
trigger deploys, so keep write actions approval-gated. The Supabase MCP should
remain project-scoped and read-only initially. It is useful for database,
debugging, and docs inspection; it does not replace the Storage upload flow
for this SQLite object. Supabase OAuth normally avoids the need to create a
PAT for this interactive setup.

## Next-session action order

1. Read this handoff, `AGENTS.md`, `docs/DEPLOYMENT-STAGING.md`, and the
   current `render.yaml`.
2. Confirm the new Render and Supabase MCP connections with read-only listing
   or status calls.
3. Inspect the Render backend service's environment variable names and the
   failed deploy logs. Do not reveal values of secrets.
4. Set/fix only the six snapshot-bootstrap variables listed above, preserving
   the existing OpenAI/model and run-store secrets. Ask for confirmation if a
   destructive or unrelated change is proposed.
5. Trigger/retry deployment of `e6d2a453`, then run the three GET readiness
   checks.
6. If readiness is green, record the deployed revision and snapshot evidence
   in a new durable handoff/status note before any live evaluation.
7. Continue the thesis masterplan: validated new-bank onboarding, query-
   adaptive critique/revision, deployed workflow verification, fair A/B/C
   evaluation, and approved six-chapter report completion.

## Do not lose these boundaries

- The accepted analytical snapshot and mutable analysis-run history remain
  separate SQLite files.
- Free Render filesystem is ephemeral; startup hydration after restart is
  expected. A new snapshot version is uploaded once; an individual analysis
  request does not upload a local SQLite file.
- A successful offline test suite is not live-provider readiness or evaluation
  evidence.
- Numeric claims require accepted observations, metric-specific source
  locators, resolvable evidence, and Stage-1 validation.
- Do not infer reporting scope, run live analysis, change formulas, or migrate
  to AWS without an explicit recorded decision and user authorization.
