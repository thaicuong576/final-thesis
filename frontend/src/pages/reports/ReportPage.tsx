import { useMemo } from 'react';
import { useParams, useLocation, useInRouterContext } from 'react-router-dom';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import {
  AnalysisReportWorkspace,
  getReportById,
  type AnalysisReport
} from '@/features/analysis-report';

interface ReportPageProps {
  report?: AnalysisReport;
}

export function ReportPage({ report: propReport }: ReportPageProps) {
  const { id } = useParams<{ id?: string }>();
  const inRouter = useInRouterContext();

  if (inRouter) {
    return <RouterBoundReportPage id={id} propReport={propReport} />;
  }
  return <ReportPageContent id={id} propReport={propReport} />;
}

function RouterBoundReportPage({
  id,
  propReport
}: {
  id?: string;
  propReport?: AnalysisReport;
}) {
  const location = useLocation();
  const stateReport = (location.state as { report?: AnalysisReport } | null)?.report;
  return (
    <ReportPageContent
      id={id}
      propReport={propReport}
      stateReport={stateReport}
    />
  );
}

function ReportPageContent({
  id,
  propReport,
  stateReport
}: {
  id?: string;
  propReport?: AnalysisReport;
  stateReport?: AnalysisReport;
}) {
  const report = useMemo<AnalysisReport>(() => {
    // 1. Explicit prop override (highest priority, used by tests)
    if (propReport) return propReport;

    // 2. Navigation location state from live analysis session
    if (stateReport && stateReport.target_ticker) {
      return stateReport;
    }

    // 3. Cached live analysis report in sessionStorage
    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = window.sessionStorage.getItem('current_analysis_report');
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as AnalysisReport;
          if (
            parsed &&
            parsed.target_ticker &&
            (id === 'live-session' || parsed.report_id === id || !id)
          ) {
            return parsed;
          }
        } catch {
          // ignore
        }
      }
    }

    // 4. Default fallback to verified static mock report by ID
    return getReportById(id);
  }, [propReport, stateReport, id]);

  const peerText =
    report.peer_tickers && report.peer_tickers.length > 0
      ? ` & ${report.peer_tickers.join(', ')}`
      : '';
  const scopeLabel = `${report.target_ticker || 'ACB'}${peerText} ${report.period || '2024'}`;



  return (
    <WorkspaceShell
      activeSection="reports"
      context={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="font-bold text-ink">BÁO CÁO PHÂN TÍCH</span>
            <span className="text-border-strong">/</span>
            <span className="font-semibold text-ink">{scopeLabel}</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-ink-secondary font-mono">
            <span className="w-2 h-2 rounded-full bg-[#2f9e62]" aria-hidden="true" />
            <span>KIỂM ĐỊNH THÀNH CÔNG</span>
          </div>
        </div>
      }
    >
      <AnalysisReportWorkspace report={report} />
    </WorkspaceShell>
  );
}
