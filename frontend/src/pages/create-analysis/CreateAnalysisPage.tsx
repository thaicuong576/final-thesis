import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';
import { useAnalysisCapabilities } from '../../features/create-analysis/hooks/useAnalysisCapabilities';
import { buildSupportedStreamRequest } from '../../features/create-analysis/model/streamRequest';
import {
  ActiveDatasetCard,
  HeroComposer,
  SuggestedQuestions,
  RecentReportsSummary,
  RequestInterpretationCard,
  ScopeMismatchAlert,
  ScopeAdjustmentDrawer,
  parseAnalysisQuestion,
  type ParseResult,
  type ParsedScope,
  type Screen1Mode
} from '../../features/analysis-composer';
import {
  AnalysisSessionWorkspace,
  getScenarioEvents,
  resolveScenarioKey,
  type AnalysisSessionEvent,
  type DriverMode
} from '../../features/analysis-session';
import type { AnalysisStreamRequest } from '../../features/analysis-session/useAnalysisSessionStream';

type PageMode = Screen1Mode | 'SESSION';

export interface CreateAnalysisPageProps {
  initialMode?: PageMode;
}

export function CreateAnalysisPage({ initialMode }: CreateAnalysisPageProps = {}) {
  const capabilitiesQuery = useAnalysisCapabilities();
  const capabilities = capabilitiesQuery.data;

  const [mode, setMode] = useState<PageMode>(initialMode || 'DEFAULT');
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [streamRequest, setStreamRequest] = useState<AnalysisStreamRequest | null>(null);
  const [isLiveStream, setIsLiveStream] = useState<boolean>(false);
  const [activeEvents, setActiveEvents] = useState<AnalysisSessionEvent[]>([]);
  const [driverMode, setDriverMode] = useState<DriverMode>('FROZEN');
  const [driverStep, setDriverStep] = useState<number | undefined>(undefined);
  const [scopeDrawerOpen, setScopeDrawerOpen] = useState(false);
  const [scopeExecutionError, setScopeExecutionError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();


  const handleQuestionChange = useCallback(
    (question: string) => {
      setCurrentQuestion(question);
      if (!capabilities) return;
      if (!question.trim()) {
        setParseResult(null);
        return;
      }
      const result = parseAnalysisQuestion(question, capabilities);
      setParseResult(result);
    },
    [capabilities]
  );

  const handleQuestionSubmit = useCallback(
    (question: string) => {
      if (!capabilities) return;
      const trimmed = question.trim();
      if (!trimmed) return;
      setCurrentQuestion(trimmed);
      setScopeExecutionError(null);

      const result = parseAnalysisQuestion(trimmed, capabilities);
      setParseResult(result);

      if (result.mismatch.isMismatch) {
        setMode('MISMATCH');
      } else {
        setMode('INTERPRETED');
      }
    },
    [capabilities]
  );

  const handleSelectSuggestion = useCallback(
    (promptText: string) => {
      setCurrentQuestion(promptText);
      if (!capabilities) return;
      const result = parseAnalysisQuestion(promptText, capabilities);
      setParseResult(result);
      // DO NOT auto-submit: let analyst review/edit before execution
    },
    [capabilities]
  );

  useEffect(() => {
    if (!capabilities) return;

    // Audit and demo parameter support: mockScenario or scenario + mockStep + autoplay
    const scenarioParam = searchParams.get('mockScenario') || searchParams.get('scenario');
    const stepParam = searchParams.get('mockStep');
    const isAutoplay = searchParams.get('autoplay') === 'true';

    if (scenarioParam) {
      const canonicalKey = resolveScenarioKey(scenarioParam);
      const events = getScenarioEvents(canonicalKey);
      const parsedStep = stepParam ? parseInt(stepParam, 10) : undefined;
      const timer = setTimeout(() => {
        setIsLiveStream(false);
        setActiveEvents(events);
        setDriverMode(isAutoplay ? 'AUTOPLAY' : 'FROZEN');
        setDriverStep(parsedStep !== undefined && !isNaN(parsedStep) ? parsedStep : undefined);
        setMode('SESSION');
      }, 0);
      return () => clearTimeout(timer);
    }

    const q = searchParams.get('q');
    if (q && mode === 'DEFAULT') {
      const timer = setTimeout(() => {
        handleQuestionSubmit(q);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [searchParams, capabilities, mode, handleQuestionSubmit]);

  if (capabilitiesQuery.isPending) {
    return (
      <WorkspaceShell activeSection="analysis">
        <LoadingState />
      </WorkspaceShell>
    );
  }

  if (capabilitiesQuery.isError || !capabilities) {
    return (
      <WorkspaceShell activeSection="analysis">
        <ErrorState onRetry={() => void capabilitiesQuery.refetch()} />
      </WorkspaceShell>
    );
  }

  function handleScopeOverride(updatedScope: ParsedScope) {
    if (!parseResult) return;
    setScopeExecutionError(null);
    setParseResult({
      ...parseResult,
      scope: updatedScope
    });
  }

  function handleConfirmAndAnalyze() {
    if (!capabilities || !parseResult) return;
    const supported = buildSupportedStreamRequest(parseResult.rawQuestion, parseResult.scope, capabilities);
    if (!supported.request) {
      setScopeExecutionError(supported.reason);
      return;
    }
    setScopeExecutionError(null);
    setStreamRequest(supported.request);
    setSearchParams({ q: parseResult.rawQuestion });
    setIsLiveStream(true);
    setActiveEvents([]);
    setDriverMode('AUTOPLAY');
    setDriverStep(undefined);
    setMode('SESSION');
  }

  return (
    <WorkspaceShell
      activeSection="analysis"
      context={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="font-bold text-ink">BÀN LÀM VIỆC PHÂN TÍCH</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-ink-secondary">
            <span className={`w-2 h-2 rounded-full ${capabilities.analysis_available === true ? 'bg-ready' : 'bg-warning'}`} aria-hidden="true" />
            <span className="font-mono text-[11px]">{capabilities.analysis_available === true ? 'API xác nhận dữ liệu sẵn sàng' : 'API chưa xác nhận dữ liệu khả dụng'}</span>
          </div>
        </div>
      }
    >
      <div className="min-h-[calc(100vh-80px)] bg-workspace py-5 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1120px] space-y-5">
          {/* Active Dataset Context Bar (Only displayed in composer/interpretation modes) */}
          {mode !== 'SESSION' && (
            <ActiveDatasetCard
              capabilities={capabilities}
            />
          )}

          {/* SCREEN 1: DEFAULT HERO WORKSPACE */}
          {mode === 'DEFAULT' && (
            <div className="space-y-6 pt-1">
              <HeroComposer
                question={currentQuestion}
                onQuestionChange={handleQuestionChange}
                onSubmit={handleQuestionSubmit}
                parsedScope={parseResult?.scope || null}
                availableEntities={capabilities.entities}
                availablePeriods={capabilities.periods}
                availableMetrics={capabilities.metrics}
                onOpenScopeAdjustment={() => setScopeDrawerOpen(true)}
                isSubmitting={false}
              />

              <SuggestedQuestions capabilities={capabilities} onSelectPrompt={handleSelectSuggestion} />

              <RecentReportsSummary />
            </div>
          )}

          {/* SCREEN 1: INTERPRETED STATE */}
          {mode === 'INTERPRETED' && parseResult && (
            <div className="space-y-4">
              <RequestInterpretationCard
                parseResult={parseResult}
                onConfirm={handleConfirmAndAnalyze}
                onOpenScopeAdjustment={() => setScopeDrawerOpen(true)}
                onEditQuestion={() => setMode('DEFAULT')}
                isConfirming={false}
                executionBlockReason={
                  buildSupportedStreamRequest(parseResult.rawQuestion, parseResult.scope, capabilities).reason || scopeExecutionError
                }
              />
            </div>
          )}

          {/* SCREEN 1: MISMATCH STATE */}
          {mode === 'MISMATCH' && parseResult && (
            <div className="space-y-4">
              <ScopeMismatchAlert
                mismatch={parseResult.mismatch}
                rawQuestion={parseResult.rawQuestion}
                onEditQuestion={() => setMode('DEFAULT')}
              />
            </div>
          )}

          {/* SCREEN 2: ANALYSIS SESSION WORKSPACE */}
          {mode === 'SESSION' && (
            <AnalysisSessionWorkspace
              streamRequest={streamRequest}
              isLiveStream={isLiveStream}
              events={isLiveStream ? undefined : activeEvents}
              driverMode={driverMode}
              driverStep={driverStep}
              onBackToComposer={() => {
                setMode('DEFAULT');
                setIsLiveStream(false);
                setSearchParams({});
              }}
            />
          )}
        </div>
      </div>

      {/* CONTEXTUAL MODALS / DRAWERS */}
      {scopeDrawerOpen && parseResult && (
        <ScopeAdjustmentDrawer
          open={scopeDrawerOpen}
          onOpenChange={setScopeDrawerOpen}
          capabilities={capabilities}
          currentScope={parseResult.scope}
          rawQuestion={parseResult.rawQuestion}
          onApplyScope={handleScopeOverride}
        />
      )}
    </WorkspaceShell>
  );
}

function LoadingState() {
  return (
    <div className="grid min-h-[60vh] place-items-center bg-workspace p-6">
      <p className="text-xs font-mono text-ink-secondary" role="status">
        Đang chuẩn bị bộ dữ liệu và động cơ phân tích…
      </p>
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="grid min-h-[60vh] place-items-center bg-workspace p-6">
      <div className="border border-[#c84b3f]/30 bg-card p-6 text-center max-w-md rounded-md">
        <p className="font-bold text-sm text-blocked">Không thể kết nối bộ dữ liệu.</p>
        <p className="mt-2 text-xs text-ink-secondary leading-relaxed">
          Không thể xác nhận phạm vi từ API. Hãy thử lại khi dịch vụ dữ liệu sẵn sàng.
        </p>
        <Button type="button" variant="outline" onClick={onRetry} className="mt-4 border-line text-xs">Thử tải lại</Button>
      </div>
    </div>
  );
}
