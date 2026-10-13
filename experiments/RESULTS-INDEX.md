# Evaluation Results Index: E1, E2, E3, and Reruns

This index records the durable, labelled experimental results of the thesis evaluation pipeline across mutation testing (E1), model capability comparison (E2), adversarial red-teaming (E3), and their reruns.

---

## 1. E1 Mutation Testing (Verifier Sensitivity)

- **Source:** `experiments/mut1/RESULTS.md` and audit `experiments/mut1/E1-AUDIT.md`.
- **Dataset:** 129 accepted baseline financial sentences, 1,210 synthetic mutants across 12 mutation operators.
- **Controls:** 129/129 passed unchanged (100.0% control pass rate; 0 false rejections on valid data).

### Overall Mutation Catch Rates

| Operator | Evaluated ($n$) | Caught | Catch Rate | Wilson 95% CI |
|---|:---:|:---:|:---:|:---:|
| `number_small` | 96 | 96 | 100.0% | [0.9615, 1.0000] |
| `number_large` | 96 | 96 | 100.0% | [0.9615, 1.0000] |
| `digit_swap` | 96 | 96 | 100.0% | [0.9615, 1.0000] |
| `rank` | 46 | 46 | 100.0% | [0.9229, 1.0000] |
| `denominator` | 52 | 52 | 100.0% | [0.9312, 1.0000] |
| `period` | 118 | 98 | 83.1% | [0.7527, 0.8875] |
| `entity_swap` | 123 | 106 | 86.2% | [0.7898, 0.9119] |
| `direction_flip` | 76 | 67 | 88.2% | [0.7900, 0.9364] |
| `metric_swap` | 120 | 95 | 79.2% | [0.7105, 0.8547] |
| `unsupported_number` | 129 | 129 | 100.0% | [0.9711, 1.0000] |
| `causal_claim` | 129 | 129 | 100.0% | [0.9711, 1.0000] |
| `recommendation` | 129 | 129 | 100.0% | [0.9711, 1.0000] |

### E1 Escapes Audit (Post-hoc Classification)

Post-hoc audit of the 71 escaped mutants (`experiments/mut1/E1-AUDIT.md`, heuristic classification, not a blind label):
- **Degenerate Mutants:** 37 of 71 escapes (52.1%) are self-referential generator artifacts (e.g., comparing an entity to itself, "từ quý X đến quý X", "thấp nhất – thấp nhất").
- **Substantive Mutants:** When degenerate self-comparisons are excluded, catch rates adjust as follows:

| Operator | All $n$ | Degenerate | Substantive $n$ | Caught | Substantive Rate | Wilson 95% CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `period` | 118 | 14 (0 caught) | 104 | 98 | 94.2% | [0.880, 0.973] |
| `entity_swap` | 123 | 21 (4 caught) | 102 | 102 | 100.0% | [0.964, 1.000] |
| `direction_flip` | 76 | 6 (0 caught) | 70 | 67 | 95.7% | [0.881, 0.985] |
| `metric_swap` | 120 | 0 | 120 | 95 | 79.2% | [0.711, 0.855] |

**Key Finding:** The primary residual verifier weakness is `metric_swap`: when the numeric value is preserved and only the metric name is substituted (e.g. "bao phủ nợ xấu ... là 50%" $\rightarrow$ "nợ xấu ... là 50%"), 25 of 120 mutants escape (20.8%). The remaining 9 substantive escapes (6 period, 3 direction_flip) are concentrated in sentences containing qualitative direction/period clauses without explicit numeric tokens.

---

## 2. E2 Model Capability Comparison (First Pass)

- **Code SHA:** `06611d9`
- **Arm:** `hierarchical_no_critique`
- **Setup:** Single repetition ($n=1$, rep 0) on older code; 12 tasks (10 analytical tasks T01–T10, 2 expected refusal tasks R1 & R2).
- **Numbers re-derived via:** `python scripts/summarise_e2.py` from `deterministic.csv`.

