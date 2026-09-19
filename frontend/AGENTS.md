# Frontend Agent Instructions & Design System Contract

All frontend code in this directory must strictly comply with the modular design system in `.agent/rules/design/` (indexed at `.agent/rules/design/README.md`).

## Mandatory Guidelines
1. **Source of Truth**: Read `.agent/rules/design/README.md` and relevant topic modules before designing, modifying, or creating UI components, pages, or styles.
2. **Visual Direction**: Warm retro developer workbench — structured, tactile, dense, and calm.
3. **No Decorative SaaS Tropes**: Ban glassmorphism, glowing shadows, floating oversized cards, pure white `#FFFFFF` canvases, and universal pill shapes.
4. **Design Tokens**: Use CSS variables defined in `.agent/rules/design/01-tokens-and-surfaces.md` (`--bg-workspace`, `--surface-primary`, `--border-default`, `--accent`).
5. **Component States**: Implement full state coverage (hover, focus-visible, active, disabled, loading, empty, error).
6. **Localization**: All user-facing strings must be in Vietnamese.
7. **Accessibility**: Meet WCAG 2.2 AA standards with keyboard navigation and visible focus rings.
