# Universal Software Product Design System

> **Status:** Project-wide design guideline  
> **Scope:** All product surfaces, screens, components, states, and responsive behavior  
> **Design direction:** Warm retro developer workbench — tactile, structured, dense, calm, and functional  
> **Primary rule:** Personality belongs around the work. Clarity belongs inside the work.

---

## 1. Purpose

This file defines the visual language and interaction rules for the entire software product. It is intentionally domain-agnostic and should be treated as the default design contract for all new screens and components.

The system should feel:

- **Technical:** built for real work, not decorative browsing.
- **Tactile:** controls look operable and state changes are visible.
- **Warm:** neutral tones are warm rather than cold or clinical.
- **Dense but legible:** information-rich layouts are acceptable when hierarchy is clear.
- **Playful at the edges:** brand character may appear in shell, onboarding, illustrations, empty states, and special moments, but not at the expense of core workflows.
- **Predictable:** common controls behave like familiar desktop/productivity software.

The system should avoid:

- glassmorphism;
- large blurred shadows;
- excessive gradients;
- pill-shaped controls everywhere;
- oversized cards with little information;
- giant marketing typography inside application workflows;
- floating panels without clear hierarchy;
- decorative motion that slows work;
- pure-white / cool-gray SaaS styling as the default aesthetic.

---

# 2. Design Principles

## 2.1 Software should look operable

Users should be able to identify what is clickable, selected, editable, draggable, disabled, or static without guessing.

Interactive affordance must come from one or more of:

- visible border;
- background change;
- underline;
- icon;
- cursor;
- label;
- elevation or tactile bottom edge;
- focus state.

Do not rely on color alone.

## 2.2 Warm, never sterile

Use warm off-whites, beige-grays, charcoal text, and amber/orange accents. Large application surfaces should rarely use pure `#FFFFFF`.

## 2.3 Borders before shadows

Structure should primarily be expressed through:

- 1px borders;
- separators;
- surface changes;
- spacing;
- active indicators.

Use shadows only when physical layering must be communicated.

## 2.4 Compact, not cramped

Information density is encouraged, but every control must retain readable labels, adequate click targets, and predictable spacing.

## 2.5 One accent has one purpose

The primary accent color indicates:

- active state;
- selected state;
- important action;
- current context;
- focus or progress.

Do not use the accent as random decoration.

## 2.6 Personality belongs around work

Brand personality is appropriate in:

- application shell;
- launch surfaces;
- onboarding;
- empty states;
- illustrations;
- decorative system icons;
- celebratory states.

Core working areas such as tables, forms, editors, filters, and dashboards should prioritize clarity over character.

---

# 3. Design Tokens

## 3.1 Color tokens

The following palette is a project baseline. Values may be refined during implementation, but semantic usage should remain stable.

```css
:root {
  /* Canvas */
  --bg-desktop: #d9d0ba;
  --bg-app-shell: #e4e5dd;
  --bg-workspace: #f7f7f6;

  /* Surfaces */
  --surface-primary: #fbfbf8;
  --surface-secondary: #f2f2ec;
  --surface-tertiary: #ecece6;
  --surface-hover: #e8e8e1;
  --surface-selected: #dfdfd7;
  --surface-disabled: #efefe9;

  /* Text */
  --text-primary: #20201e;
  --text-secondary: #62625d;
  --text-tertiary: #85857e;
  --text-disabled: #a6a69f;
  --text-inverse: #f8f8f4;

  /* Borders */
  --border-subtle: #deded7;
  --border-default: #c9c8c0;
  --border-strong: #a3a39f;
  --border-focus: #d88b00;

  /* Accent */
  --accent: #ee9f0d;
  --accent-hover: #dfa000;
  --accent-active: #c98500;
  --accent-soft: #f7e7bd;
  --accent-border: #bc7600;

  /* Semantic */
  --success: #2f9e62;
  --success-soft: #e4f4ea;
  --warning: #cf8500;
  --warning-soft: #fbefcf;
  --danger: #c84b3f;
  --danger-soft: #f8e3e0;
  --info: #2d7fbf;
  --info-soft: #e1edf7;
}
```

## 3.2 Color usage rules

### Primary accent
Use for:

- primary CTA;
- selected top-level tab indicator;
- active item marker;
- focused important control;
- selected icon or high-priority state.

Do not use accent fill on every button.

### Semantic colors
Semantic colors must always communicate meaning, not decoration.

- success = completion, valid, online, healthy;
- warning = attention required;
- danger = destructive, failure, blocked;
- info = neutral information or explanatory state.

Always pair semantic color with icon, text, or structure.

### Contrast
All text and meaningful icons must meet WCAG 2.2 AA contrast targets.

---

# 4. Typography

## 4.1 Font family

Use a friendly grotesk or modern product sans-serif with strong readability.

