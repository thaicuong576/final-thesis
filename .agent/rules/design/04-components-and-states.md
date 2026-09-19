# Part 4: Component Guidelines and State System

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

