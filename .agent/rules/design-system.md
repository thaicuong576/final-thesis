# Design System Compliance Rule

This rule is binding for all user interfaces, components, styles, animations, layouts, and product surfaces in this repository.

## Canonical Reference
The single source of truth for design guidelines is `.agent/design.md` ("Universal Software Product Design System").

## Core Aesthetic & Direction
- **Style**: Warm retro developer workbench — tactile, structured, dense, calm, and functional.
- **Governing Axiom**: "Personality belongs around the work. Clarity belongs inside the work."
- **Surfaces & Palettes**:
  - Always use warm neutrals (`--bg-workspace: #f7f7f6`, `--surface-primary: #fbfbf8`, `--border-default: #c9c8c0`).
  - Never default to pure `#FFFFFF` canvas or clinical cool-gray SaaS aesthetics.
  - Accent (`--accent: #ee9f0d`) is single-purpose: reserve strictly for active selection, primary CTA, or focused context. Never use accent fill as gratuitous decoration.
- **Structure**:
  - Express hierarchy through 1px visible borders, surface shifts, and spacing before shadows ("Borders before shadows").
  - Do not use high-blur or oversized drop shadows.
  - Ban glassmorphism, glowing borders, and gradient backgrounds in workflows.
- **Controls & Radii**:
  - Controls must look operable (visible borders, hover states, clear click affordance).
  - Radii must remain restrained: 4px (`sm`) for table cells/inline, 6px (`md`) for buttons/inputs/cards, 8px (`lg`) for panels/dialogs.
  - Ban universal pill-shaped buttons and inputs (pills are reserved solely for tags, chips, avatars, and status badges).
- **Density & Layout**:
  - High information density is encouraged ("Compact, not cramped").
  - Data-heavy workspaces must use tables, lists, and resizable panels instead of dozens of oversized floating cards.
- **Motion**:
  - Fast, subtle, and functional (100–240ms).
  - No bouncing, spring animations, or decorative parallax.
  - Must respect `prefers-reduced-motion`.
- **States & Accessibility**:
  - Every interactive component must support: Default, Hover, Focus (2px visible outline), Active, Selected, Disabled, Loading, Empty, Error, and Read-only.
  - Must meet WCAG 2.2 AA contrast requirements. Never communicate status through color alone.
- **Domain Alignment**:
  - All user-facing product copy is Vietnamese.
  - Multi-agent reasoning boundaries: No raw internal chain-of-thought, scratchpads, or system prompt leaks in UI. Present clean business-level workflow states (planning, delegation, review, revision, artifact synthesis).
