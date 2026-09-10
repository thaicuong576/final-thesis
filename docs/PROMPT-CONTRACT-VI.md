# Prompt contract — v1

Status: `DRAFT_FROZEN_FOR_SCAFFOLD`

`prompt-contract-v1` is the prompt/configuration version recorded in every
experiment run manifest. It describes the behavior that must remain constant
while comparing the three arms. A future change to role instructions, output
rules, context layout, or verification wording requires a new prompt version;
it must not silently overwrite this one.

## Shared instructions

Every arm receives:

- one frozen snapshot ID and question ID;
- the exact non-empty `prompt_version` carried by the run configuration and
  passed through `AgentCallRequest` to the adapter;
- the target issuer and period scope;
- facts returned by the read-only query layer;
- bounded evidence records with source IDs, evidence IDs, locators, units and
  period basis;
- the same metric definitions, source policy and output contract.

The model must not fetch the network, calculate a financial ratio from prose,
use a pending observation as an accepted fact, silently merge consolidated and
standalone data, or replace a missing/conflicting value with an estimate. Every
numeric claim must either carry the corresponding provenance IDs or be stated
as unavailable/uncertain with its reason.

The model may explain, compare, classify, and synthesize the prepared facts.
Code remains responsible for unit normalization, YTD/quarter conversion,
derived ratios, peer statistics, and deterministic anomaly triggers.

`src/thesis_data/prompting.py` currently renders this contract into a stable,
provider-neutral prompt. It canonicalizes request scope and prepared context,
and the later transport receives that rendered prompt rather than constructing
an independent provider-specific version. This is deterministic plumbing only;
it is not evidence of prompt calibration or model quality.

## Arm-specific behavior

### Arm A — single agent

One call receives the shared context and produces the final contract-valid
answer. The single agent is not given less evidence or weaker tools than the
hierarchical arms.

### Arm B — hierarchical without critique

The orchestrator dispatches the same prepared context to Macro, Sector, and
Company roles. It validates each payload and synthesizes the final answer. No
verification follow-up is allowed. This arm measures decomposition without a
critique loop.

### Arm C — hierarchical with bounded critique

Arm C uses the same worker roles and context as Arm B. The orchestrator may
dispatch verification only after a deterministic trigger, and may make at most
two attempts. A trigger is not itself a contradiction label. The final output
must distinguish true contradiction, explainable divergence, data conflict, and
insufficient evidence.

## Output requirements

The response must conform to the typed `AgentPayload` contract and preserve:

- target ticker and period;
- status and findings;
- observation, source and evidence IDs;
- source locators and metric units where a numeric claim is made;
- explicit missing/conflict reasons;
- verification outcome and unresolved issues when applicable.

Contract failure is a failed run condition, not a reason to repair the answer
after the fact. The run manifest records the prompt version, question-set hash,
snapshot ID, role/attempt traces, prepared-context hash and telemetry.
Current manifests also record a SHA-256 fingerprint of each canonical rendered
prompt; older schema-version-2 artifacts may omit this additive field.
The adapter request and manifest must agree on the prompt version; a provider
adapter must not select a different prompt silently. `AgentCallRequest` rejects
an empty version, and `build_run_manifest()` rejects a call/configuration
mismatch before writing the artifact.

## Freeze boundary

This document is sufficient for offline fixture and boundary tests. It is not a
claim that provider prompts have been calibrated. Provider-backed execution
still requires a promoted Gold snapshot, approved model/configuration and
`READY_FOR_BASELINE` decision. Comparative results must use one prompt version
across all arms.
