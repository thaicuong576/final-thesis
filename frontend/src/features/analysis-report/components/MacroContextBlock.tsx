import { Landmark, TrendingUp, Percent, FileText } from 'lucide-react';
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
              {macroContext.sbv_policy_rate.toFixed(1)}%
            </span>
            <span className="text-[11px] text-ink-tertiary font-mono">Tái cấp vốn</span>
          </div>
          <p className="text-[11px] text-ink-secondary">
            Mặt bằng lãi suất duy trì ổn định hỗ trợ giảm chi phí vốn cho hệ thống NHTM.
          </p>
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
            <span className="font-mono text-2xl font-bold tracking-tight text-[#1b4332]">
              {macroContext.system_credit_growth.toFixed(2)}%
            </span>
            <span className="text-[11px] text-ink-tertiary font-mono">Cả năm 2024</span>
          </div>
          <p className="text-[11px] text-ink-secondary">
            Đạt và vượt mục tiêu định hướng 15% của NHNN trong điều kiện thanh khoản dồi dào.
          </p>
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
