import { useRef, useEffect, useCallback, useState, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowRight, Building2, Calendar } from 'lucide-react';
import type { ParsedScope } from '../model/types';
import type { Entity, Metric, Period } from '@/entities/capability/model/types';
import { formatPeriodsSignature } from '../model/intentParser';

export interface HeroComposerProps {
  question?: string;
  initialQuestion?: string;
  onQuestionChange?: (question: string) => void;
  onSubmit: (question: string) => void;
  parsedScope?: ParsedScope | null;
  availableEntities?: Entity[];
  availablePeriods?: Period[];
  availableMetrics?: Metric[];
  onOpenScopeAdjustment?: () => void;
  isSubmitting?: boolean;
}

export function HeroComposer({
  question: controlledQuestion,
  initialQuestion = '',
  onQuestionChange,
  onSubmit,
  parsedScope,
  availableEntities = [],
  availablePeriods = [],
  availableMetrics = [],
  onOpenScopeAdjustment,
  isSubmitting = false
}: HeroComposerProps) {
  const isControlled = controlledQuestion !== undefined;
  const [internalQuestion, setInternalQuestion] = useState(initialQuestion);
  const question = isControlled ? controlledQuestion : internalQuestion;
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const latestPeriod = [...availablePeriods].sort((left, right) => right.year - left.year || right.quarter - left.quarter)[0];
  const examplePeriod = latestPeriod
    ? `tại Q${latestPeriod.quarter}/${latestPeriod.year}`
    : '';
  const firstMetric = availableMetrics[0]?.acronym;

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(120, el.scrollHeight)}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [question, adjustHeight]);

  function handleSubmit() {
    const val = textareaRef.current?.value || question;
    const trimmed = val.trim();
    if (!trimmed || isSubmitting) return;
    onSubmit(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    if (!isControlled) {
      setInternalQuestion(val);
    }
    onQuestionChange?.(val);
  }

  function handleQuickBankClick(ticker: string) {
    let next: string;
    if (!question.trim()) {
      next = `Phân tích ${ticker}`;
    } else if (question.includes(ticker)) {
      return;
    } else {
      next = `${question.trim().replace(/[.,;]$/, '')} và ${ticker}.`;
    }
    if (!isControlled) {
      setInternalQuestion(next);
    }
    onQuestionChange?.(next);
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  }

  function handleQuickPeriodClick(period: Period) {
    const periodCode = `Q${period.quarter}/${period.year}`;
    let next: string;
    if (!question.trim()) {
      next = `Phân tích tại ${periodCode}`;
    } else {
      const clean = question.trim().replace(/[.,;]$/, '');
      const yearPattern = new RegExp(`trong\\s+năm\\s+${period.year}|năm\\s+${period.year}`, 'i');
      const quarterPattern = /tại\s+Q[1-4]\/\d{4}|Q[1-4]\/\d{4}|\b\d{4}_Q[1-4]\b/i;
      if (yearPattern.test(clean)) {
        next = `${clean.replace(yearPattern, `tại ${periodCode}`)}.`;
      } else if (quarterPattern.test(clean)) {
        next = `${clean.replace(quarterPattern, periodCode)}.`;
      } else {
        next = `${clean} tại ${periodCode}.`;
      }
    }
    if (!isControlled) {
      setInternalQuestion(next);
    }
    onQuestionChange?.(next);
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  }

  const isValid = question.trim().length > 0;

  // Extract chips for "Đã nhận diện"
  const entityChips = parsedScope
    ? parsedScope.entities.length > 0
      ? parsedScope.entities.map((e) => e.ticker)
      : parsedScope.referenceUniverseLabel
      ? [parsedScope.referenceUniverseLabel]
      : []
    : [];

  const timeframeChip = parsedScope ? formatPeriodsSignature(parsedScope.periods) : '';

  const topicChips = parsedScope
    ? parsedScope.topicLabels.length > 0
      ? parsedScope.topicLabels
      : parsedScope.metrics.length > 0
      ? parsedScope.metrics.map((m) => m.acronym)
      : []
    : [];

  const hasParsedFeedback =
    isValid &&
    parsedScope &&
    (entityChips.length > 0 || timeframeChip || topicChips.length > 0);

  return (
    <div className="space-y-3">
      {/* Editorial Hero Header */}
      <div className="space-y-1">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-ink">
          Bạn muốn phân tích điều gì?
        </h1>
        <p className="text-xs sm:text-sm text-ink-secondary leading-relaxed">
          Mô tả câu hỏi, đối tượng hoặc vấn đề bạn muốn kiểm tra trên hệ thống ngân hàng niêm yết.
        </p>
      </div>

      {/* Quick Bank Interactive Selector Chips */}
      {availableEntities.length > 0 && <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className="text-[11px] font-mono text-ink-secondary flex items-center gap-1 mr-0.5">
          <Building2 className="w-3 h-3 text-ink-secondary" aria-hidden="true" />
          <span>Gợi ý ngân hàng trong catalog:</span>
        </span>
        {availableEntities.slice(0, 5).map((entity) => {
          const ticker = entity.ticker;
          const isSelected = parsedScope?.entities.some((e) => e.ticker === ticker) || question.includes(ticker);
          return (
            <button
              key={ticker}
              type="button"
              onClick={() => handleQuickBankClick(ticker)}
              className={`px-2 py-0.5 text-xs font-mono font-semibold rounded transition-all cursor-pointer ${
                isSelected
                  ? 'bg-amber text-ink border border-amber-border font-bold'
                  : 'bg-card text-ink-secondary hover:text-ink hover:bg-surface-hover border border-line'
              }`}
            >
              {isSelected ? `✓ ${ticker}` : `+ ${ticker}`}
            </button>
          );
        })}
      </div>}

      {/* Quick Period Interactive Selector Chips */}
      {availablePeriods.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[11px] font-mono text-ink-secondary flex items-center gap-1 mr-0.5">
            <Calendar className="w-3 h-3 text-ink-secondary" aria-hidden="true" />
            <span>Kỳ quý trong snapshot:</span>
          </span>
          {availablePeriods.map((period) => {
            const periodLabel = `Q${period.quarter}/${period.year}`;
            const isSelected = parsedScope?.periods.some((p) => p.id === period.id);
            return (
              <button
                key={period.id}
                type="button"
                onClick={() => handleQuickPeriodClick(period)}
                className={`px-2 py-0.5 text-xs font-mono font-semibold rounded transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-amber text-ink border border-amber-border font-bold'
                    : 'bg-card text-ink-secondary hover:text-ink hover:bg-surface-hover border border-line'
                }`}
                title={`Kỳ snapshot: ${period.id}`}
              >
                {isSelected ? `✓ ${periodLabel}` : `+ ${periodLabel}`}
              </button>
            );
          })}
          <span className="text-[10px] text-ink-tertiary font-mono">
            (Snapshot chỉ hỗ trợ kỳ quý, không hỗ trợ cả năm)
          </span>
        </div>
      )}

      {/* Hero Composer Box */}
      <div className="border border-line bg-card rounded-md p-4 space-y-3 transition-colors focus-within:border-amber-border focus-within:ring-1 focus-within:ring-amber-border shadow-none">
        <label htmlFor="analysis-hero-composer" className="sr-only">
          Câu hỏi phân tích
        </label>
        <textarea
          id="analysis-hero-composer"
          ref={textareaRef}
          value={question}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          maxLength={500}
          placeholder={availableEntities.length > 0
            ? firstMetric && examplePeriod
              ? `Nêu rõ ngân hàng, một chỉ tiêu và kỳ dữ liệu; ví dụ: Phân tích ${firstMetric} của ${availableEntities[0].ticker} ${examplePeriod} (hoặc ${latestPeriod?.year}_Q${latestPeriod?.quarter}).`
              : 'Nêu rõ mã ngân hàng, một chỉ tiêu được hỗ trợ và quý cần phân tích (ví dụ: Q4/2024).'
            : 'Nêu rõ mã ngân hàng, một chỉ tiêu được hỗ trợ và quý cần phân tích (ví dụ: Q4/2024).'}
          className="w-full min-h-[120px] border-0 p-0 text-sm text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-0 resize-none leading-relaxed bg-transparent"
        />

        {/* Composer Footer */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-line">
          {/* Microcopy shortcut on the left */}
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-ink-secondary">
            <span>Nhấn</span>
            <kbd className="rounded border border-line bg-surface-secondary px-1.5 py-0.5 text-[10px] font-mono text-ink">
              Ctrl+Enter
            </kbd>
            <span>để chạy</span>
          </div>

          {/* High-contrast Primary CTA button on the right */}
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || isSubmitting}
            className={`h-9 px-4 text-xs font-bold gap-2 self-end sm:self-auto transition-all ${
              isValid && !isSubmitting
                ? 'bg-amber text-ink hover:bg-amber-hover border border-amber-border shadow-tactile cursor-pointer'
                : 'bg-surface-tertiary text-ink-tertiary border border-border-subtle cursor-not-allowed opacity-50 shadow-none'
            }`}
          >
            <span>Bắt đầu phân tích</span>
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Parsed Scope Feedback (Đã nhận diện) */}
      {hasParsedFeedback && (
        <div className="flex flex-wrap items-center justify-between gap-2.5 p-2.5 sm:p-3 rounded-md bg-surface-secondary/70 border border-border-subtle text-xs transition-all animate-in fade-in-50 duration-200">
          <div className="flex flex-wrap items-center gap-1.5 min-w-0">
            <span className="font-semibold text-ink-secondary text-xs mr-1">
              Đã nhận diện:
            </span>

            {/* Entities */}
            {entityChips.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center px-2 py-0.5 rounded bg-card border border-border text-ink font-mono font-semibold text-xs"
              >
                {ticker}
              </span>
            ))}

            {/* Timeframe */}
            {timeframeChip && (
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-card border border-border text-ink font-mono font-medium text-xs">
                {timeframeChip}
              </span>
            )}

            {/* Topic / Metric */}
            {topicChips.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center px-2 py-0.5 rounded bg-card border border-border text-ink font-medium text-xs"
              >
                {topic}
              </span>
            ))}
          </div>

          {onOpenScopeAdjustment && (
            <button
              type="button"
              onClick={onOpenScopeAdjustment}
              className="text-xs font-semibold text-amber-border hover:text-amber-active underline underline-offset-2 shrink-0 transition-colors ml-auto sm:ml-0"
            >
              Chỉnh phạm vi
            </button>
          )}
        </div>
      )}
    </div>
  );
}
