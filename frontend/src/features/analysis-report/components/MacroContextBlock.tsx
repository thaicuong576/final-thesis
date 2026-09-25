import { Landmark, TrendingUp, Percent, FileText } from 'lucide-react';
import { formatMetric } from '@/shared/lib/formatting';
import type { MacroContext } from '../model/types';

interface MacroContextBlockProps {
  macroContext?: MacroContext | null;
}

export function MacroContextBlock({ macroContext }: MacroContextBlockProps) {
  if (!macroContext) {
    return null;
  }

  return (
    <section className="border border-line bg-card rounded-lg p-5 space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Landmark className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-sm font-bold tracking-tight text-ink">
            Bối cảnh chính sách tiền tệ
          </h2>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-ink-secondary font-mono">
          <FileText className="size-3 text-ink-tertiary" aria-hidden="true" />
          <span className="truncate max-w-xs">{macroContext.source}</span>
        </div>
      </div>

      {/* Primary Macro Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {/* SBV Policy Rate */}
        <div className="border border-line rounded-md bg-surface-secondary p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-secondary">
              Lãi suất điều hành NHNN
            </span>
            <Percent className="size-3.5 text-ink-tertiary" aria-hidden="true" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold tracking-tight text-ink">
              {formatMetric(macroContext.sbv_policy_rate, 1)}
            </span>
          </div>
          <p className="text-[11px] text-ink-tertiary">Giá trị do API trả về; xem nguồn ở đầu mục.</p>
        </div>

        {/* System Credit Growth */}
        <div className="border border-line rounded-md bg-surface-secondary p-3.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-secondary">
              Tăng trưởng tín dụng hệ thống
            </span>
            <TrendingUp className="size-3.5 text-[#2d6a4f]" aria-hidden="true" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold tracking-tight text-ink">
              {formatMetric(macroContext.system_credit_growth, 2)}
            </span>
          </div>
          <p className="text-[11px] text-ink-tertiary">Giá trị do API trả về; kỳ được nêu nếu có trong báo cáo.</p>
        </div>

        {/* Policy Transmission Narrative */}
        <div className="border border-line rounded-md bg-surface-secondary p-3.5 space-y-1 sm:col-span-2 lg:col-span-1">
          <span className="text-xs font-medium text-ink-secondary">
            Định hướng điều hành tiền tệ
          </span>
          <p className="text-xs text-ink leading-relaxed pt-1">
            {macroContext.interest_rate_trend}
          </p>
        </div>
      </div>
    </section>
  );
}
