# Part 6: Interactions, Behaviors, and Workflows

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

