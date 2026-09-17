import { useState, useRef, type KeyboardEvent } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';

interface HeroComposerProps {
  initialQuestion?: string;
  onSubmit: (question: string) => void;
  isSubmitting?: boolean;
}

export function HeroComposer({
  initialQuestion = '',
  onSubmit,
  isSubmitting = false
}: HeroComposerProps) {
  const [question, setQuestion] = useState(initialQuestion);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit() {
    const trimmed = question.trim();
    if (!trimmed || isSubmitting) return;
    onSubmit(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }

  const isValid = question.trim().length > 0;

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
            Bàn làm việc phân tích
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-ink-secondary border border-border">
            TỰ ĐỘNG BÓC TÁCH PHẠM VI
          </span>
        </div>
        <h1 className="text-lg font-bold tracking-tight text-ink">
          Bạn muốn phân tích điều gì?
        </h1>
        <p className="text-xs text-ink-secondary leading-relaxed">
          Nhập câu hỏi phân tích bằng ngôn ngữ tự nhiên. Hệ thống phân tích đa tác tử sẽ tự động trích xuất phạm vi và lập luận dựa trên bằng chứng.
        </p>
      </div>

      <div className="border border-line bg-card rounded-md p-4 space-y-3 transition-colors focus-within:border-border-focus focus-within:ring-1 focus-within:ring-border-focus">
        <label htmlFor="analysis-hero-composer" className="sr-only">
          Câu hỏi phân tích
        </label>
        <Textarea
          id="analysis-hero-composer"
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          maxLength={500}
          placeholder="So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và xác định ngân hàng cải thiện rõ nhất."
          className="border-0 p-0 text-sm text-ink placeholder:text-ink-tertiary focus-visible:ring-0 resize-none shadow-none leading-relaxed bg-transparent"
        />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-line">
          <div className="text-[11px] text-ink-secondary flex items-center gap-1.5 font-mono">
            <span aria-hidden="true">💡</span>
            <span>Tự động phân tách thực thể & chỉ tiêu từ câu hỏi</span>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-ink-secondary">
              <span>Nhấn</span>
              <kbd className="rounded border border-line bg-surface-secondary px-1.5 py-0.5 text-[10px] font-mono text-ink">
                ⌘ / Ctrl + ↵
              </kbd>
            </span>

            <Button
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || isSubmitting}
              className="h-9 px-4 text-xs font-semibold gap-1.5"
            >
              <span>Bắt đầu phân tích</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
