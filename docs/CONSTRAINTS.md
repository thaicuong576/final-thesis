# Constraints and Quality Standards

## Binding architectural guardrail

The application-first constitution in
[`ARCHITECTURAL-GUARDRAILS.md`](ARCHITECTURAL-GUARDRAILS.md) is binding for
all implementation work. It governs the reusable-core/application boundary,
dataset-provider abstraction, Macro/Sector/Company architecture,
research/product separation, replaceable storage/model providers, event
privacy, phase roadmap, and review policy. If this document conflicts with the
constitution, stop and resolve the conflict before coding.

## Scope

- The default first baseline is the 48-cell ACB/TCB/VPB pilot across four 2024
  quarters. The five-bank/eight-quarter design is a conditional expansion and
  must pass the same gates before inclusion.
- Securities companies, TCBS, real-time feeds, investment execution, and public production deployment are out of the thesis MVP.
- Any change to issuer universe, period cutoff, metric formula, source priority, or evaluation arm requires a recorded decision.

## Correctness

- Financial formulas must have unit tests and hand-checked examples.
- A missing value must never become zero without an explicit rule.
- Period and unit conversions must be explicit.
- A published claim must be traceable to an accepted observation or cited document.
- Views and summaries must not silently mix incompatible snapshots.
- An anomaly trigger is not a true contradiction without an independent evaluation label.

## Data quality

- Preserve raw inputs unchanged.
- Record retrieval time, source URL, content hash, publisher, source tier, ticker, period, and parser status.
- Report coverage and missingness by ticker, metric, and period.
- Detect duplicates, conflicting values, invalid units, invalid dates, incompatible period bases, and restatements.
- Maintain a manually verified gold sample with at least 40 metric/evidence items.
- Promote staging data to gold only through a fail-closed readiness check.

## Agent behavior

- Validate every payload before critique or synthesis.
- Keep quantitative facts separate from qualitative interpretation.
- Use bounded retries and a maximum of two verification attempts.
- Never hide an unresolved anomaly, missing value, or source conflict.
- Never present mocked, fallback, estimated, or incomplete data as official live evidence.
- Agents do not calculate financial ratios from prose.

## Reproducibility

- Pin dependency versions where practical.
- Version experiment questions, run configurations, snapshot IDs, formula versions, and prompt configurations.
- Cache external inputs for benchmark runs.
- Record model name, model version, prompt/configuration version, timing, calls, tokens, and cost.
- Make a clean rerun possible from documented commands.
- Never overwrite an existing raw or staging snapshot with a gold derivative.

## Security and privacy

- Never commit API keys, OAuth tokens, service-account files, or private credentials.
- Use least-privilege access for external services.
- Redact personal or confidential financial data from reports and fixtures.
- Do not send private documents to an external model without an approved data-handling decision.
- Treat deployment, external writes, and real financial actions as approval-required.

## Performance

- Measure retrieval latency and model-call count.
- Avoid sending raw datasets when a filtered structured payload is sufficient.
- Keep prompts and evidence bounded.
- Use cached local data for repeated experiments.

## Verification gates

A phase cannot be marked complete from a successful command alone. It needs a durable record of the command, result, relevant artifact, and known limitations. The data-foundation gate must produce `READY_FOR_BASELINE` before the primary baseline experiment begins.