Recommended stack:

```css
font-family: "Inter", "Geist", "DM Sans", "Helvetica Neue", Arial, sans-serif;
```

If a custom brand font exists, it may replace the primary family only if it remains legible at 12–14px UI sizes.

## 4.2 Type scale

| Role | Size | Weight | Line Height |
|---|---:|---:|---:|
| Display | 32–40px | 700–800 | 1.15 |
| Page title | 24px | 700–800 | 32px |
| Section title | 18px | 700 | 26px |
| Subsection title | 16px | 600–700 | 24px |
| Body | 15px | 400 | 22px |
| UI label | 14px | 500–600 | 20px |
| Button | 14px | 600–700 | 20px |
| Table header | 12–13px | 700 | 18px |
| Metadata | 12–13px | 400–500 | 18px |
| Code / mono | 13px | 400–500 | 20px |

## 4.3 Typography rules

- Default body copy: 15px.
- Dense data UI may use 13–14px where necessary.
- Avoid body text below 12px.
- Do not use ultra-light weights.
- Headings should use subtle negative tracking only when needed.
- Avoid uppercase for normal navigation or body content.
- Uppercase is reserved for concise table labels, statuses, or metadata where useful.
- Use monospace only for identifiers, code, system output, timestamps, or machine-like content.

---

# 5. Spacing System

Use a 4px base unit.

```text
4   8   12   16   20   24   32   40   48   64
```

Recommended usage:

| Purpose | Spacing |
|---|---:|
| Icon ↔ label | 8px |
| Compact controls | 8px |
| Related controls | 8–12px |
| Form field gap | 12–16px |
| Toolbar groups | 12–16px |
| Section gap | 20–24px |
| Page padding | 20–24px |
| Major content break | 32–40px |

Avoid arbitrary one-off spacing values.

---

# 6. Radius, Borders, and Elevation

## 6.1 Corner radius

```css
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 12px;
--radius-pill: 999px;
```

Usage:

- 4px: table cells, compact controls, inline items;
- 6px: buttons, inputs, dropdowns, cards;
- 8px: large panels and dialogs;
- 12px: rare large branded surfaces;
- pill: tags, avatars, small status chips only.

Do not use 16–24px radii as a universal default.

## 6.2 Borders

Default:

```css
border: 1px solid var(--border-default);
```

Use strong borders for:

- active docked panels;
- important boundaries;
- selected editable regions;
- modal separation when needed.

## 6.3 Elevation

Prefer border hierarchy over shadows.

Allowed shadow styles:

```css
/* Tactile button */
box-shadow: 0 2px 0 rgba(98, 63, 0, 0.55);

/* Floating panel */
box-shadow: 0 8px 24px rgba(20, 20, 18, 0.10);
```

Avoid high-blur, high-opacity shadows on ordinary cards.

---

# 7. Iconography

## 7.1 Product icons

Use:

- 16–20px icons;
- 1.5–2px stroke;
- simple outline style;
- consistent stroke geometry;
- minimal decorative detail.

Icons should clarify labels, not replace understandable text where ambiguity exists.

## 7.2 Brand icons

Larger decorative icons may be:

- 32–48px;
- multi-color;
- illustrative;
- retro-computing inspired;
- slightly playful.

Do not mix decorative icons into dense control rows.

---

# 8. Motion

Motion must be fast, subtle, and functional.

Recommended durations:

```text
hover          100–150ms
press           60–100ms
popover        120–180ms
panel          180–220ms
page transition 180–240ms
```

Recommended easing:

```css
cubic-bezier(.2,.8,.2,1)
```

Use motion for:

- state transition;
- panel entrance/exit;
- reordering feedback;
- expand/collapse;
- loading progress;
- selection change.

Avoid:

- bouncing controls;
- large spring animations;
- parallax inside working UI;
- unnecessary scale effects;
- long animated backgrounds.

Respect `prefers-reduced-motion`.

---

# 9. Focus and Keyboard Interaction

All interactive elements must have a visible focus state.

Recommended:

```css
outline: 2px solid var(--border-focus);
outline-offset: 2px;
```

Keyboard rules:

- Tab / Shift+Tab moves through interactive elements.
- Enter activates primary action.
- Space toggles checkboxes, switches, and button-like controls.
- Escape closes transient overlays.
- Arrow keys navigate menus, listboxes, tabs, and segmented controls where appropriate.
- Focus must return to the trigger when a modal, popover, or menu closes.

Do not remove outlines without providing an equivalent focus treatment.

---

# 10. Application Layout

## 10.1 Recommended shell

Complex applications may use up to four zones:

```text
┌──────────────┬───────────────┬──────────────────────────┬─────┐
│ Global nav   │ Context nav   │ Main workspace           │Rail │
│              │               │                          │     │
└──────────────┴───────────────┴──────────────────────────┴─────┘
```

