-- ====================================================================
-- CANONICAL DATABASE SCHEMA (FINANCE MASTER V2)
-- Source: data/processed/finance_master_v2.sqlite
-- Purpose: Single Source of Truth for SQLite observations and metrics
-- ====================================================================

CREATE TABLE benchmark_periods (period TEXT PRIMARY KEY, period_start TEXT NOT NULL, period_end TEXT NOT NULL, status TEXT NOT NULL);

CREATE TABLE coverage_summary (source_family TEXT NOT NULL, ticker TEXT NOT NULL, rows INTEGER NOT NULL, non_null_values INTEGER NOT NULL, status TEXT NOT NULL, PRIMARY KEY(source_family,ticker));

CREATE TABLE dataset_run (
 run_id TEXT PRIMARY KEY, created_at_utc TEXT NOT NULL, snapshot_status TEXT NOT NULL,
 benchmark_periods TEXT NOT NULL, universe TEXT NOT NULL, data_cap_bytes INTEGER NOT NULL,
 raw_snapshot_note TEXT NOT NULL
);

CREATE TABLE document_records (
 document_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, year INTEGER NOT NULL, document_type TEXT NOT NULL,
 local_path TEXT NOT NULL, source_url TEXT NOT NULL, doi TEXT, content_hash TEXT NOT NULL, bytes INTEGER NOT NULL,
 license TEXT, quality_status TEXT NOT NULL
);

CREATE TABLE financial_observations (
 id INTEGER PRIMARY KEY, ticker TEXT NOT NULL, sector TEXT NOT NULL, statement_type TEXT NOT NULL,
 period TEXT NOT NULL, source_period_year INTEGER, source_period_quarter INTEGER, public_date TEXT,
 period_basis TEXT NOT NULL, field_code TEXT NOT NULL, field_name_vi TEXT, field_name_en TEXT,
 field_parent TEXT, field_level INTEGER, value REAL, unit TEXT NOT NULL, source_id TEXT NOT NULL,
 source_locator TEXT NOT NULL, quality_status TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);

CREATE TABLE macro_observations (
 id INTEGER PRIMARY KEY, country TEXT NOT NULL, indicator TEXT NOT NULL, applicable_period TEXT,
 publication_date TEXT, vintage TEXT, value REAL, unit TEXT, source_id TEXT NOT NULL,
 source_locator TEXT NOT NULL, quality_status TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);

CREATE TABLE market_daily (
 id INTEGER PRIMARY KEY, ticker TEXT NOT NULL, trade_date TEXT NOT NULL, open REAL, high REAL,
 low REAL, close REAL, volume REAL, traded_value REAL, source_family TEXT NOT NULL, unit_note TEXT NOT NULL,
 source_id TEXT NOT NULL, source_locator TEXT NOT NULL, quality_status TEXT NOT NULL,
 FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);

CREATE TABLE ratio_observations (
 id INTEGER PRIMARY KEY, ticker TEXT NOT NULL, sector TEXT NOT NULL, period TEXT NOT NULL,
 ratio_type TEXT, source_period_year INTEGER, source_period_quarter INTEGER, field_code TEXT NOT NULL,
 value REAL, unit TEXT NOT NULL, source_id TEXT NOT NULL, source_locator TEXT NOT NULL,
 quality_status TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES source_records(source_id)
);

CREATE TABLE source_records (
 source_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, publisher TEXT, source_url TEXT,
 retrieved_at_utc TEXT, local_path TEXT, content_hash TEXT, bytes INTEGER, quality_status TEXT NOT NULL,
 notes TEXT
);

CREATE INDEX idx_fin_field_period ON financial_observations(field_code,period);

CREATE INDEX idx_fin_ticker_period ON financial_observations(ticker,period);

CREATE INDEX idx_market_ticker_date ON market_daily(ticker,trade_date);

CREATE INDEX idx_ratio_ticker_period ON ratio_observations(ticker,period);

-- Mutable application history is defined in contracts/run-store-schema.sql.
-- Apply it only to ANALYSIS_RUNS_DB_PATH, never to an accepted dataset.
