# Clean-room frontend product proposal, Stage A

Status: Proposal only. No frontend implementation has been changed.

Branch: `frontend/clean-room-redesign`

Base: `origin/thesis/acceptance-phase-1-2` at `cdd5b713ccc1bf8e3878397edcb19179eb1b9d10`

## Design read

Reading this as: a regulated financial-analysis workspace for Vietnamese financial analysts, with a restrained enterprise and evidence-first language, leaning toward light-only shadcn/ui conventions with compact report surfaces and calm state transitions.

This is a dense product UI, not a marketing page. The anti-slop design rules are applied selectively: clear hierarchy, restrained motion, no decorative AI styling, consistent tokens, and explicit loading, missing, error, and partial states.

## 1. Primary user and job-to-be-done

The primary user is a financial analyst or research associate who needs to turn a validated data snapshot into a defensible company or peer analysis report.

Their job is:

> Chọn đúng phạm vi dữ liệu, đặt một câu hỏi phân tích có thể thực hiện, theo dõi cách hệ thống kiểm tra và tổng hợp bằng chứng, rồi kiểm tra báo cáo trước khi sử dụng.

The product should optimize for confidence and time-to-understanding, not for exposing every implementation detail.

## 2. Recommended information architecture

Use one analysis workspace with contextual data scope, an observable run surface, a report surface, and a report library.

```text
Phân tích
├── Tổng quan phân tích
├── Phân tích mới (contextual flow)
├── Lần chạy đang thực hiện (contextual state)
└── Báo cáo kết quả

Báo cáo
└── Thư viện báo cáo và phiên bản

Contextual surfaces
├── Bộ dữ liệu hiện tại / khả năng sử dụng
├── Thiết lập nguồn dữ liệu
├── Chi tiết bằng chứng
└── Chi tiết lần chạy và kiểm toán
```

The top-level mental model is `Dữ liệu đã xác thực → Câu hỏi → Phân tích → Báo cáo`. Data is a context and trust signal, not the product's main destination.

## 3. Recommended minimal navigation

Primary navigation should contain only:

- `Phân tích`: the start page, analysis-request entry point, active workflow, and most recent result.
- `Báo cáo`: report history and report versions.

The active dataset should be a compact selector in the application header, with a secondary action `Kiểm tra dữ liệu`. Source setup should open from that selector or from an onboarding state, not occupy a permanent primary nav slot.

Do not expose `Dữ liệu`, `Tạo phân tích`, and `Báo cáo` as three equal permanent destinations. `Tạo phân tích` is the primary action inside `Phân tích`; `Dữ liệu` is contextual infrastructure.

## 4. Recommended application shell

- Light mode only, as required by the brief.
- A narrow but readable left rail, approximately 224-240px on desktop, with the product mark, `Phân tích`, `Báo cáo`, and the analyst identity `Phùng Thái Cường`.
- A compact top bar for the active data context: dataset name, readiness state, period range, and `Kiểm tra dữ liệu`.
- A single main canvas with a readable maximum width around 1,280-1,360px. Avoid a full-bleed dashboard wall.
- A right-side sheet or drawer for evidence, quality details, and technical run details. Do not make the evidence panel permanently consume the report canvas.
- Use flat grouped regions and sparse borders before adding cards. A card is reserved for a true decision boundary: active data context, analysis request, workflow status, or report finding.
- One accent color across the product, likely a restrained deep blue. Use semantic green/amber/red only for actual readiness or quality state, not decoration.
- One radius rule: soft but controlled, for example 10-12px panels and 8px controls. No mixed sharp/pill language.

## 5. Recommended screen sequence

1. **Tổng quan phân tích**
   - Active validated dataset context.
   - Data readiness and supported scope.
   - Primary action `Bắt đầu phân tích`.
   - Recent reports and active run if present.

2. **Phân tích mới**
   - A focused request surface, preferably a page or large sheet because it has several structured fields.
   - The user never chooses a scope that the current dataset capability does not support.

3. **Không gian phân tích đang chạy**
   - A control-room layout showing work assignment, data/tool activity summaries, artifacts, review, and targeted revision.

4. **Báo cáo kết quả**
   - Decision-grade summary first, then comparisons, company detail, evidence, quality, and limitations.

5. **Thư viện báo cáo**
   - History of report versions and analysis runs, with enough context to distinguish a new run from a new report version.

Evidence details, source setup, and run trace should remain drawers or secondary views until user intent calls for them.

## 6. Is a dedicated Data screen justified?

Not as a primary destination for the current reference application.

