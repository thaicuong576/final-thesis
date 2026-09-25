import { useState, useMemo } from 'react';
import { useLocation, useSearchParams, useInRouterContext } from 'react-router-dom';
import { Radio, Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type {
  AnalysisSessionEvent,
  AnalysisSessionViewModel,
  SpecialistSessionState
} from '../model/types';
import { useAnalysisSessionDriver, type DriverMode } from '../mock/MockAnalysisSessionDriver';
import {
  useAnalysisSessionStream,
  type AnalysisStreamRequest
} from '../useAnalysisSessionStream';
import { SessionContextBar } from './SessionContextBar';
import { OrchestratorThread } from './OrchestratorThread';
import { SpecialistSessionSheet } from './SpecialistSessionSheet';
import type { AnalysisReport } from '../../analysis-report';

export interface AnalysisSessionWorkspaceProps {
  // Can receive either direct viewModel or event list for driver
  viewModel?: AnalysisSessionViewModel;
  events?: AnalysisSessionEvent[];
  driverMode?: DriverMode;
  driverStep?: number;
  onBackToComposer?: () => void;
  // Compatibility prop with previous snapshot signature:
  session?: AnalysisSessionViewModel;
  // Live SSE stream configuration:
  streamRequest?: AnalysisStreamRequest | null;
  request?: AnalysisStreamRequest | null;
  isLiveStream?: boolean;
  onViewReport?: (report: AnalysisReport) => void;
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
  return (
    <AnalysisSessionWorkspaceContent
      {...props}
      locationState={location.state as Record<string, unknown> | null}
      searchParams={searchParams}
    />
  );
}

interface WorkspaceContentProps extends AnalysisSessionWorkspaceProps {
  locationState?: Record<string, unknown> | null;
  searchParams?: URLSearchParams;
}

function AnalysisSessionWorkspaceContent({
  viewModel: externalViewModel,
  session: legacySession,
  events = [],
  driverMode = 'FROZEN',
  driverStep,
  onBackToComposer,
  streamRequest: propStreamRequest,
  request: legacyStreamRequest,
  isLiveStream: propIsLiveStream,
  onViewReport,
  locationState,
  searchParams = new URLSearchParams()
}: WorkspaceContentProps) {
  // Check if explicit mock scenario is requested via query params
  const hasMockScenarioParam = Boolean(
    searchParams.get('mockScenario') || searchParams.get('scenario')
  );

  // Dynamic scope / ticker extraction from navigation state or URL params
  const stateRequest = locationState?.streamRequest as AnalysisStreamRequest | undefined;
  const targetTickerParam =
    searchParams.get('ticker') ||
    searchParams.get('target') ||
    (locationState?.target_ticker as string | undefined);
  const peersParam =
    searchParams.get('peers') ||
    (locationState?.peer_tickers as string[] | string | undefined);
  const periodParam =
    searchParams.get('period') ||
    (locationState?.period as string | undefined);
  const queryParam =
    searchParams.get('q') ||
    searchParams.get('query') ||
    (locationState?.query as string | undefined);


  const dynamicRequest = useMemo<AnalysisStreamRequest | null>(() => {
    if (propStreamRequest) return propStreamRequest;
    if (legacyStreamRequest) return legacyStreamRequest;
    if (stateRequest) return stateRequest;
    if (!queryParam?.trim()) return null;

    const peerTickers = Array.isArray(peersParam)
      ? peersParam
      : peersParam
      ? peersParam.split(',').map((s: string) => s.trim())
      : undefined;

    return {
      query: queryParam,
      target_ticker: targetTickerParam,
      peer_tickers: peerTickers,
      period: periodParam
    };
  }, [
    propStreamRequest,
    legacyStreamRequest,
    stateRequest,
    peersParam,
    queryParam,
    targetTickerParam,
    periodParam
  ]);

  // Demo fixtures are activated only through explicit scenario/event inputs.
  const hasExternalViewModel = Boolean(externalViewModel || legacySession);
  const hasEventsProp = events.length > 0;
  const wantsLiveStream =
    propIsLiveStream === true ||
    (!hasExternalViewModel && !hasEventsProp && !hasMockScenarioParam);
  const activeMode = wantsLiveStream ? 'LIVE' : 'MOCK';

  // 1. Live SSE Stream Hook
  const liveStream = useAnalysisSessionStream({
    request: dynamicRequest,
    autoStart: wantsLiveStream && activeMode === 'LIVE' && Boolean(dynamicRequest)
  });

  const mockDriverEvents = useMemo(() => (hasEventsProp ? events : []), [hasEventsProp, events]);

  // 2. Mock Analysis Session Driver
  const mockDriver = useAnalysisSessionDriver({
    events: mockDriverEvents,
    mode: driverMode,
    step: driverStep
  });

  // Active view model derivation
  const activeViewModel: AnalysisSessionViewModel = useMemo(() => {
    if (externalViewModel) return externalViewModel;
    if (legacySession) return legacySession;

    if (activeMode === 'LIVE') {
      return liveStream.viewModel;
    }

    if (hasEventsProp || hasMockScenarioParam) {
      return mockDriver.viewModel;
    }

    return {
      sessionId: 'empty',
      rawQuestion: dynamicRequest?.query || '',
      datasetName: 'Snapshot chưa được xác nhận',
      scopeSignature: dynamicRequest?.target_ticker ? `${dynamicRequest.target_ticker} | ${
        dynamicRequest.peer_tickers && dynamicRequest.peer_tickers.length > 0
          ? 'So sánh'
          : 'Độc lập'
      } | ${dynamicRequest.period || 'Kỳ chưa công bố'}` : '',
      currentPhase: 'INITIALIZING',
      phaseLabel: 'Đang chuẩn bị',
      threadItems: [],
      specialistSessions: {},
      invocations: [],
      reportReady: false
    };
  }, [
    externalViewModel,
    legacySession,
    activeMode,
    liveStream.viewModel,
    hasMockScenarioParam,
    hasEventsProp,
    mockDriver.viewModel,
    dynamicRequest
  ]);

  const [selectedSpecialist, setSelectedSpecialist] =
    useState<SpecialistSessionState | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleOpenSpecialist = (session: SpecialistSessionState) => {
    setSelectedSpecialist(session);
    setSheetOpen(true);
  };

  const isActuallyLive = activeMode === 'LIVE' && Boolean(dynamicRequest);

  // Status Badge Component
  const connectionBadge = (
    <div className="flex items-center gap-2">
      {wantsLiveStream ? (
        <Badge
          variant="outline"
          className="gap-1.5 px-2 py-0.5 text-[11px] font-semibold bg-surface-secondary text-ink-secondary border-border-subtle"
        >
          <Radio className="size-3.5" aria-hidden="true" />
          <span>{liveStream.isError ? 'API lỗi' : liveStream.isComplete ? 'API đã trả về phản hồi' : liveStream.isStreaming ? 'Đang gọi API' : 'Chưa có phản hồi API'}</span>
        </Badge>
      ) : (
        <Badge
          variant="outline"
          className="gap-1.5 px-2 py-0.5 text-[11px] font-semibold bg-warning-soft text-ink border-warning/40"
        >
          <Info className="size-3.5 text-warning" aria-hidden="true" />
          <span>Mô phỏng · dữ liệu minh họa</span>
        </Badge>
      )}
    </div>
  );

  const reportArtifact = liveStream.report;
  const targetReportPath = reportArtifact?.report_id ? `/reports/${reportArtifact.report_id}` : undefined;

  return (
    <div className="space-y-4">
      {/* Backend Live Connection Error Banner */}
      {wantsLiveStream && !dynamicRequest && (
        <div className="rounded-md border border-warning/40 bg-warning-soft/50 p-3 text-xs text-ink" role="alert">
          Chưa có câu hỏi được xác nhận. Quay lại màn hình tạo phân tích để kiểm tra phạm vi trước khi gửi API.
        </div>
      )}

      {liveStream.isError && (
        <div className="border border-[#c84b3f]/30 bg-[#fdf2f2] text-[#c84b3f] rounded-md px-3.5 py-2 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-[#c84b3f] shrink-0" aria-hidden="true" />
            <span>
              Lỗi kết nối Live SSE tới backend ({liveStream.backendTarget}): {liveStream.error?.message || 'Không thể thiết lập kết nối phân tích thời gian thực'}.
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                liveStream.retry();
              }}
              className="h-6 text-[11px] px-2.5 border-[#c84b3f]/40 text-[#c84b3f] hover:bg-[#c84b3f]/10"
            >
              Thử lại Live
            </Button>
          </div>
        </div>
      )}

      {/* Layer A: Compact Session Context Bar */}
      <SessionContextBar
        datasetName={activeViewModel.datasetName}
        scopeSignature={activeViewModel.scopeSignature}
        currentPhase={activeViewModel.currentPhase}
        phaseLabel={activeViewModel.phaseLabel}
        onBackToComposer={onBackToComposer}
        connectionBadge={connectionBadge}
      />

      {/* Layer B & C: Unified Chronological Orchestrator Thread with Inline Specialists */}
      <OrchestratorThread
        threadItems={activeViewModel.threadItems}
        specialistSessions={activeViewModel.specialistSessions}
        onSelectSpecialist={handleOpenSpecialist}
        targetReportPath={targetReportPath}
        reportData={reportArtifact}
        isDemo={!wantsLiveStream}
        isStreaming={liveStream.isStreaming}
        onViewReport={
          isActuallyLive && onViewReport && reportArtifact
            ? () => onViewReport(reportArtifact)
            : undefined
        }
      />

      {/* Layer D: Specialist Inspection Sheet */}
      <SpecialistSessionSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        session={selectedSpecialist}
      />
    </div>
  );
}

