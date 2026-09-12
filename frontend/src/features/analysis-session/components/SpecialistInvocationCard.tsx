import { Building2, Users, Globe, RefreshCw, CheckCircle2, ChevronRight, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { SpecialistInvocation, SpecialistStatus } from '../model/types';

interface SpecialistInvocationCardProps {
  invocation: SpecialistInvocation;
  onClick: () => void;
}

export function SpecialistInvocationCard({ invocation, onClick }: SpecialistInvocationCardProps) {
  const getSpecialistIcon = () => {
    switch (invocation.specialistId) {
      case 'company':
        return <Building2 className="w-4 h-4 text-ink" aria-hidden="true" />;
      case 'peer':
        return <Users className="w-4 h-4 text-ink" aria-hidden="true" />;
      case 'macro':
        return <Globe className="w-4 h-4 text-ink" aria-hidden="true" />;
    }
  };

  const getStatusBadge = (status: SpecialistStatus, label: string) => {
    switch (status) {
      case 'COMPLETED':
      case 'OUTPUT_CREATED':
        return (
          <Badge
            variant="outline"
            className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-2 py-0.5 text-[11px] font-semibold"
          >
            <CheckCircle2 className="w-3 h-3 text-[#2f6f5e]" aria-hidden="true" />
            {label}
          </Badge>
        );
      case 'REVISING':
        return (
          <Badge
            variant="outline"
            className="bg-[#fef9ee] text-[#b47d14] border-[#f5dfaa] gap-1 px-2 py-0.5 text-[11px] font-semibold"
          >
            <RefreshCw className="w-3 h-3 text-[#b47d14] animate-spin" aria-hidden="true" />
            {label}
          </Badge>
        );
      case 'ANALYZING':
      case 'REVIEWING':
        return (
          <Badge
            variant="outline"
            className="bg-[#f0f7ff] text-[#0066cc] border-[#b8daff] gap-1 px-2 py-0.5 text-[11px] font-semibold"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066cc] animate-pulse" aria-hidden="true" />
            {label}
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-canvas text-muted border-line text-[11px]">
            {label}
          </Badge>
        );
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`Xem chi tiết phiên ${invocation.label}`}
      className="group text-left border border-line bg-white hover:border-[#94a3b8] rounded-lg p-4 transition-all duration-150 shadow-surface hover:shadow-md cursor-pointer flex flex-col justify-between focus:outline-none focus:ring-2 focus:ring-[#2f6f5e] focus:ring-offset-1"
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-[#f1f5f9] flex items-center justify-center shrink-0">
              {getSpecialistIcon()}
            </div>
            <h3 className="text-sm font-semibold text-ink group-hover:text-[#2f6f5e] transition-colors">
              {invocation.label}
            </h3>
          </div>
          {getStatusBadge(invocation.status, invocation.statusLabel)}
        </div>

        <p className="text-xs text-muted leading-relaxed line-clamp-2">
          {invocation.assignment}
        </p>
      </div>

      <div className="pt-3 mt-3 border-t border-line flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-1.5 truncate">
          <FileText className="w-3.5 h-3.5 text-muted shrink-0" aria-hidden="true" />
          <span className="truncate font-medium text-ink">
            {invocation.observationSummary}
          </span>
        </div>

        <span className="flex items-center gap-1 text-[#2f6f5e] font-semibold text-[11px] group-hover:underline shrink-0 ml-2">
          Chi tiết
          <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
        </span>
      </div>
    </div>
  );
}
