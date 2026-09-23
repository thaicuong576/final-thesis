import { CheckCircle2, FileText } from 'lucide-react';
import { useNavigate, useInRouterContext } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { SpecialistSessionState, ThreadItem } from '../model/types';
import type { AnalysisReport } from '@/features/analysis-report';
import { UserQuestionEntry } from './UserQuestionEntry';
import { OrchestratorEntry } from './OrchestratorEntry';
import { InlineSpecialistInvocationCard } from './InlineSpecialistInvocationCard';

interface SafeReportButtonProps {
  targetPath?: string;
  reportData?: AnalysisReport | null;
  onViewReport?: () => void;
}


function SafeReportButton({
  targetPath = '/reports/mock-session-2024-acb-tcb',
  reportData,
  onViewReport
}: SafeReportButtonProps) {
  const inRouter = useInRouterContext();
  if (inRouter) {
    return (
      <RouterReportButton
        targetPath={targetPath}
        reportData={reportData}
        onViewReport={onViewReport}
      />
    );
  }
  return (
    <StaticReportButton
      targetPath={targetPath}
      reportData={reportData}
      onViewReport={onViewReport}
    />
  );
}

function RouterReportButton({
  targetPath,
  reportData,
  onViewReport
}: {
  targetPath: string;
  reportData?: AnalysisReport | null;
  onViewReport?: () => void;
}) {
  const navigate = useNavigate();
  return (
    <Button
      type="button"
      className="bg-[#2f6f5e] text-white hover:bg-[#25584a] text-xs font-medium gap-1.5 h-8 px-3.5 shadow-sm shrink-0 self-start sm:self-auto cursor-pointer"
      onClick={() => {
        if (onViewReport) {
          onViewReport();
          return;
        }
        if (reportData && typeof window !== 'undefined' && window.sessionStorage) {
          try {
            window.sessionStorage.setItem('current_analysis_report', JSON.stringify(reportData));
          } catch {
            // ignore
          }
        }
        navigate(targetPath, { state: { report: reportData } });
      }}
    >
      <FileText className="w-3.5 h-3.5" aria-hidden="true" />
      Xem báo cáo phân tích
    </Button>
  );
}

function StaticReportButton({
  targetPath,
  reportData,
  onViewReport
}: {
  targetPath: string;
  reportData?: AnalysisReport | null;
  onViewReport?: () => void;
}) {
  return (
    <Button
      type="button"
      className="bg-[#2f6f5e] text-white hover:bg-[#25584a] text-xs font-medium gap-1.5 h-8 px-3.5 shadow-sm shrink-0 self-start sm:self-auto cursor-pointer"
      onClick={() => {
        if (onViewReport) {
          onViewReport();
          return;
        }
        if (reportData && typeof window !== 'undefined' && window.sessionStorage) {
          try {
            window.sessionStorage.setItem('current_analysis_report', JSON.stringify(reportData));
          } catch {
            // ignore
          }
        }
        if (typeof window !== 'undefined') {
          window.location.href = targetPath;
        }
      }}
    >
      <FileText className="w-3.5 h-3.5" aria-hidden="true" />
      Xem báo cáo phân tích
    </Button>
  );
}

interface OrchestratorThreadProps {
  threadItems: ThreadItem[];
  specialistSessions: Record<string, SpecialistSessionState>;
  onSelectSpecialist: (session: SpecialistSessionState) => void;
  targetReportPath?: string;
  reportData?: AnalysisReport | null;
  onViewReport?: () => void;
  isStreaming?: boolean;
}

export function OrchestratorThread({
  threadItems,
  specialistSessions,
  onSelectSpecialist,
  targetReportPath,
  reportData,
  onViewReport,
  isStreaming = false
}: OrchestratorThreadProps) {
  return (
    <div className="border border-line bg-white rounded-lg p-5 shadow-surface space-y-4">
      <div className="border-b border-line pb-2.5 flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted">
          Tiến trình làm việc của Điều phối viên
        </h2>
        <span className="text-xs text-muted">Dòng sự kiện tác tử theo thời gian</span>
      </div>

      <div className="space-y-4">
        {threadItems.map((item) => {
          switch (item.type) {
            case 'USER_MESSAGE':
              return <UserQuestionEntry key={item.id} question={item.question} />;

            case 'ORCHESTRATOR_MESSAGE':
              return (
                <OrchestratorEntry
                  key={item.id}
                  entry={{
                    id: item.id,
                    role: 'orchestrator',
                    senderLabel: item.senderLabel,
                    message: item.message,
                    phase: item.phase
                  }}
                />
              );

            case 'SPECIALIST_INVOCATION': {
              const session = specialistSessions[item.invocationId];
              if (!session) return null;
              return (
                <InlineSpecialistInvocationCard
                  key={item.id}
                  session={session}
                  onClick={() => onSelectSpecialist(session)}
                />
              );
            }

            case 'REPORT_READY_ACTION':
              return (
                <div key={item.id} className="ml-11 pt-2">
                  <div className="border border-[#bce2d3] bg-[#edf7f3] rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 max-w-2xl">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#2f6f5e]" aria-hidden="true" />
                        <h3 className="text-xs font-semibold text-ink">
                          Báo cáo phân tích đã sẵn sàng
                        </h3>
                        <Badge
                          variant="outline"
                          className="bg-white text-[#2f6f5e] border-[#bce2d3] text-[10px] font-semibold"
                        >
                          Đã hoàn tất
                        </Badge>
                      </div>
                      <p className="text-xs text-muted">
                        Điều phối viên đã tổng hợp toàn diện nhận định từ các chuyên môn kèm số liệu kiểm chứng.
                      </p>
                    </div>

                    <SafeReportButton
                      targetPath={targetReportPath || '/reports/mock-session-2024-acb-tcb'}
                      reportData={reportData}
                      onViewReport={onViewReport}
                    />
                  </div>
                </div>
              );

            default:
              return null;
          }
        })}

        {/* Animated Pulse / Typing Indicator while agents are thinking */}
        {isStreaming && !threadItems.some((t) => t.type === 'REPORT_READY_ACTION') && (
          <div className="ml-11 flex items-center gap-3 p-3.5 rounded-lg border border-amber-border/40 bg-amber-soft/30 text-ink animate-in fade-in duration-300 max-w-2xl">
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="w-2 h-2 rounded-full bg-amber-border animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-amber-border animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-amber-border animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-xs font-mono text-ink-secondary">
              Điều phối viên & các tác tử chuyên sâu đang truy xuất BCTC và đối chuẩn dữ liệu...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
