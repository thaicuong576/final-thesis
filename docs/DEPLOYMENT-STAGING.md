# Staging Deployment Architecture & Operations Guide

This document establishes the staging deployment architecture, operational runbooks, and platform contracts for the **Sprint 0: Deployment Walking Skeleton**.

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
| `OPENAI_API_KEY` | Later phases | *(Secret)* | Server-side LLM key. **Never exposed to client or version endpoint**. |

### Frontend Environment Variables (`frontend`)

| Variable | Required | Staging Example | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `https://final-thesis-api.onrender.com` | Base URL for FastAPI backend endpoints. |

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

Render deploys the FastAPI application directly from Git using `render.yaml` or manual service setup.

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
      - key: CORS_ORIGINS
        sync: false
      - key: CORS_ORIGIN_REGEX
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

### Render Dashboard Manual Setup (Alternative)

1. **Create Web Service**: Connect `thaicuong576/final-thesis` repository.
2. **Environment**: Python 3.
3. **Region**: Singapore (`singapore`) or closest region to Supabase project.
4. **Build Command**: `pip install -r requirements-render.txt`.
5. **Start Command**: `uvicorn thesis_api.main:app --host 0.0.0.0 --port $PORT`.
6. **Health Check Path**: `/api/health`.
7. **Environment Variables**:
   - `PYTHONPATH`: `src`
   - `APP_ENV`: `staging`
   - `DATABASE_URL`: *(Supabase connection string)*
   - `CORS_ORIGINS`: `https://[your-vercel-app].vercel.app`
   - `CORS_ORIGIN_REGEX`: `^https://.*final-thesis.*\.vercel\.app$`

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
  - `VITE_API_BASE_URL`: `https://final-thesis-api.onrender.com` (Production & Preview)

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

### Obtaining the Connection String

In the Supabase Dashboard:
1. Navigate to **Project Settings** → **Database**.
2. Locate **Connection parameters**.
3. For serverless / managed cloud runtimes like Render:
   - **Recommended**: Connection Pooling via Supavisor (**Port 6543**, Transaction Mode).
   - Connection string format:
     ```text
     postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
     ```
4. Set this value in Render under environment variable `DATABASE_URL`.

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

1. **URL**: `https://[your-render-api].onrender.com/api/health`
2. **Method**: `GET`
3. **Schedule**: Every 10 minutes (`*/10 * * * *`).
4. **Failure Alerts**: Email notification after 2 consecutive failures.

---

## 9. Smoke Test Acceptance Verification

Before accepting a deployment, execute the following smoke tests:

### 1. Backend Liveness Probe
```bash
curl -i https://[RENDER_SERVICE_URL]/api/health
```
- **Expected**: HTTP 200 OK
- **Response**: `{"status": "ok", "service": "final-thesis-api"}`

### 2. Safe Version Probe
```bash
curl -i https://[RENDER_SERVICE_URL]/api/version
```
- **Expected**: HTTP 200 OK
- **Response**: `{"service": "final-thesis-api", "environment": "staging", "revision": "<git-sha>"}`
- **Verification**: Zero secret tokens, passwords, or connection URLs in response headers or body.

### 3. Database Readiness Probe
```bash
curl -i https://[RENDER_SERVICE_URL]/api/ready
```
- **Expected (Connected)**: HTTP 200 OK, `{"status": "ready", "database": "connected"}`
- **Expected (Unconfigured/Down)**: HTTP 503 Service Unavailable, `{"status": "unavailable", ...}`

### 4. Frontend Browser Checks
1. Open `https://[VERCEL_APP_URL]/` → Redirects cleanly to `/analysis`.
2. Navigate to `/data` → Renders data foundation status view.
3. Hard refresh on `/analysis` and `/data` → Verifies SPA rewrite works without 404.
4. Inspect Browser Network tab: verify no client errors and verify that no secrets are present in client bundles.

---

## 10. Rollback Procedure

If a staging deployment exhibits fatal errors:
1. **Frontend (Vercel)**:
   - In Vercel Project Dashboard → **Deployments** → Select previous green deployment → Click **Instant Rollback**.
2. **Backend (Render)**:
   - In Render Dashboard → **Deploys** → Select previous stable commit deploy → Click **Rollback**.
3. **Git Level**:
   - Revert commit on feature branch or create hotfix branch using standard SDLC gates.
