import { useState } from 'react';
import type { AnalysisReport } from '../model/types';
import { ReportHeaderBar } from './ReportHeaderBar';
import { AnalysisPlanBanner } from './AnalysisPlanBanner';
import { MacroContextBlock } from './MacroContextBlock';
import { SectorBenchmarkMatrix } from './SectorBenchmarkMatrix';
import { CompanyCamelBreakdown } from './CompanyCamelBreakdown';
import { CrossLevelCritiqueGraph } from './CrossLevelCritiqueGraph';
import { EvidenceTrailTable } from './EvidenceTrailTable';

interface AnalysisReportWorkspaceProps {
  report: AnalysisReport;
  isDemo?: boolean;
}

export function AnalysisReportWorkspace({ report, isDemo = false }: AnalysisReportWorkspaceProps) {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);

  const handleSelectEvidence = (evidenceId: string) => {
    setSelectedEvidenceId(evidenceId);
    const element = document.getElementById('evidence-trail');
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleClearEvidence = () => {
    setSelectedEvidenceId(null);
  };

  const evidenceTrail = report.evidence_trail || [];
  const linkableEvidenceIds = new Set(
    evidenceTrail
      .filter((item) => {
        const source = item.source_url || item.source_doc;
        if (!source || !item.table_locator?.trim()) return false;
        try {
          return ['http:', 'https:'].includes(new URL(source).protocol);
        } catch {
          return false;
        }
      })
      .map((item) => item.evidence_id)
  );

  return (
    <div className="min-h-screen bg-workspace text-ink pb-16">
      {/* Layer 1: Report Sticky Header Bar */}
      <ReportHeaderBar report={report} isDemo={isDemo} />

      {/* Main Content Workspace Container */}
      <div className="mx-auto max-w-[1280px] px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Layer 2: Analysis Plan & Capability Banner */}
        {report.analysis_plan ? (
          <AnalysisPlanBanner
            plan={report.analysis_plan}
            revisionSummary={report.revision_summary}
            limitations={report.limitations}
          />
        ) : (
          <section className="rounded-md border border-warning/40 bg-warning-soft/40 p-4 text-sm text-ink" role="status">
            API không trả về kế hoạch phân tích cho báo cáo này.
          </section>
        )}

        {/* Layer 3: Macro Policy Context (Conditional) */}
        {report.macro_context && (
          <MacroContextBlock macroContext={report.macro_context} />
        )}

        {/* Layer 4: Sector Benchmark Comparison Matrix (Conditional) */}
        {report.sector_benchmark && (
          <SectorBenchmarkMatrix
            sectorBenchmark={report.sector_benchmark}
            period={report.period}
          />
        )}

        {/* Layer 5: Company CAMEL In-depth Breakdown */}
        {report.company_insights && report.company_insights.length > 0 && (
          <CompanyCamelBreakdown
            companyInsights={report.company_insights}
            targetTicker={report.target_ticker || ''}
          />
        )}

        {/* Layer 6: Semantic Critique & Claim Graph */}
        {report.atomic_claims && report.atomic_claims.length > 0 && (
          <CrossLevelCritiqueGraph
            crossLevelCritique={report.cross_level_critique || []}
            atomicClaims={report.atomic_claims}
            linkableEvidenceIds={linkableEvidenceIds}
            onSelectEvidence={handleSelectEvidence}
            selectedEvidenceId={selectedEvidenceId}
          />
        )}

        {/* Layer 7: Evidence Trail & Source Provenance Table */}
        {report.evidence_trail && report.evidence_trail.length > 0 && (
          <EvidenceTrailTable
            evidenceTrail={evidenceTrail}
            selectedEvidenceId={selectedEvidenceId}
            onClearSelection={handleClearEvidence}
          />
        )}
      </div>
    </div>
  );
}