The reference app needs to prove that data is trusted and analyzable. It does not need to become an ETL administration system. A permanent Data page would encourage the product to grow around connectors, mapping tables, and source operations rather than around the analyst's decision journey.

Use a contextual dataset control with these states:

- **Ready**: selected snapshot, supported entities/periods/metrics, and freshness or cutoff information.
- **Partial**: valid scope plus explicit missing or limited capability.
- **Needs setup**: no usable snapshot; guide the user through source setup.
- **Unavailable**: source or capability exists in configuration but is not ready for analysis.

If a later enterprise deployment needs administrative data operations, that can be a separate integration/admin surface. It should not reshape the analyst workspace.

## 7. Dataset and source setup

Use a compact contextual flow:

1. Select an existing validated dataset or choose `Thiết lập nguồn dữ liệu`.
2. Choose a supported source adapter: structured metrics or evidence documents. Show enterprise/API/SQL/CSV/Excel as adapter categories only when the backend actually supports them.
3. Preview recognized scope in business language: companies, periods, metrics, source types, and missingness.
4. Show validation results and source quality before analysis. Never edit raw values in the frontend.
5. Create or select an immutable snapshot for analysis.

The app may own selection, preview, validation status, capability display, and snapshot choice. Enterprise adapters should own credentials, connection details, raw ingestion, schema mapping, licensing, and storage. Those technical details belong behind a provider boundary and should not be copied into the core analysis UX.

For the current thesis slice, a read-only validated snapshot plus source/evidence inspection is sufficient. Any mocked, cached, pending, or incomplete source must carry a visible status and must not look like live validated data.

## 8. Create Analysis interaction model

Treat the structured selections as authoritative. The natural-language objective is a helpful summary, not the source of scope.

Recommended field order:

1. **Mục tiêu phân tích**: short Vietnamese objective, optionally suggested from selections.
2. **Doanh nghiệp mục tiêu**: one or more supported companies.
3. **Kỳ phân tích**: period or ordered period range.
4. **Chỉ tiêu**: NPL, coverage, ROA, ROE, only when the dataset capability supports them.
5. **Nhóm tham chiếu**: frozen peer universe or a supported subset.
6. **Ngữ cảnh bổ sung**: optional question framing, without expanding scope beyond capability.

The request summary should continuously state:

`Phạm vi: [doanh nghiệp] • [kỳ] • [chỉ tiêu] • [nhóm tham chiếu]`

Before submit, show:

- data snapshot and readiness;
- supported versus unavailable capabilities;
- explicit missingness if the selected scope contains it;
- what the analysis will produce;
- the fact that the report is evidence-backed only where the source contract permits it.

The primary action should be `Chạy phân tích`. Avoid a second equal-weighted action that suggests an unsupported alternative path.

## 9. Live multi-agent workflow interaction model

The workflow should feel like a calm analysis control room, not a chat transcript, terminal, or fake AI animation.

Recommended desktop composition:

```text
┌ Request context ┐  ┌ Điều phối phân tích ────────────────┐  ┌ Review ┐
│ scope           │  │ Current task / outcome                │  │ quality │
│ snapshot        │  │ Vĩ mô | Ngành | Doanh nghiệp         │  │ issues  │
│ capabilities   │  │ artifacts and activity summaries      │  │ revise  │
└────────────────┘  └───────────────────────────────────────┘  └────────┘
```

Show:

- the orchestrator assigning work in business language;
- role state: `Chờ xử lý`, `Đang phân tích`, `Đã tạo kết quả`, `Đang kiểm tra`, `Đã hoàn tất`;
- safe tool/data activity summaries such as `Đã đọc số liệu NPL và ROE của phạm vi đã chọn`;
- generated artifacts and structured findings;
- review feedback and why a targeted revision was requested;
- revised output and acceptance/quality status;
- unresolved missingness or anomaly status.

Use a stable timeline or task rail, not a stream of raw events. Real state changes may animate with short transitions; do not fake typing, token streams, or perpetual spinners. A task should move because a backend state changed.

On small screens, stack the request context, current workflow state, artifacts, and review in that order. The role columns become an accessible task list with expandable detail.

## 10. Final Report structure

The report should follow the analysis-report-v2 contract while using business copy:

1. **Report header**
   - title, scope, selected dataset/snapshot, report status, created time;
   - `Phiên bản báo cáo` and `Lần chạy` are distinct concepts. Technical IDs stay in `Chi tiết kỹ thuật`.

