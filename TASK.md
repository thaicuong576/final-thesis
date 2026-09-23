# Task Manifest: [THES-13] Wire Real SQLite Data Across Frontend & Backend, Optimize Multi-Agent Streaming and Routing

## 1. Linear Context
- **Issue**: [THES-13](https://linear.app/eddiephung/issue/THES-13/featapiui-thes-13-wire-real-sqlite-data-across-frontend-and-backend)
- **Title**: `feat(api,ui): [THES-13] wire real sqlite data across frontend & backend, optimize multi-agent streaming and routing`
- **User Mandate**: *t nghĩ wire data thật đi, r sửa gấp thếp. đừng mock nữa*

---

## 2. Scope of Work

### A. Backend Real Data Wiring & Streaming Concurrency (`src/thesis_api/`)
1. **Capabilities Endpoint (`src/thesis_api/service.py` & `main.py`)**:
   - `GET /api/capabilities` queries `finance_master_v2.sqlite` to return the real list of 27 banks, periods (2021–2024), and live DB status (WAL mode, distinct count).
2. **Single-Turn Data-Injected Specialists (`src/thesis_api/agents.py`)**:
   - `CompanySpecialistAgent`: Added `execute_with_data(ticker, period, precomputed_metrics)`: Formats verified SQLite CAMEL metrics directly into prompt for single-turn LLM synthesis without tool calls, adhering to Rule 3. Fallback grounded template implemented.
   - `SectorSpecialistAgent`: Added `execute_with_data(ticker, period, precomputed_benchmarks)`: Formats verified peer median metrics directly into prompt for single-turn synthesis. Fallback grounded template implemented.
   - Preserves dynamic tool-calling as a graceful fallback for open-ended queries.
3. **Immediate Event Emission & Concurrency (`src/thesis_api/service.py`)**:
   - In `_stream_analysis_query_dynamic`:
     - Emits `SPECIALIST_INVOKED`, `SPECIALIST_STARTED`, and `SPECIALIST_ACTIVITY` ("Đang đọc BCTC từ SQLite...") immediately *before* calling the LLM.
     - Runs `company` and `sector` specialists concurrently using `concurrent.futures.ThreadPoolExecutor(max_workers=2)`.
     - In fallback stream, maintains `emitted_event_types: set[str]` and deduplicates fallback stream chunks so no duplicate event types are re-emitted if dynamic streaming fails.

### B. Frontend Real Data Wiring & Persistent Routing (`frontend/src/`)
1. **Live Capability Provider (`frontend/src/entities/capability/api/capabilityService.ts`)**:
   - Connects to `/api/capabilities` (resolving `VITE_API_BASE_URL` when configured) to load the real 27 banks and active periods with graceful offline fallback.
2. **ActiveDatasetCard (`frontend/src/features/analysis-composer/components/ActiveDatasetCard.tsx`)**:
   - Displays real 27 listed banks (`... (27 NHTM)`), 2021–2024 periods, and SQLite WAL status. Re-exported at `features/create-analysis/components/ActiveDatasetCard.tsx`.
3. **Persistent Route Navigation (`frontend/src/pages/create-analysis/CreateAnalysisPage.tsx`)**:
   - Synchronizes session state with URL search params (`?mode=session&ticker=...&period=...&q=...`).
   - On page reload (F5), parses search params and automatically restores Screen 2 (`AnalysisSessionWorkspace`) with active live streaming.
   - Clears search params on returning to composer.
4. **Live Stream First (`frontend/src/features/analysis-session/components/AnalysisSessionWorkspace.tsx`)**:
   - Supports `fallbackToMockOnError` prop.
   - Displays a prominent error banner when live SSE connection fails with "Thử lại Live" and "Chuyển Mock" actions, eliminating silent mock fallback.

---

## 3. Verification & Acceptance Criteria
1. **Backend Tests**:
   - `$env:PYTHONPATH="src"; python -m unittest discover -s tests -p "test_*.py"`: 537 passed (skipped=4).
2. **Frontend Tests & Build**:
   - `npm test -- --run`: 6 test files, 74 tests passed.
   - `npx tsc -b`: 0 errors.
   - `npm run build`: Production build succeeded in 1.93s.
3. **GitHub PR & Rule 19 (Zero-Failure Handoff)**:
   - Commit: `feat(api,ui): [THES-13] wire real sqlite data across frontend & backend, optimize multi-agent streaming and routing`
   - Push branch `feat/THES-13-wire-real-data-and-optimize-streaming` to origin.
   - Create PR to `main` with `gh pr create`.
   - Monitor `gh pr checks <PR_NUMBER>` until 100% checks PASS.
