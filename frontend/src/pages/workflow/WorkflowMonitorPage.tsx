import { useState, useMemo } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';
import {
  WorkflowTopBar,
  OrchestratorCard,
  SpecialistCard,
  SpecialistDetailSheet,
  WorkflowTreeConnector,
  mockScenarios,
  type DemoScenarioId,
  type SpecialistRunState
} from '../../features/workflow-monitor';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { FileText, ArrowRight } from 'lucide-react';

export function WorkflowMonitorPage() {
  const { runId } = useParams<{ runId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  // Determine active scenario from query param or fallback to COMPANY_ONLY
  const initialScenario = (searchParams.get('scenario') as DemoScenarioId) || 'COMPANY_ONLY';
  const [activeScenarioId, setActiveScenarioId] = useState<DemoScenarioId>(
    mockScenarios[initialScenario] ? initialScenario : 'COMPANY_ONLY'
  );

  const [selectedSpecialist, setSelectedSpecialist] = useState<SpecialistRunState | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Active workflow data
  const currentRun = useMemo(() => {
    return mockScenarios[activeScenarioId] || mockScenarios.COMPANY_ONLY;
  }, [activeScenarioId]);

  const handleSelectScenario = (scenarioId: DemoScenarioId) => {
    setActiveScenarioId(scenarioId);
    setSearchParams({ scenario: scenarioId });
    if (selectedSpecialist) {
      // Refresh selected specialist in sheet if active scenario changed
      const matched = mockScenarios[scenarioId]?.specialists.find(
        (s) => s.id === selectedSpecialist.id
      );
      setSelectedSpecialist(matched || null);
    }
  };

  const handleOpenDetail = (specialist: SpecialistRunState) => {
    setSelectedSpecialist(specialist);
    setIsDetailOpen(true);
  };

  const activeSpecialists = currentRun.specialists;
  const isCompleteOrSynthesizing =
    currentRun.orchestrator.overallStatus === 'SYNTHESIZING' ||
    currentRun.orchestrator.overallStatus === 'READY_FOR_REPORT';

  return (
    <WorkspaceShell
      activeSection="analysis"
      context={
        <div className="mx-auto w-full max-w-[1200px] px-5 py-2.5 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted">
              <Link to="/analysis" className="hover:text-ink transition-colors">
                Không gian làm việc
              </Link>
              <span>/</span>
              <span className="font-medium text-ink">Quy trình phân tích đa tác tử</span>
              <span>/</span>
              <span className="font-mono text-[11px] text-muted">
                {runId || currentRun.runId}
              </span>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted">
              <span className="w-2 h-2 rounded-full bg-[#1c5d9c] animate-pulse" aria-hidden="true" />
              <span>Cơ chế thích ứng theo câu hỏi (Query-Adaptive)</span>
            </div>
          </div>
        </div>
      }
    >
      <div className="min-h-[calc(100vh-100px)] bg-canvas py-6 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-6">
          {/* Top Bar: Question, Scope signature, Dataset, Status badge, Scenario Switcher */}
          <WorkflowTopBar
            workflowRun={currentRun}
            activeScenarioId={activeScenarioId}
            onSelectScenario={handleSelectScenario}
          />

          {/* Core Multi-Agent Hierarchy Surface */}
          <div className="space-y-2">
            {/* Orchestrator Card (Central Planner & Controller) */}
            <OrchestratorCard
              orchestrator={currentRun.orchestrator}
              specialists={activeSpecialists}
            />

            {/* Tree Branching Connector */}
            <WorkflowTreeConnector count={activeSpecialists.length} />

            {/* Query-Adaptive Active Specialists Grid */}
            <div
              className={`grid gap-5 ${
                activeSpecialists.length === 1
                  ? 'grid-cols-1 max-w-xl mx-auto'
                  : activeSpecialists.length === 2
                  ? 'grid-cols-1 md:grid-cols-2'
                  : 'grid-cols-1 md:grid-cols-3'
              }`}
            >
              {activeSpecialists.map((specialist) => (
                <SpecialistCard
                  key={specialist.id}
                  specialist={specialist}
                  onOpenDetail={handleOpenDetail}
                />
              ))}
            </div>
          </div>

          {/* Next Phase CTA Bar */}
          <div className="bg-white border border-line rounded-xl p-5 shadow-surface flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start sm:items-center gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-[#f0f4f8] border border-line flex items-center justify-center text-ink shrink-0">
                <FileText className="w-5 h-5 text-muted" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-ink">
                    Đầu ra kỳ vọng: Báo cáo tài chính chuyên sâu
                  </h3>
                  {isCompleteOrSynthesizing ? (
                    <Badge className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] hover:bg-[#edf7f3] text-[11px]">
                      Sẵn sàng tổng hợp
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-muted text-[11px]">
                      Đang xử lý dữ liệu
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted mt-0.5">
                  Báo cáo tích hợp đầy đủ dẫn chứng đối soát từ nguồn BCTC, biểu đồ so sánh và khuyến nghị phân tích.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                variant="outline"
                size="sm"
                disabled
                className="w-full sm:w-auto text-xs gap-1.5 opacity-60 cursor-not-allowed"
                title="Màn hình 3 (Báo cáo phân tích) sẽ được phát triển ở pha tiếp theo"
              >
                <span>Xem báo cáo (Pha tiếp theo)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>

          {/* Detail Inspection Drawer (Sheet) */}
          <SpecialistDetailSheet
            specialist={selectedSpecialist}
            open={isDetailOpen}
            onOpenChange={setIsDetailOpen}
          />
        </div>
      </div>
    </WorkspaceShell>
  );
}