import React from 'react';
import { useEquityReport } from './useEquityReport';
import { fmtPeriod, fmtPeriodRange } from '@/shared/lib/formatting';
import type { QuestionType } from '../model/types';

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  lookup: 'Tra cứu nhanh · Ngân hàng',
  company_profile: 'Ghi chú doanh nghiệp · Ngân hàng',
  ranking: 'Ghi chú sàng lọc · Ngân hàng',
  trend: 'Ghi chú xu hướng · Ngân hàng',
  head_to_head: 'Ghi chú so sánh · Ngân hàng',
  sector_theme: 'Ghi chú toàn ngành · Ngân hàng',
  relationship: 'Ghi chú quan hệ · Ngân hàng'
};

export const ReportMasthead: React.FC = () => {
  const { report, facts, datasets, highlight } = useEquityReport();
  const qType = (report.question_type || 'lookup') as QuestionType;

  const noteLabel =
    report.report_spec?.note_label ||
    QUESTION_TYPE_LABELS[qType] ||
    'Báo cáo phân tích';

  // Format date
  const rawDate = (report as { created_at?: string }).created_at;
  const dateStr = (() => {
    if (!rawDate) return '—';
    try {
      const d = new Date(rawDate);
      if (isNaN(d.getTime())) return '—';
      return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short' }).format(d);
    } catch {
      return '—';
    }
  })();

  // Period label: answer_card displays anchor period (e.g. "Quý 4/2024"), not period range
  const periodLabel = (() => {
    if (report.report_spec?.kind === 'answer_card') {
      const answerBlock = report.report_spec.blocks?.find((b) => b.type === 'answer');
      const targetFact = answerBlock && 'value_fact_id' in answerBlock
        ? facts.find((f) => f.fact_id === answerBlock.value_fact_id)
        : facts.find((f) => f.fact_type === 'value');
      const anchorPeriod = targetFact?.period || (report as { period?: string }).period || '2024_Q4';
      return fmtPeriod(anchorPeriod);
    }
    const allPeriods: string[] = datasets.flatMap((d) => d.periods || []);
    const uniquePeriods: string[] = Array.from(new Set(allPeriods));
    const fallbackPeriod = String((report as { period?: string }).period || '2024_Q4');
    return uniquePeriods.length > 1
      ? fmtPeriodRange(uniquePeriods)
      : fmtPeriod(uniquePeriods[0] || fallbackPeriod);
  })();

  // Badges: ranking has NO entity badge; head_to_head has 2-3 badges; others show focus entities
  const showBadges = qType !== 'ranking' && highlight.length > 0;

  return (
    <header className="border-t-2 border-text-primary pt-2 mb-4 font-sans">
      <div className="flex justify-between items-baseline text-xs text-text-secondary">
        <span className="font-medium text-text-primary">{noteLabel}</span>
        <span className="text-text-muted font-mono">{dateStr}</span>
      </div>

      <div className="flex items-center gap-2.5 mt-3">
        {showBadges && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {highlight.map((code: string) => (
              <span
                key={code}
                className="text-xs font-semibold px-2 py-0.5 border border-border-strong rounded font-mono text-text-primary bg-surface-primary"
              >
                {code}
              </span>
            ))}
          </div>
        )}
        {periodLabel && (
          <span className="text-xs text-text-muted font-medium">
            {periodLabel}
          </span>
        )}
        {report.status === 'accepted_with_limitations' && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200/80">
            <span className="size-1.5 rounded-full bg-amber-500" aria-hidden="true" />
            Chấp nhận có giới hạn
          </span>
        )}
        {(report.status === 'completed' || report.status === 'accepted') && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200/80">
            <span className="size-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            Đã kiểm định
          </span>
        )}
      </div>
    </header>
  );
};
