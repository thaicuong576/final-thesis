# TASK: [THES-9] Fix Live SSE Stream UI Rendering, Add Streaming Cadence, and Allow Custom Domain CORS

## Metadata
- **Ticket**: [THES-9](https://linear.app/eddiephung/issue/THES-9/fixapiui-thes-9-unblock-live-sse-stream-ui-rendering-add-streaming)
- **Worktree**: D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-9-fix-live-stream-rendering-and-cadence
- **Branch**: eat/THES-9-fix-live-stream-rendering-and-cadence

## Root Causes Identified
1. **Frontend Screen 2 Blocked by Mock Events**:
   In AnalysisSessionWorkspace.tsx, ctiveViewModel derivation checked if (activeMode === 'LIVE' && wantsLiveStream). However, because CreateAnalysisPage.tsx passed events={activeEvents}, wantsLiveStream evaluated to alse. So even when the user clicked Kết nối Live, the component still returned mockDriver.viewModel, ignoring the live stream completely!
2. **Backend SSE Too Fast (0ms delay)**:
   In src/thesis_api/service.py, stream_analysis_query yielded all 15 events in a synchronous loop within 10ms. Without progressive pacing, it finished instantaneously in a single frame.
3. **CORS on Custom Domain in-ai.eddiephung.me**:
   The user accesses the frontend via https://fin-ai.eddiephung.me. Backend src/thesis_api/settings.py needs to explicitly permit https://fin-ai.eddiephung.me and *.eddiephung.me, and rontend/vercel.json needs an /api/:path* rewrite to Render for Same-Origin reverse proxy.

## Required Changes

### 1. Frontend: Unblock Live Stream in Screen 2
- In rontend/src/features/analysis-session/components/AnalysisSessionWorkspace.tsx:
  - Update ctiveViewModel:
    `	ypescript
    if (activeMode === 'LIVE') {
      return liveStream.viewModel;
    }
    `
    (Remove wantsLiveStream check when ctiveMode === 'LIVE').
  - Update isActuallyLive:
    `	ypescript
    const isActuallyLive =
      activeMode === 'LIVE' &&
      liveStream.connectionMode === 'LIVE' &&
      !liveStream.isMockFallback;
    `
  - In CreateAnalysisPage.tsx:
    When transitioning to mode === 'SESSION' in handleConfirmAndAnalyze:
    Pass isLiveStream={true} and events={[]} (or omit events) to ensure AnalysisSessionWorkspace immediately defaults to live SSE stream!
    `	ypescript
    <AnalysisSessionWorkspace
      streamRequest={streamRequest}
      isLiveStream={true}
      driverMode={driverMode}
      driverStep={driverStep}
      onBackToComposer={() => setMode('DEFAULT')}
    />
    `

### 2. Backend: Add Progressive SSE Stream Cadence
- In src/thesis_api/service.py:
  In stream_analysis_query(req: AnalysisRequest, db_path: Path | None = None) -> Iterator[str]:
  Add a delay parameter step_delay: float = 0.35 (or default 0.35s delay).
  Insert if step_delay > 0: time.sleep(step_delay) before yielding major event milestones:
  - After PLAN_CREATED (0.35s)
  - After each specialist invocation/activity/output (0.25s)
  - After review & critique (0.35s)
  - After synthesis (0.35s)
  - Before REPORT_READY (0.35s)
  Ensure all unit tests can still pass quickly (tests can pass step_delay=0 or unittests run without delay).

### 3. Backend: Allow in-ai.eddiephung.me in CORS Settings
- In src/thesis_api/settings.py:
  Update cors_origins:
  `python
  default_factory=lambda: [
      http://localhost:5173,
      http://127.0.0.1:5173,
      https://final-thesis-frontend.vercel.app,
      https://fin-ai.eddiephung.me,
  ]
  `
  Update cors_origin_regex:
  `python
  default=r^https?://([a-zA-Z0-9-]+\.)?(vercel\.app|eddiephung\.me)(:[0-9]+)?$|^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$
  `

### 4. Vercel Reverse Proxy Configuration
- In rontend/vercel.json:
  Add rewrite before the fallback rule:
  `json
  rewrites: [
    {
      source: /api/:path*,
      destination: https://final-thesis-zgwt.onrender.com/api/:path*
    },
    {
      source: /(.*),
      destination: /index.html
    }
  ]
  `

## Verification & PR
1. Run backend tests:
   $env:PYTHONPATH=src; python -m unittest discover -s tests -q (must pass 507+ tests).
2. Run frontend tests:
   
pm test -- --run in rontend/ (must pass 68+ tests).
3. Run lint and build:
   
pm run lint and 
px tsc --noEmit in rontend/.
4. Commit:
   ix(api,ui): [THES-9] unblock live SSE stream UI rendering, add streaming cadence, and allow custom domain CORS
5. Push to origin feat/THES-9-fix-live-stream-rendering-and-cadence.
6. Open Pull Request to main.
