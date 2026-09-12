import { useState } from 'react';
import { FileText, CheckCircle2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { AnalysisSession, SpecialistInvocation } from '../model/types';
import { SessionContextBar } from './SessionContextBar';
import { UserQuestionEntry } from './UserQuestionEntry';
import { OrchestratorEntry } from './OrchestratorEntry';
import { SpecialistInvocationGroup } from './SpecialistInvocationGroup';
import { SpecialistSessionSheet } from './SpecialistSessionSheet';

export type DemoScenarioKey = 'SCENARIO_A' | 'SCENARIO_B' | 'SCENARIO_C' | 'SCENARIO_D';

interface AnalysisSessionWorkspaceProps {
  session: AnalysisSession;
  onBackToComposer?: () => void;
  onSelectScenario?: (scenarioKey: DemoScenarioKey) => void;
  activeScenarioKey?: DemoScenarioKey;
}

export function AnalysisSessionWorkspace({
  session,
  onBackToComposer,
  onSelectScenario,
  activeScenarioKey
}: AnalysisSessionWorkspaceProps) {
  const [selectedInvocation, setSelectedInvocation] = useState<SpecialistInvocation | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleOpenInvocation = (invocation: SpecialistInvocation) => {
    setSelectedInvocation(invocation);
    setSheetOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Demo Scenario Switcher for Acceptance Verification */}
      {onSelectScenario && (
        <div className="bg-[#f8fafc] border border-line rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-ink">Kịch bản minh chứng:</span>
            <span className="text-muted">Kiểm tra tính thích ứng của hệ thống</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              type="button"
              variant={activeScenarioKey === 'SCENARIO_A' ? 'default' : 'outline'}
              size="sm"
              onClick={() => onSelectScenario('SCENARIO_A')}
              className="h-7 text-xs px-2.5"
            >
              A: Doanh nghiệp (TCB)
            </Button>
            <Button
              type="button"
              variant={activeScenarioKey === 'SCENARIO_B' ? 'default' : 'outline'}
              size="sm"
              onClick={() => onSelectScenario('SCENARIO_B')}
              className="h-7 text-xs px-2.5"
            >
              B: Doanh nghiệp + Peer
            </Button>
            <Button
              type="button"
              variant={activeScenarioKey === 'SCENARIO_C' ? 'default' : 'outline'}
              size="sm"
              onClick={() => onSelectScenario('SCENARIO_C')}
              className="h-7 text-xs px-2.5"
            >
              C: Hiệu chỉnh có chủ đích
            </Button>
            <Button
              type="button"
              variant={activeScenarioKey === 'SCENARIO_D' ? 'default' : 'outline'}
              size="sm"
              onClick={() => onSelectScenario('SCENARIO_D')}
              className="h-7 text-xs px-2.5"
            >
              D: Vĩ mô + Doanh nghiệp
            </Button>
          </div>
        </div>
      )}

      {/* Layer A: Session Context Bar */}
      <SessionContextBar
        datasetName={session.datasetName}
        scopeSignature={session.scopeSignature}
        currentPhase={session.currentPhase}
        phaseLabel={session.phaseLabel}
        onBackToComposer={onBackToComposer}
      />

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 gap-6">
        {/* Layer B: Narrative & Interaction Thread */}
        <div className="border border-line bg-white rounded-lg p-5 shadow-surface space-y-4">
          <div className="border-b border-line pb-2.5 flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-muted">
              Trao đổi với Điều phối viên
            </h2>
            <span className="text-xs text-muted">Trực tiếp từ động cơ tác tử</span>
          </div>

          {/* User Question */}
          <UserQuestionEntry question={session.rawQuestion} />

          {/* Orchestrator Narrative Entries */}
          <div className="space-y-3 pt-2">
            {session.orchestratorEntries.map((entry) => (
              <OrchestratorEntry key={entry.id} entry={entry} />
            ))}
          </div>
        </div>

        {/* Layer C: Query-Adaptive Specialist Invocations */}
        <div className="border border-line bg-white rounded-lg p-5 shadow-surface space-y-4">
          <SpecialistInvocationGroup
            invocations={session.invocations}
            onSelectInvocation={handleOpenInvocation}
          />
        </div>

        {/* Layer E: Synthesis & Report Action State */}
        {session.reportReady ? (
          <div className="border border-[#bce2d3] bg-[#edf7f3] rounded-lg p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#2f6f5e]" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-ink">
                  Báo cáo phân tích đã sẵn sàng
                </h3>
                <Badge
                  variant="outline"
                  className="bg-white text-[#2f6f5e] border-[#bce2d3] text-[10px] font-semibold"
                >
                  Đã hoàn tất tổng hợp
                </Badge>
              </div>
              <p className="text-xs text-muted">
                Điều phối viên đã tổng hợp nhận định từ các chuyên môn được yêu cầu kèm dẫn chứng số liệu kiểm chứng.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
              <Button
                type="button"
                className="bg-[#2f6f5e] text-white hover:bg-[#25584a] text-xs font-medium gap-1.5 h-9 px-4 shadow-sm"
                onClick={() => {
                  alert(
                    'Khóa luận tốt nghiệp: Màn hình Báo cáo phân tích chuyên sâu (Final Report) được triển khai ở pha kế tiếp.'
                  );
                }}
              >
                <FileText className="w-3.5 h-3.5" aria-hidden="true" />
                Xem báo cáo phân tích
              </Button>
            </div>
          </div>
        ) : session.currentPhase === 'REVISING' ? (
          <div className="border border-[#f5dfaa] bg-[#fffdfa] rounded-lg p-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <RefreshCw className="w-4 h-4 text-[#b47d14] animate-spin shrink-0" aria-hidden="true" />
              <div className="text-xs">
                <span className="font-semibold text-ink">Đang hiệu chỉnh có chủ đích: </span>
                <span className="text-muted">
                  Điều phối viên đang kiểm tra lại dữ liệu chưa đồng bộ cùng kỳ của chuyên môn liên quan.
                </span>
              </div>
            </div>
            <Badge
              variant="outline"
              className="bg-white text-[#b47d14] border-[#f5dfaa] text-[10px] font-semibold shrink-0"
            >
              Vòng 1 / 2
            </Badge>
          </div>
        ) : null}
      </div>

      {/* Layer D: Specialist Inspection Sheet */}
      <SpecialistSessionSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        invocation={selectedInvocation}
      />
    </div>
  );
}