### Global navigation
Answers: “Which major area am I in?”

### Context navigation
Answers: “Which object or section inside this area am I working with?”

### Main workspace
Contains the actual task, data, form, editor, or report.

### Utility rail
Optional. Use for secondary tools, help, notes, metadata, history, or contextual assistants.

## 10.2 Layout widths

Desktop guidelines:

- global nav: 220–280px;
- context nav: 240–320px;
- utility rail: 48–64px collapsed;
- content min width: 640px;
- content max width: flexible for data-heavy pages.

Do not constrain data-heavy workspaces to narrow marketing-style max widths.

## 10.3 Sticky areas

Appropriate sticky regions:

- app header;
- table header;
- filter bar;
- primary action bar;
- left navigation;
- contextual inspector header.

Avoid stacking too many sticky rows; keep visible content area usable.

---

# 11. Responsive Behavior

Recommended breakpoints:

```text
< 640px      mobile
640–1023px   tablet / narrow desktop
1024–1439px  desktop
>= 1440px    wide desktop
```

## 11.1 Narrow desktop

- context nav may collapse into drawer;
- utility rail may collapse into icon rail;
- table may allow horizontal scrolling;
- toolbars may wrap into an overflow menu.

## 11.2 Mobile

Mobile is not a scaled-down desktop.

Use:

- one primary column;
- drawers for secondary navigation;
- fixed bottom or top action region only when necessary;
- compact cards for previously tabular data;
- full-screen dialogs for complex pickers.

Preserve touch target size of at least 44×44px for primary touch interactions.

---

# 12. Component Guidelines

# 12.1 Buttons

## Variants

### Primary
Use for the single most important action in a local context.

Style:

- accent fill;
- dark text unless contrast requires inverse;
- visible border;
- optional 1–2px tactile bottom edge;
- 6–8px radius;
- bold label.

### Secondary
Use for important alternate actions.

Style:

- warm off-white fill;
- default border;
- dark text.

### Tertiary / Ghost
Use for low-priority actions.

Style:

- transparent or subtle fill;
- visible hover state;
- no tactile shadow.

### Destructive
Use only for destructive or irreversible actions.

Style:

- danger border or fill;
- explicit destructive label;
- confirmation when consequences are significant.

### Icon button
Use for familiar compact actions.

Requirements:

- 32–40px visual size;
- tooltip when label is not visible;
- `aria-label`;
- clear hover and focus state.

### Split button
Use only when primary action and alternate variants are tightly related.

Do not use for unrelated actions.

## Button sizing

```text
Small   30–32px
Medium  36–40px
Large   42–44px
```

Default application button: 36–40px.

## Button content

Prefer:

```text
Verb + object
```

Examples:

- Create item
- Save changes
- Add filter
- Export data
- Retry

Avoid vague labels such as “Continue” when the resulting action is not obvious.

---

# 12.2 Text Inputs

Default style:

- 36–40px high;
- 6px radius;
- 1px border;
- warm surface;
- dark text;
- placeholder uses tertiary text.

States:

- default;
- hover;
- focus;
- invalid;
- disabled;
- read-only.

Labels should appear above the field unless the surrounding structure already provides an unambiguous accessible name.

Do not rely on placeholder text as the only label.

---

# 12.3 Textarea

Use for multi-line content.

Guidelines:

- minimum height 96px;
- resize vertically by default;
- same border/radius as text input;
- show character limit only when a real constraint exists;
- preserve input on recoverable errors.

---

# 12.4 Search Input

Search is a specialized text input.

Include:

- search icon;
- clear button when content exists;
- optional keyboard shortcut hint;
- visible loading state for remote search.

Search should not execute destructive or state-changing actions.

---

# 12.5 Select

Use when:

- one value must be selected from a known option set;
- free text is not allowed.

Prefer native/select-like behavior for small option lists.

Use combobox instead when options are numerous or searchable.

---

# 12.6 Combobox

Use for searchable selection.

Requirements:

- typed filtering;
- keyboard navigation;
- active option highlight;
- clear empty state;
- support for long labels;
- virtualized list if option count is large.

Do not fake a combobox with an inaccessible custom dropdown.

---

# 12.7 Checkbox

Use for independent binary choices or multi-select lists.

States:

- unchecked;
- checked;
- indeterminate;
- disabled.

Label must be clickable.

Use indeterminate state for partial parent selections in trees.

---

# 12.8 Radio Group

Use when exactly one of several visible options must be chosen.

Prefer radio buttons over select when:

- there are 2–5 choices;
- choices benefit from immediate comparison.

---

# 12.9 Switch

Use for settings that take effect immediately.

Good examples:

- enable/disable feature;
- show/hide persistent behavior;
- turn a mode on/off.

