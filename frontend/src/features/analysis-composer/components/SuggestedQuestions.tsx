import { Sparkles } from 'lucide-react';

export interface SuggestedQuestionsProps {
  onSelectPrompt: (promptText: string) => void;
}

const DEFAULT_SUGGESTIONS = [
  {
    title: 'Chất lượng tài sản ACB, TCB, MBB',
    prompt: 'So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và xác định ngân hàng cải thiện rõ nhất.'
  },
  {
    title: 'Hiệu quả sử dụng vốn (ROE) ngành',
    prompt: 'Ngân hàng nào duy trì hiệu quả sử dụng vốn (ROE) dẫn đầu qua 4 quý 2024?'
  },
  {
    title: 'Tác động vĩ mô & nợ xấu',
    prompt: 'Đánh giá tác động của môi trường vĩ mô và tăng trưởng tín dụng lên tỷ lệ nợ xấu của ACB và TCB.'
  }
];

export function SuggestedQuestions({ onSelectPrompt }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-ink-secondary flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-border" />
          <span>Gợi ý bắt đầu</span>
        </h3>
        <span className="text-[11px] text-ink-tertiary">Bấm để điền mẫu</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {DEFAULT_SUGGESTIONS.map((item, idx) => (
          <button
            key={idx}
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
      </div>
    </div>
  );
}
