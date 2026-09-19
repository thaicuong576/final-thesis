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

## 2.7 Domain Alignment & Multi-Agent Boundaries

- **Language**: All user-facing product copy is Vietnamese.
- **Reasoning Boundaries**: No raw internal chain-of-thought, scratchpads, or system prompt leaks in UI. Present clean business-level workflow states (planning, delegation, review, revision, artifact synthesis).

---

## 🗂️ Modular Design System Navigation

This Brand Guideline is structured into modular topic files for progressive disclosure:

1. **[`01-tokens-and-surfaces.md`](./01-tokens-and-surfaces.md)**: Color palettes, surfaces, tactile borders, spacing, and elevation.
2. **[`02-typography-and-icons.md`](./02-typography-and-icons.md)**: Font families, type scales, typography rules, and iconography.
3. **[`03-layout-and-navigation.md`](./03-layout-and-navigation.md)**: Application workbench shell, responsive layouts, navigation bars, and page templates.
4. **[`04-components-and-states.md`](./04-components-and-states.md)**: Comprehensive guide for 43 UI components and 10 interaction states.
5. **[`05-data-visualization.md`](./05-data-visualization.md)**: Financial charts, bar/line graphs, tooltips, axes, and color schemes.
6. **[`06-interactions-and-behaviors.md`](./06-interactions-and-behaviors.md)**: Search, filters, sort, resizable panels, bulk actions, and confirmations.
7. **[`07-motion-accessibility-contract.md`](./07-motion-accessibility-contract.md)**: Micro-interactions (100-240ms), WCAG 2.2 AA accessibility, implementation contracts, and checklists.