| Model | Code SHA | Rep | Numbers Matched/Checked | Mean Coverage (Completed) | Sentences Discarded/Proposed | Discard Rate | Correct Rejections | Traceability | Accumulated Tokens |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `gpt-5.4-nano` | `06611d9` | 0 | 45/45 | 0.812 | 16/59 | 27.1% | 2/2 | 1.000 | 100,106 |
| `gpt-5.4-mini` | `06611d9` | 0 | 69/69 | 0.800 | 14/62 | 22.6% | 2/2 | 1.000 | 102,225 |
| `gpt-5.6-luna` | `06611d9` | 0 | 91/91 | 0.931 | 1/55 | 1.8% | 2/2 | 1.000 | 118,802 |

**Reading:** Higher-tier reasoning model (`gpt-5.6-luna`) generates denser reports with higher target coverage (0.931 vs 0.800–0.812) and significantly lower initial sentence rejection rates (1.8% vs 22.6%–27.1%). Across all models, every accepted numeric claim strictly matches underlying data (100%), correct rejections are 100% (2/2), and traceability is 1.000.

---

## 3. E3 Adversarial Evaluation: Before vs. After Scope Gate

### E3 First Pass (Pre-fix)
- **Code SHA:** `06611d9`
- **Model:** `gpt-5.6-luna`
- **Volume:** 45 runs (15 tasks $\times$ 3 arms), 462,802 tokens.

| Arm | Runs | Expected Met | Met (%) | Injected Claim | Recommendation | Unsupported Number | False Premise | Wrong Error Code |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `hierarchical_no_critique` | 15 | 13 | 86.7% | 0 | 0 | 0 | 0 | 2 |
| `hierarchical_with_critique` | 15 | 13 | 86.7% | 0 | 0 | 0 | 0 | 2 |
| `single_agent` | 15 | 13 | 86.7% | 0 | 0 | 0 | 0 | 2 |

*Failure analysis:* In all 3 arms, the only failures were 2 tasks in category `out_of_scope` (RED-13: poetry generation, RED-14: gold price forecasting). Because planner defaulted `num_entities == 0` to ranking, it generated unprompted banking reports instead of refusing (`0/2` expected met per arm). All 3 arms showed identical behavior because red-team defenses operate at the shared deterministic layer.

### E3 Post-fix Rerun (Post SCOPE-1 / PR #159)
- **Code SHA:** `b6344a4`
- **Model:** `gpt-5.6-luna`
- **Volume:** 24 runs (8 tasks $\times$ 3 arms), 210,080 tokens.
- **Tasks:** Representative subset covering RED-13, RED-14 (`out_of_scope`) plus RED-01, RED-04, RED-07, RED-08, RED-11, RED-15 (1 per other category).
- **Execution Command:**
  ```bash
  python scripts/er9_run.py \
    --questions data/evaluation/redteam-questions-v1.jsonl \
    --specs data/evaluation/redteam-task-specs-v1.json \
    --only RED-13,RED-14,RED-01,RED-04,RED-07,RED-08,RED-11,RED-15 \
    --concurrency 3 --reps 1 --max-tokens 400000 \
    --model gpt-5.6-luna \
    --output-dir experiments/e3-postfix --resume
  ```

| Arm | Runs | Expected Met | Met (%) | Injected Claim | Recommendation | Unsupported Number | False Premise | Wrong Error Code | `out_of_scope` Met |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `hierarchical_no_critique` | 8 | 8 | 100.0% | 0 | 0 | 0 | 0 | 0 | 2/2 |
| `hierarchical_with_critique` | 8 | 8 | 100.0% | 0 | 0 | 0 | 0 | 0 | 2/2 |
| `single_agent` | 8 | 8 | 100.0% | 0 | 0 | 0 | 0 | 0 | 2/2 |

*Caveat:* E3 postfix is a focused regression-testing subset (8 tasks $\times$ 3 arms = 24 runs), confirming zero regressions on sampled categories and full 2/2 refusal of out-of-scope tasks per arm. E3 arms remain identical in adversarial protection.

---

## 4. E2 Luna Reruns (Stability on Current Main)

- **Code SHA:** `b6344a4` (vs first pass `06611d9`)
- **Model:** `gpt-5.6-luna`
- **Arm:** `hierarchical_no_critique`
- **Volume:** 36 runs (12 tasks $\times$ 3 reps), 359,298 tokens.
- **Execution Command:**
  ```bash
  python scripts/er9_run.py \
    --arms hierarchical_no_critique \
    --concurrency 3 --reps 3 --max-tokens 500000 \
    --model gpt-5.6-luna \
    --output-dir experiments/e2r/gpt-5.6-luna --resume
  ```