Do not use switches for actions requiring an explicit Save step unless the UI clearly communicates deferred application.

---

# 12.10 Segmented Control

Use for 2–4 mutually exclusive lightweight modes.

Style:

- rectangular group;
- subtle selected background;
- 4–6px radius;
- no giant pills;
- equal sizing only when labels are similar in length.

Do not use for deep navigation.

---

# 12.11 Tabs

Use tabs for sibling views within the same context.

Primary tab style:

- plain text label;
- selected text may use accent;
- 2px accent underline;
- no filled pill background by default.

Tabs should not be used for unrelated actions.

If more than 6–8 tabs are needed, consider context navigation or overflow.

---

# 12.12 Breadcrumbs

Use when users navigate a meaningful hierarchy deeper than two levels.

Guidelines:

- concise labels;
- final item is current page and non-interactive;
- collapse middle items on narrow screens;
- avoid breadcrumbs when hierarchy is already obvious from persistent navigation.

---

# 12.13 Pagination

Use when full dataset loading is expensive or navigation by page is meaningful.

Support:

- previous / next;
- current page;
- total count when known;
- page size when useful.

For continuously scanned feeds, prefer infinite loading with clear boundaries and state recovery.

---

# 12.14 Tags and Chips

Use for compact labels, filters, or removable selections.

Rules:

- pill shape is allowed here;
- keep text concise;
- semantic tags use semantic colors sparingly;
- removable chips require visible remove action;
- do not make every metadata label a chip.

---

# 12.15 Badges

Use for short statuses or counts.

Examples:

- New
- Draft
- 12
- Offline

Badges must not carry long sentences.

---

# 12.16 Tooltips

Use for:

- icon-only controls;
- unfamiliar terminology;
- shortened text when full value matters.

Do not put essential instructions only in a tooltip.

Delay: approximately 300–500ms on hover.

Tooltips must also work with keyboard focus.

---

# 12.17 Dropdown Menu

Use for compact action lists.

Guidelines:

- group related actions;
- use separators sparingly;
- destructive action visually separated;
- keyboard navigable;
- close on selection or Escape;
- keep labels as verbs when actions are performed.

Do not hide frequently used primary actions inside menus.

---

# 12.18 Context Menu

Use only where right-click / secondary click behavior is expected and discoverable.

Every essential action must have another accessible path.

---

# 12.19 Popover

Use for transient contextual controls that should stay near their trigger.

Examples:

- filter configuration;
- date selection;
- formatting controls;
- small settings.

Do not use for long multi-step forms.

---

# 12.20 Modal Dialog

Use for:

- decisions requiring full attention;
- short forms;
- confirmations;
- blocking workflows.

Guidelines:

- 480–720px typical width;
- 8px radius;
- clear title;
- body text before actions;
- primary action on the right in LTR interfaces;
- destructive action clearly labeled;
- Escape closes only when safe;
- trap focus inside dialog;
- restore focus to trigger on close.

Avoid modal-on-modal flows.

---

# 12.21 Drawer / Side Panel

Use for contextual detail or editing while preserving the underlying page.

Widths:

- compact: 320–400px;
- standard: 420–560px;
- wide: up to 720px.

Use full-screen drawer on narrow devices.

---

# 12.22 Alert / Banner

Use for page-level messages.

Variants:

- info;
- success;
- warning;
- danger.

Structure:

```text
[icon] Title
       explanation
       optional action
```

Avoid persistent banners for low-priority information.

---

# 12.23 Toast

Use for short confirmation or recoverable background errors.

Guidelines:

- visible for 4–8 seconds depending on importance;
- allow manual dismissal;
- include Undo when appropriate;
- do not rely on toast for critical information users must read.

---

# 12.24 Cards

Cards are not the default layout primitive.

Use a card only when content is meaningfully grouped and benefits from a visible boundary.

Default card:

- surface primary;
- 1px border;
- 6–8px radius;
- little or no shadow;
- 16–20px padding.

Avoid dashboards made of dozens of oversized floating cards.

---

# 12.25 Panels

Use panels for persistent working regions.

Examples:

- editor panel;
- inspector;
- navigation pane;
- side details.

Panels should use borders and resizable splitters where appropriate.

---

# 12.26 Window / Workbench Surface

A window metaphor may be used on branded or special surfaces.

Structure:

```text
Window
├─ Title bar
├─ Optional toolbar
└─ Content
```

Title bar may contain:

- icon;
- title;
- path/status;
- window controls.

Do not force window chrome onto every application page.

---

# 12.27 Toolbar

Use for groups of actions associated with a workspace.

Rules:

- left side: context / navigation / primary work actions;
- right side: secondary actions / overflow;
- group related controls with 8–12px gaps;
- use separators only between logical groups;
- collapse low-frequency actions into overflow on narrow widths.

---

