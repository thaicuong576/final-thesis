# Project Agent Instructions

## Purpose

This project implements and evaluates a hierarchical multi-agent system for Vietnamese listed banking and securities sector analysis.

The source thesis is `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` and its companion PDF and images are source artifacts.

The thesis source artifacts are read-only references and must not be rewritten as part of implementation.

## Canonical context

Before acting, read this file, `README.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`, `docs/DECISIONS.md`, `docs/RESEARCH.md`, `docs/CONSTRAINTS.md`, `.agent/rules/design/README.md` (and `.agent/design.md`), and the binding `docs/ARCHITECTURAL-GUARDRAILS.md` as relevant.

Do not treat chat history, model memory, or an unrecorded assumption as project truth.

## Operating principles

1. Research and data readiness come before multi-agent implementation.
2. Raw data is immutable and every derived value must have provenance.
3. Code computes financial metrics; language models retrieve, explain, critique, and synthesize.
4. Every agent output must conform to `docs/DATA-CONTRACT.md`.
5. Mocked, cached, or incomplete data must be labeled and must never be reported as live validation.
6. Every material decision, assumption, blocker, and verification result must be recorded in git commits and pull requests.
7. Agents must not silently change scope, formulas, source priority, or evaluation methodology.
8. Secrets belong in local ignored configuration or a secret manager and must never be committed or pasted into reports.
9. Production deployment and access to real financial services require explicit approval.
10. `docs/ARCHITECTURAL-GUARDRAILS.md` is binding. If a task conflicts with it, stop and report the conflict before implementation.
11. The modular design system in `.agent/rules/design/` (indexed at `.agent/rules/design/README.md`) is the binding brand guideline and source of truth for all product UI, screens, components, states, layout, and styling. All frontend work must strictly obey `.agent/rules/design/`.

## Ownership

- The Orchestrator owns project state, task sequencing, and synthesis.
- The data specialist owns ingestion, normalization, metric calculation, and data-quality reports.
- The evidence specialist owns PDF parsing, source metadata, and retrieval quality.
- The agent-system specialist owns agent prompts, tools, routing, critique, and synthesis.
- The frontend / design specialist owns product surfaces, components, tokens, interactions, and design guideline compliance against `.agent/rules/design/`.
- The test specialist owns fixtures, regression tests, experiment execution, and evidence of results.
- A reviewer may report findings but must not silently rewrite another specialist's work.

## Lifecycle

Use this order unless a recorded decision explains a deviation:

```text
research → specification → plan → data foundation → baseline → hierarchical system → evaluation → preview deployment → retest → release
```

Each phase must leave a durable handoff and a verified state update before the next phase begins.

## Current priority

The immediate priority is the research and data-foundation phase.

Do not build the full agent loop until source coverage, metric definitions, period alignment, and a manually checked gold dataset are documented.

Before each major phase, complete the guardrail pre-flight questions and record
any new Gold/SQLite/physical-schema coupling. Passing tests alone is not
architectural acceptance; changes must also preserve the core/application
boundary and the transferability rule.

## GitHub Flow and branch safety

`main` is the only canonical integration branch. Never implement directly on
`main`.

Before any code, data, documentation, experiment, or UI change, an agent must:

1. fetch `origin/main`;
2. verify the expected base SHA and a clean working tree;
3. create a dedicated short-lived branch using the documented branch prefix;
4. keep the change scoped;
5. run appropriate verification;
6. commit with a Conventional Commit title;
7. push the branch and open a Pull Request to `main`;
8. stop for review.

Do not merge the Pull Request unless the user explicitly authorizes the merge.
After a PR is merged, every subsequent task must start from the new latest
`main` HEAD. Do not force-push `main`, rewrite its history, or start new work
from a stale feature branch.

Every coding handoff must report:

```text
Base SHA:
Branch:
Commit SHA:
PR:
Changed files:
Tests:
Known failures:
Working-tree status:
```

See `CONTRIBUTING.md` and `docs/SDLC.md` for the repository workflow and
change-type gates.
