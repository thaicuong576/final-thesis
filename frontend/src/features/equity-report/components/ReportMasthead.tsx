import React from 'react';
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

  const statusLabel =
    report.status === 'accepted_with_limitations'
      ? 'Chấp nhận có giới hạn'
      : report.status === 'completed' || report.status === 'accepted'
        ? 'Đã kiểm định'
        : null;

  return (
    <header className="-mx-5 -mt-6 mb-6 bg-ink px-5 py-3.5 font-sans text-[#efe9dd] sm:-mx-10 sm:-mt-9 sm:px-10">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-[13px]">
        <div className="flex min-w-0 flex-wrap items-center gap-2.5">
          <span className="font-semibold uppercase text-white">{noteLabel}</span>
          {showBadges &&
            highlight.map((code: string) => (
              <span key={code} className="rounded bg-amber px-1.5 py-px font-mono text-xs font-semibold text-ink">
                {code}
              </span>
            ))}
          {periodLabel && <span>{periodLabel}</span>}
        </div>
        <div className="flex items-center gap-3">
          {statusLabel && (
            <span className="inline-flex items-center gap-1.5 text-xs">
              <span
                className={`size-1.5 rounded-full ${report.status === 'accepted_with_limitations' ? 'bg-amber' : 'bg-[#4cc38a]'}`}
                aria-hidden="true"
              />
              {statusLabel}
            </span>
          )}
          <span className="tabular-nums text-[#b3ada0]">{dateStr}</span>
        </div>
      </div>
    </header>
  );
};