2. **Tóm tắt điều hành**
   - three to five high-priority findings;
   - each finding has an evidence/support state and a concise limitation.

3. **So sánh trong nhóm tham chiếu**
   - compact table or matrix for the selected companies, periods, and metrics;
   - missing cells remain visibly missing and show their reason on inspection;
   - no silent recomputation in the UI.

4. **Phân tích theo cấp độ**
   - Vĩ mô, Ngành, Doanh nghiệp. If macro is limited, say `Dữ liệu vĩ mô hiện còn hạn chế` instead of presenting a complete macro narrative.

5. **Điểm cần kiểm tra**
   - deterministic trigger or review item;
   - resolved, explained, or unresolved;
   - focused evidence used for the decision.

6. **Bằng chứng và nguồn**
   - source identity, page/section locator, quote, and data reference;
   - evidence is opened in a drawer so the main report remains readable.

7. **Chất lượng dữ liệu và giới hạn**
   - expected/valid/missing/conflict counts;
   - denominator used for each aggregate;
   - source quality and period/basis limitations;
   - clear partial status where appropriate.

8. **Chi tiết lần chạy**
   - safe task/action/output/review/revision summaries;
   - no hidden reasoning or raw prompt plumbing.

Do not turn claims into investment recommendations unless a separate supported product scope explicitly requires it.

## 11. Report history/library

The library should be a compact table/list with:

- report title and objective;
- target company or peer group;
- period and data snapshot;
- report status: complete, partial, or needs review;
- latest report version;
- last run time;
- actions: `Mở báo cáo`, `Xem bằng chứng`, `Chạy lại`.

Use filters for company, period, status, and snapshot. A report request, a run, and a report version should be distinguishable in detail, but the default library row should stay in analyst language.

## 12. Visible versus hidden

Visible in the main product:

- selected data context and readiness;
- supported scope and capability limits;
- objective, targets, periods, metrics, peer set;
- current workflow phase and safe activity summaries;
- findings, comparisons, evidence support, missingness, conflicts, quality, and limitations;
- revision requests and acceptance status.

Hidden from the primary product:

- chain-of-thought, scratchpads, private reasoning, and system prompts;
- raw prompt payloads and provider plumbing;
- backend event enums, dataset IDs, snapshot IDs, claim IDs, and issue IDs unless requested under technical detail;
- database table names and adapter-specific schema terms;
- architecture A/B/C research controls;
- internal token/cost telemetry except in a secondary run-detail surface where it has user value.

## 13. Design system direction

- Light mode only, neutral surfaces, dark readable type, one restrained blue accent.
- Use shadcn/ui conventions once the project setup is established. `components.json` is not present on the fetched base, so Stage B must decide whether to initialize the official shadcn setup or preserve the project's existing primitives.
- Tailwind v3 is currently installed. Do not migrate to Tailwind v4 or Next.js as part of this redesign.
- Use the existing `lucide-react` icon family only if retained; do not mix icon families. The dependency already exists in `frontend/package.json`.
- Prefer typography with a compact sans stack already available in the app; do not introduce a decorative serif or AI-purple gradient.
- Use a 4px base spacing rhythm, 8px control rhythm, and generous section spacing around primary decisions.
- Use semantic tokens for surface, text, border, accent, success, warning, and danger. Keep status color reserved for actual state.
- Use tabs, comboboxes, sheets, dialogs, tables/data tables, badges, alerts, progress, skeletons, scroll areas, and tooltips only when the interaction requires them.
- Motion dial for this product: `DESIGN_VARIANCE: 3`, `MOTION_INTENSITY: 2`, `VISUAL_DENSITY: 6`. The regulated financial context favors predictable alignment, low motion, and information-dense but breathable surfaces.

## 14. Likely shadcn primitives

Interaction first, component second:

- `Sidebar` for the shell;
- `Button`, `Badge`, `Separator` for navigation and state;
- `Select` or `Combobox` for dataset, company, period, and metric scope;
- `Field`, `Input`, `Textarea`, `Checkbox`, and `RadioGroup` for the request form;
- `Alert`, `Progress`, `Skeleton` for readiness and run states;
- `Sheet` for evidence and run details;
- `Dialog` or `AlertDialog` for destructive or high-consequence actions;
- `Table` or a data-table composition for comparisons and report history;
- `Tabs` for report sections only when the tab labels correspond to genuine analyst tasks;
- `ScrollArea` for artifact/event detail, with a visible fallback on mobile;
- `Tooltip` for dense but non-essential explanations.

Do not add a primitive because it looks useful. Map each component to a user decision or a necessary disclosure.

