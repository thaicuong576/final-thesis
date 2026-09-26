# Staging Deployment Architecture & Operations Guide

This document establishes the staging deployment architecture, operational runbooks, and platform contracts for the **Sprint 0: Deployment Walking Skeleton**.

## Current analysis configuration (2026-09-27)

The sections below retain the initial hosting setup. The analysis runtime also
requires an accepted snapshot, separate history storage and model configuration:

| Setting | Purpose |
|---|---|
| `SQLITE_DB_PATH` | Explicit accepted analytical snapshot, opened read-only. The ignored local Gold file is not supplied by a Git deployment. |
| `ANALYSIS_RUNS_DB_PATH` | Separate writable history file; same-file aliases with the dataset are rejected. Schema: `contracts/run-store-schema.sql`. |
| `GOLD_SCOPE_AUTHORITY_PATH` | Explicit hash-verified authority sidecar for Gold peer reporting scope; see D-073. |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | Server-side configuration for active specialist writers, synthesis and critic. No key is exposed to the browser. |

Analysis readiness requires accepted data and required model configuration.
Configuration presence does not prove provider reachability or model quality.
Final staging acceptance requires a real same-snapshot report, history roundtrip
and source-hash verification. Artifact provisioning/startup hash checks and the
Render readiness health-check change remain pending deployment work.

On ephemeral hosting, provision the accepted artifact on each start and use a
separate runtime history path. A restart may reset temporary history; disclose
that behavior in the preview. Deployment changes require explicit approval.

> [!IMPORTANT]
> **Current readiness truth (2026-09-27):** the public API returns `503` from
> `/api/ready` with `database=disconnected` and no accepted snapshot;
> `/api/capabilities` returns `analysis_available=false` and
> `limitation_code=accepted_snapshot_unavailable`. The historical Supabase
> smoke test later in this document is not current thesis acceptance. Do not
> send an analysis request until the accepted SQLite artifact is explicitly
> provisioned and readiness passes.

### Accepted-snapshot provisioning contract

Before enabling a teacher walkthrough or a scored run, provision these
server-side values from a reviewed artifact; never put them in `VITE_*`
variables:

| Variable | Required value | Readiness meaning |
|---|---|---|
| `SQLITE_DB_PATH` | Explicit path to the accepted SQLite file | Empty, missing, or default-inferred paths fail closed. |
| `EXPECTED_DATASET_SNAPSHOT_ID` | Exact provider-reported snapshot identity | Prevents an arbitrary file from being treated as the intended dataset. |
| `EXPECTED_SQLITE_SHA256` | 64-character raw-file SHA-256 | Binds the reviewed bytes to the runtime artifact. |
| `ANALYSIS_RUNS_DB_PATH` | Distinct writable path | Run history must not alias or mutate the accepted snapshot. |
| `GOLD_SCOPE_AUTHORITY_PATH` | Verified sidecar when Gold peer scope is used | Unknown reporting scope remains blocked. |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | Server-side specialist/writer/critic configuration | Necessary for runnable analysis but not proof of model quality. |

The runtime must also reject SQLite WAL/journal sidecars, failed integrity
checks, byte changes during validation, hash mismatch, provider snapshot
mismatch and unavailable company observations.

---

## 1. Architectural Distinction: Deployment Infrastructure vs. Thesis Architecture

> [!IMPORTANT]
> **Non-Negotiable Architecture Principle**:
> The deployment stack described in this document represents **operational infrastructure**, not the canonical business or analytical architecture of the thesis.
> 
> - **Supabase is NOT the canonical financial architecture**: Supabase PostgreSQL is an external persistence and staging adapter. The reusable analysis core remains database-agnostic.
> - **Render is NOT required by the analysis core**: Render provides containerized HTTP hosting for the application shell. The core logic can run on any container runtime, serverless function, or local Python process.
> - **Vercel is NOT required by the analysis core**: The React/Vite application hosted on Vercel is a reference client. Replacing the UI does not change the analytical contracts.
> - **Gold is NOT required by the core**: The application layer connects via dataset provider protocols, not physical Gold SQLite files.