# 12.28 Filter Bar

Recommended structure:

```text
[Search] [Filter] [Filter] [Add filter]            [Save view]
```

Rules:

- filters should show current value;
- removable filters need clear remove action;
- reset must be obvious when many filters are active;
- advanced filters may open popover or side panel;
- applied filter state must remain visible after refresh/navigation when persistence is expected.

---

# 12.29 Table

Tables are preferred for dense structured data.

Default style:

- warm white/off-white surface;
- 1px outer border;
- horizontal row separators;
- minimal zebra striping;
- compact but readable row height;
- strong header labels;
- no card-per-row treatment.

Recommended dimensions:

```text
Header height  36–40px
Row height     40–48px
Cell padding   10–14px vertical, 12–20px horizontal
```

Features when appropriate:

- sortable columns;
- sticky header;
- resizable columns;
- column visibility control;
- row selection;
- bulk action bar;
- inline editing;
- virtualization;
- horizontal scroll.

Rules:

- right-align numeric values;
- left-align text;
- keep units in headers or values consistently;
- avoid truncation when the full value is critical;
- use tooltip or expandable cell for unavoidable truncation;
- show empty state inside table body, not as an unrelated full-page error.

---

# 12.30 List

Use lists when items are less structured than table rows.

Each item may contain:

- primary label;
- secondary metadata;
- leading icon/avatar;
- trailing actions.

Hover may reveal low-priority actions.

Avoid hidden actions if users must discover them frequently.

---

# 12.31 Tree View

Use for hierarchical data.

Support:

- expand/collapse;
- clear indentation;
- keyboard navigation;
- parent/child selection rules;
- indeterminate checkboxes for partial selection;
- preserved expansion state when appropriate.

Do not use excessive connector lines unless hierarchy is otherwise unclear.

---

# 12.32 Accordion

Use to collapse secondary content within a page.

Guidelines:

- section title remains visible;
- chevron indicates state;
- multiple sections may remain open unless the workflow requires exclusivity;
- do not hide critical primary actions inside collapsed areas.

---

# 12.33 Form Layout

Default:

- one-column form for most settings;
- two-column form only for tightly related short fields;
- labels above inputs;
- helper text directly below field;
- validation close to the error source;
- form-level error summary when multiple fields fail.

Action area:

- primary action first in emphasis, not necessarily first in visual order;
- secondary action visible;
- sticky footer only for long forms where it improves usability.

---

# 12.34 Date and Time Picker

Use a date picker when visual calendar selection improves accuracy.

Use text entry when expert users benefit from speed.

Support:

- keyboard entry;
- locale-aware display;
- clear time zone where ambiguity matters;
- start/end validation for ranges;
- presets only when genuinely useful.

---

# 12.35 File Upload

Support:

- click to browse;
- drag and drop when appropriate;
- file type and size constraints before upload;
- progress indicator;
- retry on failure;
- remove/replace before final submission.

Do not make drag-and-drop the only path.

---

# 12.36 Empty State

Use when a region has no content.

Structure:

1. concise title;
2. short explanation;
3. primary next action;
4. optional illustration.

Do not use jokes that obscure what the user should do next.

---

# 12.37 Loading State

Use the least disruptive loading treatment possible.

Preferred order:

1. preserve existing data during refresh;
2. inline progress for local operation;
3. skeleton for first content load;
4. spinner only for compact uncertain-duration actions.

Avoid replacing whole screens with spinners when partial content is already available.

---

# 12.38 Skeleton

Skeletons should mirror actual layout.

Rules:

- no excessive animation;
- use subtle pulse;
- preserve final component height;
- do not show skeleton for very fast operations where it causes flicker.

---

# 12.39 Progress Indicators

Use determinate progress when percentage is known.

Use indeterminate progress when duration is unknown.

For long operations, provide:

- current step;
- estimated progress when reliable;
- cancel option when safe;
- background continuation where possible.

---

# 12.40 Command Palette

Use for keyboard-heavy applications with many commands.

Requirements:

- global shortcut;
- fuzzy search;
- grouped results;
- keyboard navigation;
- recent items when useful;
- clear command labels and optional shortcut hints.

Command palettes supplement navigation; they do not replace discoverable UI.

---

# 12.41 Code / Technical Content

Use monospace font for:

- code;
- identifiers;
- paths;
- logs;
- raw structured data.

Code blocks should support:

- horizontal scrolling;
- copy action;
- syntax highlighting when appropriate;
- line numbers only when useful.

Avoid decorative terminal styling for ordinary prose.

---

# 12.42 Avatars

Use avatars for people, teams, or identifiable entities where visual identification helps.

Sizes:

```text
XS 20px
S  24px
M  32px
L  40px
XL 56px
```

Fallback should use initials or a deterministic icon, not a broken image.

---