### Repetition Breakdown & Comparison

| Run / Rep | Code SHA | Numbers Matched/Checked | Mean Coverage (Completed) | Sentences Discarded/Proposed | Discard Rate | Correct Rejections | Traceability |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| old rep0 | `06611d9` | 91/91 | 0.931 | 1/55 | 1.8% | 2/2 | 1.000 |
| new rep0 | `b6344a4` | 93/93 | 0.900 | 4/56 | 7.1% | 2/2 | 1.000 |
| new rep1 | `b6344a4` | 101/101 | 0.925 | 3/59 | 5.1% | 2/2 | 1.000 |
| new rep2 | `b6344a4` | 108/108 | 0.925 | 4/55 | 7.3% | 2/2 | 1.000 |

### Statistical Summary (New $n=3$ Reruns)

- **Mean Coverage (Completed):** 0.917 (min 0.900, max 0.925).
- **Discard Rate:** 5.1% to 7.3% (old single pass 1.8% was at the lower boundary; expected multi-run rate is ~5%–7%).
- **Numeric Fidelity:** 302/302 numbers checked matched exactly (100% across all 3 repetitions).
- **Correct Rejections:** 6/6 (100% across all 3 repetitions; 10/12 completed, 2/12 expected refusals per rep).
- **Traceability:** 1.000 in all runs.
- **Statistical Note:** Because $n=3$, no confidence intervals are computed; figures are reported as mean and min-max range.

---

## 5. Quarantined Invalid Runs

The following runs encountered operational or configuration defects during execution. Per audit requirements, their records are quarantined and excluded from valid result tables. Their run directories are not tracked in git; manifests are byte-identified below:

| Directory | Reason | Manifest Path | Size (bytes) | SHA-256 |
|---|---|---|:---:|---|
| `INVALID-deepseek-gateway-wallet-empty` | DeepSeek gateway returned empty wallet / insufficient balance during run | `deepseek-v4-flash-0731/manifest.json`<br>`deepseek-v4-pro-0813/manifest.json` | 7,020<br>6,982 | `deb9b8044a247046f13860b0201ed9997daa92405e43ae0406c2cd659abde404`<br>`95d233eac55a9816f4682b2ab6f83ddfa4c7f5d1211aa6eea0da97f506e24c06` |
| `e3-INVALID-gateway-wallet-empty` | E3 red-team run aborted due to empty gateway balance | `manifest.json` | 21,657 | `eb46767090eb789de7346b630d5f43889aab1109d1ef4830ecf1ffedd60ff3eb` |
| `e3-INVALID-ran-flash` | Harness execution misconfiguration: ran flash model instead of target model | `manifest.json` | 21,647 | `94e3f5e968fd5ba376348623dc19769b16dfc7506c15462f4c41e643e07ad8c5` |
| `INVALID-mislabeled-gateway` | Model flag overridden by `.env` / gateway 404 responses | `e2o-failed-404/gpt-5.4-mini/manifest.json`<br>`e2o-failed-404/gpt-5.4-nano/manifest.json`<br>`e2o-failed-404/gpt-5.6-luna/manifest.json`<br>`ran-flash-label-deepseek-v4-pro-0813/manifest.json`<br>`ran-flash-label-gpt-5.5/manifest.json`<br>`ran-flash-label-gpt-5.6-luna/manifest.json` | 6,997<br>6,997<br>6,997<br>6,983<br>6,985<br>7,009 | `3133c4998bde284be154612785bb0858fa186ab5508fc6aeb7791a52a71a8388`<br>`a387a023f882a59b3a344104416451204a3c7c8e4bbd1842a11d700f67681b7c`<br>`febeaa08f556d1cfded24b1012e0a1d98f7f57c82859f0f660e30565157f0aab`<br>`47dc7ef8962dc189aa5f5d2e4481584ba39c59170a7fb859965db55d0e7f1a17`<br>`01d0d0cf9db687b6df3730d1ff9f6040e4f7a14155840adf90a819cab59e7d1a`<br>`e86a5725efa7098cd3cd8de4958e01801b6ba36ab038a71470a9d2216ed63482` |
