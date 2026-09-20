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
}

export function AnalysisReportWorkspace({ report }: AnalysisReportWorkspaceProps) {
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

  return (
    <div className="min-h-screen bg-workspace text-ink pb-16">
      {/* Layer 1: Report Sticky Header Bar */}
      <ReportHeaderBar report={report} />

      {/* Main Content Workspace Container */}
      <div className="mx-auto max-w-[1280px] px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Layer 2: Analysis Plan & Capability Banner */}
        <AnalysisPlanBanner
          plan={report.analysis_plan}
          revisionSummary={report.revision_summary}
          limitations={report.limitations}
        />

        {/* Layer 3: Macro Policy Context (Conditional) */}
        {report.macro_context && (
          <MacroContextBlock macroContext={report.macro_context} />
        )}

        {/* Layer 4: Sector Benchmark Comparison Matrix (Conditional) */}
        {report.sector_benchmark && (
          <SectorBenchmarkMatrix
            sectorBenchmark={report.sector_benchmark}
            targetTicker={report.target_ticker}
            peerTickers={report.peer_tickers}
            companyInsights={report.company_insights}
          />
        )}

        {/* Layer 5: Company CAMEL In-depth Breakdown */}
        {report.company_insights.length > 0 && (
          <CompanyCamelBreakdown
            companyInsights={report.company_insights}
            targetTicker={report.target_ticker}
          />
        )}

        {/* Layer 6: Semantic Critique & Claim Graph */}
        {report.atomic_claims.length > 0 && (
          <CrossLevelCritiqueGraph
            crossLevelCritique={report.cross_level_critique}
            atomicClaims={report.atomic_claims}
            onSelectEvidence={handleSelectEvidence}
            selectedEvidenceId={selectedEvidenceId}
          />
        )}

        {/* Layer 7: Evidence Trail & Source Provenance Table */}
        {report.evidence_trail.length > 0 && (
          <EvidenceTrailTable
            evidenceTrail={report.evidence_trail}
            selectedEvidenceId={selectedEvidenceId}
            onClearSelection={handleClearEvidence}
          />
        )}
      </div>
    </div>
  );
}