# 12.43 Status Indicator

Status should combine at least two of:

- icon;
- color;
- label;
- position;
- shape.

Do not communicate status through color alone.

---

# 13. Navigation Patterns

## 13.1 Global sidebar

Use for persistent primary product areas.

Rules:

- icon + text;
- selected state uses subtle warm fill;
- avoid large colored blocks;
- group related sections;
- optional compact mode on smaller screens.

## 13.2 Secondary sidebar

Use when a domain contains many related objects or pages.

Rules:

- smaller visual weight than global nav;
- section labels may use muted bold text;
- selected item uses soft neutral fill;
- preserve current group context.

## 13.3 Top tabs

Use for sibling views of the same object or workspace.

Selected state uses accent underline, not a filled pill.

## 13.4 Utility rail

Optional right-side rail for secondary tools.

Appropriate content:

- help;
- notes;
- activity;
- history;
- comments;
- contextual metadata;
- auxiliary utilities.

Keep rail visually narrow and distinct from main navigation.

---

# 14. Page Templates

# 14.1 Standard Data Page

```text
Page tabs / context
────────────────────────────────
Page title                  Primary action
Description
────────────────────────────────
Search / filters / saved view
────────────────────────────────
Toolbar / bulk actions
────────────────────────────────
Table or list
```

Use this template for collection-style pages.

---

# 14.2 Detail Page

```text
Breadcrumb / back
Title + status              Actions
Metadata
────────────────────────────────
Tabs
────────────────────────────────
Main content     | Optional inspector
```

Use for a single entity or record.

---

# 14.3 Master–Detail Page

```text
List / table      | Detail panel
                  |
                  |
```

Use when users need to scan items and inspect details quickly without navigating away.

---

# 14.4 Dashboard

A dashboard should answer a small number of meaningful questions.

Recommended order:

1. critical summary;
2. trends;
3. breakdowns;
4. details;
5. exceptions.

Avoid:

- card grids where every metric gets equal weight;
- decorative charts with no decision value;
- more than 3–5 competing accent colors;
- unnecessary 3D effects.

---

# 14.5 Settings Page

Use:

- secondary navigation or anchored sections;
- strong section headings;
- explanatory copy only where needed;
- clear save behavior;
- destructive settings separated from general settings.

Prefer immediate-save only when state changes are low-risk and reversible.

---

# 14.6 Onboarding

Onboarding should explain only what is required to reach first value.

Use:

- 3–7 steps max for guided sequences;
- progress indicator;
- skip when safe;
- visible completion state;
- contextual education later instead of front-loading everything.

Brand illustration may be stronger here than in core workflow screens.

---

# 14.7 Error Page

Structure:

- what happened;
- whether work is safe;
- what the user can do now;
- recovery action;
- technical details behind disclosure if useful.

Avoid generic “Something went wrong” with no recovery path.

---

# 14.8 Permission / Access Page

Clearly state:

- what is inaccessible;
- why, if appropriate;
- who or what can grant access;
- next action.

Do not make permission errors look like missing data.

---

# 15. Data Visualization

## 15.1 General principles

Charts must answer a question, not decorate a page.

Use semantic color sparingly.

Default chart palette should prioritize:

1. neutral series;
2. accent for the primary series;
3. secondary distinct hues only when multiple series are necessary.

## 15.2 Line chart

Use for continuous trends over ordered dimensions such as time.

Avoid more than 5–7 visible series by default.

## 15.3 Bar chart

Use for category comparisons.

Sort categories meaningfully unless natural order exists.

## 15.4 Area chart

Use only when cumulative magnitude or volume is meaningful.

Do not use stacked area charts for precise comparison.

## 15.5 Pie / donut chart

Use sparingly, ideally for 2–5 categories where part-to-whole is the primary question.

Prefer bars when precise comparison matters.

## 15.6 Scatter plot

Use to show relationship between two quantitative variables.

Include readable axis labels and tooltip values.

## 15.7 Tooltips

Chart tooltips should show:

- category/time;
- exact value;
- unit;
- comparison context where useful.

## 15.8 Axes

- start quantitative bar charts at zero unless there is a strong reason not to;
- use compact number formatting;
- retain accessible full values in tooltip or table;
- avoid unnecessary gridlines.

## 15.9 Accessibility

Provide data table or equivalent textual access for important charts.

Do not rely on red/green distinction alone.

---

# 16. Content and Microcopy

## 16.1 Tone

Product copy should be:

- direct;
- concise;
- calm;
- specific;
- non-marketing inside workflows.

Prefer:

- Create project
- Save changes
- Retry upload
- No results found

Avoid:

- vague motivational copy;
- hype-heavy language;
- excessive exclamation marks;
- jokes in error states where users may be blocked.

## 16.2 Error messages

Good error messages contain:

