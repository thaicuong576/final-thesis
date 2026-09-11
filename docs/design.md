# Product UI identity

The thesis reference application is a financial analyst workspace. It helps
analysts understand which validated data is available, define an analysis
request, observe the business-level workflow, and produce a defensible report.

It is not:

- a chatbot;
- a consumer fintech app;
- a futuristic AI interface;
- a research dashboard; or
- a developer console.

The primary qualities are enterprise, financial, compact, trustworthy,
restrained, information-dense, and professional.

## Design system

The application uses official shadcn/ui primitives where an appropriate
component exists. The project is configured for the Radix-based shadcn
component set, with Lucide as the icon library and a project-local `cn`
utility at `frontend/src/lib/utils.ts`.

The current MVP is light mode only. Its visual language is:

- white and near-white backgrounds;
- neutral gray surfaces and borders;
- dark neutral typography;
- a restrained blue primary accent;
- green for valid or ready states;
- amber for warnings and limited capability;
- red only for destructive or error states;
- subtle radius and very limited shadows; and
- no gradients, glow, or glassmorphism.

The semantic shadcn tokens live in `frontend/src/styles/index.css` and are
exposed through the Tailwind theme. Existing product tokens such as `ink`,
`canvas`, `muted`, `line`, `ready`, `warning`, and `blocked` remain available
so the current screens are not redesigned by this setup task.

## Component usage

Prefer the standard shadcn primitives:

Sidebar, Button, Badge, Sheet, Dialog, AlertDialog, Table/Data Table, Input,
Textarea, Field, Select, Combobox, Checkbox, Radio Group, Toggle Group,
Separator, Tooltip, Popover, Dropdown Menu, Progress, Skeleton, Scroll Area,
Alert, and Card.

Use Card selectively. Do not wrap every piece of content in a Card when
typography, spacing, separators, lists, tables, or panels communicate the
hierarchy more clearly.

## Interaction conventions

- Use `Sheet` for contextual workflows and details that preserve page context.
- Use `Dialog` for short focused tasks or confirmations.
- Use `AlertDialog` for destructive or consequential confirmation.
- Use `Table` or `DataTable` for structured collections.
- Use `Badge` for statuses.
- Use `Alert` for warnings or important contextual information.
- Use `Tooltip` for secondary explanations.
- Use `Skeleton` for loading states.

Do not introduce tabs unless they materially reduce complexity.

## Layout

The shell is desktop-first: a minimal left sidebar and a main workspace.
Primary navigation remains limited to:

- Phân tích
- Báo cáo

The active dataset and source setup are contextual to the analysis workspace.
Do not add a permanent Data navigation item by default. Do not add technical
navigation such as Agents, Audit, Architecture, Experiments, or Runs without
explicit product approval.

## Typography

Use strong hierarchy without oversized headings. Financial workspace density is
preferred over landing-page spacing:

- page titles are clear and restrained;
- section headings are compact; and
- supporting copy is short and muted.

The existing IBM Plex Sans and Source Serif 4 pairing remains the visual voice
of the reference prototype.

## Status

Never communicate state with color alone. Combine text with an icon or other
clear label. Examples include `✓ Sẵn sàng`, `✓ Đã xác thực`, `△ Hạn chế`, and
`! Cần kiểm tra`.

## Language

All product-facing copy is Vietnamese. Avoid exposing backend terminology such
as `dataset_id`, `snapshot_id`, `Observation`, `DataProvider`, `CritiqueIssue`,
event enum names, or architecture A/B/C. Translate system concepts into
business language.

## AI presentation

The multi-agent system may be visible when relevant, especially in the Live
Analysis Workspace, but hidden chain-of-thought, scratchpads, system prompts,
and raw internal model reasoning must not appear in the product UI.

Allowed business-level vocabulary includes task, tool activity, result,
artifact, review, revision, and status.

## Accessibility

Use semantic HTML and shadcn/Radix accessibility conventions. Interactive
controls must remain keyboard usable, status must not rely on color alone, and
text and focus states must maintain adequate contrast.

## Component acquisition rule

Before manually implementing a generic UI primitive:

1. Check whether shadcn/ui already provides it.
2. Search the official shadcn registry through the configured MCP server.
3. Inspect the actual source and examples.
4. Install or reuse the official component where appropriate.
5. Customize composition and product styling rather than recreating the
   primitive.

Future frontend agents should use `shadcn:get_project_registries`,
`shadcn:search_items_in_registries`, `shadcn:view_items_in_registries`,
`shadcn:get_item_examples_from_registries`, and
`shadcn:get_audit_checklist` before adding generic components.

## Scope

This document governs the reference application UI only. It establishes the
frontend foundation and does not redesign any product screen. Research and
evaluation interfaces may use separate layouts where necessary.
