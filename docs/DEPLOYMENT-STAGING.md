# Staging Deployment Architecture & Operations Guide

This document establishes the staging deployment architecture, operational runbooks, and platform contracts for the **Sprint 0: Deployment Walking Skeleton**.

## Current analysis configuration (2026-09-25)

The sections below retain the initial hosting setup. The analysis runtime also
requires an accepted snapshot, separate history storage and model configuration:

| Setting | Purpose |
|---|---|
| `SQLITE_DB_PATH` | Explicit accepted analytical snapshot, opened read-only. The ignored local Gold file is not supplied by a Git deployment. |
| `ANALYSIS_RUNS_DB_PATH` | Separate writable history file; same-file aliases with the dataset are rejected. Schema: `contracts/run-store-schema.sql`. |
| `EXPECTED_DATASET_SNAPSHOT_ID`, `EXPECTED_SQLITE_SHA256` | Immutable identity and byte hash required before the accepted file is served. |
| `SUPABASE_URL`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_STORAGE_OBJECT` | Private object-storage location used to hydrate the snapshot on an ephemeral Render start. |
| `SUPABASE_SERVICE_ROLE_KEY` | Render-only secret used for the private Storage download; never expose it to Vite or commit it. |
| `GOLD_SCOPE_AUTHORITY_PATH` | Explicit hash-verified authority sidecar for Gold peer reporting scope; see D-073. |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | Server-side configuration for active specialist writers, synthesis and critic. No key is exposed to the browser. |

Analysis readiness requires accepted data and required model configuration.
Configuration presence does not prove provider reachability or model quality.
Final staging acceptance requires a real same-snapshot report, history roundtrip
and source-hash verification. The application now hydrates and validates the
explicit snapshot before serving traffic; applying the Render secret and
deploying remain user-authorized operational steps.

On ephemeral hosting, provision the accepted artifact on each start and use a
separate runtime history path. A restart may reset temporary history; disclose
that behavior in the preview. Deployment changes require explicit approval.

### Free Render snapshot hydration

The accepted Gold file is uploaded once to a **private** Supabase Storage
bucket. On each Render process start, the API downloads the configured object
to `SQLITE_DB_PATH`, verifies its SHA-256, SQLite integrity, and
`snapshot_metadata.snapshot_id`, then atomically publishes the file to the
read-only provider. A missing or mismatched secret, object, hash, or identity
fails closed before the service serves readiness. Render Free's local file is
ephemeral, so a restart re-downloads the same immutable object; users do not
upload the snapshot per analysis request.

### Free Render analysis run history persistence & hydration

On Render Free instances, the local filesystem at `ANALYSIS_RUNS_DB_PATH`
(`/tmp/analysis_runs.sqlite`) resets whenever the instance sleeps or redeploys.
To maintain persistent run history and report traces across cold starts:

1. **Remote Run Upload**: After each analysis run completes (whether successful,
   limited, or blocked/error), the application writes the full run record
   (including plan, report, events, trace steps, and model metadata) as a JSON
   object under `RUN_HISTORY_REMOTE_PREFIX` (default: `run-history/`) in the
   private Supabase Storage bucket (`<prefix>/<run_id>.json`).
   - The upload executes asynchronously in the background so API responses are
     never delayed.
   - Any upload failure logs a sanitized warning without revealing API keys and
     does not fail the client request.
2. **Startup Hydration**: On application startup (FastAPI `lifespan`), the server
   lists objects under `RUN_HISTORY_REMOTE_PREFIX` (up to 500 latest runs),
   downloads missing records, and idempotently populates the local SQLite store.
   Runs already present locally are skipped.
3. **Safety Boundaries**: Run history persistence strictly respects storage
   separation: it never writes to the analytical Gold snapshot (`SQLITE_DB_PATH`),
   never overwrites the remote snapshot object (`SUPABASE_STORAGE_OBJECT`), and
   refuses objects with `.sqlite` extensions. If Supabase configuration is
   incomplete, the API operates in local-only mode without breaking `/api/ready`.

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
| `DATABASE_URL` | For readiness | `postgresql://postgres.[REF]:[PWD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require` | PostgreSQL connection string. Checked by `/api/ready`. |
| `CORS_ORIGINS` | Yes | `http://localhost:5173,https://final-thesis-frontend.vercel.app` | Comma-separated list or JSON array of allowed browser origins. |
| `CORS_ORIGIN_REGEX` | No | `^https://.*final-thesis.*\.vercel\.app$` | Optional regex pattern for dynamic Vercel preview branch URLs. |
| `APP_REVISION` | No | `${RENDER_GIT_COMMIT}` | Deployment Git commit SHA returned by `/api/version`. |
| `SQLITE_DB_PATH` | Yes | `/tmp/accepted.sqlite` | Explicit local path populated by startup hydration and opened read-only. |
| `ANALYSIS_RUNS_DB_PATH` | Yes | `/tmp/analysis_runs.sqlite` | Separate writable history path; never alias the accepted snapshot. |
| `EXPECTED_DATASET_SNAPSHOT_ID` | Yes | `gold-bank-2025-expanded-v5-evidence` | Expected `snapshot_metadata` identity. |
| `EXPECTED_SQLITE_SHA256` | Yes | `1b1b5c...` | Expected raw file SHA-256. |
| `SUPABASE_URL` | Yes for free hydration | `https://<project>.supabase.co` | Supabase project URL; not a secret. |
| `SUPABASE_STORAGE_BUCKET` | Yes for free hydration | `thesis-snapshots` | Private Storage bucket. |
| `SUPABASE_STORAGE_OBJECT` | Yes for free hydration | `gold-bank-2025-expanded-v5-evidence.sqlite` | Exact immutable object path. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes for free hydration | *(Secret)* | Server-only Storage credential. Never expose to the browser. |
| `RUN_HISTORY_REMOTE_PREFIX` | No | `run-history/` | Prefix in private Supabase Storage for persisted run JSON objects (default `run-history/`). Activates when Supabase Storage settings are configured. |
| `OPENAI_API_KEY` | Later phases | *(Secret)* | Server-side LLM key. **Never exposed to client or version endpoint**. |

