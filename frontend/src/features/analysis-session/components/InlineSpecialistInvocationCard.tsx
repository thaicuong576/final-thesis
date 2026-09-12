import { Building2, Users, Globe, RefreshCw, CheckCircle2, ChevronRight, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { SpecialistSessionState, SpecialistStatus } from '../model/types';

interface InlineSpecialistInvocationCardProps {
  session: SpecialistSessionState;
  onClick: () => void;
}

export function InlineSpecialistInvocationCard({
  session,
  onClick
}: InlineSpecialistInvocationCardProps) {
  const getSpecialistIcon = () => {
    switch (session.specialistId) {
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
        return (
          <Badge
            variant="outline"
            className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-2 py-0.5 text-[11px] font-semibold"
          >
            <CheckCircle2 className="w-3 h-3 text-[#2f6f5e]" aria-hidden="true" />
            {label}
          </Badge>
        );
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
          <Badge variant="outline" className="bg-canvas text-muted border-line text-[11px] gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-muted" aria-hidden="true" />
            {label}
          </Badge>
        );
    }
  };

  return (
    <div className="ml-11">
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
        aria-label={`Xem chi tiết phiên ${session.label}`}
        className="group text-left border border-line bg-white hover:border-[#94a3b8] rounded-lg p-3.5 transition-all duration-150 shadow-surface hover:shadow-md cursor-pointer flex flex-col justify-between focus:outline-none focus:ring-2 focus:ring-[#2f6f5e] focus:ring-offset-1 max-w-2xl"
      >
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-[#f1f5f9] flex items-center justify-center shrink-0">
                {getSpecialistIcon()}
              </div>
              <h3 className="text-xs font-semibold text-ink group-hover:text-[#2f6f5e] transition-colors">
                {session.label}
              </h3>
            </div>
            {getStatusBadge(session.status, session.statusLabel)}
          </div>

          <p className="text-xs text-muted leading-relaxed">
            {session.assignment}
          </p>
        </div>

        <div className="pt-2.5 mt-2.5 border-t border-line flex items-center justify-between text-xs text-muted">
          <div className="flex items-center gap-1.5 truncate">
            <FileText className="w-3.5 h-3.5 text-muted shrink-0" aria-hidden="true" />
            <span className="truncate font-medium text-ink text-[11px]">
              {session.observationSummary}
            </span>
          </div>

          <span className="flex items-center gap-1 text-[#2f6f5e] font-semibold text-[11px] group-hover:underline shrink-0 ml-2">
            Chi tiết
            <ChevronRight className="w-3 h-3" aria-hidden="true" />
          </span>
        </div>
      </div>
    </div>
  );
}