### Layering Diagram

#### Current Sprint 0 Walking Skeleton Flow:

```text
Browser
   ↓ HTTPS
Vercel (React 19 / Vite SPA)
   ↓ HTTPS (CORS-restricted)
Render (FastAPI HTTP Shell: /api/health, /api/ready, /api/version)
   ↓ TCP / SSL (psycopg SELECT 1)
Supabase (Managed PostgreSQL Staging Database)
```

#### Future Full System Flow (Phase 4+):

```text
Browser / API Client
   ↓ HTTPS
Render FastAPI Application Shell (thesis_api)
   ↓ Python invocation
Framework-Neutral Thesis Core (thesis_data)
   ├── AnalysisPlan & Scope Validation
   ├── Capability Activation (Macro, Sector, Company specialists)
   ├── Deterministic Acceptance & QA
   └── Bounded Semantic Critique & Revision
   ↓ Adapter Boundaries
Infrastructure & Providers
   ├── Supabase / Enterprise PostgreSQL (Runs, Reports, Audits)
   ├── Financial Dataset Providers (Normalized observations, Benchmarks)
   ├── Vector / RAG Indexes (pgvector / local indices)
   └── OpenAI API / LLM Providers
```

---

## 2. Infrastructure Platform Roles

| Platform | Role | Configuration / Root |
|---|---|---|
| **Vercel** | Reference frontend hosting (React 19 / Vite SPA) | Root: `frontend/`, Output: `dist/`, SPA rewrites: `vercel.json` |
| **Render** | Managed backend web service (FastAPI shell) | Blueprint: `render.yaml`, Runtime: Python 3.11+, Entrypoint: `uvicorn thesis_api.main:app` |
| **Supabase** | Staging PostgreSQL persistence | Direct connection or Supavisor connection pooler (`DATABASE_URL`) |
| **cron-job.org** | Staging heartbeat / liveness monitoring | Periodic `GET /api/health` keep-alive ping |

---

## 3. Environment & Secrets Contract

### Backend Environment Variables (`thesis_api`)

| Variable | Required | Staging Example | Purpose |
|---|---|---|---|
| `APP_ENV` | Yes | `staging` | Runtime environment mode (`development`, `staging`, `production`). |
| `APP_NAME` | No | `final-thesis-api` | Identifier reported by `/api/health` and `/api/version`. |
| `DATABASE_URL` | Legacy Sprint 0 connectivity only | `postgresql://postgres.[REF]:[PWD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require` | Optional Supabase adapter connection; it is not accepted analytical evidence for the current runtime. |
| `SQLITE_DB_PATH` | Yes for analysis readiness | `/opt/render/project/src/data/accepted.sqlite` | Explicit accepted analytical snapshot opened read-only; default inference is rejected. |
| `EXPECTED_DATASET_SNAPSHOT_ID` | Yes for analysis readiness | `snapshot-...` | Exact provider-reported snapshot identity required at startup. |
| `EXPECTED_SQLITE_SHA256` | Yes for analysis readiness | *(64-character SHA-256)* | Raw-file hash for the reviewed accepted snapshot. |
| `ANALYSIS_RUNS_DB_PATH` | Yes for analysis readiness | `/tmp/analysis_runs.sqlite` | Distinct writable history store; aliases with the dataset are rejected. |
| `GOLD_SCOPE_AUTHORITY_PATH` | When Gold peer scope is used | `/opt/render/project/src/config/gold-scope-authority.json` | Explicit hash-verified reporting-scope authority sidecar. |
| `CORS_ORIGINS` | Yes | `http://localhost:5173,https://final-thesis-frontend.vercel.app` | Comma-separated list or JSON array of allowed browser origins. |
| `CORS_ORIGIN_REGEX` | No | `^https://.*final-thesis.*\.vercel\.app$` | Optional regex pattern for dynamic Vercel preview branch URLs. |
| `APP_REVISION` | No | `${RENDER_GIT_COMMIT}` | Deployment Git commit SHA returned by `/api/version`. |
| `OPENAI_API_KEY` | Later phases | *(Secret)* | Server-side LLM key. **Never exposed to client or version endpoint**. |

