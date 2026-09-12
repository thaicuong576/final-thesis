import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type {
  AnalysisSessionEvent,
  AnalysisSessionViewModel,
  SpecialistSessionState
} from '../model/types';
import { useAnalysisSessionDriver, type DriverMode } from '../mock/MockAnalysisSessionDriver';
import { SessionContextBar } from './SessionContextBar';
import { OrchestratorThread } from './OrchestratorThread';
import { SpecialistSessionSheet } from './SpecialistSessionSheet';
import type { CanonicalScenarioKey } from '../mock/scenarioRegistry';

interface AnalysisSessionWorkspaceProps {
  // Can receive either direct viewModel or event list for driver
  viewModel?: AnalysisSessionViewModel;
  events?: AnalysisSessionEvent[];
  driverMode?: DriverMode;
  driverStep?: number;
  onBackToComposer?: () => void;
  onSelectScenario?: (scenarioKey: CanonicalScenarioKey) => void;
  activeScenarioKey?: string;
  // Compatibility prop with previous snapshot signature:
  session?: AnalysisSessionViewModel;
}

export function AnalysisSessionWorkspace({
  viewModel: externalViewModel,
  session: legacySession,
  events = [],
  driverMode = 'FROZEN',
  driverStep,
  onBackToComposer,
  onSelectScenario,
  activeScenarioKey
}: AnalysisSessionWorkspaceProps) {
  // If events are passed, drive state with useAnalysisSessionDriver; otherwise use provided viewModel/session
  const hasEvents = events.length > 0;
  const driver = useAnalysisSessionDriver({
    events: hasEvents ? events : [],
    mode: driverMode,
    step: driverStep
  });

  const activeViewModel: AnalysisSessionViewModel =
    externalViewModel ||
    legacySession ||
    (hasEvents
      ? driver.viewModel
      : {
          sessionId: 'empty',
          rawQuestion: '',
          datasetName: 'Ngân hàng Việt Nam 2024',
          scopeSignature: '',
          currentPhase: 'INITIALIZING',
          phaseLabel: 'Đang chuẩn bị',
          threadItems: [],
          specialistSessions: {},
          invocations: [],
          reportReady: false
        });

  const [selectedSpecialist, setSelectedSpecialist] =
    useState<SpecialistSessionState | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleOpenSpecialist = (session: SpecialistSessionState) => {
    setSelectedSpecialist(session);
    setSheetOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Demo Scenario Switcher for Acceptance Verification */}
      {onSelectScenario && (
        <div className="bg-[#f8fafc] border border-line rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-ink">Kịch bản minh chứng:</span>
            <span className="text-muted">Kiểm tra dòng sự kiện tác tử</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              type="button"
              variant={
                activeScenarioKey === 'company-only' || activeScenarioKey === 'SCENARIO_A'
                  ? 'default'
                  : 'outline'
              }
              size="sm"
              onClick={() => onSelectScenario('company-only')}
              className="h-7 text-xs px-2.5"
            >
              Doanh nghiệp (TCB)
            </Button>
            <Button
              type="button"
              variant={
                activeScenarioKey === 'company-peer' || activeScenarioKey === 'SCENARIO_B'
                  ? 'default'
                  : 'outline'
              }
              size="sm"
              onClick={() => onSelectScenario('company-peer')}
              className="h-7 text-xs px-2.5"
            >
              Doanh nghiệp + Peer
            </Button>
            <Button
              type="button"
              variant={
                activeScenarioKey === 'targeted-revision' || activeScenarioKey === 'SCENARIO_C'
                  ? 'default'
                  : 'outline'
              }
              size="sm"
              onClick={() => onSelectScenario('targeted-revision')}
              className="h-7 text-xs px-2.5"
            >
              Hiệu chỉnh có chủ đích
            </Button>
            <Button
              type="button"
              variant={
                activeScenarioKey === 'macro-company' || activeScenarioKey === 'SCENARIO_D'
                  ? 'default'
                  : 'outline'
              }
              size="sm"
              onClick={() => onSelectScenario('macro-company')}
              className="h-7 text-xs px-2.5"
            >
              Vĩ mô + Doanh nghiệp
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
      />

      {/* Layer B & C: Unified Chronological Orchestrator Thread with Inline Specialists */}
      <OrchestratorThread
        threadItems={activeViewModel.threadItems}
        specialistSessions={activeViewModel.specialistSessions}
        onSelectSpecialist={handleOpenSpecialist}
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