1. what failed;
2. why, if known;
3. what the user can do.

Example pattern:

```text
Upload failed. The file is larger than the 20 MB limit. Choose a smaller file and try again.
```

## 16.3 Labels

Prefer nouns for destinations and verbs for actions.

Examples:

- `Settings` = destination;
- `Save settings` = action.

---

# 17. Accessibility Baseline

Target WCAG 2.2 AA.

Minimum requirements:

- keyboard accessible;
- visible focus indicators;
- semantic HTML;
- proper labels and descriptions;
- sufficient color contrast;
- no color-only meaning;
- text zoom to 200% without loss of content;
- reduced motion support;
- screen-reader-friendly status updates;
- accessible error messages;
- logical heading hierarchy;
- touch targets approximately 44×44px on touch-first surfaces;
- skip links for complex persistent navigation where appropriate.

---

# 18. Empty, Error, Loading, and Disabled States

Every component must define at least these states when relevant:

```text
Default
Hover
Focus
Active
Selected
Disabled
Loading
Empty
Error
Success
Read-only
```

Do not ship a component without considering its non-happy-path states.

Disabled controls should explain why when the reason is not obvious.

Read-only content should look available but non-editable, not broken.

---

# 19. Density Modes

The product may support three density modes if needed:

## Comfortable
- larger row heights;
- 16px body text;
- larger spacing.

## Default
- balanced density;
- 14–15px body/UI text;
- 40–48px rows.

## Compact
- for expert workflows;
- 13–14px UI text;
- 32–40px rows;
- tighter spacing.

Compact mode must not reduce accessibility below acceptable thresholds.

---

# 20. Drag and Drop

Use drag and drop only when spatial movement is meaningful.

Requirements:

- visible drag handle when discoverability matters;
- drop target highlight;
- keyboard alternative;
- cancel path;
- undo when practical;
- do not start drag accidentally from ordinary click targets.

---

# 21. Resizable Panels

For workbench layouts, panel resizing is allowed.

Requirements:

- clear divider / handle;
- minimum and maximum widths;
- double-click reset optional;
- persisted preference when useful;
- keyboard-accessible resize alternative where feasible.

---

# 22. Inline Editing

Use inline editing when users repeatedly make small edits in context.

Rules:

- edited field gets obvious border/focus;
- Save/Cancel behavior must be clear;
- autosave only when safe and visible;
- show error locally;
- preserve original value until save succeeds when failure is possible.

---

# 23. Bulk Actions

When multiple rows/items are selected:

- show selection count;
- reveal contextual bulk toolbar;
- keep destructive actions visually separated;
- support clear selection;
- confirmation required only for high-impact actions.

Do not leave bulk actions visible when nothing is selected unless they also work globally.

---

# 24. Search, Filter, and Sort Patterns

## Search
Use for free-text discovery.

## Filter
Use for structured constraints.

## Sort
Use for ordering.

Do not combine all three concepts into one ambiguous control.

Saved views may store:

- filters;
- sort;
- visible columns;
- grouping;
- density;
- layout preferences.

Saved views should clearly indicate whether changes are temporary or persisted.

---

# 25. Confirmation Rules

Require confirmation when an action is:

- destructive;
- irreversible;
- affects many records;
- changes permissions;
- publishes externally;
- has financial or legal consequence.

Do not ask for confirmation for every harmless action.

Prefer Undo over confirmation for low-risk reversible actions.

---

# 26. Notifications and Activity

Persistent activity feeds should separate:

- system event;
- user action;
- failure;
- warning;
- comment/message.

Each event should include:

- actor or source;
- action;
- object;
- time;
- optional details.

Use relative time for recent events and exact timestamp on hover or detail.

---

# 27. Theming

## Light theme
The warm neutral palette above is the canonical visual direction.

## Dark theme
If supported, dark mode should preserve warmth.

Avoid pure black.

Suggested direction:

```css
--dark-bg: #1f1f1c;
--dark-surface: #272723;
--dark-surface-raised: #30302b;
--dark-border: #44443e;
--dark-text: #f0f0e8;
--dark-text-secondary: #b8b8ae;
```

Accent should remain recognizable but may need luminance adjustment.

---

# 28. Brand Layer vs Product Layer

## Brand layer
Can include:

- retro desktop metaphors;
- textured backgrounds;
- hand-drawn illustrations;
- larger decorative icons;
- playful window chrome;
- stronger visual storytelling.

## Product layer
Should favor:

- flat warm surfaces;
- thin borders;
- compact navigation;
- predictable controls;
- dense tables/forms;
- minimal decoration.

The two layers must share:

- typography;
- token system;
- accent color;
- border language;
- corner radius;
- icon principles;
- tactile interaction style.

---

# 29. Visual Do / Don’t

