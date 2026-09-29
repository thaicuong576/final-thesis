import type {
  AnalysisReport,
  AnalysisPlan,
  MacroContext,
  SectorBenchmark,
  CompanyInsight,
  CritiqueItem,
  AtomicClaim,
  EvidenceTrailItem,
  BoundedRevisionSummary
} from './types';

export interface RawAnalysisResponseArtifact {
  report_id: string;
  status?: 'completed' | 'failed' | 'partial' | 'accepted_with_limitations' | 'error';
  query?: string;
  target_ticker?: string | null;
  peer_tickers?: string[];
  period?: string | null;
  analysis_plan?: AnalysisPlan | null;
  macro_context?: MacroContext | null;
  sector_benchmark?: SectorBenchmark | null;
  company_insights?: CompanyInsight[];
  cross_level_critique?: CritiqueItem[];
  atomic_claims?: AtomicClaim[];
  evidence_trail?: EvidenceTrailItem[];
  revision_summary?: BoundedRevisionSummary | string | null;
  limitations?: string[];
}

export function normalizeAnalysisResponseToReport(
  res?: RawAnalysisResponseArtifact | Record<string, unknown> | null,
  req?: { query?: string; target_ticker?: string; peer_tickers?: string[]; period?: string } | null
): AnalysisReport {
  if (!res || typeof res.report_id !== 'string' || !res.report_id.trim()) {
    throw new Error('API không trả mã báo cáo hợp lệ.');
  }
  const typed = res as RawAnalysisResponseArtifact;
  const plan = typed.analysis_plan;

  const rawStatus = typed.status;
  const status: AnalysisReport['status'] =
    rawStatus === 'failed'
      ? 'error'
      : (rawStatus as AnalysisReport['status']) ?? 'completed';

  const revSummary: BoundedRevisionSummary | null =
    typeof typed.revision_summary === 'object' && typed.revision_summary !== null
      ? typed.revision_summary
      : null;

  return {
    report_id: typed.report_id,
    status,
    query: typed.query ?? plan?.query ?? req?.query,
    target_ticker: typed.target_ticker ?? plan?.target_ticker ?? req?.target_ticker,
    peer_tickers: typed.peer_tickers ?? plan?.peer_tickers ?? req?.peer_tickers,
    period: typed.period ?? plan?.period ?? req?.period ?? undefined,
    analysis_plan: plan ?? null,
    macro_context: typed.macro_context,
    sector_benchmark: typed.sector_benchmark,
    company_insights: typed.company_insights,
    cross_level_critique: typed.cross_level_critique,
    atomic_claims: typed.atomic_claims,
    evidence_trail: typed.evidence_trail,
    revision_summary: revSummary,
    limitations: typed.limitations
  };
}