## 15. First-screen low-fidelity wireframe

First screen: `Phân tích`, with a selected validated dataset and no active run.

```text
┌──────────────────────┬─────────────────────────────────────────────────────────────┐
│ THESIS ANALYSIS      │ Bộ dữ liệu: Gold pilot 2024                 [Sẵn sàng]       │
│                      │ ACB, TCB, VPB • Q1-Q4 2024 • 4 chỉ tiêu   [Kiểm tra dữ liệu] │
│ Phân tích             ├─────────────────────────────────────────────────────────────┤
│ Báo cáo               │                                                             │
│                      │ Phân tích tài chính                                         │
│                      │ Bắt đầu từ phạm vi dữ liệu đã xác thực.                     │
│                      │                                                             │
│                      │ ┌──────────────────────────────┐  ┌─────────────────────┐ │
│                      │ │ Phân tích mới                 │  │ Báo cáo gần đây     │ │
│                      │ │ Chọn doanh nghiệp, kỳ và     │  │ Chưa có báo cáo mới │ │
│                      │ │ chỉ tiêu được hỗ trợ.        │  │ trong bộ dữ liệu này│ │
│                      │ │                              │  │                     │ │
│                      │ │ [Bắt đầu phân tích]          │  │ [Mở thư viện]       │ │
│                      │ └──────────────────────────────┘  └─────────────────────┘ │
│                      │                                                             │
│                      │ Phạm vi có thể sử dụng                                     │
│                      │ ┌────────────┬────────────┬────────────┬─────────────────┐ │
│                      │ │ Doanh       │ Kỳ dữ liệu │ Chỉ tiêu   │ Bằng chứng      │ │
│                      │ │ nghiệp      │ 2024 Q1-Q4 │ NPL...ROE  │ 44 hợp lệ       │ │
│                      │ │ ACB...VPB   │            │            │ 4 ô thiếu       │ │
│                      │ └────────────┴────────────┴────────────┴─────────────────┘ │
│                      │                                                             │
│                      │ Ghi chú dữ liệu: Một số ô thiếu được giữ nguyên và sẽ      │
│                      │ được nêu rõ trong báo cáo.                                 │
│                      │                                                             │
│ Phùng Thái Cường    │                                                              │
└──────────────────────┴─────────────────────────────────────────────────────────────┘
```

The exact issuer list and counts must be capability-driven. The wireframe uses the current pilot truth from canonical project docs as an example; the master brief's five-bank demonstration scope conflicts with those docs and must not be hard-coded until reconciled.

## 16. Disagreement with existing design documentation

No `docs/design.md` exists on the fetched default branch or `thesis/phase-1-7`, so there is no visual document to accept or reject.

The existing `docs/APP-WIREFRAME-NOTE-V1.md` aligns with the evidence-first report direction, especially its cell-level evidence drawer and hidden agent terminology. I would extend it by making data context contextual rather than a permanent top-level screen, and by adding the live workflow as a separate run surface.

The canonical docs describe a three-issuer pilot as the default first baseline while the master brief describes a five-bank demonstration universe. This is a product-truth conflict, not a visual preference. Stage B must use a capability response rather than hard-coded UI logic, and the scope must be reconciled before any screen is presented as live validation.

The binding `docs/ARCHITECTURAL-GUARDRAILS.md` file is absent from both available refs. Architectural pre-flight cannot be marked complete until the authoritative file is restored or its owner explicitly confirms that the current canonical guardrails are elsewhere.

## 17. Top 3 product risks

1. **Capability overclaiming**: a UI that implies five-bank or macro readiness while the accepted Gold snapshot is narrower or partially missing would undermine trust and violate the data contract.
2. **Fake observability**: a workflow that shows raw logs, token animation, or private reasoning would make the thesis differentiator look like a console and violate the observability boundary.
3. **Provenance overload**: showing every technical ID and event field in the primary report could make the report unreadable; hiding evidence too aggressively would make claims indefensible. The right compromise is concise support states with on-demand evidence and run detail.

## 18. Recommended next action

Approval gate: confirm this product direction, especially the two-item primary navigation, contextual dataset setup, the light-only control-room/report shell, and the capability-driven scope rule.

After explicit approval, Stage B should inspect the existing frontend structure and report `KEEP / REFACTOR / REPLACE` for the router, shell, pages, forms, primitives, tests, and global theme before implementation. The first implementation slice should be the `Phân tích` start screen plus the contextual dataset selector and request flow, followed by the running workflow and report surfaces.
