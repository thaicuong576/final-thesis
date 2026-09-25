# Evaluation Protocol v1 — pre-freeze draft

**Status:** pre-freeze; do not run or cite as the final experiment yet.  
**Freeze condition:** composite truth gate, query-adaptive peer path, and real
critique/revision path all pass end-to-end against the same snapshot.  
**Dataset:** `gold-bank-2025-expanded-v5-evidence`, SHA-256
`1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73`.

## 1. Experiment arms

| Arm | Behavior |
|---|---|
| A | One agent receives the same accepted facts, tools, evidence policy and output contract. |
| B | Query-adaptive hierarchy; only plan-required specialists run; no semantic critique/revision. |
| C | Same planner and specialists as B, then semantic critique and at most two targeted revision rounds. |

All arms use the same question bytes, snapshot, model/version, deterministic
tools, prompt/config version and report schema. B and C must share their plan
and specialist behavior up to the critique boundary. C reruns only affected
active specialists, re-synthesizes, and executes Stage-1 again.

Use comparable maximum budgets but record actual latency, model calls, input and
output tokens, cost, revision rounds, errors and completion. Do not force equal
call counts. Preserve failed runs in the completion denominator.

## 2. Candidate analytical tasks

| ID | Type | Scope and Vietnamese prompt intent | Required capability | Eligibility gate |
|---|---|---|---|---|
| T01 | company snapshot | MBB 2024_Q4: assess NPL, LLR, ROA and ROE; cite every number and state limits. | Company | Gold provider + Stage-1 E2E |
| T02 | company snapshot | VCB 2024_Q4: assess asset quality and profitability from the four accepted metrics. | Company | Gold provider + Stage-1 E2E |
| T03 | missingness | ACB 2024_Q1: answer what can and cannot be concluded; never replace the four missing cells. | Company | Missing-data fail-closed E2E |
| T04 | company trend | TCB 2024_Q1–Q4: explain NPL and LLR movement without introducing unsupported causes. | Company | Multi-period request + exact period scope |
| T05 | company trend | MBB 2024_Q1–Q4: assess ROA/ROE movement and distinguish observed trend from interpretation. | Company | Multi-period request + exact period scope |
| T06 | peer snapshot | Compare ACB, MBB, TCB, VCB and VPB at 2024_Q4 on NPL and LLR; name the accepted-member denominator. | Company + Peer | Query-adaptive peer runtime |
| T07 | peer snapshot | Compare ACB, MBB, TCB, VCB and VPB at 2024_Q4 on ROA and ROE; do not generalize to the whole sector. | Company + Peer | Query-adaptive peer runtime + D-072 authority gate |
| T08 | multi-period peer | Across 2024_Q1–Q4, compare the five-bank Gold set on the trade-off between asset quality and profitability; preserve ACB Q1 missingness and disclose each period's accepted denominator. | Company + Peer + synthesis | Multi-period peer runtime and context budget |

D-063/D-072 now admit VPB ROE for the exact hash-bound Gold v5 snapshot after
the independent review attestation and authority reconciliation. Every peer
task still reports its accepted-member denominator and does not generalize the
five-bank case study to the whole banking sector. CTG is excluded because it is
an operational portability case, not a Gold benchmark label. Macro tasks are a
separate optional stratum and are not added until period-aligned macro
observations pass the Gold gate.

Ten candidate tasks are now recorded in `data/evaluation/p4-questions-v1.jsonl`
and `p4-task-specs-v1.json`: the eight analytical tasks above plus T09
(unsupported 2025_Q1) and T10 (CTG outside the frozen peer set) as rejection
controls. Expected cells and denominators are in `p4-expected-coverage-v1.json`.
These controls use canonical LF UTF-8 hashes; the question-set digest is
`c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09`.
They remain candidates and contain no scored outcomes. T04/T05/T08 are explicitly
ineligible while the public API rejects multi-period scope. The other exact
questions still need same-snapshot end-to-end and fair A/B/C verification.
The eight-task count below describes the proposed analytical experiment;
T09/T10 are reported separately as robustness controls. Freeze the final
eligible task list, repetition count and rubric before scoring any run.

## 3. Repetitions and execution order

Target design: 8 tasks × 3 arms × 2 repetitions = 48 planned runs. If provider
budget permits, use three repetitions (72 planned runs). Choose the repetition
count before the first scored run. Randomize run order with a recorded seed,
while rate-limit or outage retries follow one written policy. Never rerun only
low-scoring outputs.

Each manifest records:

- task ID and exact question-set hash;
- arm, repetition and randomized order;
- snapshot ID/hash and capability-catalog version;
- model/provider version and prompts/configuration;
- tool/evidence policy and maximum budgets;
- start/end, latency, calls, tokens/cost, revisions and terminal status;
- every retry, provider error and acceptance failure.

## 4. Scoring

### 4.1. Deterministic dimensions

| Dimension | Measurement |
|---|---|
| Numeric accuracy | Accepted numeric claims exactly match canonical observations within the metric tolerance. |
| Reference validity | Claim IDs resolve to exact observations, sources and locators; no generic snippet fan-out. |
| Evidence support | Numeric and narrative claims satisfy their appropriate evidence route. |
| Coverage | Required plan items addressed divided by applicable required items. |
| Completion | Terminal accepted/limited/failed state; every planned run remains in the denominator. |

`NOT_APPLICABLE` is removed from a criterion's denominator. Missing data is a
separate expected behavior, not zero and not a wrong numeric answer when the
system states the limitation correctly.

### 4.2. Blind human dimensions

Score each from 0–4 with anchored examples fixed before review:

- logical coherence;
- explicit uncertainty and limitations;
- usefulness for a financial analyst;
- relevant integration across levels, only when the plan declares a link.

Remove arm labels and randomize report order for the author's review. Re-score
a predeclared subset after a delay and report within-rater agreement plus the
single-rater limitation. Do not rewrite the rubric after seeing arm results.

## 5. Analysis and reporting

Report per arm and task type: planned/completed/failed counts, deterministic
rates, blind scores, latency, calls, tokens/cost and revisions. Show both
completed-only quality and completion-adjusted quality. Because the expected
sample is small, emphasize effect sizes, paired differences and run-level
results; treat inferential statistics as exploratory if used.

The historical 75-job/61-completion pilot remains feasibility evidence only.
It cannot be pooled with this experiment because its bounded-critique arm did
not demonstrate the final targeted revision behavior.
