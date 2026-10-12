import { useCallback, useMemo } from 'react';
import { useNavigate, useLocation, useSearchParams, useInRouterContext } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { TraceStep } from '../model/types';
import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { useTraceStream } from '../useTraceStream';
import { AgentStage } from './AgentStage';
import { ProcessTrace } from './ProcessTrace';

export interface AnalysisSessionWorkspaceProps {
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
  capabilities,
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

      {/* Screen B: Orchestrator & child agents board */}
      <AgentStage
        steps={activeSteps}
        query={query}
        live={isStreaming || (isLiveStream && !propSteps?.length)}
        reportId={reportId}
        isDisconnected={isDisconnected}
        liveWorkState={liveWorkState}
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
