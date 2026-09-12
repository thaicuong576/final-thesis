import type { SpecialistRunState } from '../model/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Building2,
  Users2,
  Globe2,
  CheckCircle2,
  RefreshCw,
  Clock,
  FileText,
  Eye,
  AlertCircle
} from 'lucide-react';

interface SpecialistCardProps {
  specialist: SpecialistRunState;
  onOpenDetail: (specialist: SpecialistRunState) => void;
}

export function SpecialistCard({ specialist, onOpenDetail }: SpecialistCardProps) {
  const isCompany = specialist.id === 'company';
  const isPeer = specialist.id === 'peer';

  const icon = isCompany ? (
    <Building2 className="w-4 h-4 text-[#1c5d9c]" />
  ) : isPeer ? (
    <Users2 className="w-4 h-4 text-[#2f6f5e]" />
  ) : (
    <Globe2 className="w-4 h-4 text-[#9a6700]" />
  );

  const statusConfig = {
    PREPARING: { bg: 'bg-[#f0f4f8]', text: 'text-muted', border: 'border-line', icon: Clock, label: 'Đang chuẩn bị' },
    ANALYZING: { bg: 'bg-[#ebf3fb]', text: 'text-[#1c5d9c]', border: 'border-[#b8d5f2]', icon: Clock, label: 'Đang phân tích' },
    PRODUCED_FINDINGS: { bg: 'bg-[#edf7f3]', text: 'text-[#2f6f5e]', border: 'border-[#bce2d3]', icon: FileText, label: 'Đã tạo kết quả' },
    UNDER_REVIEW: { bg: 'bg-[#f5f8fb]', text: 'text-[#1c5d9c]', border: 'border-[#b8d5f2]', icon: Eye, label: 'Đang kiểm tra' },
    REVISING: { bg: 'bg-[#fff8eb]', text: 'text-[#9a6700]', border: 'border-[#fde0a3]', icon: RefreshCw, label: 'Đang hiệu chỉnh' },
    COMPLETED: { bg: 'bg-[#edf7f3]', text: 'text-[#2f6f5e]', border: 'border-[#bce2d3]', icon: CheckCircle2, label: 'Đã hoàn tất' }
  }[specialist.status] || {
    bg: 'bg-[#ebf3fb]',
    text: 'text-[#1c5d9c]',
    border: 'border-[#b8d5f2]',
    icon: Clock,
    label: specialist.statusLabel
  };

  const StatusIcon = statusConfig.icon;

  return (
    <div
      onClick={() => onOpenDetail(specialist)}
      className={`border rounded-xl p-5 bg-white shadow-surface flex flex-col justify-between space-y-4 cursor-pointer hover:border-slate-400 transition ${
        specialist.status === 'REVISING' ? 'border-[#fde0a3] bg-[#fffdfa]' : 'border-line'
      }`}
    >
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="grid place-items-center w-8 h-8 rounded-md bg-canvas border border-line shrink-0">
              {icon}
            </div>
            <div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <h3 className="text-xs font-bold text-ink">{specialist.name}</h3>
                {specialist.targetEntity && (
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#ebf3fb] text-[#1c5d9c]">
                    {specialist.targetEntity}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted line-clamp-1">{specialist.roleDescription}</p>
            </div>
          </div>

          <Badge
            variant="outline"
            className={`${statusConfig.bg} ${statusConfig.text} ${statusConfig.border} text-[10px] font-semibold gap-1 shrink-0 px-2`}
          >
            <StatusIcon className={`w-3 h-3 ${specialist.status === 'REVISING' ? 'animate-spin' : ''}`} />
            <span>{specialist.statusLabel}</span>
          </Badge>
        </div>

        {/* Assigned Task */}
        <div className="p-2.5 rounded-lg bg-canvas border border-line text-xs space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted block">
            Nhiệm vụ được giao
          </span>
          <p className="text-ink leading-relaxed line-clamp-2">{specialist.assignedTask}</p>
        </div>

        {/* Safe Observable Activity */}
        <div className="space-y-1 text-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted block">
            Hoạt động quan sát được
          </span>
          <p className="text-ink font-medium leading-relaxed flex items-start gap-1.5">
            <span className="text-[#1c5d9c] mt-0.5">•</span>
            <span>{specialist.currentActivityDescription}</span>
          </p>
        </div>

        {/* Targeted Revision Callout (if active) */}
        {specialist.revision && (
          <div className="p-2.5 rounded-lg bg-[#fff8eb] border border-[#fde0a3] text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-[#9a6700] flex items-center gap-1 text-[11px]">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Yêu cầu hiệu chỉnh (Vòng {specialist.revision.iteration}/{specialist.revision.maxIterations})</span>
              </span>
              <span className="text-[10px] text-[#9a6700] font-medium">Khoanh vùng</span>
            </div>
            <p className="text-muted text-[11px] leading-relaxed italic">
              “{specialist.revision.orchestratorFeedback}”
            </p>
            {specialist.revision.resolvedNote && (
              <p className="text-[#2f6f5e] text-[11px] font-medium pt-0.5">
                ✓ {specialist.revision.resolvedNote}
              </p>
            )}
          </div>
        )}

        {/* Findings Summary */}
        {specialist.findings.length > 0 && (
          <div className="pt-2 border-t border-line text-xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted block">
              Kết quả sơ bộ ({specialist.findings.length} nhận định có dẫn chứng)
            </span>
            <p className="text-ink text-[11px] line-clamp-2 leading-relaxed">
              {specialist.findings[0].title}
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="pt-3 border-t border-line flex items-center justify-between">
        <span className="text-[11px] text-muted">
          {specialist.observableActivities.length} hoạt động ghi nhận
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onOpenDetail(specialist);
          }}
          className="h-7 text-xs font-semibold text-[#1c5d9c] hover:text-[#154676] hover:bg-[#ebf3fb] px-2 gap-1"
        >
          <span>Chi tiết hoạt động</span>
          <Eye className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}
