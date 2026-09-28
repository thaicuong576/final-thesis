-- Application persistence only: apply to ANALYSIS_RUNS_DB_PATH.
-- This schema must never be applied to SQLITE_DB_PATH / an accepted snapshot.
-- Existing accepted dataset bytes and schemas are not migrated by this contract.
-- Idempotent runtime migration is handled in ER-5; failed runs are persisted; target_ticker and period may be null.
CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    query TEXT NOT NULL,
    target_ticker TEXT,
    peer_tickers TEXT,
    period TEXT,
    status TEXT NOT NULL,
    report_json TEXT,
    events_json TEXT,
    model_used TEXT,
    latency_ms INTEGER,
    trace_json TEXT,
    error_code TEXT,
    duration_ms INTEGER,
    model_calls INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    arm TEXT,
    question_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_target ON analysis_runs(target_ticker, period);

