import { useState } from 'react';
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
  onSelectScenario: _onSelectScenario,
  activeScenarioKey: _activeScenarioKey
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
