import { Check, ChevronDown, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import type { FieldErrors, UseFormWatch } from 'react-hook-form';
import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import type { AnalysisFormValues } from '../schema';
import { cn } from '../../../shared/lib/cn';

interface TopicMetricSelectorProps {
  capabilities: AnalysisCapabilities;
  errors: FieldErrors<AnalysisFormValues>;
  watch: UseFormWatch<AnalysisFormValues>;
  selectedTopicIds: string[];
  onTopicToggle: (topicId: string) => void;
  onManualMetricToggle: (metricId: string) => void;
  onRestoreDefaults: () => void;
}

export function TopicMetricSelector({ capabilities, errors, watch, selectedTopicIds, onTopicToggle, onManualMetricToggle, onRestoreDefaults }: TopicMetricSelectorProps) {
  const [customOpen, setCustomOpen] = useState(false);
  const selectedMetrics = watch('metricIds') ?? [];

  return (
    <section className="surface-section" aria-labelledby="topic-heading">
      <div className="mb-3">
        <h2 id="topic-heading" className="section-title">Chủ đề phân tích <span className="text-blocked">*</span></h2>
        <p className="section-helper">Chọn chủ đề để hệ thống tự động áp dụng các chỉ tiêu mặc định.</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {capabilities.topics.map((topic) => {
          const selected = selectedTopicIds.includes(topic.id);
          const topicMetrics = capabilities.metrics.filter((metric) => topic.metricIds.includes(metric.id));
          return (
            <button
              key={topic.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onTopicToggle(topic.id)}
              className={cn('topic-option text-left', selected && 'topic-option-selected')}
            >
              <span className={cn('topic-radio', selected && 'topic-radio-selected')} aria-hidden="true"><span /></span>
              <span className="min-w-0">
                <span className="block font-semibold text-ink">{topic.label}</span>
                <span className="mt-2 flex flex-col gap-1 text-xs text-muted">
                  {topicMetrics.map((metric) => <span key={metric.id} className="flex items-start gap-1.5"><Check size={14} className={cn(selected ? 'text-[#1c5d9c]' : 'text-slate-400')} aria-hidden="true" /><span><strong className="text-ink">{metric.acronym}</strong> — {metric.label}</span></span>)}
                </span>
              </span>
            </button>
          );
        })}

        <button
          type="button"
          aria-expanded={customOpen}
          onClick={() => setCustomOpen((open) => !open)}
          className={cn('topic-option text-left', customOpen && 'topic-option-selected')}
        >
          <span className={cn('topic-radio', customOpen && 'topic-radio-selected')} aria-hidden="true"><span /></span>
          <span className="min-w-0 flex-1">
            <span className="flex items-center justify-between gap-2 font-semibold text-ink"><span>Tùy chỉnh chỉ tiêu</span><ChevronDown size={16} className={cn('transition-transform', customOpen && 'rotate-180')} aria-hidden="true" /></span>
            <span className="mt-2 block text-xs text-muted">Chọn và cấu hình chỉ tiêu theo nhu cầu phân tích riêng.</span>
          </span>
        </button>
      </div>

      {customOpen && (
        <div className="mt-4 border border-[#a8c5df] bg-[#f5f8fb] p-4" role="group" aria-label="Tùy chỉnh chỉ tiêu">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold text-ink">Chỉ tiêu được lưu trong yêu cầu phân tích</p>
            <button type="button" onClick={onRestoreDefaults} className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1c5d9c] underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1c5d9c]"><RotateCcw size={14} aria-hidden="true" /> Khôi phục mặc định</button>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {capabilities.metrics.map((metric) => (
              <label key={metric.id} htmlFor={`metric-${metric.id}`} className="check-option bg-white">
                <input id={`metric-${metric.id}`} type="checkbox" checked={selectedMetrics.includes(metric.id)} onChange={() => onManualMetricToggle(metric.id)} />
                <span><strong>{metric.acronym}</strong> — {metric.label}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {errors.metricIds && <p className="field-error">{errors.metricIds.message}</p>}
    </section>
  );
}
