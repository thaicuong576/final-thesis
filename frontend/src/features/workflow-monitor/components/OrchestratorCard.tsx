import type { OrchestratorRunState, SpecialistRunState } from '../model/types';
import { Badge } from '@/components/ui/badge';
import { Compass, CheckCircle2, RefreshCw, Layers } from 'lucide-react';

interface OrchestratorCardProps {
  orchestrator: OrchestratorRunState;
  specialists: SpecialistRunState[];
}

export function OrchestratorCard({ orchestrator, specialists }: OrchestratorCardProps) {
  const isRevising = orchestrator.overallStatus === 'REVISING';
  const isSynthesizing = orchestrator.overallStatus === 'SYNTHESIZING';

  return (
    <div className="bg-white border-2 border-[#1c5d9c]/40 rounded-xl p-6 shadow-surface space-y-5 relative">
      {/* Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-line">
        <div className="flex items-center gap-3">
          <div className="grid place-items-center w-9 h-9 rounded-lg bg-[#ebf3fb] border border-[#b8d5f2] text-[#1c5d9c]">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-ink">Tác tử Điều phối</h2>
              <Badge
                variant="outline"
                className="bg-[#f5f8fb] text-[#1c5d9c] border-[#b8d5f2] text-[10px] font-semibold px-2"
              >
                Trung tâm điều hành cấp bậc
              </Badge>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Lập kế hoạch thích ứng theo câu hỏi · Phân công nhiệm vụ chuyên sâu · Kiểm soát chất lượng phản biện
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="text-xs text-muted font-medium">Chuyên gia hoạt động:</span>
          <div className="flex items-center gap-1">
            {specialists.map((s) => (
              <Badge
                key={s.id}
                variant="secondary"
                className="text-[11px] font-semibold bg-[#ebf3fb] text-[#1c5d9c] border-none"
              >
                {s.name}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Orchestrator 3-Column Lifecycle Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        {/* Step 1: Kế hoạch phân tích thích ứng */}
        <div className="p-3.5 rounded-lg bg-canvas border border-line space-y-1.5">
          <div className="flex items-center gap-1.5 text-ink font-semibold">
            <Layers className="w-3.5 h-3.5 text-[#1c5d9c]" />
            <span>Kế hoạch thích ứng</span>
          </div>
          <p className="text-muted leading-relaxed line-clamp-3">
            {orchestrator.planningRationale}
          </p>
        </div>

        {/* Step 2: Phân công nhiệm vụ chuyên gia */}
        <div className="p-3.5 rounded-lg bg-canvas border border-line space-y-1.5">
          <div className="flex items-center gap-1.5 text-ink font-semibold">
            <Compass className="w-3.5 h-3.5 text-[#1c5d9c]" />
            <span>Phân công chuyên gia ({specialists.length})</span>
          </div>
          <ul className="space-y-1 text-muted">
            {specialists.map((s) => (
              <li key={s.id} className="flex items-start gap-1.5">
                <span className="text-[#1c5d9c] font-bold">•</span>
                <span className="line-clamp-1">
                  <strong>{s.name}:</strong> {s.assignedTask}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Step 3: Kiểm duyệt & Hiệu chỉnh phản biện */}
        <div
          className={`p-3.5 rounded-lg border space-y-1.5 ${
            isRevising
              ? 'bg-[#fffbf0] border-[#fde0a3]'
              : isSynthesizing
              ? 'bg-[#f7f5fd] border-[#d7c9f8]'
              : 'bg-canvas border border-line'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-semibold text-ink">
              {isRevising ? (
                <RefreshCw className="w-3.5 h-3.5 text-[#9a6700] animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-[#2f6f5e]" />
              )}
              <span>Kiểm soát chất lượng</span>
            </div>
            {isRevising && (
              <Badge
                variant="outline"
                className="bg-[#fff8eb] text-[#9a6700] border-[#fde0a3] text-[10px] font-bold"
              >
                Hiệu chỉnh vòng {orchestrator.revisionRound || 1}
              </Badge>
            )}
          </div>
          <p className="text-muted leading-relaxed">
            {orchestrator.reviewSummary || 'Các chỉ số được đối soát với quy chuẩn tính toán Gold và số liệu gốc.'}
          </p>
        </div>
      </div>
    </div>
  );
}
