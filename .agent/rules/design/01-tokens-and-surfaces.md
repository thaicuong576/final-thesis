# Part 1: Design Tokens, Spacing, and Surfaces

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

