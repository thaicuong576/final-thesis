import { useCallback, useMemo } from 'react';
import { useNavigate, useLocation, useSearchParams, useInRouterContext } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { TraceStep } from '../model/types';
import { useTraceStream } from '../useTraceStream';
import { OrchestratorBoard } from './OrchestratorBoard';
import { ProcessTrace } from './ProcessTrace';

export interface AnalysisSessionWorkspaceProps {
  streamRequest?: { query: string } | null;
  request?: { query: string } | null;
  isLiveStream?: boolean;
  steps?: TraceStep[];
  events?: unknown[]; // Backward compatibility with previous test props
  driverMode?: string;
  driverStep?: number;
  onBackToComposer?: () => void;
  onViewReport?: (reportId: string) => void;
  onBlocked?: (info: { code?: string; message: string; suggestions?: string[] }) => void;
  apiEndpoint?: string;
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
  streamRequest,
  request,
  isLiveStream = true,
  steps: propSteps,
  onBackToComposer,
  onViewReport,
  onBlocked,
  apiEndpoint
}: WorkspaceContentProps) {
  const activeRequest = streamRequest || request || null;

  const {
    steps: streamSteps,
    isStreaming,
    isDisconnected,
    reportId,
    retry
  } = useTraceStream({
    request: isLiveStream && activeRequest ? { query: activeRequest.query } : null,
    autoStart: isLiveStream && Boolean(activeRequest?.query),
    apiEndpoint,
    initialSteps: propSteps,
    onReportReady: onViewReport,
    onBlocked
  });

  const activeSteps = useMemo(() => {
    if (propSteps && propSteps.length > 0) return propSteps;
    return streamSteps;
  }, [propSteps, streamSteps]);

  const query = activeRequest?.query || '';

  return (
    <div className="space-y-4 max-w-4xl mx-auto py-2">
      {/* Navigation / back link */}
      {onBackToComposer && (
        <div>
          <button
            type="button"
            onClick={onBackToComposer}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Quay lại trang hỏi</span>
          </button>
        </div>
      )}

      {/* Screen B: Orchestrator & child agents board */}
      <OrchestratorBoard
        steps={activeSteps}
        query={query}
        reportId={reportId}
        isDisconnected={isDisconnected}
        onOpenReport={onViewReport}
        onRetry={retry}
      />

      {/* Screen C: Interactive Process Trace */}
      <ProcessTrace
        steps={activeSteps}
        live={isStreaming}
      />
    </div>
  );
}
