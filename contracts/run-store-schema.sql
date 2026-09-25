-- Application persistence only: apply to ANALYSIS_RUNS_DB_PATH.
-- This schema must never be applied to SQLITE_DB_PATH / an accepted snapshot.
-- Existing accepted dataset bytes and schemas are not migrated by this contract.
CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    query TEXT NOT NULL,
    target_ticker TEXT NOT NULL,
    peer_tickers TEXT,
    period TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT,
    events_json TEXT,
    model_used TEXT,
    latency_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_target ON analysis_runs(target_ticker, period);
