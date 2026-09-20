import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';
import { useAnalysisCapabilities } from '../../features/create-analysis/hooks/useAnalysisCapabilities';
import { analysisService } from '../../entities/analysis/api/analysisService';
import type { AnalysisRequest } from '../../entities/analysis/model/types';
import {
  ActiveDatasetCard,
  HeroComposer,
  SuggestedQuestions,
  RecentReportsSummary,
  RequestInterpretationCard,
  ScopeMismatchAlert,
  DatasetSelectorSheet,
  ScopeAdjustmentDrawer,
  parseAnalysisQuestion,
  type ParseResult,
  type ParsedScope,
  type Screen1Mode
} from '../../features/analysis-composer';
import {
  AnalysisSessionWorkspace,
  getScenarioEvents,
  getEventsForParseResult,
  resolveScenarioKey,
  type AnalysisSessionEvent,
  type DriverMode
} from '../../features/analysis-session';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { CheckCircle2 } from 'lucide-react';

type PageMode = Screen1Mode | 'SESSION';

export function CreateAnalysisPage() {
  const capabilitiesQuery = useAnalysisCapabilities();
  const capabilities = capabilitiesQuery.data;

  const [mode, setMode] = useState<PageMode>('DEFAULT');
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [activeEvents, setActiveEvents] = useState<AnalysisSessionEvent[]>([]);
  const [driverMode, setDriverMode] = useState<DriverMode>('FROZEN');
  const [driverStep, setDriverStep] = useState<number | undefined>(undefined);
  const [datasetSelectorOpen, setDatasetSelectorOpen] = useState(false);
  const [scopeDrawerOpen, setScopeDrawerOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionSuccessMessage, setSubmissionSuccessMessage] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

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
      setSubmissionSuccessMessage(null);

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
        <ErrorState />
      </WorkspaceShell>
    );
  }

  function handleScopeOverride(updatedScope: ParsedScope) {
    if (!parseResult) return;
    setParseResult({
      ...parseResult,
      scope: updatedScope
    });
  }

  async function handleConfirmAndAnalyze() {
    if (!capabilities || !parseResult) return;
    const isMacroSelected = parseResult.scope.analysisPlan.selectedCapabilities.some((c) => c.id === 'macro');
    if (isMacroSelected && capabilities.macro.status === 'UNAVAILABLE') return;

    setIsSubmitting(true);
    try {
      const request: AnalysisRequest = {
        objective: parseResult.rawQuestion,
        analysisTargetIds: parseResult.scope.entities.map((e) => e.id),
        periodIds: parseResult.scope.periods.map((p) => p.id),
        metricIds: parseResult.scope.metrics.map((m) => m.id),
        capabilitySnapshotId: capabilities.snapshotId,
        peerUniverseId: capabilities.peerUniverse.id
      };

      const receipt = await analysisService.submit(request);
      setSubmissionSuccessMessage(
        receipt.message ||
          'Yêu cầu đã được xác nhận. Hệ thống phân tích đa tác tử đang khởi tạo quy trình làm việc.'
      );

      // Start Analysis Session event stream with autoplay for normal confirmed runs
      const events = getEventsForParseResult(parseResult);
      setActiveEvents(events);
      setDriverMode('AUTOPLAY');
      setDriverStep(undefined);
      setMode('SESSION');
    } finally {
      setIsSubmitting(false);
    }
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
            <span className="w-2 h-2 rounded-full bg-ready" aria-hidden="true" />
            <span className="font-mono text-[11px]">Hệ thống phân tích sẵn sàng</span>
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
              onOpenSelector={() => setDatasetSelectorOpen(true)}
            />
          )}

          {/* Submission Success Banner */}
          {submissionSuccessMessage && (
            <Alert className="border-[#2f9e62]/30 bg-[#e4f4ea] text-[#2f9e62]">
              <CheckCircle2 className="h-4 w-4 text-[#2f9e62]" />
              <AlertTitle className="text-xs font-bold">Khởi tạo quy trình thành công</AlertTitle>
              <AlertDescription className="text-xs text-ink mt-1">
                {submissionSuccessMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* SCREEN 1: DEFAULT HERO WORKSPACE */}
          {mode === 'DEFAULT' && (
            <div className="space-y-6 pt-1">
              <HeroComposer
                question={currentQuestion}
                onQuestionChange={handleQuestionChange}
                onSubmit={handleQuestionSubmit}
                parsedScope={parseResult?.scope || null}
                onOpenScopeAdjustment={() => setScopeDrawerOpen(true)}
                isSubmitting={isSubmitting}
              />

              <SuggestedQuestions onSelectPrompt={handleSelectSuggestion} />

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
                isConfirming={isSubmitting}
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
                onOpenDatasetSelector={() => setDatasetSelectorOpen(true)}
              />
            </div>
          )}

          {/* SCREEN 2: ANALYSIS SESSION WORKSPACE */}
          {mode === 'SESSION' && (
            <AnalysisSessionWorkspace
              events={activeEvents}
              driverMode={driverMode}
              driverStep={driverStep}
              onBackToComposer={() => setMode('DEFAULT')}
            />
          )}
        </div>
      </div>

      {/* CONTEXTUAL MODALS / DRAWERS */}
      <DatasetSelectorSheet
        open={datasetSelectorOpen}
        onOpenChange={setDatasetSelectorOpen}
      />

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

function ErrorState() {
  return (
    <div className="grid min-h-[60vh] place-items-center bg-workspace p-6">
      <div className="border border-[#c84b3f]/30 bg-card p-6 text-center max-w-md rounded-md">
        <p className="font-bold text-sm text-blocked">Không thể kết nối bộ dữ liệu.</p>
        <p className="mt-2 text-xs text-ink-secondary leading-relaxed">
          Vui lòng kiểm tra lại dịch vụ cung cấp dữ liệu hoặc chọn nguồn dữ liệu khác để tiếp tục.
        </p>
      </div>
    </div>
  );
}
