# Task Manifest: ER-6 Lean Ask Screen, Orchestrator Session and Process Trace

## Metadata
- Branch: `feat/er-6-ui-ask-session`
- Role: `worker-ui`
- Spec: `docs/plans/2026-09-28-er-report/PR-6-ui-ask-session-trace.md`
- Base: `55a7a51 feat(ui): [ER-7] block-rendered equity-research report (#92)`

## Scope of Work
1. **Screen A (Ask / `/analysis`)**:
   - Lean ask screen:
     - Title: "Bạn muốn phân tích gì?" (24px/700).
     - Auto-expanding `textarea` (3 rows) with placeholder from `capabilities.suggestedQuestions[0]`, primary "Phân tích" button at bottom right. Enter submits, Shift+Enter new line. Remove Ctrl+Enter hint.
     - Secondary text (13px `--text-secondary`): "Dữ liệu hiện có: {entities} · {Q1–Q4/2024} · {shortLabel các chỉ tiêu}", from `/api/capabilities`, with link "Chi tiết" to `/data`.
     - "Thử hỏi": chips from `capabilities.suggestedQuestions`. Hidden if empty. Clicking fills the textarea without submitting.
     - "Báo cáo gần đây": max 5 items from `/api/runs?limit=5` with question, date, and text status: "Hoàn tất", "Có giới hạn", "Bị chặn". Click opens report, or trace if blocked.
     - Error banner below textarea for `RUN_BLOCKED` or `status = "error"` with `error.message` and clickable `error.suggestions`. Keep user input intact.
     - Remove obsolete UI components: `ActiveDatasetCard`, `ActiveDatasetContextCard`, `DatasetSelectorSheet`, bank/quarter chips, `RequestInterpretationCard`, `ScopeMismatchAlert`, `ScopeAdjustmentDrawer`, old `SuggestedQuestions`, sample mockup links, "API: ..." labels, snapshot IDs.
     - `streamRequest.ts`: remove all client-side blocking; request only `{ query }`. Remove/deprecate client `intentParser.ts` for sending.

2. **Screen B (Session / `/session`)**:
   - `OrchestratorBoard`:
     - Top card: Orchestrator ("Điều phối viên"), full width.
     - Child agent cards: ONLY agents in `plan.detail.agents` with `decision = "run"`, plus "Phản biện" if arm has critic. DO NOT render skipped agents (e.g. Macro).
     - Connect Orchestrator to child cards via 1px SVG line `--border-default`.
     - Under each child card name: assigned analysis tasks (tool labels in plan). Orchestrator shows "Dạng câu hỏi: {nhãn}".
     - Status labels in text + color: Chờ / Đang làm / Xong / Đang sửa. Summary from latest step for that actor.
     - State transitions:
       - `assign` -> "Đang làm"
       - `tool_result` / `draft` -> "Xong"
       - `critique_issue` -> "Đang sửa"
       - `revision` -> "Xong"
       - Orchestrator -> "Xong" when `report_ready`.
     - Right corner: `mm:ss` elapsed timer based on latest step `t_ms`.
     - On `report_ready`: primary button "Mở báo cáo", auto-redirects after 1.5s if no interaction (respects `prefers-reduced-motion`).
     - SSE disconnect: "Mất kết nối. Thử lại" with retry button. No fake events.
     - Remove unused legacy session components (list in PR).

3. **Screen C (`ProcessTrace`)**:
   - Props: `steps: TraceStep[]`, `live: boolean`.
   - Header: "Quá trình phân tích", meta "{n} agent · {m} vòng phản biện · {thời lượng}", "Mở tất cả" / "Thu gọn".
   - Filter chips: "Tất cả" + each actor present in steps with color dot.
   - Rows: `mm:ss` · color dot · "{Actor} → {Recipient}" (500) · summary · chevron. Expandable with `aria-expanded`, keyboard accessible.
   - Default expanded: `critique_issue` and `revision`. Auto-scroll on `live` only if user is at bottom.
   - Render content by `kind`:
     - `plan`: question type, rationale, tools table, agent decisions table.
     - `assign`: blockquote with task.
     - `tool_result`: tool name, facts table (Content | Value | Source), datasets created, missing cells.
     - `draft`: draft sentences.
     - `compose`: report blocks in order.
     - `verify`: "{matched}/{checked} số khớp dữ liệu gốc", rejected sentences + reasons.
     - `critique_issue`: table Type | Severity | Requirement, quoted flagged sentence, evidence.
     - `revision`: old sentence strikethrough `--danger`, new sentence `--success`, with text labels "Trước" / "Sau".
     - `cross_level_finding`: Level | Signal table.
     - `blocked`: Vietnamese error message.
   - No raw technical IDs (fact_id, observation_id).

4. **Additional Review Fixes from PR #92**:
   - `SmallMultiples`: use `useChartWidth` for 1:1 scaling, stack to 1 column when container < 480px. Text in SVG >= 11px on 375px.
   - `ReportPage`: `capabilityMetrics`: extract all presentation fields from capabilities (`shortLabel`, `unit`, `direction`, `decimals`, `group`, `groupLabel`), field-by-field fallback to `DEFAULT_METRICS`. Ignore label if it matches metric id. For metrics not in registry: default `direction: "neutral"`, `unit` from capabilities.
   - Remove `docs/images/er-report-preview/*.png` from git repository.

5. **Verification**:
   - Lint, test (vitest + python unittest + guards), build.
   - Capture 1280px & 375px screenshots across screens.
