# Product direction: source-driven financial research workflow

## Discussion summary

The proposed product should not be limited to placing financial documents into a language model and asking for an answer.

The stronger idea is to study previous banking, securities, sector, macroeconomic and market reports to identify the sources, metrics, periods, peer groups and reasoning patterns used by analysts.

The system then builds a source registry and automated acquisition pipeline that retrieves newer information from those sources, preserves immutable snapshots, validates the observations and exports an updated analysis.

## Product concept

The product is an agentic financial research system that converts changing primary and contextual sources into reproducible, evidence-backed company and sector reports.

A typical request should produce the latest verified report for a company or segment, explain what changed since the previous report, compare the target with its peers, identify contradictions and cite the underlying evidence.

## Proposed workflow

1. Collect historical analyst reports and relevant source documents.
2. Extract claims, metrics, citations, source names, URLs, periods, peer groups and assumptions.
3. Build a source registry containing authority, fields, update frequency, access method, licensing, coverage and validation rules.
4. Implement deterministic connectors for issuer filings, market data, macro indicators, exchange statistics and policy documents.
5. Preserve every retrieval as an immutable snapshot with timestamp, URL, hash, period and source status.
6. Normalize units, periods, tickers, report bases and missing values.
7. Compute financial ratios, peer benchmarks, liquidity measures and change indicators with deterministic code.
8. Use specialized agents to interpret macro, sector and company evidence.
9. Run cross-level contradiction checks and request focused verification evidence when needed.
10. Export a current report, evidence trail, quality report, change log and reproducible run record.

## Division of responsibilities

Code should own acquisition, normalization, financial formulas, validation and reproducible comparisons.

Agents should own source discovery, evidence interpretation, question decomposition, contradiction explanation and report synthesis.

Historical reports should guide source and methodology discovery, but they should not be treated as authoritative data.

Official issuer, SBV, GSO, HOSE, HNX and SSC publications should remain the primary evidence where available.

Vendor APIs and analyst reports should be explicitly labeled as accelerators, cross-checks or contextual material.

## Differentiation from NotebookLM

A NotebookLM-style system mainly answers questions over documents supplied to it.

This product should maintain a refreshable source map, calculate structured metrics, compare periods and peers, detect contradictions, track changes and preserve an auditable evidence trail.

The same frozen input snapshot and configuration should produce a reproducible run rather than an answer that depends on an opaque search session.

The product must be evaluated against a document-question-answering baseline and a single general financial-analysis agent.

If the hierarchical system does not improve numerical accuracy, citation correctness, missing-data honesty, contradiction detection or consistency, the added architecture is not justified.

## Recommended MVP

Begin with Vietnamese banks rather than all financial sectors.

Use five representative tickers, three report types and five to eight reliable sources.

Run on a fixed quarterly update cycle using daily end-of-day market data where required.

Produce a company report, peer comparison, macro context, what-changed section, contradiction section and evidence appendix.

Add wider coverage only after the source registry, validation rules and report output are stable.

## Rating and risks

The idea is rated 8.5 out of 10 for product value and research relevance.

Its main strength is that it creates a repeatable research process rather than another document chatbot.

Its main risk is overestimating what can be learned from analyst reports because citations may be incomplete, data may be licensed, and analyst judgment may not be reproducible.

Another risk is building an overly autonomous crawler when a small number of deterministic, monitored connectors would be safer.

The target should be the latest verified snapshot, not an unconditional promise that every source is always current.

## Relationship to the thesis

The source-driven workflow can serve as the product framing while the thesis evaluates the hierarchical Macro, Sector and Company agents coordinated by the Master Orchestrator.

The evaluation should compare the baseline and hierarchical systems on factual accuracy, calculation accuracy, evidence completeness, citation correctness, contradiction detection, cross-level consistency, latency, model calls and cost.

Architecture interfaces and test fixtures may begin before every data gap is closed.

Full financial analysis claims and final evaluation should wait until the normalized gold dataset and its quality report are available.
