# Task manifest — fix Gold scope authority dataset_id in service provider

## Identity

- Branch: `feat/THES-80-fix-gold-scope-dataset-id`
- Base: `c54c64846d6c6b83d0efb2045769ec9c5b6b4312` (`origin/main`)
- Role: `worker-api`
- Tracker: THES-80 (Linear bypassed per user instruction)
- Binding contracts: `docs/DATA-CONTRACT.md`, `docs/ARCHITECTURAL-GUARDRAILS.md`, `data/evaluation/gold-v5-reporting-scope-authority-v1.json`

## Objective

Fix the `dataset_id` mismatch in `src/thesis_api/service.py` where `GoldSqliteDatasetProvider` is instantiated with hardcoded `dataset_id="gold-sqlite"` instead of the dataset ID declared in the verified scope authority (`authority.authority.dataset_id`), causing `DatasetProviderError("reporting-scope authority dataset_id mismatch")` and resulting in HTTP 503 on `/api/ready`.

## Scope

- In `src/thesis_api/service.py`:
  - When loading the authorized Gold provider in `_load_provider()`, pass `authority.authority.dataset_id` to `GoldSqliteDatasetProvider`.
- In `tests/`:
  - Add or update tests verifying that `_load_provider` with scope authority binds successfully without dataset_id mismatch.
- Run test suite:
  - `pytest tests/`
  - `python scripts/check_openapi_contract.py`
  - `python scripts/check_architecture_guardrails.py`
  - `python -m compileall src tests`
  - `git diff --check`

## Acceptance Criteria

1. `GoldSqliteDatasetProvider` receives the exact dataset_id declared in the verified scope authority.
2. `_load_provider` successfully binds `gold-sqlite-authorized` without throwing `DatasetProviderError`.
3. All checkout-available tests pass with zero regressions.
