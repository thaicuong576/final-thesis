# Clean-room frontend Stage B pre-flight

Status: Stage B direction revised after review. The existing `CreateAnalysisPage`
is now the primary `Phân tích` surface and is embedded in the shared workspace
shell. The previously introduced analysis-home surface was removed.

## Guardrail answers

1. **Does this increase coupling to the current Gold dataset?** No. The screen reads the injected dataset and capability services and renders their returned values.
2. **Does this increase coupling to SQLite or a physical schema?** No. No SQLite, table, or storage access is added to the frontend.
3. **Does this hard-code the current five-bank universe?** No. Entity, period, metric, peer, and macro counts come from capability responses.
4. **Would it still work if the frontend were replaced?** Yes. The change is reference-client presentation only.
5. **Would it still work if the database were replaced through an adapter?** Yes. The existing service seams remain the integration boundary.
6. **Is it reusable core logic or reference-application logic?** Reference-application shell and presentation only.
7. **Does it preserve evidence/provenance?** Yes. It presents readiness, source state, and explicit limitations without inventing claims.
8. **Does it preserve dataset/snapshot traceability?** Yes. The active capability snapshot is shown as a secondary context detail.
9. **Does it help the financial-analyst workflow?** Yes. It starts from trusted context and exposes one clear action to configure an analysis.
10. **Is it thesis scope that is not necessary?** No. Live workflow and final report remain out of scope for this slice.

## Keep / Refactor / Replace

### KEEP

- React 19, Vite, TypeScript, React Router, TanStack Query.
- React Hook Form, Zod, and existing capability/request services.
- Official shadcn/Radix primitives and Lucide icon family.
- Existing tests and the current analysis request form behavior.
- Current API seams so a future provider can replace mock data without changing the screen contract.

### REFACTOR

- Root routing so `/analysis` is the primary product surface and `/analysis/new` remains a compatibility redirect.
- The shared application shell and navigation so `Phân tích` and `Báo cáo` are the only primary destinations.
- The existing analysis form shell so its behavior and data contracts remain unchanged while the sidebar becomes consistent.

### REPLACE

- `DataPage` as the landing experience. It remains available as legacy/contextual engineering material for now, but is no longer the default product entry point.
- The current Data-first visual hierarchy and its permanent source-management emphasis.
- The separate clean-room `AnalysisHomePage` surface and its duplicated scope summary hierarchy.

## First-screen implementation plan

1. Keep the existing `CreateAnalysisPage` form and its capability-driven request behavior.
2. Wrap the form in the reusable `WorkspaceShell` with the approved two-item navigation.
3. Remove the duplicated `AnalysisHomePage` and route `/analysis` directly to the request form.
4. Keep `/analysis/new` as a redirect to `/analysis` so existing links remain valid.
5. Keep loading, failure, drawer, validation, and submission states from the existing form.
6. Keep source setup contextual and avoid adding a permanent Data nav item or a new connector flow in this slice.

## Approved low-fidelity shape

```text
┌ rail ┐ ┌ existing request form inside shared workspace shell ─────────────┐
│Phân  │ │ Tạo phân tích                                                     │
│tích  │ │ Xây dựng một yêu cầu trong phạm vi dữ liệu đã được xác thực.       │
│Báo   │ │                                                                   │
│cáo   │ │ capability summary                                                │
│      │ │ intent + scope + topics + system context      request summary      │
│user  │ │                                                                   │
└──────┘ └───────────────────────────────────────────────────────────────────┘
```
