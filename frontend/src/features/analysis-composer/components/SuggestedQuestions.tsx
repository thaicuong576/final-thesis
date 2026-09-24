import { Sparkles } from 'lucide-react';
import type { AnalysisCapabilities } from '@/entities/capability/model/types';

export interface SuggestedQuestionsProps {
  capabilities: AnalysisCapabilities;
  onSelectPrompt: (promptText: string) => void;
}

export function SuggestedQuestions({ capabilities, onSelectPrompt }: SuggestedQuestionsProps) {
  const isCompanyAvailable =
    capabilities.analysis_available === true &&
    Boolean(capabilities.dataset_snapshot_id?.trim()) &&
    (capabilities.implemented_capabilities ?? []).includes('company') &&
    capabilities.entities.length > 0 &&
    capabilities.periods.length > 0 &&
    capabilities.metrics.length > 0;
  const target = capabilities.entities[0];
  const availableYears = [...new Set(capabilities.periods.map((period) => period.year))].sort((a, b) => b - a);
  const fullYear = availableYears.find((year) => {
    const quarters = new Set(capabilities.periods.filter((period) => period.year === year).map((period) => period.quarter));
    return [1, 2, 3, 4].every((quarter) => quarters.has(quarter));
  });
  const latestPeriod = [...capabilities.periods].sort((a, b) => b.year - a.year || b.quarter - a.quarter)[0];
  const periodPhrase = fullYear
    ? `trong năm ${fullYear}`
    : latestPeriod
    ? `tại Q${latestPeriod.quarter}/${latestPeriod.year}`
    : '';
  const suggestions = isCompanyAvailable && target && periodPhrase
    ? capabilities.metrics.slice(0, 3).map((metric) => ({
        title: `Phân tích ${metric.acronym} · ${target.ticker}`,
        prompt: `Phân tích ${metric.acronym} của ${target.ticker} ${periodPhrase}.`
      }))
    : [];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-ink-secondary flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-border" />
          <span>Gợi ý bắt đầu</span>
        </h3>
        <span className="text-[11px] text-ink-tertiary">Bấm để điền mẫu</span>
      </div>

      {suggestions.length > 0 ? <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {suggestions.map((item) => (
          <button
            key={item.title}
            type="button"
            onClick={() => onSelectPrompt(item.prompt)}
            className="text-left p-3 rounded-md bg-card hover:bg-surface-hover border border-border-subtle hover:border-border transition-colors group flex flex-col justify-between gap-1.5 shadow-none"
          >
            <div className="text-xs font-semibold text-ink group-hover:text-amber-border transition-colors line-clamp-1">
              {item.title}
            </div>
            <div className="text-[11px] text-ink-secondary line-clamp-2 leading-relaxed">
              {item.prompt}
            </div>
          </button>
        ))}
      </div> : (
        <p className="rounded-md border border-line bg-surface-secondary p-3 text-xs leading-relaxed text-ink-secondary" role="status">
          API chưa xác nhận snapshot doanh nghiệp khả dụng. Gợi ý phân tích sẽ xuất hiện khi API công bố phạm vi có thể chạy.
        </p>
      )}
    </div>
  );
}