### Frontend Environment Variables (`frontend`)

| Variable | Required | Staging Example | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `https://final-thesis-zgwt.onrender.com` | Base URL for FastAPI backend endpoints. |

> [!CAUTION]
> **Secret Boundary Rule**:
> Never prefix backend secrets (`DATABASE_URL`, `OPENAI_API_KEY`, etc.) with `VITE_`. Vite bundles all `VITE_*` environment variables directly into public client-side JavaScript.

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
  - `DATABASE_URL`: `postgresql://postgres.klaukirnadifltzhqidg:[SECRET]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require`
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
      - key: SQLITE_DB_PATH
        value: /tmp/accepted.sqlite
      - key: ANALYSIS_RUNS_DB_PATH
        value: /tmp/analysis_runs.sqlite
      - key: EXPECTED_DATASET_SNAPSHOT_ID
        value: gold-bank-2025-expanded-v5-evidence
      - key: EXPECTED_SQLITE_SHA256
        value: 1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73
      - key: SUPABASE_URL
        value: https://klaukirnadifltzhqidg.supabase.co
      - key: SUPABASE_STORAGE_BUCKET
        value: thesis-snapshots
      - key: SUPABASE_STORAGE_OBJECT
        value: gold-bank-2025-expanded-v5-evidence.sqlite
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: RUN_HISTORY_REMOTE_PREFIX
        value: run-history/
      - key: GOLD_SCOPE_AUTHORITY_PATH
        value: data/evaluation/gold-v5-reporting-scope-authority-v1.json
      - key: DATABASE_URL
        sync: false
      - key: CORS_ORIGINS
        sync: false
      - key: CORS_ORIGIN_REGEX
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

### Optional SSI FastConnect Market Data Environment Variables (MKT-1)

To enable real-time market price context and P/B valuation beside verified financial reports, configure the following optional variables in the Render Web Service Environment settings:

| Variable Name | Required | Description & Source |
|---|---|---|
| `SSI_FC_URL` | No | Base URL for SSI FastConnect API (e.g. `https://fc-data.ssi.com.vn`). Any trailing `/api/v2` is automatically stripped. |
| `SSI_CONSUMER_ID` | No | Consumer ID issued in the SSI FastConnect iBoard developer portal. |
| `SSI_CONSUMER_SECRET` | No | Consumer Secret issued in the SSI FastConnect iBoard developer portal. |

> **Graceful Degradation Note**: If any of these 3 variables are empty or unset, the backend market endpoints (`/api/market/quotes`, `/api/market/valuation`) return HTTP 200 with `{"configured": false, "quotes": []}` / `{"configured": false, "items": []}`. The frontend price strip and valuation cards stay cleanly hidden with zero error banners or layout breaks. The application health and readiness probe (`/api/ready`) does NOT depend on SSI availability.

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

## 7. Supabase PostgreSQL Staging Configuration

Supabase provides the managed PostgreSQL database instance.

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

### Database Invariant for Sprint 0

- **NO domain tables created**: Table schemas (`analyses`, `reports`, `audit_events`, `embeddings`) will be created in future slices when their respective contracts are implemented.
- **NO Gold data migration**: Raw research datasets remain local and immutable.
- Connectivity is validated purely via `SELECT 1` through `GET /api/ready`.

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

## 9. Smoke Test Acceptance Verification

Verified live against the active staging deployment:

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

### 3. Database Readiness Probe (Supabase Reachability)
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

## 10. Rollback Procedure

If a staging deployment exhibits fatal errors:
1. **Frontend (Vercel)**:
   - In Vercel Project Dashboard → **Deployments** → Select previous green deployment → Click **Instant Rollback**.
2. **Backend (Render)**:
   - In Render Dashboard → **Deploys** → Select previous stable commit deploy → Click **Rollback**.
3. **Git Level**:
   - Revert commit on feature branch or create hotfix branch using standard SDLC gates.
