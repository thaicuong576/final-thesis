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
  sbv_policy_rate: number;
  system_credit_growth: number;
  interest_rate_trend: string;
  source: string;
}

export interface SectorBenchmark {
  sector: string;
  peer_median_roe: number;
  peer_median_nim: number;
  peer_median_npl: number;
  peer_median_cir: number;
  peer_median_casa: number;
  peer_median_car: number;
  peer_median_ldr: number;
}

export interface CompanyInsight {
  ticker: string;
  roe: number;
  nim: number;
  npl: number;
  cir: number;
  casa: number;
  car: number;
  ldr: number;
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
  value: number;
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
