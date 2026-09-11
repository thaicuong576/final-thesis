# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are financial analysts who need to understand which validated data is available, define an analysis request, observe the multi-agent workflow, and produce a defensible report.

## Product Purpose

This is a reference web application for a reusable hierarchical multi-agent financial analysis architecture. It helps analysts combine macroeconomic context, peer/sector analysis, and company-level data, validate evidence, reconcile insights, and prepare an evidence-backed report.

## Positioning

The application exposes a business-oriented analysis workflow while keeping the reusable analysis core independent from the frontend, physical storage, and model provider.

## Operating Context

The reference flow is:

DATA → ANALYSIS REQUEST → LIVE MULTI-AGENT WORKFLOW → FINAL REPORT → REPORT LIBRARY

The product is an analyst workspace, not a chatbot, developer console, ETL monitor, research benchmark UI, or database administration tool.

## Capabilities and Constraints

- The reusable core must remain replaceable behind data, evidence, model, and storage adapters.
- Dataset capabilities define the available entities, periods, metrics, peer universe, and macro readiness.
- Gold data is a validated dataset instance, not the architecture.
- Material analytical statements must remain traceable to structured claims and evidence.
- The product uses the final hierarchical architecture; research A/B/C comparisons do not appear in normal product UX.
- Current demonstration scope is five Vietnamese banks, Q1–Q4/2024, and NPL, Coverage, ROA, and ROE; this is a narrow validated fixture, not a generic application limit.
- User-facing language is Vietnamese and business-oriented. Internal identifiers, provider names, physical schemas, chain-of-thought, and hidden prompts stay out of the main UX.
- `/app`, thesis research artifacts, and Python core are outside the frontend surface scope unless explicitly requested.

## Brand Commitments

- Product name: Financial Analysis.
- The visual language is a restrained, professional financial-analyst workspace with neutral surfaces, strong typography, subtle borders, and limited blue/semantic status accents.
- Avoid gradients, glow, glassmorphism, decorative AI effects, oversized KPI cards, and consumer-fintech styling.

## Evidence on Hand

- Existing reference frontend under `frontend/`.
- Existing validated thesis fixture and capability mock used for the current prototype.
- No production enterprise connectors or backend API are claimed by the reference UI.

## Product Principles

1. Keep the reusable analysis core separable from the reference application.
2. Make capability, validation, provenance, and limitations understandable to analysts.
3. Use narrow but complete vertical slices without pretending the thesis fixture represents the whole sector.
4. Preserve enterprise integration paths through stable contracts and replaceable adapters.

## Accessibility & Inclusion

Interactive states must be keyboard accessible, status must not rely on color alone, and responsive behavior must preserve the analyst's ability to understand scope and data readiness.
