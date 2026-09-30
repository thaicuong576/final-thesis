import React from 'react';
import { AlertCircle } from 'lucide-react';
import { useEquityReport } from './useEquityReport';
import { fmtPeriod, fmtPeriodRange } from '@/shared/lib/formatting';
import type { QuestionType } from '../model/types';

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  lookup: 'Tra cứu',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng nhóm',
  trend: 'Diễn biến xu hướng',
  head_to_head: 'So sánh trực tiếp',
  sector_theme: 'Phân tích toàn ngành',
  relationship: 'Tương quan chỉ tiêu'
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
    <header className="border-t-2 border-text-primary pt-3 mb-5 font-sans">
      <div className="flex justify-between items-baseline text-[13px] text-text-secondary">
        <span className="font-semibold text-text-primary">{noteLabel}</span>
        <span className="text-text-tertiary tabular-nums">{dateStr}</span>
      </div>

      <div className="flex items-center gap-2.5 mt-3">
        {showBadges && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {highlight.map((code: string) => (
              <span
                key={code}
                className="text-xs font-semibold px-2 py-0.5 border border-border-strong rounded font-mono tracking-wide text-text-primary bg-surface-primary"
              >
                {code}
              </span>
            ))}
          </div>
        )}
        {periodLabel && (
          <span className="text-[13px] text-text-secondary font-medium">
            {periodLabel}
          </span>
        )}
        {report.status === 'accepted_with_limitations' && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-warning-soft text-text-warning border border-warning/30">
            <span className="size-1.5 rounded-full bg-warning" aria-hidden="true" />
            Chấp nhận có giới hạn
          </span>
        )}
        {(report.status === 'completed' || report.status === 'accepted') && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-ready-soft text-text-success border border-ready/30">
            <span className="size-1.5 rounded-full bg-ready" aria-hidden="true" />
            Đã kiểm định
          </span>
        )}
      </div>

      {(() => {
        const rawLim = (report as { limitations?: unknown }).limitations;
        const limList: string[] = Array.isArray(rawLim) ? rawLim : [];
        const userUploadLimitation = limList.find(
          (lim) => typeof lim === 'string' && (lim.includes('do người dùng cung cấp') || lim.startsWith('Số liệu '))
        );
        if (!userUploadLimitation) return null;
        return (
          <div className="mt-3 flex items-start gap-2 rounded border border-amber-border/70 bg-amber-soft/40 p-2.5 text-xs text-ink">
            <AlertCircle className="size-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <span className="leading-relaxed">{userUploadLimitation}</span>
          </div>
        );
      })()}
    </header>
  );
};
