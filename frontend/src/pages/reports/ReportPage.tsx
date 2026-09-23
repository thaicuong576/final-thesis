import { useEffect, useMemo, useState } from 'react';
import { useParams, useLocation, useInRouterContext, Link } from 'react-router-dom';
import { FileQuestion, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import {
  AnalysisReportWorkspace,
  getReportById,
  type AnalysisReport
} from '@/features/analysis-report';
import { getApiBaseUrl, normalizeAnalysisResponseToReport } from '@/features/analysis-session/useAnalysisSessionStream';
import { ReportErrorBoundary } from './ReportErrorBoundary';

interface ReportPageProps {
  report?: AnalysisReport;
}

export function ReportPage({ report: propReport }: ReportPageProps) {
  const { id } = useParams<{ id?: string }>();
  const inRouter = useInRouterContext();

  return (
    <ReportErrorBoundary>
      {inRouter ? (
        <RouterBoundReportPage id={id} propReport={propReport} />
      ) : (
        <ReportPageContent id={id} propReport={propReport} />
      )}
    </ReportErrorBoundary>
  );
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
  // Synchronous resolution priority:
  // 1. Explicit prop override (used by tests)
  // 2. Navigation location state from live analysis session
  // 3. Cached live analysis report in sessionStorage
  // 4. Sample benchmark templates (acb-solo, acb-tcb-peer, macro-acb-cross)
  const initialSyncReport = useMemo<AnalysisReport | null>(() => {
    if (propReport) return propReport;
    if (stateReport && stateReport.target_ticker) return stateReport;

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

    if (id === 'acb-solo' || id === 'acb-tcb-peer' || id === 'macro-acb-cross') {
      return getReportById(id);
    }

    return null;
  }, [propReport, stateReport, id]);

  const [fetchedReport, setFetchedReport] = useState<AnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!initialSyncReport && Boolean(id));
  const [isNotFound, setIsNotFound] = useState<boolean>(false);

  useEffect(() => {
    if (initialSyncReport || !id) {
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setIsNotFound(false);

    const fetchReport = async () => {
      try {
        const baseUrl = getApiBaseUrl();
        // 1. Try GET /api/reports/{id}
        let res = await fetch(`${baseUrl}/api/reports/${id}`, {
          headers: { Accept: 'application/json' }
        });

        // 2. Fallback to GET /api/runs/{id}
        if (!res.ok) {
          res = await fetch(`${baseUrl}/api/runs/${id}`, {
            headers: { Accept: 'application/json' }
          });
        }

        if (res.ok) {
          const data = await res.json();
          const reportData = (data.report || data) as Record<string, unknown>;
          const normalized = normalizeAnalysisResponseToReport(reportData);
          if (isMounted) {
            setFetchedReport(normalized);
            setIsLoading(false);
          }
          return;
        }

        if (isMounted) {
          setIsNotFound(true);
          setIsLoading(false);
        }
      } catch (err) {
        console.warn('Failed to fetch report from API:', err);
        if (isMounted) {
          setIsNotFound(true);
          setIsLoading(false);
        }
      }
    };

    void fetchReport();

    return () => {
      isMounted = false;
    };
  }, [id, initialSyncReport]);

  const activeReport = propReport || initialSyncReport || fetchedReport;

  if (isLoading) {
    return (
      <WorkspaceShell
        activeSection="reports"
        context={
          <div className="flex items-center justify-between w-full text-xs font-mono">
            <span className="font-bold text-ink">BÁO CÁO PHÂN TÍCH</span>
            <span className="text-ink-secondary">ĐANG TẢI...</span>
          </div>
        }
      >
        <div className="min-h-[calc(100vh-80px)] bg-workspace py-12 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[720px] p-8 border border-line bg-card rounded-lg text-center space-y-4">
            <div className="inline-flex items-center justify-center size-10 rounded-full bg-amber-soft border border-amber-border/50 text-amber-border animate-spin mx-auto">
              <RotateCw className="size-5" />
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-bold text-ink">Đang tải báo cáo phân tích</h2>
              <p className="text-xs text-ink-secondary max-w-md mx-auto leading-relaxed">
                Đang truy xuất bản báo cáo và số liệu kiểm chứng từ cơ sở dữ liệu SQLite...
              </p>
            </div>
          </div>
        </div>
      </WorkspaceShell>
    );
  }

  if (isNotFound || !activeReport) {
    return (
      <WorkspaceShell
        activeSection="reports"
        context={
          <div className="flex items-center justify-between w-full text-xs font-mono">
            <span className="font-bold text-ink">BÁO CÁO PHÂN TÍCH</span>
            <span className="text-[#c84b3f]">KHÔNG TÌM THẤY</span>
          </div>
        }
      >
        <div className="min-h-[calc(100vh-80px)] bg-workspace py-12 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[640px] p-8 border border-line bg-card rounded-lg text-center space-y-4 shadow-sm">
            <div className="inline-flex items-center justify-center size-12 rounded-full bg-surface-secondary border border-border text-ink-secondary mx-auto">
              <FileQuestion className="size-6" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-base font-bold text-ink">Không tìm thấy báo cáo phân tích</h2>
              <p className="text-xs text-ink-secondary leading-relaxed">
                Mã báo cáo <code className="font-mono bg-surface-secondary px-1.5 py-0.5 rounded text-ink border border-border">{id}</code> không tồn tại hoặc chưa được lưu trữ trong cơ sở dữ liệu.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-3">
              <Button asChild className="bg-amber text-ink border border-amber-border hover:bg-amber-hover text-xs font-semibold h-8 px-4">
                <Link to="/analysis">Tạo phân tích mới</Link>
              </Button>
              <Button asChild variant="outline" className="border-line text-xs font-medium h-8 px-4">
                <Link to="/reports">Xem danh sách báo cáo</Link>
              </Button>
            </div>
          </div>
        </div>
      </WorkspaceShell>
    );
  }

  const peerText =
    activeReport.peer_tickers && activeReport.peer_tickers.length > 0
      ? ` & ${activeReport.peer_tickers.join(', ')}`
      : '';
  const scopeLabel = `${activeReport.target_ticker || 'ACB'}${peerText} ${activeReport.period || '2024'}`;

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
      <AnalysisReportWorkspace report={activeReport} />
    </WorkspaceShell>
  );
}
