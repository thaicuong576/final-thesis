# Part 7: Motion, Accessibility, and Implementation Contract

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
