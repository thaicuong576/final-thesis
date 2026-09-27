# Task manifest — fix live stream RUN_BLOCKED handling and period guidance

## Identity

- Branch: `feat/THES-81-live-stream-blocked-ui`
- Base: `6097a1893d18564d8c9d4038e89561273e41dbb4` (`origin/main`)
- Role: `worker-ui`
- Tracker: THES-81
- Binding contracts: `docs/DATA-CONTRACT.md`, `.agent/rules/design/README.md`, `contracts/openapi.json`
- User Screenshot: `C:/Users/ASUS/.gemini/antigravity/brain/ffbbfbd3-2b7f-4be7-88e0-6440290341a7/.user_uploaded/media_1790529968719.png`

## Objective

Fix the false-positive SSE connection error banner when a run is legitimately blocked by domain validation (`RUN_BLOCKED`, e.g. `unsupported_period`), and ensure graceful guidance on Screen 2 (Live Session) and Screen 1 (Composer).

## Problem Analysis from User Screenshot

In the user's screenshot (`media_1790529968719.png`):
1. User asked: "Phân tích LLR_COVERAGE của ACB trong năm 2024."
2. Backend correctly validated capabilities: snapshot only contains quarterly periods (`2024_Q1` .. `2024_Q4`), not full year `2024`.
3. Backend emitted `RUN_BLOCKED` event: `unsupported_period: Period 2024 is not an exact period in the accepted snapshot.`
4. Frontend Screen 2 (Live Session) correctly showed badge `Cần điều chỉnh yêu cầu` and the event message, BUT because the SSE stream completed without a `REPORT_READY` event, the frontend erroneously triggered its stream-ended fallback error:
   `Lỗi kết nối Live SSE tới backend (https://final-thesis-zgwt.onrender.com): Luồng đã kết thúc nhưng API không gửi báo cáo. Phiên chưa được đánh dấu hoàn tất..` with an `API lỗi` badge and `Thử lại Live` button.
5. This misleads the user into thinking the backend/network crashed, when in reality it is a controlled business validation rejection (`RUN_BLOCKED`).

## Required Fixes

1. **Frontend SSE Stream Consumer (`frontend/src/`):**
   - When receiving a `RUN_BLOCKED` event (or terminal blocked state):
     - Mark the session state as `blocked` / `needs_adjustment`.
     - Do NOT trigger the "Luồng đã kết thúc nhưng API không gửi báo cáo" error banner.
     - Hide the `API lỗi` badge and `Thử lại Live` button.
     - Keep the `Cần điều chỉnh yêu cầu` status and prompt the user to use "← Chỉnh sửa câu hỏi".
2. **Frontend Composer Period Selector (`frontend/src/`):**
   - Check how periods are displayed and selected from `/api/capabilities`.
   - Ensure the user can easily pick from the valid periods in capabilities (`2024_Q1` to `2024_Q4`).
3. **Verification:**
   - Run frontend lint and build: `npm run build` or `npm run lint` in `frontend/`.
   - Ensure clean build without errors.

## Acceptance Criteria

1. Submitting a query with an unsupported period (e.g. `2024`) shows a clean `Cần điều chỉnh yêu cầu` state with the orchestrator's explanation without any false network error banner.
2. The user is guided to click "← Chỉnh sửa câu hỏi" to select an exact supported period (e.g. `2024_Q4`).
3. All frontend tests/builds pass.
