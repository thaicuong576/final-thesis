# Task Manifest: [THES-14] Persist Analysis Runs in SQLite, Fix Live SSE Streaming, Eliminate Mock Data, and Polish Friendly UI

## 1. Linear Context
- **Issue**: [THES-14](https://linear.app/eddiephung/issue/THES-14/featapiui-thes-14-persist-analysis-runs-in-sqlite-fix-live-sse)
- **Title**: eat(api,ui): [THES-14] persist analysis runs in sqlite, fix live sse streaming, eliminate mock data, and polish friendly ui
- **User Mandate**:
  1. Frontend không stream được event từ backend/llm hoạt động
  2. Chưa có database lưu trữ run / history
  3. Vẫn còn mock data
  4. UI nhìn vẫn không friendly

---

## 2. Detailed Technical Requirements

### A. SQLite Run Persistence & API (src/thesis_api/, contracts/schema.sql)
1. **Schema Migration**:
   - Add table nalysis_runs to contracts/schema.sql and run CREATE TABLE IF NOT EXISTS analysis_runs (...) in src/thesis_api/database.py or startup:
     `sql
     CREATE TABLE IF NOT EXISTS analysis_runs (
         run_id TEXT PRIMARY KEY,
         created_at TEXT NOT NULL,
         query TEXT NOT NULL,
         target_ticker TEXT NOT NULL,
         peer_tickers TEXT,
         period TEXT NOT NULL,
         status TEXT NOT NULL,
         report_json TEXT,
         events_json TEXT,
         model_used TEXT,
         latency_ms INTEGER
     );
     CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at DESC);
     CREATE INDEX IF NOT EXISTS idx_analysis_runs_target ON analysis_runs(target_ticker, period);
     `
2. **Backend Endpoints (src/thesis_api/main.py & service.py)**:
   - GET /api/runs: Returns list of past analysis runs sorted by created_at DESC (limit 20).
   - GET /api/runs/{run_id}: Returns run details, events, and report artifact.
   - GET /api/reports/{report_id}: Returns report artifact directly from nalysis_runs.
3. **Save Run on Completion**:
   - When stream_analysis_query emits REPORT_READY, insert the completed run into nalysis_runs in SQLite.

### B. Fix Live SSE Streaming (src/thesis_api/service.py & rontend/)
1. **Instant First Event Flush**:
   - In _stream_analysis_query_dynamic, yield USER_REQUEST_CONFIRMED and PLANNING_STARTED at tick 0ms **BEFORE** awaiting orchestrator.plan(). This establishes the HTTP 200 SSE connection and flushes the first event to the client immediately (<100ms), eliminating the 8-second browser freeze.
2. **Direct Backend SSE Endpoint in Frontend (useAnalysisSessionStream.ts)**:
   - When running on in-ai.eddiephung.me (or production hostname), connect directly to https://final-thesis-zgwt.onrender.com/api/analyze/stream instead of the relative path /api/analyze/stream (which passes through Vercel's buffering rewrite proxy that adds Connection: close).

### C. Eliminate All Remaining Mock Data
1. **ReportPage (rontend/src/pages/reports/ReportPage.tsx)**:
   - Fetch real report from GET /api/reports/{id} or GET /api/runs/{id} via React Query / fetch.
   - If not found or loading, show a clean, friendly loading skeleton or 404 Not Found state, NOT a hardcoded mock report from mockReports.ts.
2. **RecentReportsSummary (RecentReportsSummary.tsx)**:
   - Fetch and display real recent analysis runs from GET /api/runs instead of static mock cards.

### D. UI/UX Friendliness Polish (Warm Retro Workbench Style)
1. **Screen 1 (Composer)**:
   - Conversational, warm placeholder (Hỏi bất kỳ điều gì về sức khỏe tài chính ACB, VCB, MBB...).
   - Quick-select interactive chips for popular Vietnamese banks: ACB, VCB, MBB, TCB, CTG.
   - Clear and friendly empty/helper states.
2. **Screen 2 (Live Multi-Agent Session)**:
   - Friendly visual agent status:
     - Orchestrator: Lập kế hoạch & Phân rã câu hỏi
     - Company Specialist: Bóc tách BCTC & CAMEL
     - Sector Specialist: Đối chuẩn Trung vị Ngành
     - Semantic Critic: Phản biện & Kiểm định Chéo
   - Animated pulse/typing indicators while agents are thinking.
   - Clear progress timeline with friendly completion state.
   - Explicit connection error banner with 1-click retry.
3. **Screen 3 (Report)**:
   - Friendly executive summary card with key CAMEL findings.
   - Visual badges for healthy/warning metrics.
   - Clean, readable typography with font mono for financial metrics.

---

## 3. Verification & Quality Gates
1. **Backend Tests**:
   - $env:PYTHONPATH=src; python -m unittest discover -s tests -q
2. **Frontend Tests & Build**:
   - 
pm test -- --run
   - 
px tsc -b
   - 
pm run build
3. **GitHub PR & Rule 19 (Zero-Failure Handoff)**:
   - Commit: eat(api,ui): [THES-14] persist analysis runs in sqlite, fix live sse streaming, eliminate mock data, and polish friendly ui
   - Push branch eat/THES-14-persist-runs-fix-streaming-polish-ui to origin.
   - Open PR to main with gh pr create.
   - Ensure 100% CI/CD checks PASS before reporting back.
