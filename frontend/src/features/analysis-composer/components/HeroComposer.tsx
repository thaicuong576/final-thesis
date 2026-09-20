import { useRef, useEffect, useCallback, useState, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';
import type { ParsedScope } from '../model/types';
import { formatPeriodsSignature } from '../model/intentParser';

export interface HeroComposerProps {
  question?: string;
  initialQuestion?: string;
  onQuestionChange?: (question: string) => void;
  onSubmit: (question: string) => void;
  parsedScope?: ParsedScope | null;
  onOpenScopeAdjustment?: () => void;
  isSubmitting?: boolean;
}

export function HeroComposer({
  question: controlledQuestion,
  initialQuestion = '',
  onQuestionChange,
  onSubmit,
  parsedScope,
  onOpenScopeAdjustment,
  isSubmitting = false
}: HeroComposerProps) {
  const [question, setQuestion] = useState(
    controlledQuestion !== undefined ? controlledQuestion : initialQuestion
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (controlledQuestion !== undefined) {
      setQuestion(controlledQuestion);
    }
  }, [controlledQuestion]);

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
    setQuestion(val);
    onQuestionChange?.(val);
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
          Mô tả câu hỏi, đối tượng hoặc vấn đề bạn muốn kiểm tra.
        </p>
      </div>

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
          placeholder="So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và xác định ngân hàng cải thiện rõ nhất."
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
