# TASK — Define teacher walkthrough acceptance checklist

- **Tracking:** task-specific Linear waiver; no Linear issue requested for this thesis workstream.
- **Role:** Lead Architect / thesis acceptance-document owner.
- **Base:** `origin/main` at `1cab2549db20f710165cffe8197aaa24a4014d69`.
- **Scope:** add and maintain a Vietnamese, read-only walkthrough checklist under `docs/`; GET/browser inspection is allowed for evidence, but do not post analysis runs, access secrets, or change deployment settings.
- **Required content:** readiness prerequisites, Dataset → Create Analysis → Session → Report journeys, negative/blocked cases, provenance checks, responsive UI checks, evidence capture fields, and the current blocked status from the 2026-09-26 preflight.
- **Verification:** Markdown link check, `git diff --check`, inspect changed-file scope, and no implementation/data/contract/deployment mutations. A fresh GET/browser recheck may update the blocked evidence timestamp without changing runtime state.
