# Part 3: Application Layout, Responsive Grids, and Page Templates

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

