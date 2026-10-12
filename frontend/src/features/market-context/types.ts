/**
 * Types for Market Context & SSI FastConnect Data (MKT-1).
 */

export interface MarketQuote {
  ticker: string;
  close: number;
  reference: number;
  change: number;
  change_percent: number;
  volume: number;
  trading_date: string;
  fetched_at: string;
  source: string;
  stale: boolean;
  stale_reason?: string | null;
}

export interface MarketQuotesResponse {
  configured: boolean;
  source: string;
  fetched_at?: string | null;
  stale: boolean;
  stale_reason?: string | null;
  quotes: MarketQuote[];
}

export interface MarketValuationInputs {
  close_vnd?: number | null;
  close_source: string;
  close_date?: string | null;
  listed_shares?: number | null;
  shares_source: string;
  parent_attributable_equity_billion_vnd?: number | null;
  equity_period?: string | null;
  equity_source?: string | null;
  roe_percent?: number | null;
  roe_period?: string | null;
  formula: string;
}

export interface BankValuation {
  ticker: string;
  close?: number | null;
  listed_shares?: number | null;
  parent_attributable_equity?: number | null;
  bvps?: number | null;
  pb?: number | null;
  roe?: number | null;
  inputs: MarketValuationInputs;
  missing_reason?: string | null;
}

export interface MarketValuationResponse {
  configured: boolean;
  source: string;
  fetched_at?: string | null;
  stale: boolean;
  stale_reason?: string | null;
  items: BankValuation[];
}
