# Project Agent Instructions

## Purpose

This project implements and evaluates a hierarchical multi-agent system for Vietnamese listed banking and securities sector analysis.

The source thesis is `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` and its companion PDF and images are source artifacts.

The thesis source artifacts are read-only references and must not be rewritten as part of implementation.

## Canonical context

Before acting, read this file, `README.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`, `docs/DECISIONS.md`, `docs/RESEARCH.md`, `docs/CONSTRAINTS.md`, and the binding `docs/ARCHITECTURAL-GUARDRAILS.md` as relevant.

Dynamic project truth lives in `.agents/project-state/current.json` and `.agents/project-state/events.jsonl`.

Worker handoffs live in `.agents/handoffs/`.

Do not treat chat history, model memory, or an unrecorded assumption as project truth.

## Operating principles

1. Research and data readiness come before multi-agent implementation.
2. Raw data is immutable and every derived value must have provenance.
3. Code computes financial metrics; language models retrieve, explain, critique, and synthesize.
4. Every agent output must conform to `docs/DATA-CONTRACT.md`.
5. Mocked, cached, or incomplete data must be labeled and must never be reported as live validation.
6. Every material decision, assumption, blocker, and verification result must be recorded in the project state or a handoff.
7. Agents must not silently change scope, formulas, source priority, or evaluation methodology.
8. Secrets belong in local ignored configuration or a secret manager and must never be committed or pasted into reports.
9. Production deployment and access to real financial services require explicit approval.
10. `docs/ARCHITECTURAL-GUARDRAILS.md` is binding. If a task conflicts with it, stop and report the conflict before implementation.

## Ownership

- The Orchestrator owns project state, task sequencing, and synthesis.
- The data specialist owns ingestion, normalization, metric calculation, and data-quality reports.
- The evidence specialist owns PDF parsing, source metadata, and retrieval quality.
- The agent-system specialist owns agent prompts, tools, routing, critique, and synthesis.
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
