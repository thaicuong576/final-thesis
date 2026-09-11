import { ChevronRight, Database, ExternalLink } from 'lucide-react';
import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import { cn } from '../../../shared/lib/cn';
import { formatGoldVersion, formatPeriodCollection } from '../../../shared/lib/formatting';

interface CapabilitySummaryBarProps {
  capabilities: AnalysisCapabilities;
  onOpenDetails: () => void;
}

const macroLabel: Record<AnalysisCapabilities['macro']['status'], string> = {
  AVAILABLE: 'KHẢ DỤNG',
  LIMITED: 'HẠN CHẾ',
  UNAVAILABLE: 'KHÔNG KHẢ DỤNG'
};

export function CapabilitySummaryBar({ capabilities, onOpenDetails }: CapabilitySummaryBarProps) {
  const { status } = capabilities.macro;
  const periodLabel = formatPeriodCollection(capabilities.periods);

  return (
    <section className="border border-line bg-white px-4 py-3 shadow-surface" aria-label="Tóm tắt năng lực dữ liệu">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-ink">
        <Database size={16} strokeWidth={1.8} className="text-slate-500" aria-hidden="true" />
        <span className="font-semibold">{capabilities.entities.length} ngân hàng</span>
        <span className="text-slate-300" aria-hidden="true">·</span>
        <span>{periodLabel}</span>
        <span className="text-slate-300" aria-hidden="true">·</span>
        <span>{capabilities.metrics.length} chỉ tiêu</span>
        <span className="text-slate-300" aria-hidden="true">·</span>
        <span>Macro:</span>
        <span className={cn('inline-flex items-center gap-1.5 font-semibold', {
          'text-ready': status === 'AVAILABLE',
          'text-warning': status === 'LIMITED',
          'text-blocked': status === 'UNAVAILABLE'
        })}>
          <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
          {macroLabel[status]}
        </span>
        <span className="hidden h-5 w-px bg-line sm:block" aria-hidden="true" />
        <span className="text-muted">Phiên bản dữ liệu: <strong className="font-semibold text-ink">{formatGoldVersion(capabilities.goldVersion)}</strong></span>
        <button
          type="button"
          onClick={onOpenDetails}
          className="ml-auto inline-flex items-center gap-1 font-semibold text-[#1c5d9c] underline decoration-[#a8c5df] underline-offset-4 transition hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1c5d9c] focus-visible:ring-offset-2"
        >
          Xem chi tiết phạm vi dữ liệu
          <ChevronRight size={15} aria-hidden="true" />
          <ExternalLink size={13} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
