export interface AnalysisPlan {
  plan_id: string;
  query: string;
  target_ticker?: string | null;
  peer_tickers: string[];
  period: string;
  required_capabilities: ('macro' | 'sector' | 'company')[];
  applicable_links: ('peer_comparison' | 'macro_transmission' | 'cross_level_stress')[];
  dataset_snapshot_id: string;
  rationale: string;
  known_limitations: string[];
}

export interface MacroContext {
  sbv_policy_rate: number | null;
  system_credit_growth: number | null;
  interest_rate_trend: string;
  source: string;
}

export interface SectorBenchmark {
  sector: string;
  peer_median_roe: number | null;
  peer_median_nim: number | null;
  peer_median_npl: number | null;
  peer_median_cir: number | null;
  peer_median_casa: number | null;
  peer_median_car: number | null;
  peer_median_ldr: number | null;
}

export interface CompanyInsight {
  ticker: string;
  roe: number | null;
  nim: number | null;
  npl: number | null;
  cir: number | null;
  casa: number | null;
  car: number | null;
  ldr: number | null;
  assessment: string;
}

export interface CritiqueItem {
  dimension: string;
  finding: string;
  confidence: number;
  evidence_ref?: string;
}

export type ClaimType =
  | 'factual_observation'
  | 'peer_comparison'
  | 'policy_transmission'
  | 'synthesis_evaluation';

export interface AtomicClaim {
  claim_id: string;
  capability: 'macro' | 'sector' | 'company' | 'synthesis';
  ticker?: string | null;
  metric?: string | null;
  period?: string | null;
  statement: string;
  claim_type: ClaimType;
  evidence_refs: string[];
  confidence: number;
  stage1_status: 'accepted' | 'rejected';
  stage2_critique_status: 'sound' | 'revised' | 'limited';
}

export interface EvidenceTrailItem {
  evidence_id: string;
  metric: string;
  ticker: string;
  period: string;
  value: number | string | null;
  source_doc: string;
  table_locator: string;
  provenance_hash: string;
}

export interface BoundedRevisionSummary {
  rounds_executed: number;
  max_rounds: number;
  status: 'passed' | 'revised_and_passed' | 'accepted_with_limitations' | 'rejected';
  reason: string;
  revised_capabilities: string[];
}

export interface AnalysisReport {
  session_id?: string;
  report_id: string;
  status: 'completed' | 'partial' | 'accepted_with_limitations' | 'error';
  query: string;
  target_ticker: string;
  peer_tickers: string[];
  period: string;
  analysis_plan: AnalysisPlan;
  macro_context: MacroContext | null;
  sector_benchmark: SectorBenchmark | null;
  company_insights: CompanyInsight[];
  cross_level_critique: CritiqueItem[];
  atomic_claims: AtomicClaim[];
  evidence_trail: EvidenceTrailItem[];
  revision_summary: BoundedRevisionSummary;
  limitations: string[];
}
