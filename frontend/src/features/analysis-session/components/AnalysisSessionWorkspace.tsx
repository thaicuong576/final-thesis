import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation, useSearchParams, useInRouterContext } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { TraceStep } from '../model/types';
import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { useTraceStream } from '../useTraceStream';
import { ReasoningTimeline } from './ReasoningTimeline';
import { ProcessTrace } from './ProcessTrace';
import { AdaptiveReport, type AdaptiveReportResponse } from '@/features/equity-report';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import { apiFetch } from '@/shared/api/apiClient';

const FIXTURE_LOADERS: Record<string, () => Promise<unknown>> = {
  t01: () => import('../../../../../experiments/er9/runs/er9-T01-hierarchical_with_critique-r0.json'),
  t03: () => import('../../../../../experiments/er9/runs/er9-T03-hierarchical_with_critique-r0.json'),
  t05: () => import('../../../../../experiments/er9/runs/er9-T05-hierarchical_with_critique-r0.json'),
  t07: () => import('../../../../../experiments/er9/runs/er9-T07-hierarchical_with_critique-r0.json'),
  t09: () => import('../../../../../experiments/er9/runs/er9-T09-hierarchical_with_critique-r0.json'),
};

export interface AnalysisSessionWorkspaceProps {
  report?: AdaptiveReportResponse | null;
  streamRequest?: { query: string; upload_id?: string } | null;
  request?: { query: string; upload_id?: string } | null;
  isLiveStream?: boolean;
  steps?: TraceStep[];
  events?: unknown[]; // Backward compatibility with previous test props
  driverMode?: string;
  driverStep?: number;
  capabilities?: AnalysisCapabilities | null;
  onBackToComposer?: () => void;
  onViewReport?: (reportId: string) => void;
  onBlocked?: (info: { code?: string; message: string; suggestions?: string[] }) => void;
  apiEndpoint?: string;
  autoRedirect?: boolean;
}

export function AnalysisSessionWorkspace(props: AnalysisSessionWorkspaceProps) {
  const inRouter = useInRouterContext();
  if (inRouter) {
    return <RouterBoundAnalysisSessionWorkspace {...props} />;
  }
  return <AnalysisSessionWorkspaceContent {...props} />;
}

function RouterBoundAnalysisSessionWorkspace(props: AnalysisSessionWorkspaceProps) {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const handleOpenReport = useCallback(
    (reportId: string) => {
      if (props.onViewReport) {
        props.onViewReport(reportId);
      } else {
        navigate(`/reports/${reportId}`);
      }
    },
    [navigate, props]
  );

  return (
    <AnalysisSessionWorkspaceContent
      {...props}
      locationState={location.state as Record<string, unknown> | null}
      searchParams={searchParams}
      onViewReport={handleOpenReport}
    />
  );
}

interface WorkspaceContentProps extends AnalysisSessionWorkspaceProps {
  locationState?: Record<string, unknown> | null;
  searchParams?: URLSearchParams;
}

function AnalysisSessionWorkspaceContent({
  report: propReport,
  streamRequest,
  request,
  isLiveStream = true,
  steps: propSteps,
  capabilities,
  onBackToComposer,
  onViewReport,
  onBlocked,
  apiEndpoint,
  autoRedirect = false
}: WorkspaceContentProps) {
  const activeRequest = streamRequest || request || null;

  const {
    steps: streamSteps,
    isStreaming,
    isDisconnected,
    reportId,
    liveWorkState,
    retry
  } = useTraceStream({
    request: isLiveStream && activeRequest ? { query: activeRequest.query, upload_id: activeRequest.upload_id } : null,
    autoStart: isLiveStream && Boolean(activeRequest?.query),
    apiEndpoint,
    capabilities,
    initialSteps: propSteps,
    onBlocked
  });

  const activeSteps = useMemo(() => {
    if (propSteps && propSteps.length > 0) return propSteps;
    return streamSteps;
  }, [propSteps, streamSteps]);

  const effectiveReportId = useMemo(() => {
    if (reportId) return reportId;
    const readyStep = activeSteps.find((s) => s.kind === 'report_ready');
    return (readyStep?.detail?.report_id as string | undefined) || null;
  }, [reportId, activeSteps]);

  const inlineReport = useMemo(() => {
    const readyStep = activeSteps.find((s) => s.kind === 'report_ready');
    const rep = readyStep?.detail?.report;
    return (rep as unknown as AdaptiveReportResponse) || null;
  }, [activeSteps]);

  const [fetchedReport, setFetchedReport] = useState<AdaptiveReportResponse | null>(null);

  useEffect(() => {
    if (propReport || inlineReport || !effectiveReportId || !isLiveStream) return;

    let isMounted = true;
    const loadReport = async () => {
      try {
        const cleanId = effectiveReportId.toLowerCase().replace(/^er9-/, '');
        if (cleanId in FIXTURE_LOADERS) {
          const mod = (await FIXTURE_LOADERS[cleanId]()) as {
            default?: { response?: unknown };
            response?: unknown;
          };
          const loaded = mod.default?.response || mod.default || mod.response || mod;
          if (isMounted && loaded) {
            setFetchedReport(loaded as unknown as AdaptiveReportResponse);
          }
          return;
        }

        const baseUrl = getApiBaseUrl();
        const origin =
          typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
            ? window.location.origin
            : '';
        const base = baseUrl || origin;

        let res = await apiFetch(`${base}/api/reports/${effectiveReportId}`, {
          headers: { Accept: 'application/json' }
        });
        if (!res.ok) {
          res = await apiFetch(`${base}/api/runs/${effectiveReportId}`, {
            headers: { Accept: 'application/json' }
          });
        }
        if (res.ok && isMounted) {
          const data = await res.json();
          const rep = (data.report || data) as Record<string, unknown>;
          setFetchedReport(rep as unknown as AdaptiveReportResponse);
        }
      } catch {
        // ignore
      }
    };

    void loadReport();
    return () => {
      isMounted = false;
    };
  }, [propReport, inlineReport, effectiveReportId, isLiveStream]);

  const displayReport = propReport || inlineReport || fetchedReport;
  const query = activeRequest?.query || '';

  return (
    <div className="mx-auto max-w-[1180px] space-y-5 py-2">
      {/* Navigation / back link */}
      {onBackToComposer && (
        <div>
          <button
            type="button"
            onClick={onBackToComposer}
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-text-secondary transition-colors hover:text-text-primary"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Quay lại trang hỏi</span>
          </button>
        </div>
      )}

      {/* One chronological timeline ("Dòng suy luận") */}
      <ReasoningTimeline
        steps={activeSteps}
        query={query}
        live={isStreaming || (isLiveStream && !propSteps?.length)}
        reportId={effectiveReportId}
        isDisconnected={isDisconnected}
        liveWorkState={liveWorkState}
        onOpenReport={onViewReport}
        onRetry={retry}
        autoRedirect={autoRedirect}
      />

      {/* Fresh Report Result */}
      {displayReport && (
        <section
          aria-label="Báo cáo phân tích vừa tạo"
          className="mt-8 border-t border-border-subtle pt-6 animate-in fade-in duration-200"
        >
          <AdaptiveReport report={displayReport} />
        </section>
      )}

      {/* Screen C: Interactive Process Trace */}
      <ProcessTrace
        steps={activeSteps}
        live={isStreaming}
      />
    </div>
  );
}
