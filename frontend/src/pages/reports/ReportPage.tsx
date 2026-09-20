import { useParams } from 'react-router-dom';
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
  const report = propReport ?? getReportById(id);

  const scopeLabel = `${report.target_ticker}${
    report.peer_tickers.length > 0 ? ` & ${report.peer_tickers.join(', ')}` : ''
  } ${report.period}`;

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
