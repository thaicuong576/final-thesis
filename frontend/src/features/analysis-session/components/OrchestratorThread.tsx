import { CheckCircle2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { SpecialistSessionState, ThreadItem } from '../model/types';
import { UserQuestionEntry } from './UserQuestionEntry';
import { OrchestratorEntry } from './OrchestratorEntry';
import { InlineSpecialistInvocationCard } from './InlineSpecialistInvocationCard';

interface OrchestratorThreadProps {
  threadItems: ThreadItem[];
  specialistSessions: Record<string, SpecialistSessionState>;
  onSelectSpecialist: (session: SpecialistSessionState) => void;
}

export function OrchestratorThread({
  threadItems,
  specialistSessions,
  onSelectSpecialist
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

                    <Button
                      type="button"
                      className="bg-[#2f6f5e] text-white hover:bg-[#25584a] text-xs font-medium gap-1.5 h-8 px-3.5 shadow-sm shrink-0 self-start sm:self-auto"
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
              );

            default:
              return null;
          }
        })}
      </div>
    </div>
  );
}
