# Evaluation Protocol

Status: Working protocol for the scoped applied-thesis benchmark.

## Research question

On the same frozen dataset, evidence policy, question set, model version, and output contract, does a hierarchical Macro/Sector/Company workflow with deterministic anomaly verification improve factual correctness, evidence traceability, cross-level consistency, and anomaly explanation over a single-agent workflow, and what additional latency, model calls, and cost does it require?

## Experimental controls

Every arm uses:

- the same frozen gold snapshot selected by the versioned scope manifest (the
  48-cell pilot, or a later approved 80/200-cell expansion);
- the same fixed question set and question order;
- the same primary-source policy and evidence store;
- the same model family/version and temperature/settings;
- the same output contract;
- the same report cutoff and no live network retrieval during benchmark runs.

The arms may differ in orchestration and permitted model-call count. That difference is measured rather than hidden.

## Experimental arms

### Arm A — single-agent baseline

One general financial-analysis agent receives the user question and accesses the same deterministic query/evidence tools available to the hierarchical system. It produces the same final report schema.

### Arm B — hierarchical without critique

Macro, Sector, and Company specialists run once, followed by synthesis. No verification feedback is sent after the initial payloads.

### Arm C — hierarchical with bounded critique

Macro, Sector, and Company specialists run once; deterministic anomaly triggers are evaluated; at most two focused verification attempts are allowed; the orchestrator records resolved, explained, or unresolved anomalies before synthesis.

The document-question-answering baseline is optional descriptive context. It
cannot replace Arm A because a document-only system does not receive the same
structured financial tools.

## Question-set design

The fixed set must cover:

- one single-company request;
- one peer-comparison request;
- one macro-to-bank interpretation request;
- one period-change request;
- one request containing a known missing or conflicting evidence case;
- one anomaly case for each retained verification trigger.

Questions are versioned and frozen before the benchmark run. They must not be
written after inspecting the system's outputs. The pilot question set records
the intended anomaly trigger IDs and the known target cell as metadata. These
are coverage commitments, not gold labels: if a frozen Gold snapshot does not
contain the evidence needed to produce a trigger, the result must be reported
as not-triggered or unscorable rather than manufactured. The macro-to-bank case
also requires accepted, period-aligned official macro observations; fallback or
pending macro data cannot support a comparative claim.

## Primary outcomes

### Factual correctness

Compare stated numeric and categorical facts with the gold observations. Score each claim as correct, partially correct, incorrect, unsupported, or appropriately missing.

For a Gold cell labelled `missing`, numeric accuracy does not invent an expected
number and does not include that cell in the numeric denominator. The report must
still show the missing cell in coverage/missingness counts and score whether the
arm correctly preserved and communicated the missing status. Every numeric
aggregate must publish its expected, valid, missing, conflict/unresolved counts
and effective denominator; silently dropping missing cells is invalid.

### Calculation correctness

Compare displayed derived values with deterministic expected values and tolerance rules. A correct number with wrong unit or period is not fully correct.

### Evidence completeness

Measure the share of externally verifiable claims that have a source ID and locator.

### Citation correctness

Measure whether the cited source actually supports the claim, including ticker, period, unit, page, and quote relevance.

### Cross-level consistency

Use a rubric that checks whether macro, sector, and company statements refer to compatible periods, definitions, and directions. A company-specific deviation is not automatically a contradiction.

### Anomaly verification quality

Create independent labels for each trigger case: true contradiction, explainable divergence, data conflict, or not enough evidence. Report precision, recall, false-positive rate, and unresolved rate.

## Secondary outcomes

- end-to-end latency;
- model-call count;
- input/output token count or monetary cost;
- schema-validation rate;
- retrieval failure rate;
- unresolved-conflict rate.

## Human review

A fixed subset of outputs is reviewed blind by two reviewers using the same rubric. Reviewer disagreements are preserved and agreement is reported. A single reviewer may not define both the anomaly rule and the final success label without an independent check.

Every atomic `ClaimReview` must identify its `run_id` and carry the snapshot
ID, question-set SHA-256, rubric version, prompt version, and model ID. The
deterministic scorer rejects a review file that mixes any of those comparison
bindings, while still allowing different run IDs for the multiple questions
and arms in one benchmark. This prevents results from silently combining
outputs produced from different datasets or configurations.

## Interpretation rules

The hierarchy is supported only if it improves at least one pre-registered primary outcome without unacceptable degradation in the others, and the magnitude is discussed together with extra calls, latency, and cost. A null or negative result is valid and must be reported if the hierarchy does not justify its overhead.