### Frontend Environment Variables (`frontend`)

| Variable | Required | Staging Example | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `https://final-thesis-zgwt.onrender.com` | Base URL for FastAPI backend endpoints. |

> [!CAUTION]
> **Secret Boundary Rule**:
> Never prefix backend secrets or snapshot controls (`DATABASE_URL`, `OPENAI_API_KEY`, `SQLITE_DB_PATH`, expected hashes, etc.) with `VITE_`. Vite bundles all `VITE_*` environment variables directly into public client-side JavaScript.

---

## 4. Local Development Runbook

### Running Backend API Shell

```bash
# From repository root:
# 1. Install dependencies
pip install -r requirements-render.txt

# 2. Configure environment
cp .env.example .env

# 3. Launch FastAPI with auto-reload
python -m uvicorn thesis_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Test endpoints:
- `curl http://127.0.0.1:8000/api/health`
- `curl http://127.0.0.1:8000/api/version`
- `curl http://127.0.0.1:8000/api/ready`

### Running Frontend

```bash
# From frontend directory:
cd frontend

# 1. Install dependencies
npm ci

# 2. Configure environment
cp .env.example .env.local

# 3. Start Vite dev server
npm run dev
```

Visit `http://localhost:5173`.

---

## 5. Render Web Service Deployment

Render deploys the FastAPI application directly from Git using `render.yaml` or managed web service setup.

### Active Staging Web Service

- **Service Name**: `final-thesis`
- **Service ID**: `srv-dam0348u01pc73avsorg`
- **Service Slug**: `final-thesis-zgwt`
- **Primary URL**: `https://final-thesis-zgwt.onrender.com`
- **Dashboard URL**: `https://dashboard.render.com/web/srv-dam0348u01pc73avsorg`
- **Region**: Singapore (`singapore`)
- **Plan**: Free
- **Branch**: `feat/deployment-walking-skeleton`
- **Build Command**: `pip install -r requirements-render.txt`
- **Start Command**: `uvicorn thesis_api.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/health`
- **Active Environment Variables**:
  - `PYTHONPATH`: `src`
  - `APP_ENV`: `staging`
  - `DATABASE_URL`: legacy Supabase connectivity variable retained for Sprint 0 infrastructure only; it does not provision accepted analytical data.
  - `SQLITE_DB_PATH`: **not provisioned in the current public staging service**; required before analysis readiness can pass.
  - `EXPECTED_DATASET_SNAPSHOT_ID`: **not provisioned in the current public staging service**.
  - `EXPECTED_SQLITE_SHA256`: **not provisioned in the current public staging service**.
  - `ANALYSIS_RUNS_DB_PATH`: **not provisioned in the current public staging service**; must be distinct from the accepted snapshot.
  - `CORS_ORIGINS`: `["http://localhost:5173","https://final-thesis-frontend.vercel.app"]`
  - `CORS_ORIGIN_REGEX`: `^https://.*final-thesis.*\.vercel\.app$`

### Blueprint Specifications (`render.yaml`)

