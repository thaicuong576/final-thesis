# Provider adapter contract

Status: structured response boundary implemented; provider execution remains
gated by the Gold readiness decision.

## Purpose

`src/thesis_data/provider_config.py` defines the secret-free configuration
boundary for a future provider-backed adapter. It validates the provider/model,
source policy, environment, network mode, and basic request limits. It does not
create a client, read an API key, call a network, retrieve financial facts, or
promote staging data.

The runtime adapter remains dependency-injected through
`src/thesis_data/agent_runtime.py`. This separation is intentional: choosing a
provider configuration must not silently choose a network implementation or
bypass the experiment input gate.

## Structured response boundary

`src/thesis_data/provider_adapter.py` implements the provider-neutral portion
of the adapter. `StructuredProviderAdapter` receives a `ProviderTransport` by
dependency injection. The transport receives the canonical prompt produced by
`src/thesis_data/prompting.py`; it is the only component allowed to own
provider I/O. Neither boundary creates a client, resolves an API key, reads the
network, or retrieves financial data.

The transport must implement `complete(request, rendered_prompt, config)` and
return a `ProviderResponse` containing either a typed
`AgentPayload`, a JSON object, or a JSON string, plus typed
`AgentCallTelemetry` when telemetry is required. The boundary then:

- parses JSON and validates the payload against `DATA-CONTRACT.md`;
- fails closed on malformed JSON, schema-invalid payloads, wrong response
  types, missing required telemetry, or invalid telemetry types;
- marks telemetry explicitly as `unavailable` when the config allows it; and
- wraps transport exceptions as a stable `provider_transport_failed` blocker
  without copying provider exception text into experiment artifacts.

This is a parsing and contract layer, not evidence that a provider has been
connected or that a provider-backed experiment has run. The real transport
implementation remains a later, separately approved change. The offline
fixture is an exception only for deterministic plumbing: its
`OfflineFixtureTransport` returns test payloads through this boundary with
network disabled and cannot be used as provider or financial evidence.

## Deterministic prompt boundary

`render_agent_prompt()` canonicalizes request scope and prepared context with
stable JSON ordering and `allow_nan=false`. It includes the prompt version,
role-specific instruction, issuer, periods, metric/indicator IDs, question,
and the complete prepared context. Unknown roles, missing questions, or
non-JSON-safe context fail closed before the transport is called. The renderer
is provider-neutral and is suitable for offline replay; it does not claim that
the prompt has been calibrated against a real model.

## Required configuration rules

- `environment=offline_fixture` must use `network_access=disabled`.
- `environment=provider_backed` must explicitly use `network_access=enabled`.
- A provider-backed config stores only an environment-variable name such as
  `THESIS_PROVIDER_API_KEY`; the secret value is never stored in JSON, SQLite,
  manifests, or thesis documents.
- `model_id` and `source_policy_id` must match the `ExperimentRunConfig` for
  every job in the plan.
- Unknown fields and malformed environment-variable names are rejected.

## Execution boundary

`execute_baseline_plan` now requires a `ProviderExecutionConfig` whenever
`environment=provider_backed`. It validates that config for every planned job
before the first adapter dispatch. Missing config, environment mismatch, model
mismatch, or source-policy mismatch fails closed and leaves the adapter and
output directory untouched.

The following remain separate gates and must all pass before a real provider
run:

1. a promoted versioned Gold snapshot;
2. complete target-cell decisions and at least 40 independently checked labels;
3. `READY_FOR_BASELINE` readiness decision;
4. core plan hash and question binding preflight;
5. explicit provider configuration and an injected adapter implementation.

The current config contract therefore advances the build surface without
changing the current `NOT_READY` data decision.
