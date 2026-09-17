import { User } from 'lucide-react';

interface UserQuestionEntryProps {
  question: string;
}

export function UserQuestionEntry({ question }: UserQuestionEntryProps) {
  return (
    <div className="flex gap-3.5 items-start">
      <div className="w-8 h-8 rounded-full bg-[#f1f5f9] border border-line flex items-center justify-center shrink-0 mt-0.5 text-muted">
        <User className="w-4 h-4 text-ink" aria-hidden="true" />
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-ink">Chuyên viên phân tích</span>
          <span className="text-[11px] text-muted">Câu hỏi phân tích</span>
        </div>

        <div className="bg-[#fafafa] border border-line rounded-lg p-3.5 text-sm text-ink font-medium leading-relaxed">
          {question}
        </div>
      </div>
    </div>
  );
}
