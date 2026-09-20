import { useState, useMemo } from 'react';
import { useLocation, useSearchParams, useInRouterContext } from 'react-router-dom';
import { Radio, RotateCw, RefreshCw } from 'lucide-react';
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
    (locationState?.target_ticker as string | undefined) ||
    'ACB';
  const peersParam =
    searchParams.get('peers') ||
    (locationState?.peer_tickers as string[] | string | undefined);
  const periodParam =
    searchParams.get('period') ||
    (locationState?.period as string | undefined) ||
    '2024';
  const queryParam =
    searchParams.get('q') ||
    searchParams.get('query') ||
    (locationState?.query as string | undefined);


  const dynamicRequest: AnalysisStreamRequest = useMemo(() => {
    if (propStreamRequest) return propStreamRequest;
    if (legacyStreamRequest) return legacyStreamRequest;
    if (stateRequest) return stateRequest;

    const peerTickers = Array.isArray(peersParam)
      ? peersParam
      : peersParam
      ? peersParam.split(',').map((s: string) => s.trim())
      : ['TCB', 'MBB'];

    const question =
      queryParam ||
      `So sánh chất lượng tài sản của ${targetTickerParam}, ${peerTickers.join(' và ')} trong năm ${periodParam} và xác định ngân hàng cải thiện rõ nhất.`;

    return {
      query: question,
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

  // Determine whether to use Live SSE Stream:
  // - If explicit viewModel / legacySession is passed: pure static mock view
  // - If events are passed and propIsLiveStream is not explicitly true: pure driver mock
  // - If hasMockScenarioParam: pure driver mock
  // - Otherwise (no events prop, or propIsLiveStream=true): connect Live SSE Stream
  const hasExternalViewModel = Boolean(externalViewModel || legacySession);
  const hasEventsProp = events.length > 0;
  const wantsLiveStream =
    propIsLiveStream === true ||
    (!hasExternalViewModel && !hasEventsProp && !hasMockScenarioParam);

  const [activeMode, setActiveMode] = useState<'LIVE' | 'MOCK'>(
    wantsLiveStream ? 'LIVE' : 'MOCK'
  );

  // 1. Live SSE Stream Hook
  const liveStream = useAnalysisSessionStream({
    request: dynamicRequest,
    autoStart: wantsLiveStream && activeMode === 'LIVE',
    fallbackToMockOnError: true
  });

  const mockDriverEvents = useMemo(() => {
    if (hasEventsProp) return events;
    if (liveStream.connectionMode === 'MOCK' && liveStream.events.length > 0) {
      return liveStream.events;
    }
    return [];
  }, [hasEventsProp, events, liveStream.connectionMode, liveStream.events]);

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
      if (liveStream.connectionMode === 'MOCK' && driverMode === 'AUTOPLAY') {
        return mockDriver.viewModel;
      }
      return liveStream.viewModel;
    }

    if (hasEventsProp || (liveStream.connectionMode === 'MOCK' && mockDriverEvents.length > 0)) {
      return mockDriver.viewModel;
    }

    return {
      sessionId: 'empty',
      rawQuestion: dynamicRequest.query,
      datasetName: 'Ngân hàng Việt Nam 2024',
      scopeSignature: `${dynamicRequest.target_ticker} | ${
        dynamicRequest.peer_tickers && dynamicRequest.peer_tickers.length > 0
          ? 'So sánh'
          : 'Độc lập'
      } | ${dynamicRequest.period}`,
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
    liveStream.connectionMode,
    driverMode,
    hasEventsProp,
    mockDriver.viewModel,
    mockDriverEvents.length,
    dynamicRequest
  ]);

  const [selectedSpecialist, setSelectedSpecialist] =
    useState<SpecialistSessionState | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleOpenSpecialist = (session: SpecialistSessionState) => {
    setSelectedSpecialist(session);
    setSheetOpen(true);
  };

  const isActuallyLive =
    activeMode === 'LIVE' &&
    liveStream.connectionMode === 'LIVE' &&
    !liveStream.isMockFallback;

  const handleToggleMode = () => {
    if (isActuallyLive) {
      setActiveMode('MOCK');
      liveStream.switchToMock();
    } else {
      setActiveMode('LIVE');
      liveStream.switchToLive();
    }
  };

  // Status Badge Component
  const connectionBadge = (
    <div className="flex items-center gap-2">
      {isActuallyLive ? (
        <Badge
          variant="outline"
          className="gap-1.5 px-2 py-0.5 text-[11px] font-semibold bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2f9e62] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2f9e62]" />
          </span>
          <span>Live SSE Stream</span>
        </Badge>
      ) : (
        <Badge
          variant="outline"
          className="gap-1.5 px-2 py-0.5 text-[11px] font-semibold bg-[#fbefcf] text-[#cf8500] border-[#d88b00]/30"
        >
          <span className="h-2 w-2 rounded-full bg-[#cf8500]" />
          <span>Demo Mock Mode</span>
        </Badge>
      )}

      {/* Mode toggle button (only when not rigidly controlled by external viewModel prop) */}
      {!hasExternalViewModel && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleToggleMode}
          className="h-6 px-2 text-[10px] font-mono text-ink-secondary hover:text-ink hover:bg-surface-secondary border border-border-subtle"
        >
          {isActuallyLive ? (
            <>
              <RotateCw className="w-2.5 h-2.5 mr-1" aria-hidden="true" />
              Chuyển Mock
            </>
          ) : (
            <>
              <RefreshCw className="w-2.5 h-2.5 mr-1" aria-hidden="true" />
              Kết nối Live
            </>
          )}
        </Button>
      )}
    </div>
  );

  const reportArtifact = liveStream.report;
  const targetReportPath = reportArtifact?.report_id
    ? `/reports/${reportArtifact.report_id}`
    : '/reports/mock-session-2024-acb-tcb';

  return (
    <div className="space-y-4">
      {/* Backend Fallback Notification Banner */}
      {liveStream.isMockFallback && (
        <div className="border border-[#d88b00]/30 bg-[#fbefcf] text-[#78350f] rounded-md px-3.5 py-2 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-[#cf8500] shrink-0" aria-hidden="true" />
            <span>
              Không thể kết nối Live SSE tới backend ({liveStream.backendTarget || 'https://final-thesis-zgwt.onrender.com'}). Hệ thống đã tự động chuyển sang chế độ Demo Mock để không làm gián đoạn phân tích.
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setActiveMode('LIVE');
              liveStream.retry();
            }}
            className="h-6 text-[11px] px-2.5 border-[#d88b00]/40 text-[#78350f] hover:bg-[#d88b00]/10 shrink-0 self-start sm:self-auto"
          >
            Thử lại Live
          </Button>
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
        onViewReport={
          onViewReport && reportArtifact
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

