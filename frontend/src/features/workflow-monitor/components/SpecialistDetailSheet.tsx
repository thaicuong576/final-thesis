import type { SpecialistRunState } from '../model/types';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Building2,
  CheckCircle2,
  Clock,
  FileCheck2,
  Compass,
  RefreshCw
} from 'lucide-react';

interface SpecialistDetailSheetProps {
  specialist: SpecialistRunState | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SpecialistDetailSheet({
  specialist,
  open,
  onOpenChange
}: SpecialistDetailSheetProps) {
  if (!specialist) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg bg-white p-6 flex flex-col justify-between overflow-y-auto"
      >
        <div className="space-y-6">
          {/* Header */}
          <SheetHeader className="text-left space-y-1 pb-3 border-b border-line">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="grid place-items-center w-7 h-7 rounded-md bg-[#ebf3fb] text-[#1c5d9c]">
                  <Building2 className="w-4 h-4" />
                </div>
                <SheetTitle className="text-base font-bold text-ink">
                  {specialist.name}
                </SheetTitle>
              </div>
              <Badge variant="outline" className="text-xs font-semibold px-2 py-0.5">
                {specialist.statusLabel}
              </Badge>
            </div>
            <SheetDescription className="text-xs text-muted">
              {specialist.roleDescription}
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-5 text-xs">
            {/* 1. Assigned Task */}
            <div className="space-y-1.5 p-3 rounded-lg bg-canvas border border-line">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
                Nhiệm vụ được giao
              </span>
              <p className="text-ink font-medium leading-relaxed">
                {specialist.assignedTask}
              </p>
            </div>

            {/* 2. Observable Activities Chronology */}
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
                Nhật ký hoạt động quan sát được ({specialist.observableActivities.length})
              </span>
              <div className="space-y-2">
                {specialist.observableActivities.map((act) => (
                  <div
                    key={act.id}
                    className="p-2.5 rounded-lg border border-line bg-white space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between text-muted text-[11px]">
                      <span className="font-mono">{act.timestamp}</span>
                      <span className="flex items-center gap-1 font-semibold text-[#2f6f5e]">
                        {act.status === 'COMPLETED' ? (
                          <>
                            <CheckCircle2 className="w-3 h-3 text-[#2f6f5e]" />
                            <span>Hoàn tất</span>
                          </>
                        ) : (
                          <>
                            <Clock className="w-3 h-3 text-[#1c5d9c]" />
                            <span>Đang xử lý</span>
                          </>
                        )}
                      </span>
                    </div>
                    <div className="font-semibold text-ink">{act.action}</div>
                    <div className="text-muted text-[11px] flex items-center gap-1">
                      <span className="font-medium text-ink">Nguồn dữ liệu:</span>
                      <span>{act.dataSource}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. Findings Artifacts & Provenance */}
            {specialist.findings.length > 0 && (
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
                  Kết quả phân tích có dẫn chứng ({specialist.findings.length})
                </span>
                <div className="space-y-2">
                  {specialist.findings.map((f) => (
                    <div
                      key={f.id}
                      className="p-3 rounded-lg bg-[#edf7f3] border border-[#bce2d3] space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-[#2f6f5e] font-bold text-xs">
                          <FileCheck2 className="w-3.5 h-3.5" />
                          <span>{f.metric || 'Chỉ số tài chính'}</span>
                        </div>
                        {f.value && (
                          <span className="font-mono font-bold text-ink text-xs">{f.value}</span>
                        )}
                      </div>
                      <p className="text-ink font-medium leading-relaxed">{f.title}</p>
                      <div className="text-[11px] text-muted pt-1 border-t border-[#bce2d3]/50">
                        <strong>Dẫn chứng:</strong> {f.evidenceSource}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. Sequential Official Review & Revision Dialogue */}
            {specialist.revision && (
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
                  Trao đổi kiểm duyệt chính thức
                </span>
                <div className="space-y-2.5">
                  {/* Message from Orchestrator */}
                  <div className="p-3 rounded-lg bg-[#fff8eb] border border-[#fde0a3] space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-bold text-[#9a6700] flex items-center gap-1">
                        <Compass className="w-3.5 h-3.5" />
                        <span>Ý kiến phản biện từ Tác tử Điều phối</span>
                      </span>
                      <span className="text-muted">Vòng {specialist.revision.iteration}</span>
                    </div>
                    <p className="text-ink leading-relaxed italic">
                      “{specialist.revision.orchestratorFeedback}”
                    </p>
                  </div>

                  {/* Response from Specialist */}
                  {specialist.revision.resolvedNote && (
                    <div className="p-3 rounded-lg bg-canvas border border-line space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-ink flex items-center gap-1">
                          <RefreshCw className="w-3 h-3 text-[#2f6f5e]" />
                          <span>Phản hồi từ {specialist.name}</span>
                        </span>
                        <span className="text-[#2f6f5e] font-semibold">Đã cập nhật</span>
                      </div>
                      <p className="text-ink leading-relaxed">
                        {specialist.revision.resolvedNote}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <SheetFooter className="pt-4 border-t border-line mt-6 flex-row justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="text-xs font-semibold"
          >
            Đóng
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
