# Blind-Score Provider Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Blind-score all 39 provider outputs against the frozen Gold-bound question set and rubric, then report quality scores together with latency and cost without claiming superiority before the evidence supports it.

**Architecture:** Load the immutable provider manifests and select one published answer per job: `single_agent` for the single-agent arm and the last `orchestrator` payload for both hierarchical arms. Create a deterministic blind map that removes arm/run/role identity from reviewer packets. Combine mechanical Gold checks for structured numeric/provenance fields with two independent AI-assisted rubric reviews for narrative, evidence, missing/conflict and consistency judgments; preserve reviewer disagreement rather than silently averaging it.

**Tech Stack:** Python 3.11, Pydantic contracts already in `src/thesis_data/evaluation.py`, read-only SQLite Gold queries, OpenAI Responses API with strict JSON output, JSONL review artifacts, Markdown/JSON aggregation.

**Spec:** `experiments/scoring-rubric-v1.md`, `docs/EVALUATION-PROTOCOL.md`, `docs/DATA-CONTRACT.md`, and `docs/superpowers/specs/2026-09-06-closed-world-tool-calling-design.md`.

## Global Constraints

- Gold snapshot is read-only: `data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite`.
- Use only the frozen 13-question set and 39-job provider run.
- Hide `arm`, `run_id`, filename, payload role, and call count from reviewer packets.
- Never score the `verification` payload as the published final answer; bounded critique uses its last `orchestrator` payload.
- Preserve snapshot ID, question-set SHA-256, rubric version, prompt version, and model ID in every score record.
- Missing values are not treated as zero and are scored separately from numeric accuracy.
- AI-assisted scores are labeled as such and are not presented as human thesis validation.
- Do not write API keys or raw secret-bearing configuration to any scoring artifact.

---

### Task 1: Freeze scoring bindings and write failing packet tests

**Files:**
- Create: `tests/test_blind_scoring.py`
- Create: `docs/superpowers/plans/2026-09-06-blind-score-provider-pilot.md`

**Interfaces:**
- `select_published_payload(manifest: dict) -> dict`
- `blind_id_for(job_id: str, seed: str) -> str`
- `sanitize_payload(payload: dict) -> dict`

- [x] **Step 1: Write tests that select `orchestrator` over `verification`, preserve single-agent output, and remove arm/role identifiers from a blinded payload.**
- [x] **Step 2: Run `PYTHONPATH=src python -m unittest tests.test_blind_scoring` and verify it fails because `thesis_data.blind_scoring` is not implemented.**

### Task 2: Implement immutable blind packet construction

**Files:**
- Create: `src/thesis_data/blind_scoring.py`
- Modify: `tests/test_blind_scoring.py`

**Interfaces:**
- `load_provider_manifests(run_dir: Path) -> list[dict]`
- `build_blind_packets(run_dir: Path, db_path: Path, question_set_path: Path, seed: str) -> tuple[list[dict], dict]`
- `write_blind_artifacts(...)` writes packet JSONL and private map without overwriting existing files.

- [x] **Step 1: Implement fail-closed manifest loading: exclude only `failures.json`, reject duplicate job IDs, mixed bindings, missing arms, missing selected payloads, or non-39 job sets.**
- [x] **Step 2: Build question-scoped Gold references from read-only `get_company_metrics`, `get_sector_benchmarks`, evidence and missing/conflict queries.**
- [x] **Step 3: Sanitize final payloads and generate deterministic blind IDs from a fixed seed; store arm/job mapping separately from packets.**
- [x] **Step 4: Run the packet tests and verify they pass.**

### Task 3: Add mechanical structured-output scoring

**Files:**
- Modify: `src/thesis_data/blind_scoring.py`
- Create: `scripts/build_blind_score.py`
- Modify: `tests/test_blind_scoring.py`

**Interfaces:**
- `score_structured_answer(packet: dict) -> list[dict]`
- `score_operational_metrics(manifests: list[dict]) -> dict`
- `aggregate_score_rows(rows: list[ClaimReview]) -> list[ScoreSummary]`

- [x] **Step 1: Score Gold-bound numeric facts, null/missing discipline, units/period binding, observation/source binding, evidence locator presence, and mechanical cross-level period compatibility.**
- [x] **Step 2: Emit `ClaimReview`-compatible rows with separate reason codes and explicit non-applicable dimensions; do not hide unscorable narrative claims.**
- [x] **Step 3: Record latency, model calls, input/output tokens, tool calls, rejection counts and cost per arm from manifests.**
- [x] **Step 4: Run tests and verify summary aggregation rejects mixed frozen bindings.**

### Task 4: Run two independent blinded AI-assisted reviews

**Files:**
- Create: `scripts/run_blind_ai_review.py`
- Create: `tests/test_blind_ai_review.py`

**Interfaces:**
- `run_reviewer(packet: dict, reviewer_id: str, client: ResponsesClient) -> list[ClaimReview]`
- `run_blind_review_suite(packet_path: Path, output_dir: Path, client: ResponsesClient) -> None`

- [x] **Step 1: Define strict JSON schema for dimension decisions: score, applicable/unscorable status, and reason code.**
- [x] **Step 2: Send only sanitized answer, question, and Gold reference to two differently instructed reviewers; never send arm/run/file identity.**
- [x] **Step 3: Validate every response through `ClaimReview`, retry invalid JSON once, and fail closed if a decision cannot be validated.**
- [x] **Step 4: Preserve raw reviewer decisions, latency/tokens, disagreement rows, and no-secret checks.**

### Task 5: Execute and aggregate the 39-job blind score

**Files:**
- Create: `reports/provider-blind-score-gpt-5.6-luna-20260906T085022Z/`
- Create: `reports/provider-blind-score-gpt-5.6-luna-20260906T085022Z.md`
- Create: `reports/provider-blind-score-gpt-5.6-luna-20260906T085022Z.json`

- [x] **Step 1: Build blind packets and inspect counts/bindings before reviewer calls.**
- [x] **Step 2: Run mechanical scoring for all 39 jobs.**
- [x] **Step 3: Run both blinded AI-assisted reviewers for all applicable dimensions.**
- [x] **Step 4: Aggregate per-arm numerator/denominator, disagreement, unscorable counts, latency and cost.**
- [x] **Step 5: Write an interpretation section that distinguishes measured score differences from operational overhead and refuses a superiority claim if primary outcomes are tied, mixed, or unscorable.**
- [x] **Step 6: Run the full test suite, compileall, artifact/state validation, and inspect the final report.**

### Task 6: Update durable project state

**Files:**
- Modify: `.agents/project-state/current.json`
- Modify: `.agents/project-state/events.jsonl`
- Create: `.agents/handoffs/2026-09-06-blind-score-provider-pilot.md`

- [x] **Step 1: Record exact score artifacts, reviewer mode, binding checks, and remaining human-review limitations.**
- [x] **Step 2: Mark comparative interpretation as provisional unless the review protocol's human-review requirement is actually satisfied.**
- [x] **Step 3: Verify JSON/JSONL parsing and update the goal only when every explicit scoring deliverable is evidenced.** The 39-packet score, operational telemetry, two blind reviews, 27-disagreement adjudication overlay, full test suite, compileall, state/event sync, and secret scan are verified. The separate human thesis-validation gate remains open and is not silently waived.