| Do | Don’t |
|---|---|
| Use warm off-white surfaces | Default everything to pure white |
| Use 1px borders | Use large blurred shadows everywhere |
| Use 4–8px radii | Use 20px+ radii globally |
| Keep primary actions obvious | Make every button accent-filled |
| Keep workspaces dense and structured | Turn every data group into floating cards |
| Use simple outline product icons | Mix decorative icons into toolbars |
| Use accent for state/action | Use accent randomly as decoration |
| Use fast subtle motion | Use bouncing/spring animations for routine UI |
| Use tabs/rectangular controls | Use pills for all navigation |
| Keep empty states helpful | Make empty states purely decorative |

---

# 30. Implementation Contract

All UI implementations should follow these rules unless a documented exception exists.

## MUST

- use semantic design tokens rather than hard-coded colors where practical;
- use 4px spacing grid;
- use visible focus states;
- define hover/focus/disabled/loading/error states;
- meet WCAG 2.2 AA for core interactions;
- use borders before shadows;
- reserve primary accent for meaningful interaction/state;
- keep application typography compact and readable;
- avoid oversized border radii;
- preserve responsive usability.

## SHOULD

- use platform-native behavior where it improves accessibility;
- use tables for dense structured data;
- use side panels for contextual editing;
- use saved views for repeated data configurations;
- use progressive disclosure for complex controls;
- keep primary action count low;
- keep page hierarchy visually explicit.

## SHOULD NOT

- introduce one-off visual styles without token support;
- add gradients without a brand-specific reason;
- use floating cards as the default layout;
- hide high-frequency actions in overflow menus;
- use icon-only controls without tooltips/accessibility labels;
- use modal dialogs for every edit flow;
- make destructive actions visually similar to neutral actions.

---

# 31. Component Review Checklist

Before shipping any new component, verify:

- What is the primary use case?
- What is its semantic role?
- Is there already an existing component that solves this?
- Does it use project tokens?
- Does it follow spacing/radius/border rules?
- Are hover, focus, active, disabled, loading, error, and empty states defined?
- Is keyboard navigation correct?
- Is screen-reader labeling correct?
- Does it work at narrow widths?
- Does it still work with long labels and localized text?
- Does it preserve data during recoverable errors?
- Is the primary action visually obvious?
- Is accent usage justified?
- Is a border enough, or is elevation truly required?
- Is the component visually consistent with surrounding density?

---

# 32. Page Review Checklist

Before shipping any new page, verify:

- The user can identify the page context immediately.
- Primary action is clear.
- Navigation state is obvious.
- Search/filter/sort are separated conceptually.
- Empty/loading/error states are implemented.
- Long content and long labels are supported.
- No important action depends only on hover.
- Responsive behavior is defined.
- Keyboard path is complete.
- Accent color is not overused.
- Information hierarchy is clear before decoration.
- Content can be scanned without reading every line.
- High-density regions remain readable.
- Destructive actions are separated and explicit.

---

# 33. Default CSS Primitive Example

```css
:root {
  --bg-workspace: #f7f7f6;
  --surface-primary: #fbfbf8;
  --surface-secondary: #f2f2ec;
  --surface-hover: #e8e8e1;
  --surface-selected: #dfdfd7;

  --text-primary: #20201e;
  --text-secondary: #62625d;
  --text-tertiary: #85857e;

  --border-subtle: #deded7;
  --border-default: #c9c8c0;
  --border-strong: #a3a39f;

  --accent: #ee9f0d;
  --accent-hover: #dfa000;
  --accent-active: #c98500;

  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
}

body {
  color: var(--text-primary);
  background: var(--bg-workspace);
  font-family: Inter, Geist, "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.47;
}

.ui-surface {
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.ui-control {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface-primary);
  color: var(--text-primary);
}

.ui-control:hover {
  background: var(--surface-hover);
}

.ui-control:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.ui-button-primary {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-md);
  background: var(--accent);
  color: var(--text-primary);
  font-weight: 700;
  box-shadow: 0 2px 0 rgba(98, 63, 0, 0.55);
}

.ui-button-primary:hover {
  background: var(--accent-hover);
}

.ui-button-primary:active {
  transform: translateY(1px);
  box-shadow: 0 1px 0 rgba(98, 63, 0, 0.55);
}
```

---

# 34. Final Design Direction

The product should feel like a **warm, modern software workbench with subtle retro-computing character**.

The final experience should be:

- visually memorable without being distracting;
- dense without being cluttered;
- playful without becoming toy-like;
- technical without becoming cold;
- modern without looking like generic SaaS;
- highly usable for repeated daily work.

When design choices conflict, use this priority order:

```text
1. Comprehension
2. Task efficiency
3. Accessibility
4. Consistency
5. Brand character
6. Decoration
```

If a visual flourish reduces clarity, speed, or accessibility, remove the flourish.
