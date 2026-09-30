import { useEffect, useMemo, useState } from 'react';
import { useParams, useLocation, useInRouterContext, Link } from 'react-router-dom';
import { FileQuestion, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageCrumbs, StatusPill } from '@/components/layout/PageCrumbs';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import {
  LegacyReport,
  getReportById,
  SAMPLE_REPORTS,
  type AnalysisReport
} from '@/features/analysis-report';
import {
  AdaptiveReport,
  DEFAULT_METRICS,
  type AdaptiveReportResponse,
  type MetricPresentation
} from '@/features/equity-report';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import { normalizeAnalysisResponseToReport } from '@/features/analysis-report';
import { ReportErrorBoundary } from './ReportErrorBoundary';

type ReportUnion = (AnalysisReport & { report_version?: string }) | AdaptiveReportResponse;

interface ReportPageProps {
  report?: ReportUnion;
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
  propReport?: ReportUnion;
}) {
  const location = useLocation();
  const stateReport = (location.state as { report?: ReportUnion } | null)?.report;
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
  propReport?: ReportUnion;
  stateReport?: ReportUnion;
}) {
  // Synchronous resolution priority:
  // 1. Explicit prop override (used by tests)
  // 2. Navigation location state from live analysis session
  // 3. Cached live analysis report in sessionStorage
  // 4. Explicitly routed demo samples
  const initialSyncReport = useMemo<ReportUnion | null>(() => {
    if (propReport) return propReport;
    if (stateReport?.report_id) return stateReport;

    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = window.sessionStorage.getItem('current_analysis_report');
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as ReportUnion;
          if (
            parsed?.report_id &&
            (id === 'live-session' || parsed.report_id === id || !id)
          ) {
            return parsed;
          }
        } catch {
          // ignore
        }
      }
    }

    if (SAMPLE_REPORTS.some((sample) => sample.slug === id || sample.id === id)) {
      return getReportById(id);
    }

    return null;
  }, [propReport, stateReport, id]);

  const [retryCount, setRetryCount] = useState(0);
  const [fetchState, setFetchState] = useState<{
    id: string | undefined;
    report: ReportUnion | null;
    isLoading: boolean;
    isNotFound: boolean;
    isError: boolean;
  }>({
    id,
    report: null,
    isLoading: Boolean(id && !initialSyncReport),
    isNotFound: false,
    isError: false
  });

  useEffect(() => {
    if (initialSyncReport || !id) {
      return;
    }

    let isMounted = true;

    const fetchReport = async () => {
      setFetchState((prev) => ({
        ...prev,
        isLoading: true,
        isNotFound: false,
        isError: false
      }));

      try {
        const baseUrl = getApiBaseUrl();
        const origin =
          typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
            ? window.location.origin
            : '';
        const base = baseUrl || origin;

        // 1. Try GET /api/reports/{id}
        let res = await fetch(`${base}/api/reports/${id}`, {
          headers: { Accept: 'application/json' }
        });

        // 2. Fallback to GET /api/runs/{id}
        if (!res.ok) {
          res = await fetch(`${base}/api/runs/${id}`, {
            headers: { Accept: 'application/json' }
          });
        }

        if (res.ok) {
          const data = await res.json();
          const reportData = (data.report || data) as Record<string, unknown>;

          // If er-report-v1, keep as AdaptiveReportResponse; otherwise normalize to legacy
          const normalized: ReportUnion =
            reportData.report_version === 'er-report-v1'
              ? (reportData as unknown as AdaptiveReportResponse)
              : normalizeAnalysisResponseToReport(reportData);

          if (isMounted) {
            setFetchState({
              id,
              report: normalized,
              isLoading: false,
              isNotFound: false,
              isError: false
            });
          }
          return;
        }

        if (isMounted) {
          if (res.status === 404) {
            setFetchState({
              id,
              report: null,
              isLoading: false,
              isNotFound: true,
              isError: false
            });
          } else {
            setFetchState({
              id,
              report: null,
              isLoading: false,
              isNotFound: false,
              isError: true
            });
          }
        }
      } catch (err) {
        console.warn('Failed to fetch report from API:', err);
        if (isMounted) {
          setFetchState({
            id,
            report: null,
            isLoading: false,
            isNotFound: false,
            isError: true
          });
        }
      }
    };

    void fetchReport();

    return () => {
      isMounted = false;
    };
  }, [id, initialSyncReport, retryCount]);

  const capabilitiesQuery = useAnalysisCapabilities();
  const rawMetrics = capabilitiesQuery.data?.metrics;
  const capabilityMetrics = useMemo<MetricPresentation[] | undefined>(() => {
    if (!rawMetrics) return undefined;
    return rawMetrics.map((m) => {
      const mRaw = m as unknown as Record<string, unknown>;
      const fallback = DEFAULT_METRICS[m.id];
      const rawLabel = typeof m.label === 'string' && m.label.trim() !== '' && m.label !== m.id ? m.label : undefined;
      const label = rawLabel || fallback?.label || m.id;
      const acronym = (typeof m.acronym === 'string' && m.acronym) || fallback?.acronym || m.id;
      const shortLabel =
        (typeof mRaw.shortLabel === 'string' && mRaw.shortLabel) ||
        (typeof mRaw.short_label === 'string' && mRaw.short_label) ||
        fallback?.shortLabel ||
        acronym;
      const unit =
        typeof mRaw.unit === 'string'
          ? mRaw.unit
          : (fallback?.unit ?? '');
      const direction =
        (typeof mRaw.direction === 'string' && (mRaw.direction as MetricPresentation['direction'])) ||
        fallback?.direction ||
        'neutral';
      const decimals =
        typeof mRaw.decimals === 'number'
          ? mRaw.decimals
          : (fallback?.decimals ?? 1);
      const group =
        (typeof mRaw.group === 'string' && mRaw.group) ||
        fallback?.group ||
        m.topicId ||
        'general';
      const groupLabel =
        (typeof mRaw.groupLabel === 'string' && mRaw.groupLabel) ||
        (typeof mRaw.group_label === 'string' && mRaw.group_label) ||
        fallback?.groupLabel ||
        m.topicId ||
        'Chung';

      return {
        id: m.id,
        acronym,
        label,
        shortLabel,
        unit,
        direction,
        decimals,
        group,
        groupLabel,
      };
    });
  }, [rawMetrics]);

  const activeReport = propReport || initialSyncReport || (fetchState.id === id ? fetchState.report : null);
  const isLoading = !initialSyncReport && Boolean(id) && (fetchState.id !== id || fetchState.isLoading);
  const isNotFound = !initialSyncReport && fetchState.id === id && fetchState.isNotFound;
  const isError = !initialSyncReport && fetchState.id === id && fetchState.isError;

  if (isLoading) {
    return (
      <WorkspaceShell
        activeSection="reports"
        context={<PageCrumbs items={[{ label: 'Thư viện báo cáo', to: '/reports' }, { label: 'Đang tải' }]} />}
      >
        <div className="min-h-[calc(100vh-80px)] bg-workspace py-12 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[720px] p-8 border border-line bg-card rounded-lg text-center space-y-4">
            <div className="inline-flex items-center justify-center size-10 rounded-full bg-amber-soft border border-amber-border/50 text-amber-border animate-spin mx-auto">
              <RotateCw className="size-5" />
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-bold text-ink">Đang tải báo cáo phân tích</h2>
              <p className="text-xs text-ink-secondary max-w-md mx-auto leading-relaxed">
                Đang tải báo cáo và số liệu đã kiểm chứng…
              </p>
            </div>
          </div>
        </div>
      </WorkspaceShell>
    );
  }

  if (isError) {
    return (
      <WorkspaceShell
        activeSection="reports"
        context={<PageCrumbs items={[{ label: 'Thư viện báo cáo', to: '/reports' }, { label: 'Lỗi tải báo cáo' }]} />}
      >
        <div className="min-h-[calc(100vh-80px)] bg-workspace py-12 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[640px] p-8 border border-line bg-card rounded-lg text-center space-y-4 shadow-sm">
            <div className="inline-flex items-center justify-center size-12 rounded-full bg-surface-secondary border border-border text-danger mx-auto">
              <FileQuestion className="size-6 text-[#c84b3f]" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-base font-bold text-ink">Không thể tải báo cáo phân tích</h2>
              <p className="text-xs text-ink-secondary leading-relaxed">
                Đã xảy ra lỗi khi kết nối tới máy chủ API để tải báo cáo mã{' '}
                <code className="font-mono bg-surface-secondary px-1.5 py-0.5 rounded text-ink border border-border">{id}</code>.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-3">
              <Button
                onClick={() => setRetryCount((c) => c + 1)}
                className="bg-amber text-ink border border-amber-border hover:bg-amber-hover text-xs font-semibold h-8 px-4"
              >
                <RotateCw className="size-3.5 mr-1.5" />
                Thử lại
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

  if (isNotFound || !activeReport) {
    return (
      <WorkspaceShell
        activeSection="reports"
        context={<PageCrumbs items={[{ label: 'Thư viện báo cáo', to: '/reports' }, { label: 'Không tìm thấy' }]} />}
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

  const isAdaptive = (activeReport as { report_version?: string })?.report_version === 'er-report-v1';
  const legacyReport = activeReport as AnalysisReport;
  const adaptiveReport = activeReport as AdaptiveReportResponse;

  const QUESTION_TYPE_BREADCRUMB: Record<string, string> = {
    lookup: 'Tra cứu',
    company_profile: 'Hồ sơ doanh nghiệp',
    ranking: 'Xếp hạng',
    trend: 'Xu hướng',
    head_to_head: 'So sánh trực tiếp',
    sector_theme: 'Toàn ngành',
    relationship: 'Tương quan',
  };

  const peerText =
    legacyReport.peer_tickers && legacyReport.peer_tickers.length > 0
      ? ` & ${legacyReport.peer_tickers.join(', ')}`
      : '';
  const scopeLabel =
    [legacyReport.target_ticker, peerText ? peerText.trim() : '', legacyReport.period]
      .filter(Boolean)
      .join(' · ') ||
    (isAdaptive
      ? adaptiveReport.report_spec?.note_label ||
        QUESTION_TYPE_BREADCRUMB[(adaptiveReport as { question_type?: string }).question_type || ''] ||
        'Báo cáo phân tích'
      : QUESTION_TYPE_BREADCRUMB[(legacyReport as { question_type?: string }).question_type || ''] ||
        (legacyReport as unknown as { report_spec?: { note_label?: string } }).report_spec?.note_label ||
        'Báo cáo phân tích');

  const isDemo = SAMPLE_REPORTS.some(
    (sample) => (sample.slug === id || sample.id === id) && sample.report.report_id === activeReport.report_id
  );

  return (
    <WorkspaceShell
      activeSection="reports"
      context={
        <PageCrumbs
          items={[{ label: 'Thư viện báo cáo', to: '/reports' }, { label: scopeLabel }]}
          aside={
            isDemo ? (
              <StatusPill tone="neutral">Mẫu minh họa</StatusPill>
            ) : activeReport.status === 'accepted_with_limitations' ? (
              <StatusPill tone="warning">Chấp nhận có giới hạn</StatusPill>
            ) : activeReport.status === 'completed' || activeReport.status === 'accepted' ? (
              <StatusPill tone="ready">Đã kiểm định</StatusPill>
            ) : (
              <StatusPill tone="neutral">{activeReport.status ? `Trạng thái: ${activeReport.status}` : 'Chưa có trạng thái'}</StatusPill>
            )
          }
        />
      }
    >
      {isAdaptive ? (
        <AdaptiveReport report={adaptiveReport} metrics={capabilityMetrics} />
      ) : (
        <LegacyReport report={legacyReport} isDemo={isDemo} />
      )}
    </WorkspaceShell>
  );
}