```yaml
services:
  - type: web
    name: final-thesis-api
    runtime: python
    region: singapore
    plan: free
    branch: main
    buildCommand: pip install -r requirements-render.txt
    startCommand: uvicorn thesis_api.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/health
    envVars:
      - key: PYTHONPATH
        value: src
      - key: APP_ENV
        value: staging
      - key: DATABASE_URL
        sync: false
      - key: SQLITE_DB_PATH
        sync: false
      - key: EXPECTED_DATASET_SNAPSHOT_ID
        sync: false
      - key: EXPECTED_SQLITE_SHA256
        sync: false
      - key: ANALYSIS_RUNS_DB_PATH
        sync: false
      - key: GOLD_SCOPE_AUTHORITY_PATH
        sync: false
      - key: CORS_ORIGINS
        sync: false
      - key: CORS_ORIGIN_REGEX
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

---

## 6. Vercel Frontend Deployment

### Active Staging / Production Deployment

- **Project Name**: `final-thesis-frontend`
- **Project ID**: `prj_4M0YPjycNLG5aK7atZKlSbbl61IU`
- **Scope**: `eddies-projects-69fa3178`
- **Canonical URL**: `https://final-thesis-frontend.vercel.app`
- **Git Connection**: `https://github.com/thaicuong576/final-thesis` (monitored for automatic deployments)
- **Framework Preset**: Vite
- **Root Directory**: `frontend`
- **Build Command**: `npm run build` (`tsc -b && vite build`)
- **Output Directory**: `dist`
- **Install Command**: `npm ci`
- **Configured Environment Variables**:
  - `VITE_API_BASE_URL`: `https://final-thesis-zgwt.onrender.com` (Production & Preview)

### Project Settings on Vercel (Reference)

### SPA Routing & Page Refresh Configuration

Vercel static file serving handles deep client-side routes (such as `/analysis`, `/data`, `/reports`) via `frontend/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

This prevents 404 errors when a user bookmarks or hard-refreshes any SPA route.

---

## 7. Historical Supabase PostgreSQL Staging Adapter

Supabase provides the historical Sprint 0 managed PostgreSQL adapter. It is
not the accepted analytical snapshot for the current thesis runtime.

### Active Staging Database Project

- **Project Name**: `Final thesis`
- **Project Ref**: `klaukirnadifltzhqidg`
- **Organization**: `Eddie Agent` (`pomhwmgylzkjnjnjsrbb`)
- **Region**: `Southeast Asia (Singapore)` (`ap-southeast-1`)
- **Dashboard URL**: `https://supabase.com/dashboard/project/klaukirnadifltzhqidg`

### Obtaining the Connection String

