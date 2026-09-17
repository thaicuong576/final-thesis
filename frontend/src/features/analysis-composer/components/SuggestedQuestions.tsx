interface SuggestedQuestionsProps {
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
    <div className="border border-line bg-white rounded-lg p-4 space-y-3 shadow-surface">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          Gợi ý câu hỏi phân tích
        </h3>
        <span className="text-[11px] text-muted">Bấm để điền mẫu</span>
      </div>

      <div className="space-y-2">
        {DEFAULT_SUGGESTIONS.map((item, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectPrompt(item.prompt)}
            className="w-full text-left p-3 rounded-md bg-[#f7f6f2] hover:bg-[#e9eef2] hover:border-[#8eb6da] border border-transparent transition text-xs text-ink group"
          >
            <div className="font-semibold text-ink group-hover:text-[#1c5d9c] transition-colors mb-0.5">
              • {item.title}
            </div>
            <div className="text-[11px] text-muted line-clamp-2">
              {item.prompt}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
