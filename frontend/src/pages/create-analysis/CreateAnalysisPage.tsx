import { useEffect, useState } from 'react';
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
  createAnalysisSession,
  type AnalysisSession,
  type DemoScenarioKey
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
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [activeScenarioKey, setActiveScenarioKey] = useState<DemoScenarioKey | undefined>(undefined);
  const [datasetSelectorOpen, setDatasetSelectorOpen] = useState(false);
  const [scopeDrawerOpen, setScopeDrawerOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionSuccessMessage, setSubmissionSuccessMessage] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (!capabilities) return;

    const scenarioParam = searchParams.get('scenario');
    if (scenarioParam) {
      if (scenarioParam === 'COMPANY_ONLY' || scenarioParam === 'A') {
        const q = 'ROE của TCB thay đổi thế nào trong năm 2024?';
        const parsed = parseAnalysisQuestion(q, capabilities);
        setParseResult(parsed);
        setCurrentQuestion(q);
        setSession(createAnalysisSession(parsed, capabilities));
        setActiveScenarioKey('SCENARIO_A');
        setMode('SESSION');
        return;
      } else if (scenarioParam === 'COMPANY_PEER' || scenarioParam === 'B') {
        const q = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
        const parsed = parseAnalysisQuestion(q, capabilities);
        setParseResult(parsed);
        setCurrentQuestion(q);
        setSession(createAnalysisSession(parsed, capabilities));
        setActiveScenarioKey('SCENARIO_B');
        setMode('SESSION');
        return;
      } else if (scenarioParam === 'TARGETED_REVISION' || scenarioParam === 'C') {
        const q = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
        const parsed = parseAnalysisQuestion(q, capabilities);
        setParseResult(parsed);
        setCurrentQuestion(q);
        setSession(createAnalysisSession(parsed, capabilities, { withTargetedRevision: true }));
        setActiveScenarioKey('SCENARIO_C');
        setMode('SESSION');
        return;
      } else if (scenarioParam === 'MACRO_COMPANY' || scenarioParam === 'D') {
        const q = 'Lãi suất điều hành liên quan thế nào đến TCB trong năm 2024?';
        const parsed = parseAnalysisQuestion(q, capabilities);
        setParseResult(parsed);
        setCurrentQuestion(q);
        setSession(createAnalysisSession(parsed, capabilities));
        setActiveScenarioKey('SCENARIO_D');
        setMode('SESSION');
        return;
      }
    }

    const q = searchParams.get('q');
    if (q && mode === 'DEFAULT') {
      handleQuestionSubmit(q);
    }
  }, [searchParams, capabilities, mode]);

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

  function handleQuestionSubmit(question: string) {
    if (!capabilities) return;
    setCurrentQuestion(question);
    setSubmissionSuccessMessage(null);

    const result = parseAnalysisQuestion(question, capabilities);
    setParseResult(result);

    if (result.mismatch.isMismatch) {
      setMode('MISMATCH');
    } else {
      setMode('INTERPRETED');
    }
  }

  function handleSelectSuggestion(promptText: string) {
    handleQuestionSubmit(promptText);
  }

  function handleScopeOverride(updatedScope: ParsedScope) {
    if (!parseResult) return;
    setParseResult({
      ...parseResult,
      scope: updatedScope
    });
  }

  function handleSelectScenario(scenarioKey: DemoScenarioKey) {
    if (!capabilities) return;
    setActiveScenarioKey(scenarioKey);
    let q = '';
    let withRevision = false;
    if (scenarioKey === 'SCENARIO_A') {
      q = 'ROE của TCB thay đổi thế nào trong năm 2024?';
    } else if (scenarioKey === 'SCENARIO_B') {
      q = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
    } else if (scenarioKey === 'SCENARIO_C') {
      q = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
      withRevision = true;
    } else if (scenarioKey === 'SCENARIO_D') {
      q = 'Lãi suất điều hành liên quan thế nào đến TCB trong năm 2024?';
    }
    const parsed = parseAnalysisQuestion(q, capabilities);
    setParseResult(parsed);
    setCurrentQuestion(q);
    setSession(createAnalysisSession(parsed, capabilities, { withTargetedRevision: withRevision }));
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

      // Initialize analysis session
      const newSession = createAnalysisSession(parseResult, capabilities);
      setSession(newSession);
      setMode('SESSION');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <WorkspaceShell
      activeSection="analysis"
      context={
        <div className="mx-auto w-full max-w-[1200px] px-5 py-2.5 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted">
              <span>Không gian làm việc</span>
              <span>/</span>
              <span className="font-semibold text-ink">Phân tích tài chính</span>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted">
              <span className="w-2 h-2 rounded-full bg-[#2f6f5e]" aria-hidden="true" />
              <span>Hệ thống phân tích cấp bậc sẵn sàng</span>
            </div>
          </div>
        </div>
      }
    >
      <div className="min-h-[calc(100vh-100px)] bg-canvas py-6 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Active Dataset Anchor Card (Only displayed in composer/interpretation modes) */}
          {mode !== 'SESSION' && (
            <ActiveDatasetCard
              capabilities={capabilities}
              onOpenSelector={() => setDatasetSelectorOpen(true)}
            />
          )}

          {/* Submission Success Banner */}
          {submissionSuccessMessage && (
            <Alert className="border-[#bce2d3] bg-[#edf7f3] text-[#2f6f5e]">
              <CheckCircle2 className="h-4 w-4 text-[#2f6f5e]" />
              <AlertTitle className="text-xs font-semibold">Khởi tạo quy trình thành công</AlertTitle>
              <AlertDescription className="text-xs text-ink mt-1">
                {submissionSuccessMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* SCREEN 1 & SCREEN 2 STATE MACHINE */}
          {mode === 'DEFAULT' && (
            <div className="space-y-6">
              <HeroComposer
                initialQuestion={currentQuestion}
                onSubmit={handleQuestionSubmit}
                isSubmitting={isSubmitting}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <SuggestedQuestions onSelectPrompt={handleSelectSuggestion} />
                <RecentReportsSummary />
              </div>
            </div>
          )}

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

          {mode === 'SESSION' && session && (
            <AnalysisSessionWorkspace
              session={session}
              onBackToComposer={() => setMode('DEFAULT')}
              onSelectScenario={handleSelectScenario}
              activeScenarioKey={activeScenarioKey}
            />
          )}
        </div>
      </div>

      {/* CONTEXTUAL MODALS / DRAWERS */}
      <DatasetSelectorSheet
        open={datasetSelectorOpen}
        onOpenChange={setDatasetSelectorOpen}
      />

      {parseResult && (
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
    <div className="grid min-h-[60vh] place-items-center bg-canvas p-6">
      <p className="text-sm text-muted" role="status">
        Đang chuẩn bị bộ dữ liệu và động cơ phân tích…
      </p>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="grid min-h-[60vh] place-items-center bg-canvas p-6">
      <div className="border border-[#e4c0bb] bg-white p-6 text-center max-w-md rounded-lg shadow-surface">
        <p className="font-semibold text-blocked">Không thể kết nối bộ dữ liệu.</p>
        <p className="mt-2 text-xs text-muted leading-relaxed">
          Vui lòng kiểm tra lại dịch vụ cung cấp dữ liệu hoặc chọn nguồn dữ liệu khác để tiếp tục.
        </p>
      </div>
    </div>
  );
}