In the Supabase Dashboard:
1. Open [Project Settings → Database](https://supabase.com/dashboard/project/klaukirnadifltzhqidg/settings/database).
2. Locate **Connection string** (or click the **Connect** modal in the top header).
3. Select **Transaction Pooler** (Supavisor on **Port 6543**, recommended for Render managed backend):
   ```text
   postgresql://postgres.klaukirnadifltzhqidg:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```
4. Alternatively, for Session mode (**Port 5432**):
   ```text
   postgresql://postgres.klaukirnadifltzhqidg:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```
5. Set this connection string in the Render service environment as `DATABASE_URL`.

### Historical Database Invariant for Sprint 0

- **NO domain tables created**: Table schemas (`analyses`, `reports`, `audit_events`, `embeddings`) will be created in future slices when their respective contracts are implemented.
- **NO Gold data migration**: Raw research datasets remain local and immutable.
- Historical connectivity was validated purely via `SELECT 1` through
  `GET /api/ready`; that probe does not establish accepted snapshot readiness.

---

## 8. cron-job.org Heartbeat Monitoring

### Purpose & Render Policy Guardrails

Render free-tier instances spin down after 15 minutes without incoming HTTP traffic. An external heartbeat monitor can keep staging responsive for scheduled demonstrations.

> [!WARNING]
> **Render Free Allowance Notice**:
> Render provides 750 free instance hours per month per user account. Pinging an instance 24/7 consumes ~720 hours/month. If multiple free services exist on the account, continuous keepalive pings will exhaust free hours and suspend services.
> 
> - For staging / thesis defense demos: enable keepalive during active testing hours.
> - For long-term production: upgrade to Render Starter plan ($7/mo) which does not spin down, rather than running aggressive pingers.

### Job Configuration on cron-job.org

- **Job ID**: `8462735`
- **Title**: `final-thesis-api-staging-heartbeat`
- **URL**: `https://final-thesis-zgwt.onrender.com/api/health`
- **Method**: `GET`
- **Schedule**: Every 10 minutes (`0,10,20,30,40,50` min past every hour)
- **Status**: Enabled (Active)
- **Timezone**: `Asia/Ho_Chi_Minh`

---

## 9. Historical Sprint 0 Smoke Test Record

The following record is retained for traceability to the Sprint 0 deployment
walking skeleton. It is tied to the historical deployment revision shown below
and must not be presented as current analytical readiness or thesis evaluation
evidence.

### 1. Backend Liveness Probe
```bash
curl -i https://final-thesis-zgwt.onrender.com/api/health
```
- **Result**: HTTP 200 OK
- **Response**: `{"status": "ok", "service": "final-thesis-api"}`

### 2. Safe Version Probe
```bash
curl -i https://final-thesis-zgwt.onrender.com/api/version
```
- **Result**: HTTP 200 OK
- **Response**: `{"service": "final-thesis-api", "environment": "staging", "revision": "1bec250621a5f37796a5657279e3bb6eaba2d7aa"}`
- **Verification**: Zero secret tokens, passwords, or connection URLs in response headers or body.

### 3. Historical Database Probe (Supabase Reachability)
```bash
curl -i https://final-thesis-zgwt.onrender.com/api/ready
```
- **Result**: HTTP 200 OK
- **Response**: `{"status": "ready", "database": "connected"}`
- **Verification**: Backend successfully executes `SELECT 1;` against Supabase pooler on port 6543 via SSL.

### 4. CORS Preflight Probe
```bash
curl -i -X OPTIONS https://final-thesis-zgwt.onrender.com/api/health \
  -H "Origin: https://final-thesis-frontend.vercel.app" \
  -H "Access-Control-Request-Method: GET"
```
- **Result**: HTTP 200 OK
- **Headers**:
  - `access-control-allow-origin: https://final-thesis-frontend.vercel.app`
  - `access-control-allow-methods: GET, POST, OPTIONS`

### 5. Frontend Browser & SPA Routing Checks
1. `https://final-thesis-frontend.vercel.app/` → HTTP 200 OK, client redirects cleanly to `/analysis`.
2. `https://final-thesis-frontend.vercel.app/analysis` → HTTP 200 OK, SPA rewrites cleanly without 404 on refresh.
3. `https://final-thesis-frontend.vercel.app/data` → HTTP 200 OK, renders data foundation status view.
4. Browser Network tab / bundle audit: zero secrets present in client bundles.

---

## 10. Current Read-only Recheck (2026-09-27)

No deployment settings, secrets, data files, uploads or analysis requests were
changed or sent during this recheck.

### Public API

```text
GET https://final-thesis-zgwt.onrender.com/api/ready
HTTP 503
{"status":"unavailable","database":"disconnected","dataset_snapshot_id":null,"detail":"No readable accepted canonical or Gold snapshot is configured."}

GET https://final-thesis-zgwt.onrender.com/api/capabilities
HTTP 200
snapshotId=null; datasetId=null; entities=[]; periods=[]; metrics=[];
analysis_available=false; limitation_code=accepted_snapshot_unavailable;
database_status=disconnected; semantic_reviewer_configured=true;
specialist_writer_configured=true; analysis_runs_store_configured=true
```

### Frontend walkthrough state

The public frontend reports a disconnected data foundation with zero banks,
metrics and periods; the analysis action is disabled; and the report library
contains explicitly simulated/mock examples. This is a blocked walkthrough
state until an accepted SQLite snapshot is provisioned and `/api/ready` passes.

## 11. Rollback Procedure

If a staging deployment exhibits fatal errors:
1. **Frontend (Vercel)**:
   - In Vercel Project Dashboard → **Deployments** → Select previous green deployment → Click **Instant Rollback**.
2. **Backend (Render)**:
   - In Render Dashboard → **Deploys** → Select previous stable commit deploy → Click **Rollback**.
3. **Git Level**:
   - Revert commit on feature branch or create hotfix branch using standard SDLC gates.
